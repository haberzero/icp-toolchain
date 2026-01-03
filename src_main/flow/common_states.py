from typing import Dict, Optional

from flow.flow_context import FlowContext
from flow.flow_engine import FlowState
from libs.text_funcs import ChatResponseCleaner
from typedef.cmd_data_types import Colors


class LLMGenerateState(FlowState):
    """
    Generic LLM Generation State.
    Handles mapping preparation, prompt building, API call, and result cleaning.
    """
    def __init__(self, name: str, role_name: str, sys_template_key: str, user_template_key: str, 
                 next_state: str, retry_state: str = None):
        super().__init__(name)
        self.role_name = role_name
        self.sys_template_key = sys_template_key
        self.user_template_key = user_template_key
        self.next_state = next_state
        self.retry_state = retry_state or "__END__"

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [AI Generation] Calling role {self.role_name}...")
        
        # 1. Prepare Mapping
        mapping = self.prepare_mapping(ctx)
        
        # 2. Build Prompts
        # Use specific store access
        if " " in self.sys_template_key or len(self.sys_template_key) > 50:
             # Treat as content if it looks like a prompt
            sys_prompt = self.sys_template_key
        else:
            sys_prompt = ctx.toolchain.get_sys_prompt(self.sys_template_key)
            
        user_prompt = ctx.toolchain.build_user_prompt(
            self.user_template_key, mapping
        )
        
        # 3. Record Context (for retry and debugging)
        ctx.last_sys_prompt = sys_prompt
        ctx.last_user_prompt = user_prompt
        
        # Save base prompts if this is the first attempt
        if not ctx.base_user_prompt:
            ctx.base_user_prompt = user_prompt
            ctx.base_sys_prompt = sys_prompt
        
        # 4. Call API
        response, success = await ctx.chat_handler.get_role_response(
            role_name=self.role_name,
            sys_prompt=sys_prompt,
            user_prompt=user_prompt
        )
        
        if not success:
            print(f"    {Colors.WARNING}AI call failed{Colors.ENDC}")
            return self.retry_state
            
        # 5. Clean Result and Store
        cleaned_content = ChatResponseCleaner.clean_code_block_markers(response)
        ctx.last_generated_content = cleaned_content
        
        return self.next_state

    def prepare_mapping(self, ctx: FlowContext) -> Dict[str, str]:
        """Subclasses should override this to inject specific variables."""
        return {}


class ValidationState(FlowState):
    """
    Generic Validation State.
    Executes validation logic and routes based on result.
    """
    def __init__(self, name: str, success_state: str, fail_state: str, max_retry_fail_state: str):
        super().__init__(name)
        self.success_state = success_state
        self.fail_state = fail_state
        self.max_retry_fail_state = max_retry_fail_state

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [Validation] Checking result (Attempt {ctx.current_attempt + 1}/{ctx.max_attempts})...")
        
        # Clear previous issues
        ctx.issue_recorder.clear()
            
        is_valid = self.validate(ctx)
        
        if is_valid:
            print(f"    {Colors.OKGREEN}Validation Passed{Colors.ENDC}")
            return self.success_state
        else:
            issue_count = ctx.issue_recorder.get_issue_count()
            print(f"    {Colors.WARNING}Validation Failed, {issue_count} issues found{Colors.ENDC}")
            
            ctx.current_attempt += 1
            if ctx.current_attempt >= ctx.max_attempts:
                print(f"    {Colors.FAIL}Max retries reached, abandoning file.{Colors.ENDC}")
                return self.max_retry_fail_state
            else:
                return self.fail_state

    def validate(self, ctx: FlowContext) -> bool:
        """Subclasses must implement validation logic."""
        return True


class AnalysisAndFixState(FlowState):
    """
    Diagnosis and Fix Preparation State.
    Analyzes issues using AI and generates a fix suggestion.
    """
    def __init__(self, name: str, next_state: str):
        super().__init__(name)
        self.next_state = next_state

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [Diagnosis] Analyzing failure and generating fix suggestion...")
        
        # 1. Construct Diagnosis Prompt
        issues_text = ctx.get_issues_formatted()
        
        analysis_mapping = {
            "PREVIOUS_SYS_PROMPT_PLACEHOLDER": ctx.last_sys_prompt or "(None)",
            "PREVIOUS_USER_PROMPT_PLACEHOLDER": ctx.last_user_prompt or "(None)",
            "PREVIOUS_CONTENT_PLACEHOLDER": ctx.last_generated_content or "(No Output)",
            "ISSUES_LIST_PLACEHOLDER": issues_text or "(No Issues Detected)"
        }
        
        analysis_sys_prompt = ctx.toolchain.get_sys_prompt("retry_analysis_sys_prompt")
        # Fallback if template is missing
        if not analysis_sys_prompt:
             analysis_sys_prompt = "You are a code diagnosis expert. Analyze the provided code and error report."

        analysis_user_prompt = ctx.toolchain.build_user_prompt(
            "retry_analysis_prompt_template", analysis_mapping
        )
        if not analysis_user_prompt:
             # Fallback
             analysis_user_prompt = f"Code:\n{ctx.last_generated_content}\n\nIssues:\n{issues_text}\n\nPlease analyze why the code failed and provide a fix suggestion."
        
        # 2. Call AI for Fix Suggestion
        fix_suggestion_raw, success = await ctx.chat_handler.get_role_response(
            role_name="5_depend_analyzer", 
            sys_prompt=analysis_sys_prompt,
            user_prompt=analysis_user_prompt
        )
        
        if success:
            ctx.fix_suggestion = fix_suggestion_raw
            print(f"    [Diagnosis] Fix suggestion received: {fix_suggestion_raw[:50]}...")
        else:
            print(f"    {Colors.WARNING}[Diagnosis] Failed to get suggestion, using generic instruction.{Colors.ENDC}")
            ctx.fix_suggestion = "Please fix the code based on the issue list."
            
        return self.next_state


class LLMRetryExecutionState(FlowState):
    """
    Retry Execution State.
    Re-generates content based on fix suggestions.
    """
    def __init__(self, name: str, role_name: str, next_state: str, code_block_type: str = ""):
        super().__init__(name)
        self.role_name = role_name
        self.next_state = next_state
        self.code_block_type = code_block_type

    async def execute(self, ctx: FlowContext) -> str:
        print(f"    [Retry Execution] Regenerating based on fix suggestion...")
        
        # 1. Build Retry Prompt
        issues_text = ctx.get_issues_formatted()
        formatted_content = f"```{self.code_block_type}\n{ctx.last_generated_content}\n```"
        
        retry_mapping = {
            "PREVIOUS_CONTENT_PLACEHOLDER": formatted_content,
            "ISSUES_LIST_PLACEHOLDER": issues_text
        }
        
        # Try to use a dedicated retry template
        retry_user_prompt = ctx.toolchain.build_user_prompt(
            "retry_prompt_template", retry_mapping
        )
        
        if not retry_user_prompt:
             # Fallback: Manual construction
             retry_user_prompt = f"Original Code:\n{formatted_content}\n\nIssues Found:\n{issues_text}\n\nPlease fix the code."

        # Append the specific fix suggestion from the Analysis step
        retry_user_prompt += f"\n\n[Fix Suggestion]\n{ctx.fix_suggestion}"
        
        # Update context prompts
        ctx.last_user_prompt = retry_user_prompt
        # Sys prompt remains the same as base
        sys_prompt = ctx.base_sys_prompt
        
        # 2. Call API
        response, success = await ctx.chat_handler.get_role_response(
            role_name=self.role_name,
            sys_prompt=sys_prompt,
            user_prompt=retry_user_prompt
        )

        if not success:
             print(f"    {Colors.WARNING}Retry AI call failed{Colors.ENDC}")
             return self.next_state

        # 3. Clean Result
        cleaned_content = ChatResponseCleaner.clean_code_block_markers(response)
        ctx.last_generated_content = cleaned_content
        
        return self.next_state

import os
from typing import Dict

from flow.common_states import LLMGenerateState, ValidationState
from flow.flow_context import FlowContext
from flow.flow_engine import FlowState
from typedef.cmd_data_types import Colors


class IBCGenState(LLMGenerateState):
    """
    IBC Specific Generation State.
    Prepares mapping with requirements content.
    """
    def prepare_mapping(self, ctx: FlowContext) -> Dict[str, str]:
        file_path = ctx.current_file_path
        
        # Get requirement file path using PathManager
        staging_dir = ctx.paths.get_staging_dir()
        
        req_filename = f"{file_path}_one_file_req.txt"
        req_path = os.path.join(staging_dir, req_filename)
        
        req_content = ""
        if os.path.exists(req_path):
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    req_content = f.read()
            except Exception as e:
                req_content = f"(Error reading requirements: {e})"
        else:
             req_content = f"(Requirements file not found: {req_path})"
        
        return {
            "CLASS_CONTENT_PLACEHOLDER": f"Request for {file_path}:\n{req_content}",
            "FUNC_CONTENT_PLACEHOLDER": "Func Placeholder",
            "AVAILABLE_SYMBOLS_PLACEHOLDER": "No symbols (demo)",
            "MODULE_DEPENDENCIES_PLACEHOLDER": "No deps (demo)",
            "EXTRACTED_PARAMS_PLACEHOLDER": "No params"
        }

class IBCValidateState(ValidationState):
    """
    IBC Specific Validation State.
    """
    def validate(self, ctx: FlowContext) -> bool:
        content = ctx.last_generated_content
        
        if not content:
            ctx.issue_recorder.add_issue("Content is empty", severity="error")
            return False
            
        # Demo validation logic
        if "error" in content:
            ctx.issue_recorder.add_issue("Code contains 'error' keyword", severity="error", line_num=1, line_content="error line")
            
        return not ctx.issue_recorder.has_issues()

class IBCSaveState(FlowState):
    """
    IBC Save State.
    Saves the generated content to the IBC directory.
    """
    async def execute(self, ctx: FlowContext) -> str:
        print(f"    {Colors.OKGREEN}[Save] Saving file: {ctx.current_file_path}{Colors.ENDC}")
        
        # Use ProjectStore to save
        try:
            ctx.project.save_ibc_content(ctx.current_file_path, ctx.last_generated_content)
        except Exception as e:
            print(f"    {Colors.FAIL}[Save] Failed to save: {e}{Colors.ENDC}")
            
        return "__END__"

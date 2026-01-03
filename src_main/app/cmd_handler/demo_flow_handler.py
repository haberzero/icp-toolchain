import asyncio
from typing import List
from typedef.cmd_data_types import Colors
from app.cmd_handler.base_cmd_handler import BaseCmdHandler

# Import new Flow Engine components
from flow.flow_context import FlowContext
from flow.flow_engine import FlowEngine
from flow.common_states import AnalysisAndFixState, LLMRetryExecutionState
from flow.ibc_flow import IBCGenState, IBCValidateState, IBCSaveState

# Import specific data stores
from data_store.unified.toolchain_store import ToolchainStore
from data_store.unified.project_store import ProjectStore
from data_store.unified.path_manager import get_instance as get_path_manager

class DemoFlowHandler(BaseCmdHandler):
    """
    Handler for the 'demo_flow' command.
    Refactored to use specific Data Store entities and modular Flow Engine.
    """
    
    def __init__(self, chat_handler, sys_prompt_manager, user_prompt_manager):
        super().__init__(chat_handler, sys_prompt_manager, user_prompt_manager)

    def execute(self):
        """Entry point for the command."""
        print(f"{Colors.HEADER}Starting Experimental Flow Engine (Refactored)...{Colors.ENDC}")
        asyncio.run(self._run_async())

    async def _run_async(self):
        # 1. Initialize Stores
        # The user prefers explicit instantiation over a Unified facade.
        toolchain_store = ToolchainStore()
        project_store = ProjectStore()
        path_mgr = get_path_manager()
        
        # 2. Initialize Context
        ctx = FlowContext(
            chat_handler=self.chat_handler,
            toolchain=toolchain_store,
            project=project_store,
            paths=path_mgr,
            max_attempts=3
        )
        
        # 3. Get files to process
        # TODO: Integrate with Dependency Analysis to get real file list
        files_to_process = ["demo/file_a", "demo/file_b"]
        
        # 4. Build Flow Engine
        # Define State Graph:
        # Start -> Gen -> Validate -> Success -> Save -> End
        #                  |
        #                  v (Fail)
        #               Analyze -> Fix -> RetryExec -> Validate
        
        engine = FlowEngine(ctx)
        
        # Register States
        engine.add_state(IBCGenState(
            name="generate",
            role_name="7_intent_behavior_code_gen",
            sys_template_key="7_intent_behavior_code_gen",
            user_template_key="intent_code_behavior_gen_user",
            next_state="validate",
            retry_state="__END__"
        ))
        
        engine.add_state(IBCValidateState(
            name="validate",
            success_state="save",
            fail_state="analyze",
            max_retry_fail_state="__END__"
        ))
        
        engine.add_state(AnalysisAndFixState(
            name="analyze",
            next_state="retry_exec"
        ))
        
        engine.add_state(LLMRetryExecutionState(
            name="retry_exec",
            role_name="7_intent_behavior_code_gen",
            next_state="validate",
            code_block_type="intent_behavior_code"
        ))
        
        engine.add_state(IBCSaveState(
            name="save"
        ))
        
        engine.set_start("generate")
        
        # 5. Process each file
        for file_path in files_to_process:
            print(f"\n{Colors.BOLD}=== Processing File: {file_path} ==={Colors.ENDC}")
            ctx.reset_per_file(file_path)
            await engine.run()

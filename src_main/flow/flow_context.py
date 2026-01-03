from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from data_store.unified.toolchain_store import ToolchainStore
from data_store.unified.project_store import ProjectStore
from data_store.unified.path_manager import PathManager, get_instance as get_path_manager
from utils.issue_recorder.issue_recorder import IssueRecorder

@dataclass
class FlowContext:
    """
    Flow Context: Unique object passed between state machine nodes.
    Holds references to specific data stores.
    """
    # Infrastructure
    chat_handler: Any # External service handler
    
    # Data Stores
    toolchain: ToolchainStore
    project: ProjectStore
    paths: PathManager = field(default_factory=get_path_manager)
    
    # Global Data (Read-only / Config)
    global_data: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime State (Mutable)
    current_file_path: str = ""
    current_attempt: int = 0
    max_attempts: int = 3
    
    # Process Artifacts
    last_generated_content: Optional[str] = None
    last_sys_prompt: str = ""
    last_user_prompt: str = ""
    
    # Base prompts for retry logic (captures the first attempt's prompts)
    base_sys_prompt: str = ""
    base_user_prompt: str = ""

    # Issue Recorder
    issue_recorder: IssueRecorder = field(default_factory=IssueRecorder)
    
    fix_suggestion: str = ""
    should_terminate: bool = False

    def reset_per_file(self, file_path: str):
        """Reset state for processing a new file."""
        self.current_file_path = file_path
        self.current_attempt = 0
        self.last_generated_content = None
        self.last_sys_prompt = ""
        self.last_user_prompt = ""
        self.base_sys_prompt = ""
        self.base_user_prompt = ""
        self.issue_recorder.clear()
        self.fix_suggestion = ""
        self.should_terminate = False

    def get_issues_formatted(self) -> str:
        """Get formatted issue text."""
        return self.issue_recorder.get_formatted_text()

    def get_work_dir(self) -> str:
        return self.paths.get_work_dir()

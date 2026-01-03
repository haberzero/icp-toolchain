from abc import ABC, abstractmethod
from typing import Dict, Optional
from typedef.cmd_data_types import Colors
from flow.flow_context import FlowContext
import traceback

class FlowState(ABC):
    """Base class for all flow states."""
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, ctx: FlowContext) -> str:
        """
        Executes the state logic.
        Returns the name of the next state.
        """
        pass

class FlowEngine:
    """Flow Engine: Drives the state machine execution."""
    def __init__(self, context: FlowContext):
        self.ctx = context
        self.states: Dict[str, FlowState] = {}
        self.start_state_name: str = ""

    def add_state(self, state: FlowState):
        self.states[state.name] = state
        return self # Chainable

    def set_start(self, name: str):
        self.start_state_name = name
        return self

    async def run(self):
        current_name = self.start_state_name
        print(f"{Colors.OKBLUE}Flow started, start state: {current_name}{Colors.ENDC}")
        
        while current_name and current_name != "__END__":
            if self.ctx.should_terminate:
                print(f"{Colors.WARNING}Flow marked for termination.{Colors.ENDC}")
                break
                
            state = self.states.get(current_name)
            if not state:
                print(f"{Colors.FAIL}State not found: {current_name}{Colors.ENDC}")
                break
                
            try:
                next_name = await state.execute(self.ctx)
                current_name = next_name
            except Exception as e:
                print(f"{Colors.FAIL}State {state.name} execution exception: {e}{Colors.ENDC}")
                traceback.print_exc()
                break
        
        print(f"{Colors.OKBLUE}Flow ended.{Colors.ENDC}")

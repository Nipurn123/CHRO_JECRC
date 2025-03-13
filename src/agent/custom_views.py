from dataclasses import dataclass
from typing import Type, Dict, Any, Optional
from time import time

from browser_use.agent.views import AgentOutput
from browser_use.controller.registry.views import ActionModel
from pydantic import BaseModel, ConfigDict, Field, create_model

@dataclass
class CustomAgentStepInfo:
    step_number: int
    max_steps: int
    task: str
    add_infos: str
    memory: str
    task_progress: str
    last_state_change: float = Field(default_factory=time)
    consecutive_same_state: int = 0
    timeout_threshold: int = 30  # seconds

class CustomAgentBrain(BaseModel):
    """Current state of the agent"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    prev_action_evaluation: str
    important_contents: str
    completed_contents: str
    thought: str
    summary: str
    last_state_hash: Optional[str] = None
    state_unchanged_count: int = 0
    last_state_change_time: float = Field(default_factory=time)
    
    def update_state_tracking(self, current_state: Dict[str, Any]) -> bool:
        """
        Track state changes and detect if we're stuck
        Returns True if state has changed, False if unchanged
        """
        import hashlib
        import json
        
        # Create a hash of the current state
        state_str = json.dumps(current_state, sort_keys=True)
        current_hash = hashlib.md5(state_str.encode()).hexdigest()
        
        if self.last_state_hash == current_hash:
            self.state_unchanged_count += 1
            return False
        
        # State has changed
        self.last_state_hash = current_hash
        self.state_unchanged_count = 0
        self.last_state_change_time = time()
        return True
    
    def is_stuck(self, timeout_seconds: int = 30, max_unchanged_states: int = 5) -> bool:
        """Check if the agent is stuck based on state changes and time"""
        time_since_change = time() - self.last_state_change_time
        return (time_since_change > timeout_seconds or 
                self.state_unchanged_count > max_unchanged_states)
    
    def get_timeout_info(self) -> str:
        """Get information about the current timeout/stuck state"""
        time_since_change = time() - self.last_state_change_time
        return (f"Time since last state change: {time_since_change:.1f}s, "
                f"Unchanged states: {self.state_unchanged_count}")

class CustomAgentOutput(AgentOutput):
    """Output model for agent

    @dev note: this model is extended with custom actions in AgentService. You can also use some fields that are not in this model as provided by the linter, as long as they are registered in the DynamicActions model.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_state: CustomAgentBrain
    action: list[ActionModel]

    @staticmethod
    def type_with_custom_actions(
        custom_actions: Type[ActionModel],
    ) -> Type["CustomAgentOutput"]:
        """Extend actions with custom actions"""
        return create_model(
            "AgentOutput",
            __base__=CustomAgentOutput,
            action=(
                list[custom_actions],
                Field(...),
            ),  # Properly annotated field with no default
            __module__=CustomAgentOutput.__module__,
        )
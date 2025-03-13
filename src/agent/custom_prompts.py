from typing import List, Optional
from browser_use.agent.prompts import SystemPrompt
from browser_use.agent.views import ActionResult
from browser_use.browser.views import BrowserState
from langchain_core.messages import HumanMessage, SystemMessage
from .custom_views import CustomAgentStepInfo

class CustomSystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        """
        Returns enhanced rules for more precise and efficient agent behavior.
        """
        text = """
    1. RESPONSE FORMAT: You must ALWAYS respond with valid JSON in this exact format:
       {
         "current_state": {
           "prev_action_evaluation": "Success|Failed|Partial|Unknown - Detailed evaluation of previous action with specific success criteria and failure points. Include unexpected behaviors like dynamic content updates, AJAX responses, or state changes.",
           "important_contents": "Critical page elements and dynamic content updates relevant to the task. Include form validation messages, error states, and dynamic suggestions. Track progress indicators and state changes.",
           "completed_contents": "Structured completion log with timestamps and verification status. Format: 1. [✓] Action (verified) | 2. [!] Action (needs verification) | 3. [P] Action (partially complete). Include rollback points for failed actions.",
           "thought": "Strategic planning with contingencies. Format: 1. Current State Analysis 2. Next Action Justification 3. Risk Assessment 4. Fallback Strategy. For failures: 1. Root Cause 2. Impact Assessment 3. Recovery Plan",
           "summary": "Concise action plan with expected outcomes and success criteria. Include timing estimates and dependencies."
         },
         "action": [
           {
             "action_name": {
               // Enhanced action parameters
               "verification": "success_criteria",
               "timeout": "timeout_in_ms",
               "retry_strategy": "retry_policy",
               "fallback": "fallback_action"
             }
           }
         ]
       }

    2. ADVANCED ACTION SEQUENCES:
       - Parallel Actions: Group compatible actions for concurrent execution
       - Smart Retries: Implement exponential backoff for unstable elements
       - State Verification: Add verification steps after critical actions
       Example sequences:
       - Smart Form Filling: [
           {"prepare_form": {"validate_fields": true, "prefill_known_data": true}},
           {"batch_input": {"fields": [
               {"index": 1, "text": "username", "validation": "^[A-Za-z0-9_]+$"},
               {"index": 2, "text": "password", "validation": "^.{8,}$"}
           ]}},
           {"submit_with_verification": {"index": 3, "success_criteria": "url_change || confirmation_element"}}
         ]

    3. INTELLIGENT ELEMENT INTERACTION:
       - Element State Awareness: Track element visibility, enabled state, and mutation
       - Smart Waiting: Dynamic wait times based on element state and page load
       - Interaction Chains: Handle multi-step interactions (dropdown -> selection -> confirmation)
       - Attribute-Based Selection: Use multiple attributes for reliable element identification

    4. ADVANCED NAVIGATION & ERROR RECOVERY:
       - Progressive Enhancement: Try simple actions first, escalate complexity if needed
       - State Management: Track page state changes and handle navigation stack
       - Smart Popup Handling: Contextual decisions on popup/overlay management
       - Intelligent Scrolling: Predictive scrolling based on element location
       - Session Recovery: Handle session timeouts and authentication failures

    5. COMPREHENSIVE TASK COMPLETION:
       - Progress Tracking: Maintain detailed progress log with verification status
       - Dependency Management: Handle task dependencies and prerequisites
       - Rollback Support: Maintain recovery points for complex operations
       - Completion Verification: Multi-point verification for task completion
       - Result Persistence: Cache important results for future reference

    6. ENHANCED VISUAL CONTEXT:
       - Layout Analysis: Consider element grouping and spatial relationships
       - Dynamic Content: Track visibility changes and content updates
       - Responsive Design: Handle different viewport sizes and layouts
       - Z-Index Management: Handle overlapping elements correctly
       - Visual Hierarchy: Understand primary vs secondary elements

    7. INTELLIGENT FORM HANDLING:
       - Input Validation: Pre-validate input against form requirements
       - Suggestion Management: Smart handling of autocomplete and dynamic suggestions
       - Error Prevention: Check for common input errors before submission
       - State Persistence: Cache form data for recovery scenarios
       - Dynamic Updates: Handle form fields that update based on other inputs

    8. OPTIMIZED ACTION SEQUENCING:
       - Predictive Actions: Queue likely next actions based on context
       - Batch Operations: Group compatible actions for efficiency
       - State-Aware Sequencing: Adapt sequence based on page state
       - Priority Management: Handle critical actions first
       - Resource Optimization: Minimize page reloads and heavy operations
    """
        text += f"   - Optimize sequences within {self.max_actions_per_step} action limit per batch"
        return text

    def input_format(self) -> str:
        return """
    ENHANCED INPUT STRUCTURE:
    1. Task: Primary and secondary objectives with priority indicators
    2. Hints: Contextual information and known constraints
    3. Memory: Structured history with state transitions and decision points
    4. Task Progress: Detailed progress log with verification status
    5. Current URL: Active URL with navigation history
    6. Available Tabs: Tab inventory with state and relationship tracking
    7. Interactive Elements: Enhanced element registry:
       index[:]<element_type attributes="values">element_text</element_type>
       - Indexed references for reliable interaction
       - Complete attribute set for precise targeting
       - State information for interaction planning
       - Relationship data for complex interactions

    Element Format Examples:
    33[:]<button state="enabled" context="form-submit" priority="high">Submit Form</button>
    _[:] Context element with relationship data
    """

    def get_system_message(self) -> SystemMessage:
        time_str = self.current_date.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        AGENT_PROMPT = f"""You are an advanced browser automation agent with sophisticated interaction capabilities. Your core functions are:
    1. Intelligent page analysis and element relationship mapping
    2. Predictive action planning with contingency management
    3. State-aware execution with comprehensive verification
    4. Adaptive error recovery and performance optimization

    System Time: {time_str} (UTC)

    {self.input_format()}

    {self.important_rules()}

    Available Functions:
    {self.default_action_description}

    Performance Requirements:
    - Maintain 99.9% action success rate through intelligent retry and verification
    - Optimize action sequences for minimal latency and resource usage
    - Ensure atomic operations with rollback capability
    - Maintain detailed execution logs for analysis and optimization"""
        return SystemMessage(content=AGENT_PROMPT)

class CustomAgentMessagePrompt:
    def __init__(
            self,
            state: BrowserState,
            result: Optional[List[ActionResult]] = None,
            include_attributes: list[str] = ['state', 'context', 'priority', 'validation'],
            max_error_length: int = 800,
            step_info: Optional[CustomAgentStepInfo] = None,
    ):
        self.state = state
        self.result = result
        self.max_error_length = max_error_length
        self.include_attributes = include_attributes
        self.step_info = step_info

    def get_user_message(self) -> HumanMessage:
        state_description = f"""
    Task Analysis:
    1. Primary Task: {self.step_info.task}
    2. Context & Constraints:
    {self.step_info.add_infos}
    3. Execution History:
    {self.step_info.memory}
    4. Progress Matrix:
    {self.step_info.task_progress}
    5. Navigation Context:
       - Current URL: {self.state.url}
       - Session State: Active
    6. Tab Ecosystem:
    {self.state.tabs}
    7. Interactive Element Registry:
    {self.state.element_tree.clickable_elements_to_string(include_attributes=self.include_attributes)}
            """

        if self.result:
            state_description += "\nExecution Results:"
            for i, result in enumerate(self.result, 1):
                if result.extracted_content:
                    state_description += f"\n[Action {i}/{len(self.result)}] Success: {result.extracted_content}"
                if result.error:
                    error = result.error[-self.max_error_length:]
                    state_description += f"\n[Action {i}/{len(self.result)}] Error: ...{error}"
                    state_description += "\nRecovery Strategy: Analyzing error pattern for intelligent retry"

        if self.state.screenshot:
            return HumanMessage(
                content=[
                    {"type": "text", "text": state_description},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{self.state.screenshot}"
                        },
                    },
                ]
            )

        return HumanMessage(content=state_description)
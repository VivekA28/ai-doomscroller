from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState


class InvalidTransitionError(Exception):
    """Raised when the agent attempts an invalid state transition."""


class Agent:
    """
    Controls the high-level state of the doomscrolling agent.

    The agent state machine is deterministic.
    Decision-making will be added separately later.
    """

    VALID_TRANSITIONS = {
        AgentState.IDLE: {
            AgentState.SEARCH,
            AgentState.STOPPED,
        },
        AgentState.SEARCH: {
            AgentState.OBSERVE,
            AgentState.ERROR,
            AgentState.RATE_LIMITED,
            AgentState.AUTH_REQUIRED,
            AgentState.STOPPED,
        },
        AgentState.OBSERVE: {
            AgentState.DECIDE,
            AgentState.ERROR,
            AgentState.STOPPED,
        },
        AgentState.DECIDE: {
            AgentState.SCROLL,
            AgentState.OPEN,
            AgentState.EXPLORE,
            AgentState.WAIT,
            AgentState.STOPPED,
            AgentState.SESSION_COMPLETE,
        },
        AgentState.SCROLL: {
            AgentState.OBSERVE,
            AgentState.ERROR,
            AgentState.STOPPED,
        },
        AgentState.OPEN: {
            AgentState.OBSERVE,
            AgentState.ERROR,
            AgentState.STOPPED,
        },
        AgentState.EXPLORE: {
            AgentState.SEARCH,
            AgentState.ERROR,
            AgentState.RATE_LIMITED,
            AgentState.STOPPED,
        },
        AgentState.WAIT: {
            AgentState.OBSERVE,
            AgentState.STOPPED,
        },
        AgentState.PAUSED: {
            AgentState.OBSERVE,
            AgentState.STOPPED,
        },
        AgentState.ERROR: {
            AgentState.IDLE,
            AgentState.STOPPED,
        },
        AgentState.AUTH_REQUIRED: {
            AgentState.IDLE,
            AgentState.STOPPED,
        },
        AgentState.RATE_LIMITED: {
            AgentState.WAIT,
            AgentState.STOPPED,
        },
        AgentState.STOPPED: set(),
        AgentState.SESSION_COMPLETE: set(),
    }

    def __init__(self):
        self.state = AgentState.IDLE

    def transition(self, new_state: AgentState) -> None:
        """
        Move to a new state if the transition is valid.
        """
        allowed = self.VALID_TRANSITIONS[self.state]

        if new_state not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: "
                f"{self.state.value} -> {new_state.value}"
            )

        self.state = new_state

    def get_state(self) -> AgentState:
        """Return the current agent state."""
        return self.state

    def execute(self, action: AgentAction) -> None:
        """
        Validate and apply a high-level agent action.

        Actual platform execution will be added later.
        """

        transitions = {
            ActionType.SEARCH: AgentState.SEARCH,
            ActionType.SCROLL: AgentState.SCROLL,
            ActionType.OPEN: AgentState.OPEN,
            ActionType.EXPLORE: AgentState.EXPLORE,
            ActionType.WAIT: AgentState.WAIT,
            ActionType.STOP: AgentState.STOPPED,
        }

        if action.type == ActionType.BACK:
            raise InvalidTransitionError(
                "BACK execution is not implemented yet"
            )

        target_state = transitions[action.type]
        self.transition(target_state)
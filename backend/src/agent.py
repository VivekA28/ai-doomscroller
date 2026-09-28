from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from src.observation import Observation
from src.platform_adapter import PlatformAdapter


class InvalidTransitionError(Exception):
    """Raised when the agent attempts an invalid state transition."""


class Agent:
    """
    Controls the high-level state of the doomscrolling agent.

    The agent validates actions, delegates platform operations,
    and produces normalized observations.
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

    def __init__(self, adapter: PlatformAdapter):
        self.state = AgentState.IDLE
        self.adapter = adapter
        self.last_observation: Observation | None = None

    def transition(self, new_state: AgentState) -> None:
        """Move to a new state if the transition is valid."""

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

    def get_observation(self) -> Observation | None:
        """Return the most recent observation."""

        return self.last_observation

    def _create_observation(
        self,
        *,
        topic: str | None = None,
        current_item_id: str | None = None,
        candidates: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Observation:
        """Create and store the current normalized observation."""

        observation = Observation(
            state=self.state.value,
            topic=topic,
            current_item_id=current_item_id,
            candidates=candidates or [],
            metadata=metadata or {},
        )

        self.last_observation = observation
        return observation

    def execute(self, action: AgentAction) -> None:
        """
        Execute one high-level agent action.

        Planner-selected actions normally originate from OBSERVE.
        In that case the agent explicitly passes through DECIDE before
        entering the selected action state.
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
            self.adapter.back()
            return

        target_state = transitions[action.type]

        if self.state == AgentState.OBSERVE:
            self.transition(AgentState.DECIDE)

        self.transition(target_state)

        if action.type == ActionType.SEARCH:
            if action.value is None:
                raise ValueError("SEARCH action requires a query")

            candidates = self.adapter.search(action.value)
            candidate_ids = [
                candidate.video_id
                for candidate in candidates
            ]

            self.transition(AgentState.OBSERVE)

            self._create_observation(
                topic=action.value,
                candidates=candidate_ids,
                metadata={
                    "candidate_count": len(candidates),
                },
            )

        elif action.type == ActionType.OPEN:
            if action.value is None:
                raise ValueError("OPEN action requires an item ID")

            self.adapter.open(action.value)

            self.transition(AgentState.OBSERVE)

            self._create_observation(
                current_item_id=action.value,
            )

        elif action.type == ActionType.SCROLL:
            self.adapter.scroll()

            self.transition(AgentState.OBSERVE)

            self._create_observation()

        elif action.type == ActionType.EXPLORE:
            if action.value is None:
                raise ValueError("EXPLORE action requires a topic")

            candidates = self.adapter.search(action.value)
            candidate_ids = [
                candidate.video_id
                for candidate in candidates
            ]

            self.transition(AgentState.SEARCH)

            self._create_observation(
                topic=action.value,
                candidates=candidate_ids,
                metadata={
                    "candidate_count": len(candidates),
                },
            )

        elif action.type == ActionType.WAIT:
            self.adapter.wait()

            self.transition(AgentState.OBSERVE)

            self._create_observation()

        elif action.type == ActionType.STOP:
            return

    def run(
        self,
        planner,
        initial_action: AgentAction,
        max_steps: int = 10,
    ) -> None:
        """
        Run a bounded planner-action-observation loop.

        The planner chooses the next action from the latest observation.
        Execution continues until a terminal state is reached or the
        maximum number of steps is exhausted.
        """

        action = initial_action

        for _ in range(max_steps):
            self.execute(action)

            if self.state in {
                AgentState.STOPPED,
                AgentState.SESSION_COMPLETE,
                AgentState.ERROR,
                AgentState.AUTH_REQUIRED,
                AgentState.RATE_LIMITED,
            }:
                return

            observation = self.get_observation()

            if observation is None:
                raise RuntimeError(
                    "Agent has no observation after executing an action"
                )

            action = planner.decide(observation)

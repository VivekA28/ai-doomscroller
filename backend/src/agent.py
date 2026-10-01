from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from src.observation import Observation
from src.platform_adapter import PlatformAdapter
from src.planner import PlannerError
from src.session_state import SessionState


class InvalidTransitionError(Exception):
    """Raised when the agent attempts an invalid state transition."""


class Agent:
    """Controls state, executes permitted actions, and owns session memory."""

    VALID_TRANSITIONS = {
        AgentState.IDLE: {AgentState.SEARCH, AgentState.STOPPED},
        AgentState.SEARCH: {AgentState.OBSERVE, AgentState.ERROR, AgentState.RATE_LIMITED, AgentState.AUTH_REQUIRED, AgentState.STOPPED},
        AgentState.OBSERVE: {AgentState.DECIDE, AgentState.ERROR, AgentState.STOPPED},
        AgentState.DECIDE: {AgentState.SCROLL, AgentState.OPEN, AgentState.EXPLORE, AgentState.WAIT, AgentState.OBSERVE, AgentState.STOPPED, AgentState.SESSION_COMPLETE},
        AgentState.SCROLL: {AgentState.OBSERVE, AgentState.ERROR, AgentState.STOPPED},
        AgentState.OPEN: {AgentState.OBSERVE, AgentState.ERROR, AgentState.STOPPED},
        AgentState.EXPLORE: {AgentState.OBSERVE, AgentState.ERROR, AgentState.RATE_LIMITED, AgentState.AUTH_REQUIRED, AgentState.STOPPED},
        AgentState.WAIT: {AgentState.OBSERVE, AgentState.STOPPED},
        AgentState.PAUSED: {AgentState.OBSERVE, AgentState.STOPPED},
        AgentState.ERROR: {AgentState.IDLE, AgentState.STOPPED},
        AgentState.AUTH_REQUIRED: {AgentState.IDLE, AgentState.STOPPED},
        AgentState.RATE_LIMITED: {AgentState.WAIT, AgentState.STOPPED},
        AgentState.STOPPED: set(),
        AgentState.SESSION_COMPLETE: set(),
    }

    def __init__(self, adapter: PlatformAdapter, session: SessionState | None = None):
        self.state = AgentState.IDLE
        self.adapter = adapter
        self.session = session
        self.last_observation: Observation | None = None

    def transition(self, new_state: AgentState) -> None:
        allowed = self.VALID_TRANSITIONS[self.state]
        if new_state not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: {self.state.value} -> {new_state.value}"
            )
        self.state = new_state

    def get_state(self) -> AgentState:
        return self.state

    def get_observation(self) -> Observation | None:
        return self.last_observation

    _UNSET = object()

    def _create_observation(self, *, topic: str | None | object = _UNSET,
                            current_item_id: str | None | object = _UNSET,
                            candidates: list[str] | None | object = _UNSET,
                            metadata: dict | None | object = _UNSET,
                            preserve: bool = False) -> Observation:
        previous = self.last_observation
        if preserve and previous is not None:
            if topic is self._UNSET:
                topic = previous.topic
            if current_item_id is self._UNSET:
                current_item_id = previous.current_item_id
            if candidates is self._UNSET:
                candidates = list(previous.candidates)
            if metadata is self._UNSET:
                metadata = dict(previous.metadata)
            elif isinstance(metadata, dict):
                merged_metadata = dict(previous.metadata)
                merged_metadata.update(metadata)
                metadata = merged_metadata

        if topic is self._UNSET:
            topic = None
        if current_item_id is self._UNSET:
            current_item_id = None
        if candidates is self._UNSET:
            candidates = []
        if metadata is self._UNSET:
            metadata = {}

        observation = Observation(
            state=self.state.value,
            topic=topic,
            current_item_id=current_item_id,
            candidates=candidates,
            metadata=metadata,
        )
        self.last_observation = observation
        return observation

    def _ensure_session(self, goal: str) -> None:
        if self.session is None:
            self.session = SessionState(goal=goal)

    def execute(self, action: AgentAction) -> None:
        transitions = {
            ActionType.SEARCH: AgentState.SEARCH,
            ActionType.SCROLL: AgentState.SCROLL,
            ActionType.OPEN: AgentState.OPEN,
            ActionType.EXPLORE: AgentState.EXPLORE,
            ActionType.WAIT: AgentState.WAIT,
            ActionType.STOP: AgentState.STOPPED,
        }

        if action.type == ActionType.BACK:
            if self.state == AgentState.OBSERVE:
                self.transition(AgentState.DECIDE)
            elif self.state != AgentState.DECIDE:
                raise InvalidTransitionError(
                    f"Invalid transition for BACK: {self.state.value} -> back"
                )
            self.adapter.back()
            self.session.record_action(action) if self.session else None
            self.transition(AgentState.OBSERVE)
            self._create_observation(current_item_id=None, preserve=True)
            return

        if action.type == ActionType.SEARCH and action.value is None:
            raise ValueError("SEARCH action requires a query")
        if action.type == ActionType.OPEN and action.value is None:
            raise ValueError("OPEN action requires an item ID")
        if action.type == ActionType.EXPLORE and action.value is None:
            raise ValueError("EXPLORE action requires a topic")

        if action.type == ActionType.SEARCH:
            self._ensure_session(action.value)
        elif action.type == ActionType.STOP:
            pass
        elif self.session is None:
            raise RuntimeError("SessionState must exist before this action")

        if action.type == ActionType.OPEN and self.session.has_seen_item(action.value):
            raise ValueError(
                f"OPEN target has already been viewed in this session: {action.value}"
            )

        if self.state == AgentState.OBSERVE:
            self.transition(AgentState.DECIDE)
        self.transition(transitions[action.type])

        if self.session is not None:
            self.session.record_action(action)

        if action.type == ActionType.SEARCH:
            candidates = self.adapter.search(action.value)
            self.session.record_search(action.value)
            candidate_ids = [candidate.video_id for candidate in candidates]
            self.transition(AgentState.OBSERVE)
            self._create_observation(
                topic=action.value,
                candidates=candidate_ids,
                metadata={"candidate_count": len(candidates)},
            )

        elif action.type == ActionType.OPEN:
            opened = self.adapter.open(action.value)
            self.session.record_item(action.value)
            self.transition(AgentState.OBSERVE)
            metadata = None
            if opened is not None:
                metadata = {
                    "item": {
                        "video_id": opened.video_id,
                        "title": opened.title,
                        "channel": opened.channel,
                        "duration_seconds": opened.duration_seconds,
                        "signals": {
                            "duration_score": opened.signals.duration_score,
                            "text_score": opened.signals.text_score,
                            "visual_score": opened.signals.visual_score,
                        },
                        "metadata": dict(opened.metadata),
                    }
                }
            self._create_observation(
                current_item_id=action.value,
                metadata=metadata,
                preserve=True,
            )

        elif action.type == ActionType.SCROLL:
            self.adapter.scroll()
            self.transition(AgentState.OBSERVE)
            self._create_observation(preserve=True)

        elif action.type == ActionType.EXPLORE:
            candidates = self.adapter.search(action.value)
            self.session.record_search(action.value)
            self.session.record_discovered_topic(action.value)
            candidate_ids = [candidate.video_id for candidate in candidates]
            self.transition(AgentState.OBSERVE)
            self._create_observation(
                topic=action.value,
                candidates=candidate_ids,
                metadata={"candidate_count": len(candidates), "exploration": True},
            )

        elif action.type == ActionType.WAIT:
            self.adapter.wait()
            self.transition(AgentState.OBSERVE)
            self._create_observation(preserve=True)

        elif action.type == ActionType.STOP:
            return

    def run(self, planner, initial_action: AgentAction, max_steps: int = 10) -> None:
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
                raise RuntimeError("Agent has no observation after executing an action")
            if hasattr(planner, "set_session") and self.session is not None:
                planner.set_session(self.session)
            try:
                action = planner.decide(observation)
            except PlannerError:
                self.transition(AgentState.ERROR)
                return

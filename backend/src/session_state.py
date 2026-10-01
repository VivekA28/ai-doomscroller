from dataclasses import dataclass, field
from typing import Any

from src.agent_action import AgentAction


@dataclass
class SessionState:
    """Deterministic memory for one doomscrolling session."""

    goal: str
    current_topic: str | None = None
    seen_item_ids: set[str] = field(default_factory=set)
    searched_topics: list[str] = field(default_factory=list)
    discovered_topics: list[str] = field(default_factory=list)
    action_history: list[AgentAction] = field(default_factory=list)

    def record_action(self, action: AgentAction) -> None:
        self.action_history.append(action)

    @staticmethod
    def _contains_casefolded(values: list[str], value: str) -> bool:
        normalized = value.casefold()
        return any(existing.casefold() == normalized for existing in values)

    def record_search(self, topic: str) -> None:
        self.current_topic = topic
        if not self._contains_casefolded(self.searched_topics, topic):
            self.searched_topics.append(topic)

    def record_item(self, item_id: str) -> None:
        self.seen_item_ids.add(item_id)

    def record_discovered_topic(self, topic: str) -> None:
        if topic and not self._contains_casefolded(
            self.discovered_topics, topic
        ):
            self.discovered_topics.append(topic)

    def has_seen_item(self, item_id: str) -> bool:
        return item_id in self.seen_item_ids

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-safe snapshot for planner/UI use."""
        return {
            "goal": self.goal,
            "current_topic": self.current_topic,
            "seen_item_ids": sorted(self.seen_item_ids),
            "searched_topics": list(self.searched_topics),
            "discovered_topics": list(self.discovered_topics),
            "recent_actions": [
                {"type": action.type.value, "value": action.value}
                for action in self.action_history[-5:]
            ],
        }

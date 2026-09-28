from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    SEARCH = "search"
    SCROLL = "scroll"
    OPEN = "open"
    BACK = "back"
    EXPLORE = "explore"
    WAIT = "wait"
    STOP = "stop"


@dataclass
class AgentAction:
    """
    A validated high-level action chosen by the decision system.

    The action describes WHAT the agent wants to do.
    Platform adapters will later decide HOW to execute it.
    """

    type: ActionType
    value: str | None = None
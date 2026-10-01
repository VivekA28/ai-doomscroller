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
    type: ActionType
    value: str | None = None

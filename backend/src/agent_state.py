from enum import Enum


class AgentState(str, Enum):
    IDLE = "idle"
    SEARCH = "search"
    OBSERVE = "observe"
    DECIDE = "decide"
    SCROLL = "scroll"
    OPEN = "open"
    EXPLORE = "explore"
    WAIT = "wait"
    PAUSED = "paused"
    ERROR = "error"
    AUTH_REQUIRED = "auth_required"
    RATE_LIMITED = "rate_limited"
    STOPPED = "stopped"
    SESSION_COMPLETE = "session_complete"

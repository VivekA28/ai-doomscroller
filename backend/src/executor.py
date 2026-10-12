from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from src.observation import Observation
from src.platform_adapter import PlatformAdapter
from src.quota import QuotaExceededError
from src.session_state import SessionState
from src.youtube_adapter import UnsupportedOperationError
from src.youtube_client import YouTubeAPIError

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base error raised while executing a validated agent action."""


class UnsupportedActionError(ExecutionError):
    """Raised when an adapter cannot perform a requested action."""


class AuthenticationRequiredError(ExecutionError):
    """Raised when execution requires the user to authenticate."""


class RateLimitedError(ExecutionError):
    """Raised when an upstream service refuses further requests due to limits."""


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of one deterministic action execution."""

    action: AgentAction
    state: AgentState
    observation: Observation | None
    success: bool
    message: str
    error_type: str | None = None


class ActionExecutor:
    """
    Deterministic boundary between planner output, Agent, and platform adapter.

    This component maps known structured actions to Agent.execute; it never
    evaluates or executes arbitrary model-generated code or browser commands.
    """

    def __init__(
        self,
        agent,
        *,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.agent = agent
        self.event_sink = event_sink

    def execute(self, action: AgentAction) -> ExecutionResult:
        if not isinstance(action, AgentAction):
            raise TypeError("action must be an AgentAction")

        if not isinstance(action.type, ActionType):
            raise ValueError("action.type must be a known ActionType")

        self._validate_value(action)

        try:
            self.agent.execute(action)
        except UnsupportedOperationError as exc:
            return self._failure(action, UnsupportedActionError(str(exc)))
        except QuotaExceededError as exc:
            return self._failure(action, RateLimitedError(str(exc)))
        except YouTubeAPIError as exc:
            category = self._classify_api_error(exc)
            if category == "auth":
                return self._failure(action, AuthenticationRequiredError(str(exc)))
            if category == "rate_limit":
                return self._failure(action, RateLimitedError(str(exc)))
            return self._failure(action, ExecutionError(str(exc)))
        except (TimeoutError, ConnectionError) as exc:
            return self._failure(action, ExecutionError(str(exc)))
        except Exception as exc:
            # Deterministic boundary: report failure; don't allow failed actions
            # to be recorded as successful or escape into an uncontrolled loop.
            logger.exception("Action execution failed: %s", action.type.value)
            return self._failure(action, ExecutionError(str(exc)))

        result = ExecutionResult(
            action=action,
            state=self.agent.get_state(),
            observation=self.agent.get_observation(),
            success=True,
            message=f"{action.type.value} completed",
        )
        self._emit(result)
        return result

    @staticmethod
    def _validate_value(action: AgentAction) -> None:
        requires_value = {ActionType.SEARCH, ActionType.EXPLORE, ActionType.OPEN}
        forbids_value = {
            ActionType.SCROLL, ActionType.BACK, ActionType.WAIT, ActionType.STOP
        }
        if action.type in requires_value and (
            not isinstance(action.value, str) or not action.value.strip()
        ):
            raise ValueError(f"{action.type.value.upper()} requires a non-empty value")
        if action.type in forbids_value and action.value is not None:
            raise ValueError(f"{action.type.value.upper()} must have value=None")

    @staticmethod
    def _classify_api_error(exc: YouTubeAPIError) -> str:
        text = str(exc).casefold()
        if "401" in text or "forbidden" in text or "keyinvalid" in text:
            return "auth"
        if "quotaexceeded" in text or "ratelimitexceeded" in text or "429" in text:
            return "rate_limit"
        return "other"

    def _failure(self, action: AgentAction, error: ExecutionError) -> ExecutionResult:
        if isinstance(error, AuthenticationRequiredError):
            target = AgentState.AUTH_REQUIRED
        elif isinstance(error, RateLimitedError):
            target = AgentState.RATE_LIMITED
        else:
            target = AgentState.ERROR

        # Execution failures may happen after Agent has entered an action state.
        current = self.agent.get_state()
        if target in self.agent.VALID_TRANSITIONS.get(current, set()):
            self.agent.transition(target)
        elif current not in {AgentState.STOPPED, AgentState.SESSION_COMPLETE}:
            self.agent.state = target

        result = ExecutionResult(
            action=action,
            state=self.agent.get_state(),
            observation=self.agent.get_observation(),
            success=False,
            message=str(error),
            error_type=type(error).__name__,
        )
        logger.warning("Action %s failed (%s): %s", action.type.value, result.error_type, error)
        self._emit(result)
        return result

    def _emit(self, result: ExecutionResult) -> None:
        if self.event_sink is not None:
            self.event_sink({
                "action": result.action.type.value,
                "value": result.action.value,
                "success": result.success,
                "state": result.state.value,
                "message": result.message,
                "error_type": result.error_type,
            })

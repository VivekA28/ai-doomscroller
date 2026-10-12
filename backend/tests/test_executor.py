import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import Agent
from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from src.executor import (
    ActionExecutor,
    AuthenticationRequiredError,
    RateLimitedError,
    UnsupportedActionError,
)
from src.quota import QuotaExceededError
from src.youtube_adapter import YouTubeAdapter
from src.youtube_client import YouTubeAuthenticationError
from tests.mock_adapter import MockAdapter


class QuotaFailingAdapter(MockAdapter):
    def search(self, query):
        raise QuotaExceededError("local budget exhausted")


class AuthenticationFailingAdapter(MockAdapter):
    def search(self, query):
        raise YouTubeAuthenticationError("YouTube API error (401): invalidCredentials")


class EmptyStore:
    def get(self, video_id):
        return None


class EmptyPipeline:
    def __init__(self):
        self.store = EmptyStore()

    def search(self, query):
        return []


class ScrollPlanner:
    def decide(self, observation):
        return AgentAction(ActionType.SCROLL)


class ActionExecutorTests(unittest.TestCase):
    def test_successful_action_returns_structured_result_and_event(self):
        adapter = MockAdapter()
        events = []
        agent = Agent(adapter)
        executor = ActionExecutor(agent, event_sink=events.append)

        result = executor.execute(AgentAction(ActionType.SEARCH, "JDM"))

        self.assertTrue(result.success)
        self.assertEqual(result.state, AgentState.OBSERVE)
        self.assertEqual(result.observation.topic, "JDM")
        self.assertIsNone(result.error_type)
        self.assertEqual(events[0]["action"], "search")
        self.assertTrue(events[0]["success"])

    def test_invalid_action_value_is_rejected_before_execution(self):
        agent = Agent(MockAdapter())
        executor = ActionExecutor(agent)

        with self.assertRaises(ValueError):
            executor.execute(AgentAction(ActionType.SCROLL, "not-allowed"))

        self.assertEqual(agent.get_state(), AgentState.IDLE)

    def test_unsupported_operation_transitions_to_error(self):
        agent = Agent(YouTubeAdapter(EmptyPipeline()))
        executor = ActionExecutor(agent)

        search = executor.execute(AgentAction(ActionType.SEARCH, "JDM"))
        self.assertTrue(search.success)

        result = executor.execute(AgentAction(ActionType.SCROLL))

        self.assertFalse(result.success)
        self.assertIsInstance(result.error_type, str)
        self.assertEqual(result.error_type, UnsupportedActionError.__name__)
        self.assertEqual(result.state, AgentState.ERROR)
        self.assertIn("does not provide feed/Shorts scrolling", result.message)

    def test_quota_exhaustion_transitions_to_rate_limited(self):
        agent = Agent(QuotaFailingAdapter())
        executor = ActionExecutor(agent)

        result = executor.execute(AgentAction(ActionType.SEARCH, "JDM"))

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, RateLimitedError.__name__)
        self.assertEqual(result.state, AgentState.RATE_LIMITED)

    def test_authentication_failure_transitions_to_auth_required(self):
        agent = Agent(AuthenticationFailingAdapter())
        executor = ActionExecutor(agent)

        result = executor.execute(AgentAction(ActionType.SEARCH, "JDM"))

        self.assertFalse(result.success)
        self.assertEqual(result.error_type, AuthenticationRequiredError.__name__)
        self.assertEqual(result.state, AgentState.AUTH_REQUIRED)

    def test_agent_run_uses_executor_and_stops_after_unsupported_scroll(self):
        agent = Agent(YouTubeAdapter(EmptyPipeline()))

        agent.run(
            ScrollPlanner(),
            AgentAction(ActionType.SEARCH, "JDM"),
            max_steps=5,
        )

        self.assertEqual(agent.get_state(), AgentState.ERROR)


if __name__ == "__main__":
    unittest.main()

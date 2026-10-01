import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import Agent, InvalidTransitionError
from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from src.planner import Planner, PlannerError
from src.session_state import SessionState
from tests.mock_adapter import MockAdapter, make_candidate


class ScriptedPlanner:
    def __init__(self, *actions):
        self.actions = list(actions)

    def decide(self, observation):
        if not self.actions:
            return AgentAction(ActionType.STOP)
        return self.actions.pop(0)


class FailingPlanner:
    def decide(self, observation):
        raise PlannerError("Simulated LLM failure")


class NoneReturningAdapter(MockAdapter):
    def open(self, item_id: str):
        self.opened.append(item_id)
        return None


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.adapter = MockAdapter()
        self.first = make_candidate("first", "First video")
        self.second = make_candidate("second", "Second video")
        self.adapter.add_results("JDM", self.first, self.second)
        self.adapter.add_results("RB26", self.second)

    def test_search_creates_observation(self):
        agent = Agent(self.adapter)

        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))

        self.assertEqual(agent.get_state(), AgentState.OBSERVE)
        observation = agent.get_observation()
        self.assertEqual(observation.topic, "JDM")
        self.assertEqual(observation.candidates, ["first", "second"])
        self.assertEqual(observation.metadata["candidate_count"], 2)

    def test_session_records_actions_and_items(self):
        agent = Agent(self.adapter, SessionState(goal="JDM"))

        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        agent.execute(AgentAction(ActionType.OPEN, "first"))
        agent.execute(AgentAction(ActionType.EXPLORE, "RB26"))

        self.assertEqual(agent.session.searched_topics, ["JDM", "RB26"])
        self.assertEqual(agent.session.seen_item_ids, {"first"})
        self.assertEqual(agent.session.discovered_topics, ["RB26"])
        self.assertEqual(
            [action.type for action in agent.session.action_history],
            [ActionType.SEARCH, ActionType.OPEN, ActionType.EXPLORE],
        )

    def test_agent_rejects_reopening_seen_item(self):
        agent = Agent(self.adapter, SessionState(goal="JDM"))
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        agent.execute(AgentAction(ActionType.OPEN, "first"))

        with self.assertRaises(ValueError):
            agent.execute(AgentAction(ActionType.OPEN, "first"))

        self.assertEqual(self.adapter.opened, ["first"])

    def test_explore_returns_to_observe_with_results(self):
        agent = Agent(self.adapter)
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))

        agent.execute(AgentAction(ActionType.EXPLORE, "RB26"))

        observation = agent.get_observation()
        self.assertEqual(agent.get_state(), AgentState.OBSERVE)
        self.assertEqual(observation.state, "observe")
        self.assertEqual(observation.topic, "RB26")
        self.assertEqual(observation.candidates, ["second"])
        self.assertTrue(observation.metadata["exploration"])

    def test_open_preserves_context_and_metadata(self):
        agent = Agent(self.adapter)
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))

        agent.execute(AgentAction(ActionType.OPEN, "first"))

        observation = agent.get_observation()
        self.assertEqual(agent.get_state(), AgentState.OBSERVE)
        self.assertEqual(observation.topic, "JDM")
        self.assertEqual(observation.current_item_id, "first")
        self.assertEqual(observation.candidates, ["first", "second"])
        self.assertEqual(observation.metadata["item"]["title"], "First video")

    def test_back_creates_fresh_observation(self):
        agent = Agent(self.adapter)
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        agent.execute(AgentAction(ActionType.OPEN, "first"))

        agent.execute(AgentAction(ActionType.BACK))

        self.assertEqual(agent.get_state(), AgentState.OBSERVE)
        self.assertEqual(self.adapter.back_count, 1)
        self.assertIsNotNone(agent.get_observation())
        self.assertIsNone(agent.get_observation().current_item_id)

    def test_back_from_idle_is_rejected(self):
        agent = Agent(self.adapter)

        with self.assertRaises(InvalidTransitionError):
            agent.execute(AgentAction(ActionType.BACK))

    def test_run_end_to_end_search_open_stop(self):
        agent = Agent(self.adapter)
        planner = ScriptedPlanner(
            AgentAction(ActionType.OPEN, "first"),
            AgentAction(ActionType.STOP),
        )

        agent.run(
            planner,
            AgentAction(ActionType.SEARCH, "JDM"),
            max_steps=5,
        )

        self.assertEqual(agent.get_state(), AgentState.STOPPED)
        self.assertEqual(self.adapter.opened, ["first"])

    def test_run_explore_path(self):
        agent = Agent(self.adapter)
        planner = ScriptedPlanner(
            AgentAction(ActionType.EXPLORE, "RB26"),
            AgentAction(ActionType.STOP),
        )

        agent.run(
            planner,
            AgentAction(ActionType.SEARCH, "JDM"),
            max_steps=5,
        )

        self.assertEqual(agent.get_state(), AgentState.STOPPED)
        self.assertEqual(
            agent.get_observation().topic,
            "RB26",
        )
        self.assertEqual(
            agent.get_observation().candidates,
            ["second"],
        )

    def test_wait_preserves_observation(self):
        agent = Agent(self.adapter)
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        before = agent.get_observation()

        agent.execute(AgentAction(ActionType.WAIT))

        after = agent.get_observation()
        self.assertEqual(after.topic, before.topic)
        self.assertEqual(after.candidates, before.candidates)

    def test_invalid_search_from_observe_without_decision_is_not_needed(self):
        agent = Agent(self.adapter)
        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        self.assertEqual(agent.get_state(), AgentState.OBSERVE)

    def test_stop_from_idle_with_no_session(self):
        agent = Agent(self.adapter)
        self.assertIsNone(agent.session)
        self.assertEqual(agent.get_state(), AgentState.IDLE)

        agent.execute(AgentAction(ActionType.STOP))

        self.assertEqual(agent.get_state(), AgentState.STOPPED)
        self.assertIsNone(agent.session)

    def test_open_returning_none_still_records_item_and_prevents_reopening(self):
        adapter = NoneReturningAdapter()
        adapter.add_results("JDM", make_candidate("video-none", "No metadata video"))
        agent = Agent(adapter, SessionState(goal="JDM"))

        agent.execute(AgentAction(ActionType.SEARCH, "JDM"))
        agent.execute(AgentAction(ActionType.OPEN, "video-none"))

        self.assertIn("video-none", agent.session.seen_item_ids)
        self.assertTrue(agent.session.has_seen_item("video-none"))

        with self.assertRaises(ValueError):
            agent.execute(AgentAction(ActionType.OPEN, "video-none"))

    def test_run_transitions_to_error_on_planner_error(self):
        agent = Agent(self.adapter)
        planner = FailingPlanner()

        agent.run(
            planner,
            AgentAction(ActionType.SEARCH, "JDM"),
            max_steps=5,
        )

        self.assertEqual(agent.get_state(), AgentState.ERROR)


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent_action import ActionType
from src.observation import Observation
from src.planner import Planner, PlannerError
from src.session_state import SessionState


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def complete(self, instructions, input_data):
        self.calls.append((instructions, input_data))
        return self.response


class PlannerTests(unittest.TestCase):
    def make_observation(self):
        return Observation(
            state="observe",
            topic="JDM",
            current_item_id=None,
            candidates=["first", "second"],
            metadata={"candidate_count": 2},
        )

    def test_returns_valid_open_action(self):
        llm = FakeLLM('{"action":"open","value":"first"}')
        planner = Planner(llm)

        action = planner.decide(self.make_observation())

        self.assertEqual(action.type, ActionType.OPEN)
        self.assertEqual(action.value, "first")
        self.assertEqual(len(llm.calls), 1)

    def test_returns_explore_action(self):
        llm = FakeLLM('{"action":"explore","value":"RB26"}')
        planner = Planner(llm)

        action = planner.decide(self.make_observation())

        self.assertEqual(action.type, ActionType.EXPLORE)
        self.assertEqual(action.value, "RB26")

    def test_rejects_invalid_json(self):
        planner = Planner(FakeLLM("not json"))

        with self.assertRaises(PlannerError):
            planner.decide(self.make_observation())

    def test_rejects_unknown_action(self):
        planner = Planner(FakeLLM('{"action":"click","value":"first"}'))

        with self.assertRaises(PlannerError):
            planner.decide(self.make_observation())

    def test_rejects_open_of_unknown_candidate(self):
        planner = Planner(FakeLLM('{"action":"open","value":"unknown"}'))

        with self.assertRaises(PlannerError):
            planner.decide(self.make_observation())

    def test_rejects_value_for_scroll(self):
        planner = Planner(FakeLLM('{"action":"scroll","value":"JDM"}'))

        with self.assertRaises(PlannerError):
            planner.decide(self.make_observation())

    def test_build_input_contains_only_controlled_agent_context(self):
        llm = FakeLLM('{"action":"stop","value":null}')
        planner = Planner(llm)
        observation = self.make_observation()

        planner.decide(observation)

        _, input_data = llm.calls[0]
        self.assertEqual(input_data["observation"]["topic"], "JDM")
        self.assertEqual(input_data["observation"]["candidates"], ["first", "second"])
        self.assertIn("available_actions", input_data)

    def test_non_observe_state_stops_without_calling_llm(self):
        llm = FakeLLM('{"action":"open","value":"first"}')
        planner = Planner(llm)
        observation = Observation(state="search")

        action = planner.decide(observation)

        self.assertEqual(action.type, ActionType.STOP)
        self.assertEqual(llm.calls, [])

    def test_seen_candidates_are_omitted_from_input_data(self):
        session = SessionState(goal="JDM")
        session.record_item("first")

        llm = FakeLLM('{"action":"stop","value":null}')
        planner = Planner(llm, session=session)
        observation = self.make_observation()

        planner.decide(observation)

        _, input_data = llm.calls[0]
        self.assertEqual(input_data["observation"]["candidates"], ["second"])

    def test_input_data_contains_session_snapshot(self):
        session = SessionState(goal="JDM")
        session.record_search("JDM")
        session.record_item("first")

        llm = FakeLLM('{"action":"stop","value":null}')
        planner = Planner(llm, session=session)
        observation = self.make_observation()

        planner.decide(observation)

        _, input_data = llm.calls[0]
        self.assertIsNotNone(input_data["session"])
        self.assertEqual(input_data["session"]["goal"], "JDM")
        self.assertEqual(input_data["session"]["seen_item_ids"], ["first"])
        self.assertEqual(input_data["session"]["searched_topics"], ["JDM"])

    def test_rejects_open_of_already_seen_candidate(self):
        session = SessionState(goal="JDM")
        session.record_item("first")

        llm = FakeLLM('{"action":"open","value":"first"}')
        planner = Planner(llm, session=session)
        observation = self.make_observation()

        with self.assertRaises(PlannerError):
            planner.decide(observation)


if __name__ == "__main__":
    unittest.main()

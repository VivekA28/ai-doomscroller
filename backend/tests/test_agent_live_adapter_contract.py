import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent import Agent
from src.agent_action import ActionType, AgentAction
from src.agent_state import AgentState
from tests.mock_adapter import MockAdapter, make_candidate


class CandidateNavigationAdapter(MockAdapter):
    def __init__(self):
        super().__init__()
        self.next_candidate = None
        self.previous_candidate = None
        self.stop_playback_calls = 0

    def scroll(self):
        self.scroll_count += 1
        return self.next_candidate

    def back(self):
        self.back_count += 1
        return self.previous_candidate

    def stop_playback(self):
        self.stop_playback_calls += 1


class AgentLiveAdapterContractTests(unittest.TestCase):
    def setUp(self):
        self.adapter = CandidateNavigationAdapter()
        self.first = make_candidate("first-video", "First video")
        self.second = make_candidate("second-video", "Second video")
        self.adapter.add_results("topic", self.first, self.second)
        self.agent = Agent(self.adapter)
        self.agent.execute(AgentAction(ActionType.SEARCH, "topic"))

    def test_scroll_result_updates_observation_and_seen_items(self):
        self.adapter.next_candidate = self.second

        self.agent.execute(AgentAction(ActionType.SCROLL))

        observation = self.agent.get_observation()
        self.assertEqual(self.agent.get_state(), AgentState.OBSERVE)
        self.assertEqual(observation.current_item_id, self.second.video_id)
        self.assertEqual(observation.metadata["item"]["title"], "Second video")
        self.assertTrue(self.agent.session.has_seen_item(self.second.video_id))

    def test_scroll_without_return_value_preserves_legacy_adapter_behavior(self):
        before = self.agent.get_observation()
        self.adapter.next_candidate = None

        self.agent.execute(AgentAction(ActionType.SCROLL))

        after = self.agent.get_observation()
        self.assertEqual(after.candidates, before.candidates)
        self.assertEqual(after.topic, before.topic)

    def test_back_result_updates_current_item(self):
        self.agent.execute(AgentAction(ActionType.OPEN, self.first.video_id))
        self.adapter.previous_candidate = self.first

        self.agent.execute(AgentAction(ActionType.BACK))

        observation = self.agent.get_observation()
        self.assertEqual(observation.current_item_id, self.first.video_id)
        self.assertEqual(observation.metadata["item"]["title"], "First video")

    def test_stop_calls_adapter_before_terminal_state(self):
        self.agent.execute(AgentAction(ActionType.STOP))

        self.assertEqual(self.adapter.stop_playback_calls, 1)
        self.assertEqual(self.agent.get_state(), AgentState.STOPPED)


if __name__ == "__main__":
    unittest.main()

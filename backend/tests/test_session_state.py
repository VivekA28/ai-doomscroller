import sys
from pathlib import Path
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent_action import ActionType, AgentAction
from src.session_state import SessionState


class SessionStateTests(unittest.TestCase):
    def test_initial_state(self):
        session = SessionState(goal="JDM")

        self.assertEqual(session.goal, "JDM")
        self.assertIsNone(session.current_topic)
        self.assertEqual(session.seen_item_ids, set())
        self.assertEqual(session.searched_topics, [])
        self.assertEqual(session.discovered_topics, [])
        self.assertEqual(session.action_history, [])

    def test_record_search_is_case_insensitive(self):
        session = SessionState(goal="JDM")

        session.record_search("JDM")
        session.record_search("RB26")
        session.record_search("jdm")

        self.assertEqual(session.current_topic, "jdm")
        self.assertEqual(session.searched_topics, ["JDM", "RB26"])

    def test_record_items_are_deduplicated(self):
        session = SessionState(goal="JDM")

        session.record_item("video-1")
        session.record_item("video-1")
        session.record_item("video-2")

        self.assertTrue(session.has_seen_item("video-1"))
        self.assertTrue(session.has_seen_item("video-2"))
        self.assertFalse(session.has_seen_item("video-3"))
        self.assertEqual(session.seen_item_ids, {"video-1", "video-2"})

    def test_discovered_topics_are_case_insensitive(self):
        session = SessionState(goal="JDM")

        session.record_discovered_topic("RB26")
        session.record_discovered_topic("drifting")
        session.record_discovered_topic("rb26")
        session.record_discovered_topic("")

        self.assertEqual(session.discovered_topics, ["RB26", "drifting"])

    def test_action_history_preserves_order(self):
        session = SessionState(goal="JDM")
        search = AgentAction(ActionType.SEARCH, "JDM")
        open_action = AgentAction(ActionType.OPEN, "video-1")

        session.record_action(search)
        session.record_action(open_action)

        self.assertEqual(session.action_history, [search, open_action])

    def test_to_dict_is_json_safe(self):
        session = SessionState(goal="JDM")
        session.current_topic = "RB26"
        session.record_item("video-2")
        session.record_item("video-1")
        session.record_search("JDM")
        session.record_discovered_topic("RB26")
        session.record_action(AgentAction(ActionType.OPEN, "video-1"))

        snapshot = session.to_dict()
        json.dumps(snapshot)

        self.assertEqual(snapshot["seen_item_ids"], ["video-1", "video-2"])
        self.assertEqual(
            snapshot["recent_actions"],
            [{"type": "open", "value": "video-1"}],
        )


if __name__ == "__main__":
    unittest.main()

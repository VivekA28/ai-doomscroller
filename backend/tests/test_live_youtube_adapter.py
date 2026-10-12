import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live_youtube_adapter import LiveYouTubeAdapter
from src.models import CandidateSignals, VideoCandidate
from src.platform_adapter import PlatformAdapter, UnsupportedOperationError


def candidate(video_id: str, title: str) -> VideoCandidate:
    return VideoCandidate(
        video_id=video_id,
        title=title,
        channel="Test Channel",
        duration_seconds=30,
        signals=CandidateSignals(duration_score=1.0, text_score=0.5),
        metadata={"title": title},
    )


class FakeDiscovery(PlatformAdapter):
    def __init__(self, results):
        self.results = results
        self.by_id = {item.video_id: item for group in results.values() for item in group}

    def search(self, query):
        return list(self.results.get(query, []))

    def open(self, item_id):
        return self.by_id[item_id]

    def scroll(self):
        raise UnsupportedOperationError("Not used by discovery adapter")

    def back(self):
        raise UnsupportedOperationError("Not used by discovery adapter")

    def wait(self):
        return None


class FakeBridge:
    def __init__(self):
        self.opened = []
        self.stop_calls = 0
        self.fail_open = False

    def open_video(self, video_id):
        if self.fail_open:
            raise RuntimeError("Browser did not acknowledge video")
        self.opened.append(video_id)
        return {"success": True, "video_id": video_id, "player_state": "cued"}

    def stop_playback(self):
        self.stop_calls += 1
        return {"success": True}


class LiveYouTubeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.first = candidate("aaaaaaaaaaa", "First")
        self.second = candidate("bbbbbbbbbbb", "Second")
        self.third = candidate("ccccccccccc", "Third")
        discovery = FakeDiscovery({"topic": [self.first, self.second, self.third]})
        self.bridge = FakeBridge()
        self.adapter = LiveYouTubeAdapter(discovery, self.bridge)

    def test_search_caches_candidates_for_navigation(self):
        found = self.adapter.search("topic")
        self.assertEqual([item.video_id for item in found], [
            "aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"
        ])

    def test_open_cues_known_video_and_updates_current_item(self):
        self.adapter.search("topic")
        opened = self.adapter.open("bbbbbbbbbbb")
        self.assertEqual(opened.video_id, "bbbbbbbbbbb")
        self.assertEqual(self.bridge.opened, ["bbbbbbbbbbb"])
        self.assertEqual(self.adapter.current_item_id, "bbbbbbbbbbb")

    def test_open_rejects_candidate_not_found_by_session_search(self):
        with self.assertRaises(ValueError):
            self.adapter.open("ddddddddddd")
        self.assertEqual(self.bridge.opened, [])

    def test_scroll_opens_next_unseen_candidate(self):
        self.adapter.search("topic")
        self.adapter.open("aaaaaaaaaaa")
        next_item = self.adapter.scroll()
        self.assertEqual(next_item.video_id, "bbbbbbbbbbb")
        self.assertEqual(self.bridge.opened, ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        self.assertEqual(self.adapter.current_item_id, "bbbbbbbbbbb")

    def test_scroll_skips_items_already_viewed(self):
        self.adapter.search("topic")
        self.adapter.open("aaaaaaaaaaa")
        self.adapter.open("bbbbbbbbbbb")
        next_item = self.adapter.scroll()
        self.assertEqual(next_item.video_id, "ccccccccccc")

    def test_scroll_requires_candidates(self):
        with self.assertRaises(UnsupportedOperationError):
            self.adapter.scroll()

    def test_scroll_fails_explicitly_when_candidates_are_exhausted(self):
        self.adapter.search("topic")
        for video_id in ("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"):
            self.adapter.open(video_id)
        with self.assertRaises(UnsupportedOperationError):
            self.adapter.scroll()

    def test_back_restores_previous_video(self):
        self.adapter.search("topic")
        self.adapter.open("aaaaaaaaaaa")
        self.adapter.open("bbbbbbbbbbb")
        previous = self.adapter.back()
        self.assertEqual(previous.video_id, "aaaaaaaaaaa")
        self.assertEqual(self.adapter.current_item_id, "aaaaaaaaaaa")
        self.assertEqual(self.bridge.opened[-1], "aaaaaaaaaaa")

    def test_back_fails_when_history_is_empty(self):
        with self.assertRaises(UnsupportedOperationError):
            self.adapter.back()

    def test_bridge_failure_does_not_change_current_item(self):
        self.adapter.search("topic")
        self.bridge.fail_open = True
        with self.assertRaises(RuntimeError):
            self.adapter.open("aaaaaaaaaaa")
        self.assertIsNone(self.adapter.current_item_id)

    def test_stop_playback_delegates_to_bridge(self):
        self.adapter.stop_playback()
        self.assertEqual(self.bridge.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()

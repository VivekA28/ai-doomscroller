import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import CandidateSignals, VideoCandidate
from src.youtube_adapter import YouTubeAdapter, UnsupportedOperationError


class FakePipeline:
    def __init__(self):
        self.store = FakeStore()
        self.search_calls = 0

    def search(self, query):
        self.search_calls += 1
        return []


class FakeStore:
    def __init__(self):
        self.candidate = None

    def get(self, video_id):
        if self.candidate is not None and self.candidate.video_id == video_id:
            return self.candidate
        return None


class YouTubeAdapterUnitTests(unittest.TestCase):
    def test_open_uses_candidate_store_without_api_client(self):
        pipeline = FakePipeline()
        candidate = VideoCandidate(
            video_id="abc123",
            title="JDM test",
            channel="Test Channel",
            duration_seconds=30,
            signals=CandidateSignals(duration_score=1.0),
            metadata={"title": "JDM test"},
        )
        pipeline.store.candidate = candidate

        adapter = YouTubeAdapter(pipeline)

        opened = adapter.open("abc123")

        self.assertIs(opened, candidate)

    def test_open_rejects_unknown_candidate(self):
        adapter = YouTubeAdapter(FakePipeline())

        with self.assertRaises(ValueError):
            adapter.open("missing")

    def test_scroll_remains_unsupported(self):
        adapter = YouTubeAdapter(FakePipeline())

        with self.assertRaises(UnsupportedOperationError):
            adapter.scroll()

    def test_back_remains_unsupported(self):
        adapter = YouTubeAdapter(FakePipeline())

        with self.assertRaises(UnsupportedOperationError):
            adapter.back()


if __name__ == "__main__":
    unittest.main()

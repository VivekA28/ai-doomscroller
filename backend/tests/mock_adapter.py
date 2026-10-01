from src.models import CandidateSignals, VideoCandidate
from src.platform_adapter import PlatformAdapter


def make_candidate(video_id: str, title: str = "Test video") -> VideoCandidate:
    return VideoCandidate(
        video_id=video_id,
        title=title,
        channel="Test Channel",
        duration_seconds=30,
        signals=CandidateSignals(duration_score=1.0, text_score=0.0),
        metadata={"title": title},
    )


class MockAdapter(PlatformAdapter):
    """Offline adapter for agent/state-machine tests."""

    def __init__(self):
        self.search_results: dict[str, list[VideoCandidate]] = {}
        self.opened: list[str] = []
        self.searches: list[str] = []
        self.back_count = 0
        self.scroll_count = 0
        self.wait_count = 0

    def add_results(self, query: str, *candidates: VideoCandidate) -> None:
        self.search_results[query] = list(candidates)

    def search(self, query: str) -> list[VideoCandidate]:
        self.searches.append(query)
        return self.search_results.get(query, [])

    def scroll(self) -> None:
        self.scroll_count += 1

    def open(self, item_id: str) -> VideoCandidate:
        for candidates in self.search_results.values():
            for candidate in candidates:
                if candidate.video_id == item_id:
                    self.opened.append(item_id)
                    return candidate
        raise ValueError(f"Unknown test candidate: {item_id}")

    def back(self) -> None:
        self.back_count += 1

    def wait(self) -> None:
        self.wait_count += 1

from src.candidate_pipeline import CandidatePipeline
from src.models import VideoCandidate
from src.platform_adapter import PlatformAdapter


class UnsupportedOperationError(Exception):
    """Raised when the current YouTube integration cannot perform an operation."""


class YouTubeAdapter(PlatformAdapter):
    """
    YouTube platform adapter.

    Current implementation supports API-based content discovery.
    UI navigation will be added through a separate permitted interface.
    """

    def __init__(self, pipeline: CandidatePipeline):
        self.pipeline = pipeline

    def search(self, query: str) -> list[VideoCandidate]:
        """Search YouTube and return newly discovered candidates."""
        return self.pipeline.search(query)

    def scroll(self) -> None:
        raise UnsupportedOperationError(
            "YouTube API does not provide feed/Shorts scrolling."
        )

    def open(self, item_id: str) -> VideoCandidate:
        """
        Open a candidate already discovered by the pipeline.

        The candidate store is authoritative for items already discovered
        during this session, so opening an item does not make another
        videos.list API request.
        """
        candidate = self.pipeline.store.get(item_id)

        if candidate is None:
            raise ValueError(
                f"YouTube video is not in the candidate store: {item_id}"
            )

        return candidate

    def back(self) -> None:
        raise UnsupportedOperationError(
            "YouTube API does not provide browser-style back navigation."
        )

    def wait(self) -> None:
        """No API operation is required for waiting."""
        return None

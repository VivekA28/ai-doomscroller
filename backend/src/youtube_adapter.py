from src.candidate_pipeline import CandidatePipeline
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

    def search(self, query: str) -> None:
        """Search YouTube and store newly discovered candidates."""
        self.pipeline.search(query)

    def scroll(self) -> None:
        raise UnsupportedOperationError(
            "YouTube API does not provide feed/Shorts scrolling."
        )

    def open(self, item_id: str) -> None:
        """
        Retrieve metadata for a known video.

        Actual content viewing will be implemented separately.
        """
        details = self.pipeline.youtube.get_videos([item_id])

        if not details.get("items"):
            raise ValueError(f"YouTube video not found: {item_id}")

    def back(self) -> None:
        raise UnsupportedOperationError(
            "YouTube API does not provide browser-style back navigation."
        )

    def wait(self) -> None:
        """No API operation is required for waiting."""
        return None

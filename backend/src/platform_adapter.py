from abc import ABC, abstractmethod

from src.models import VideoCandidate


class UnsupportedOperationError(RuntimeError):
    """Raised when an adapter cannot perform a requested operation."""


class PlatformAdapter(ABC):
    """
    Abstract interface between the agent and a content platform.

    The agent should only interact with this interface.
    Platform-specific implementation belongs in subclasses.
    """

    @abstractmethod
    def search(self, query: str) -> list[VideoCandidate]:
        """Search for content and return discovered candidates."""
        raise NotImplementedError

    @abstractmethod
    def scroll(self) -> VideoCandidate | None:
        """Move to the next content position when supported."""
        raise NotImplementedError

    @abstractmethod
    def open(self, item_id: str) -> VideoCandidate | None:
        """Open a content item and return its normalized item data, if available."""
        raise NotImplementedError

    @abstractmethod
    def back(self) -> VideoCandidate | None:
        """Return to the previous view when supported."""
        raise NotImplementedError

    @abstractmethod
    def wait(self) -> None:
        """Wait without taking another navigation action."""
        raise NotImplementedError

    def stop_playback(self) -> None:
        """Stop live playback if the adapter owns a playback surface.

        Metadata-only adapters intentionally inherit this no-op implementation.
        """
        return None

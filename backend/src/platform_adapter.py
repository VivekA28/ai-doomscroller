from abc import ABC, abstractmethod
from typing import Any

from src.models import VideoCandidate


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
    def scroll(self) -> None:
        """Move to the next content position."""
        raise NotImplementedError

    @abstractmethod
    def open(self, item_id: str) -> VideoCandidate | None:
        """
        Open a content item and return available normalized item data.

        A platform may return None when opening does not provide metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def back(self) -> None:
        """Return to the previous view."""
        raise NotImplementedError

    @abstractmethod
    def wait(self) -> None:
        """Wait without taking another navigation action."""
        raise NotImplementedError

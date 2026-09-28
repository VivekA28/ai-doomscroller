from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    """
    Abstract interface between the agent and a content platform.

    The agent should only interact with this interface.
    Platform-specific implementation belongs in subclasses.
    """

    @abstractmethod
    def search(self, query: str) -> None:
        """Search for content."""
        raise NotImplementedError

    @abstractmethod
    def scroll(self) -> None:
        """Move to the next content position."""
        raise NotImplementedError

    @abstractmethod
    def open(self, item_id: str) -> None:
        """Open a content item."""
        raise NotImplementedError

    @abstractmethod
    def back(self) -> None:
        """Return to the previous view."""
        raise NotImplementedError

    @abstractmethod
    def wait(self) -> None:
        """Wait without taking another navigation action."""
        raise NotImplementedError

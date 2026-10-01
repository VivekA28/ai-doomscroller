from typing import Any


class CandidateStore:
    """
    Session-level store for video candidates.

    video_id is the canonical identity of a video.
    """

    def __init__(self):
        self._candidates: dict[str, Any] = {}

    def add(self, candidate: Any) -> bool:
        """
        Add a candidate if its video_id has not been seen.

        Returns:
            True  -> newly added
            False -> duplicate
        """
        if candidate.video_id in self._candidates:
            return False

        self._candidates[candidate.video_id] = candidate
        return True

    def add_many(self, candidates) -> int:
        """Add multiple candidates and return the number of new ones."""
        added = 0

        for candidate in candidates:
            if self.add(candidate):
                added += 1

        return added

    def get(self, video_id: str):
        """Return a candidate by video ID, or None if unseen."""
        return self._candidates.get(video_id)

    def all(self):
        """Return all stored candidates."""
        return list(self._candidates.values())

    def __len__(self):
        return len(self._candidates)

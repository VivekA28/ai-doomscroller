"""Adapter that connects discovered YouTube candidates to the visible player.

This adapter deliberately advances through candidates discovered by the search
pipeline. It does not claim to control YouTube's native Shorts feed.
"""
from __future__ import annotations

from src.models import VideoCandidate
from src.platform_adapter import PlatformAdapter, UnsupportedOperationError


class LiveYouTubeAdapter(PlatformAdapter):
    """Wrap a discovery adapter and cue real videos in LocalPlayerBridge.

    ``discovery`` is normally the existing YouTubeAdapter. ``bridge`` is the
    LocalPlayerBridge instance serving the visible page in this same process.
    Agent actions block until the player acknowledges opening the selected video.
    """

    def __init__(self, discovery: PlatformAdapter, bridge) -> None:
        self.discovery = discovery
        self.bridge = bridge
        self._known: dict[str, VideoCandidate] = {}
        self._feed_ids: list[str] = []
        self._viewed_ids: set[str] = set()
        self._back_stack: list[str] = []
        self._current_id: str | None = None

    @property
    def current_item_id(self) -> str | None:
        """The last candidate acknowledged by the visible player."""
        return self._current_id

    def search(self, query: str) -> list[VideoCandidate]:
        """Delegate search and cache candidates for validated local navigation."""
        candidates = self.discovery.search(query)
        for candidate in candidates:
            self._known[candidate.video_id] = candidate
            if candidate.video_id not in self._feed_ids:
                self._feed_ids.append(candidate.video_id)
        return candidates

    def open(self, item_id: str) -> VideoCandidate:
        """Cue a candidate that has been returned by this session's search."""
        candidate = self._known.get(item_id)
        if candidate is None:
            raise ValueError(
                f"Video is not a known candidate in this session: {item_id}"
            )
        self._show(candidate, remember_history=True)
        return candidate

    def scroll(self) -> VideoCandidate:
        """Advance to the next unseen candidate from the local search results.

        This is candidate-list navigation inside Doomscroller, not native
        YouTube Shorts-feed scrolling. An exhausted list asks the agent to search
        or explore another topic instead of silently faking a next item.
        """
        if not self._feed_ids:
            raise UnsupportedOperationError(
                "No candidates are available; SEARCH for a topic first."
            )

        if self._current_id in self._feed_ids:
            start = self._feed_ids.index(self._current_id) + 1
        else:
            start = 0

        for offset in range(len(self._feed_ids)):
            candidate_id = self._feed_ids[(start + offset) % len(self._feed_ids)]
            if candidate_id in self._viewed_ids:
                continue
            candidate = self._known[candidate_id]
            self._show(candidate, remember_history=True)
            return candidate

        raise UnsupportedOperationError(
            "No unseen candidates remain. SEARCH or EXPLORE another topic."
        )

    def back(self) -> VideoCandidate:
        """Return to the previously opened candidate, if one exists."""
        while self._back_stack:
            previous_id = self._back_stack.pop()
            candidate = self._known.get(previous_id)
            if candidate is None or previous_id == self._current_id:
                continue
            self.bridge.open_video(previous_id)
            self._current_id = previous_id
            self._viewed_ids.add(previous_id)
            return candidate
        raise UnsupportedOperationError(
            "There is no previous video in this session's navigation history."
        )

    def wait(self) -> None:
        """No platform operation is needed for a planner WAIT action."""
        return None

    def stop_playback(self) -> None:
        """Stop actual playback in the visible player."""
        self.bridge.stop_playback()

    def _show(self, candidate: VideoCandidate, *, remember_history: bool) -> None:
        previous_id = self._current_id
        # Do not mutate local navigation state until the browser acknowledges it.
        self.bridge.open_video(candidate.video_id)
        if remember_history and previous_id and previous_id != candidate.video_id:
            self._back_stack.append(previous_id)
        self._current_id = candidate.video_id
        self._viewed_ids.add(candidate.video_id)

from typing import Any

from src.models import VideoCandidate
from src.short_detector import detect_signals, parse_duration


def build_candidate(video: dict[str, Any]) -> VideoCandidate:
    """
    Build a VideoCandidate from YouTube video metadata.
    """
    video_id = video["id"]
    snippet = video["snippet"]
    duration = video["contentDetails"]["duration"]

    duration_seconds = parse_duration(duration)

    signals = detect_signals(
        title=snippet["title"],
        duration=duration,
    )

    return VideoCandidate(
        video_id=video_id,
        title=snippet["title"],
        channel=snippet["channelTitle"],
        duration_seconds=duration_seconds,
        signals=signals,
        metadata=video,
    )

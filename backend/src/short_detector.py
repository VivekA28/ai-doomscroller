import re

from src.models import CandidateSignals


def parse_duration(duration: str) -> int:
    """
    Convert ISO 8601 YouTube duration into total seconds.

    Examples:
        PT15S    -> 15
        PT1M     -> 60
        PT1M30S  -> 90
        PT1H2M3S -> 3723
    """
    match = re.fullmatch(
        r"PT"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?",
        duration,
    )

    if not match:
        raise ValueError(f"Unsupported duration format: {duration}")

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def duration_score(duration_seconds: int) -> float:
    """
    Return a duration-based short-form signal.

    This is evidence, NOT an authoritative Shorts classification.
    """
    if duration_seconds <= 60:
        return 1.0

    if duration_seconds <= 180:
        return 0.7

    if duration_seconds <= 240:
        return 0.3

    return 0.0


def text_score(title: str) -> float:
    """
    Return a text-based short-form signal using title/hashtag clues.
    """
    text = title.lower()

    strong_terms = (
        "#shorts",
        "#short",
        "shorts",
    )

    if any(term in text for term in strong_terms):
        return 1.0

    return 0.0


def detect_signals(title: str, duration: str) -> CandidateSignals:
    """
    Generate independent signals for a YouTube video.
    """
    seconds = parse_duration(duration)

    return CandidateSignals(
        duration_score=duration_score(seconds),
        text_score=text_score(title),
        visual_score=None,
    )

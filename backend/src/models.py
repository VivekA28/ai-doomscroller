from dataclasses import dataclass
from typing import Any


@dataclass
class CandidateSignals:
    duration_score: float | None = None
    text_score: float | None = None
    visual_score: float | None = None


@dataclass
class VideoCandidate:
    video_id: str
    title: str
    channel: str
    duration_seconds: int | None
    signals: CandidateSignals
    metadata: dict[str, Any]

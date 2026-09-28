from dataclasses import dataclass, field
from typing import Any


@dataclass
class Observation:
    """
    Normalized information currently available to the agent.

    Platform-specific details remain inside metadata.
    """

    state: str
    topic: str | None = None
    current_item_id: str | None = None
    candidates: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

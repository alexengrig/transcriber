from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """One recognized phrase with times in seconds."""

    start: float
    end: float
    text: str

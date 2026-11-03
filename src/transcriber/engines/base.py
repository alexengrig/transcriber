from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from transcriber.types import Segment


@dataclass(frozen=True)
class EngineOptions:
    model: str | None = None  # None => engine default
    device: str = "auto"  # auto | cpu | cuda
    compute: str = "auto"  # engine-specific, e.g. float16 / int8
    beam_size: int = 5
    vad: bool = True
    prompt: str | None = None  # vocabulary hint (whisper only)


class Engine(Protocol):
    name: str
    description: str  # e.g. "large-v3-turbo on cuda (float16)"

    def transcribe(self, wav: Path, language: str | None) -> Iterator[Segment]:
        """Yield segments in order. `language` None means auto-detect."""
        ...

    def close(self) -> None:
        """Release model memory."""
        ...

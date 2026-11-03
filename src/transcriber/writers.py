import json
import os
from collections.abc import Sequence
from pathlib import Path

from transcriber.formatting import short_ts, srt_ts
from transcriber.types import Segment

FORMATS = ("txt", "jsonl", "srt")


def render(segments: Sequence[Segment], fmt: str, source: str) -> str:
    """Serialize segments; segments with empty text are skipped."""
    items = [(s, s.text.strip()) for s in segments if s.text.strip()]
    if fmt == "txt":
        return "".join(f"{short_ts(s.start)} {t}\n" for s, t in items)
    if fmt == "jsonl":
        return "".join(
            json.dumps(
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": t, "source": source},
                ensure_ascii=False,
            )
            + "\n"
            for s, t in items
        )
    if fmt == "srt":
        return "".join(
            f"{i}\n{srt_ts(s.start)} --> {srt_ts(s.end)}\n{t}\n\n"
            for i, (s, t) in enumerate(items, start=1)
        )
    raise ValueError(f"Unsupported format: {fmt}")


def write_atomic(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)

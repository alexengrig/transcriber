import re
from pathlib import Path


def safe_stem(path: Path) -> str:
    stem = path.stem.strip()
    stem = re.sub(r"[^\w\-. ]+", "_", stem, flags=re.UNICODE)
    return stem[:200] or "untitled"


def short_ts(seconds: float) -> str:
    """M:SS, or H:MM:SS from one hour on (YouTube-like)."""
    total = int(max(0.0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def hhmmss(seconds: float) -> str:
    total = int(max(0.0, seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def srt_ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

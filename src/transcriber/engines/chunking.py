"""Group VAD speech spans into chunks short enough for models with a length limit."""

Span = tuple[float, float]


def plan_chunks(
    spans: list[Span], max_len: float = 20.0, max_gap: float = 0.8, pad: float = 0.15,
    total: float | None = None,
) -> list[Span]:
    """Merge neighbouring spans separated by short gaps while the chunk stays <= max_len.

    Spans longer than max_len are split into equal parts (a fallback; the VAD is
    normally asked to split at silences already).
    """
    pieces: list[Span] = []
    for start, end in spans:
        n = max(1, -int(-(end - start) // max_len))
        step = (end - start) / n
        pieces += [(start + i * step, start + (i + 1) * step) for i in range(n)]

    chunks: list[list[float]] = []
    for start, end in pieces:
        if chunks and start - chunks[-1][1] <= max_gap and end - chunks[-1][0] <= max_len:
            chunks[-1][1] = end
        else:
            chunks.append([start, end])

    out: list[Span] = []
    for start, end in chunks:
        lo = max(0.0, start - pad)
        hi = end + pad if total is None else min(total, end + pad)
        out.append((lo, hi))
    return out


def split_phrases(
    words: list[tuple[float, float, str]], max_gap: float = 0.8, max_len: float = 12.0
) -> list[tuple[float, float, str]]:
    """Group timed words into phrases: break after .?! , on long pauses or long phrases."""
    out: list[tuple[float, float, str]] = []
    cur: list[tuple[float, float, str]] = []

    def flush() -> None:
        if cur:
            out.append((cur[0][0], cur[-1][1], " ".join(w[2] for w in cur)))
            cur.clear()

    for w in words:
        if cur and (w[0] - cur[-1][1] > max_gap or w[1] - cur[0][0] > max_len):
            flush()
        cur.append(w)
        if w[2].rstrip().endswith((".", "?", "!", "…")):
            flush()
    flush()
    return out

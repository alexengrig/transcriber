import json

from transcriber.formatting import short_ts, srt_ts
from transcriber.types import Segment
from transcriber.writers import render

SEGS = [Segment(0.11, 5.93, " Привет, мир. "), Segment(6.0, 7.0, "   "), Segment(3661.5, 3662, "x")]


def test_txt_skips_empty_and_uses_short_timestamps():
    assert render(SEGS, "txt", "a.mp4") == "0:00 Привет, мир.\n1:01:01 x\n"


def test_jsonl_keeps_unicode_and_source():
    first = json.loads(render(SEGS, "jsonl", "a.mp4").splitlines()[0])
    assert first == {"start": 0.11, "end": 5.93, "text": "Привет, мир.", "source": "a.mp4"}


def test_srt_numbering_and_times():
    out = render(SEGS, "srt", "a.mp4")
    assert out.startswith("1\n00:00:00,110 --> 00:00:05,930\nПривет, мир.\n\n2\n")
    assert srt_ts(3661.5) == "01:01:01,500"


def test_short_ts():
    assert short_ts(59.9) == "0:59"
    assert short_ts(3600) == "1:00:00"

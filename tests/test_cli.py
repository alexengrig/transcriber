from pathlib import Path

from transcriber.cli import default_engines, main, output_names
from transcriber.media import find_inputs


def test_colliding_stems_get_unique_names():
    names = output_names([Path("a/meeting.v1.mp4"), Path("a/meeting.v1.mkv"), Path("b/x.mp3")])
    assert names[Path("a/meeting.v1.mp4")] != names[Path("a/meeting.v1.mkv")]
    assert names[Path("b/x.mp3")] == "x"


def test_find_inputs_filters_and_recurses(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.MP4").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "sub" / "b.wav").touch()
    assert [p.name for p in find_inputs(tmp_path)] == ["a.MP4"]
    assert [p.name for p in find_inputs(tmp_path, recursive=True)] == ["a.MP4", "b.wav"]


def test_missing_input_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path / "nope.mp4")]) == 2


def test_default_engine_depends_on_language():
    assert default_engines("ru") == ["gigaam"]
    assert default_engines("en") == ["whisper"]
    assert default_engines(None) == ["whisper"]

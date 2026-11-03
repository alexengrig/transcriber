import subprocess
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS

ENHANCE_FILTER = "highpass=f=80,lowpass=f=8000,afftdn,loudnorm=I=-16:LRA=11:TP=-1.5"


def find_inputs(root: Path, recursive: bool = False) -> list[Path]:
    if root.is_file():
        return [root]
    it = root.rglob("*") if recursive else root.iterdir()
    return sorted(p for p in it if p.is_file() and p.suffix.lower() in MEDIA_EXTS)


def probe_duration(path: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(p.stdout.strip()) if p.returncode == 0 else 0.0
    except ValueError:
        return 0.0


def to_wav(src: Path, dst: Path, enhance: bool = False, sample_rate: int = 16000) -> None:
    """Convert any audio/video file to mono PCM WAV."""
    cmd = ["ffmpeg", "-nostdin", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", str(sample_rate)]
    if enhance:
        cmd += ["-af", ENHANCE_FILTER]
    cmd += ["-c:a", "pcm_s16le", str(dst)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {src.name}:\n{p.stderr[-2000:]}")

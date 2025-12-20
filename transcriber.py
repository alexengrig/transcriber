import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel

# -------------------- Supported formats --------------------

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}
ALL_EXTS = VIDEO_EXTS | AUDIO_EXTS


# -------------------- Utils --------------------

def safe_stem(path: Path) -> str:
    stem = path.stem.strip()
    stem = re.sub(r"[^\w\-. ]+", "_", stem, flags=re.UNICODE)
    return stem[:200]


def ts(seconds: float) -> str:
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"


def fmt_hhmmss(seconds: float) -> str:
    seconds = max(0.0, seconds)
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_srt_timestamp(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    hh = ms // 3600000
    ms %= 3600000
    mm = ms // 60000
    ms %= 60000
    ss = ms // 1000
    ms %= 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def parse_language(value: str) -> Optional[str]:
    """
    "auto" => None (let Whisper auto-detect)
    Otherwise => normalized language code (lowercase).
    """
    v = value.strip().lower()
    return None if v in {"auto", ""} else v


# -------------------- Audio --------------------

def ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    p = run(cmd)
    if p.returncode != 0:
        return 0.0
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def prepare_wav(
        input_path: Path,
        wav_path: Path,
        sr: int = 16000,
        enhance: bool = True,
) -> None:
    """
    Convert any supported media (audio or video) to mono 16kHz PCM WAV.
    Compatible with ffmpeg 4.4 (Ubuntu 22.04).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sr),
    ]

    if enhance:
        af = "highpass=f=80,lowpass=f=8000,afftdn,loudnorm=I=-16:LRA=11:TP=-1.5"
        cmd += ["-af", af]

    cmd += ["-c:a", "pcm_s16le", str(wav_path)]

    p = run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{p.stderr}")


# -------------------- Output writers --------------------

def write_segments_one_format(
        segments,
        input_name: str,
        out_path: Path,
        fmt: str,
) -> None:
    if fmt == "txt":
        with open(out_path, "w", encoding="utf-8") as f:
            for seg in segments:
                text = seg.text.strip()
                if text:
                    f.write(f"{ts(seg.start)} {text}\n")

    elif fmt == "jsonl":
        with open(out_path, "w", encoding="utf-8") as f:
            for seg in segments:
                text = seg.text.strip()
                if not text:
                    continue
                rec = {
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": text,
                    "source": input_name,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    elif fmt == "srt":
        with open(out_path, "w", encoding="utf-8") as f:
            idx = 1
            for seg in segments:
                text = seg.text.strip()
                if not text:
                    continue
                f.write(f"{idx}\n")
                f.write(
                    f"{format_srt_timestamp(seg.start)} --> "
                    f"{format_srt_timestamp(seg.end)}\n"
                )
                f.write(f"{text}\n\n")
                idx += 1
    else:
        raise ValueError(f"Unsupported format: {fmt}")


# -------------------- Core transcription --------------------

def transcribe_one(
        model: WhisperModel,
        input_path: Path,
        outdir: Path,
        language: Optional[str],
        formats: list[str],
        beam_size: int,
        vad_filter: bool,
        progress_step: float,
        keep_wav: bool,
        enhance_audio: bool,
):
    base = safe_stem(input_path)
    wav_path = outdir / f"{base}.wav"

    print(f"\n=== {input_path.name} ===", flush=True)
    print("1) Preparing audio…", flush=True)
    prepare_wav(input_path, wav_path, enhance=enhance_audio)

    audio_duration = ffprobe_duration(wav_path)
    if audio_duration > 0:
        print(f"[INFO] Audio duration: {fmt_hhmmss(audio_duration)}", flush=True)

    print("2) Transcribing…", flush=True)
    t0 = time.time()

    segments_iter, _info = model.transcribe(
        str(wav_path),
        language=language,  # None => auto-detect
        vad_filter=vad_filter,
        beam_size=beam_size,
        temperature=[0.0, 0.2, 0.4, 0.6],
    )

    segments = []
    last_reported = 0.0
    step = max(1.0, float(progress_step))

    for seg in segments_iter:
        segments.append(seg)

        if audio_duration > 0:
            progress = min(seg.end / audio_duration, 1.0)
            if (seg.end - last_reported >= step) or (progress >= 1.0):
                elapsed = time.time() - t0
                rtf = (seg.end / elapsed) if elapsed > 0 else 0.0
                remaining = max(0.0, audio_duration - seg.end)
                eta = remaining / rtf if rtf > 0 else 0.0
                print(
                    f"[TRANSCRIBE] {progress * 100:5.1f}% | "
                    f"audio {fmt_hhmmss(seg.end)} / {fmt_hhmmss(audio_duration)} | "
                    f"rtf {rtf:4.2f}x | ETA {fmt_hhmmss(eta)}",
                    flush=True,
                )
                last_reported = seg.end

    print("3) Writing outputs…", flush=True)

    for fmt in formats:
        out_path = (outdir / base).with_suffix(f".{fmt}")
        print(f" → {out_path.name}", flush=True)
        write_segments_one_format(
            segments=segments,
            input_name=input_path.name,
            out_path=out_path,
            fmt=fmt,
        )

    if not keep_wav:
        wav_path.unlink(missing_ok=True)

    total_elapsed = time.time() - t0
    print(f"[DONE] {input_path.name} in {fmt_hhmmss(total_elapsed)}", flush=True)


# -------------------- Input discovery --------------------

def iter_inputs(root: Path) -> list[Path]:
    if root.is_file():
        return [root]

    return sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix.lower() in ALL_EXTS
    )


# -------------------- Main --------------------

def main():
    ap = argparse.ArgumentParser("Batch transcriber (audio + video)")
    ap.add_argument("input", help="Input file or directory")
    ap.add_argument("--outdir", default="/transcripts")
    ap.add_argument("--model", default="large-v2")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--compute", default="float16")
    ap.add_argument("--language", default="auto", help="auto / en / ...")
    ap.add_argument("--beam_size", type=int, default=10)
    ap.add_argument("--no_vad", action="store_true")
    ap.add_argument("--progress_step", type=float, default=10.0)
    ap.add_argument("--keep_wav", action="store_true")
    ap.add_argument("--no_enhance_audio", action="store_true")
    ap.add_argument(
        "--formats",
        nargs="+",
        choices=["txt", "jsonl", "srt"],
        default=["txt"],
        help="Output formats (default: txt)",
    )

    args = ap.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    inputs = iter_inputs(input_path)
    if not inputs:
        print("No supported media files found.")
        return

    language = parse_language(args.language)

    print(f"[INFO] Found {len(inputs)} file(s).")
    print(
        f"[INFO] Loading model once: {args.model} "
        f"({args.device}, {args.compute})",
        flush=True,
    )
    if language is None:
        print("[INFO] Language: auto-detect", flush=True)
    else:
        print(f"[INFO] Language: {language}", flush=True)

    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute,
    )

    for idx, p in enumerate(inputs, start=1):
        print(f"\n[FILE {idx}/{len(inputs)}]", flush=True)
        transcribe_one(
            model=model,
            input_path=p,
            outdir=outdir,
            language=language,
            formats=args.formats,
            beam_size=args.beam_size,
            vad_filter=not args.no_vad,
            progress_step=args.progress_step,
            keep_wav=args.keep_wav,
            enhance_audio=not args.no_enhance_audio,
        )

    print("\nAll files processed.")


if __name__ == "__main__":
    main()

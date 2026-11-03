import argparse
import sys
import tempfile
import time
from pathlib import Path

from transcriber.engines import ENGINE_NAMES, Engine, EngineOptions, create_engine
from transcriber.formatting import hhmmss, safe_stem
from transcriber.media import find_inputs, probe_duration, to_wav
from transcriber.types import Segment
from transcriber.writers import FORMATS, render, write_atomic


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="transcriber", description="Transcribe audio and video files locally."
    )
    ap.add_argument("input", help="Audio/video file or a directory with such files")
    ap.add_argument("--outdir", default="transcripts",
                    help="Output directory (default: ./transcripts)")
    ap.add_argument(
        "--engine", nargs="+", choices=ENGINE_NAMES, metavar="ENGINE",
        help=f"One or more of {', '.join(ENGINE_NAMES)}. Default: gigaam for --language ru, "
             "whisper otherwise. Several engines run one after another, each writing to "
             "<outdir>/<engine>/ (handy for comparing quality).",
    )
    ap.add_argument("--model", help="Model name; engine default if omitted "
                    "(whisper: large-v3-turbo, gigaam: v3_e2e_rnnt). With several engines, "
                    "leave unset.")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--compute", default="auto",
                    help="whisper compute type: auto, float16, int8, int8_float16, float32")
    ap.add_argument("--language", default="auto", help="Language code (ru, en, ...) or auto")
    ap.add_argument("--beam_size", type=int, default=5)
    ap.add_argument("--prompt", help="Whisper only: text with names/terms to bias recognition, "
                    'e.g. "Acme, Jane Doe, ProjectX"')
    ap.add_argument("--no_vad", action="store_true", help="Disable voice activity detection")
    ap.add_argument("--formats", nargs="+", choices=FORMATS, default=["txt"])
    ap.add_argument("--recursive", action="store_true", help="Search directories recursively")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing transcripts")
    ap.add_argument("--progress_step", type=float, default=30.0,
                    help="Progress update interval, in seconds of audio")
    ap.add_argument("--keep_wav", action="store_true", help="Keep converted WAV in the outdir")
    ap.add_argument("--enhance_audio", action="store_true",
                    help="Apply ffmpeg denoise + loudness normalization before recognition")
    return ap


def default_engines(language: str | None) -> list[str]:
    """GigaAM for Russian, Whisper for everything else (including auto-detect)."""
    return ["gigaam"] if language == "ru" else ["whisper"]


def output_names(inputs: list[Path]) -> dict[Path, str]:
    """Base name per input; falls back to the full file name when stems collide."""
    stems = [safe_stem(p) for p in inputs]
    out = {}
    for p, stem in zip(inputs, stems, strict=True):
        out[p] = stem if stems.count(stem) == 1 else safe_stem(Path(p.name + ".x"))
    return out


def transcribe_file(
    engine: Engine, src: Path, wav_dir: Path, language: str | None, step: float,
    enhance: bool, keep_wav: bool,
) -> list[Segment]:
    wav = wav_dir / f"{safe_stem(src)}.wav"
    print("  preparing audio…", flush=True)
    to_wav(src, wav, enhance=enhance)
    try:
        duration = probe_duration(wav)
        if duration:
            print(f"  audio duration {hhmmss(duration)}", flush=True)
        t0 = time.monotonic()
        segments: list[Segment] = []
        last = 0.0
        for seg in engine.transcribe(wav, language):
            segments.append(seg)
            if duration and seg.end - last >= step:
                elapsed = time.monotonic() - t0
                speed = seg.end / elapsed if elapsed > 0 else 0.0
                eta = (duration - seg.end) / speed if speed else 0.0
                print(f"  {min(seg.end / duration, 1) * 100:5.1f}% | {speed:4.1f}x realtime"
                      f" | ETA {hhmmss(eta)}", flush=True)
                last = seg.end
        return segments
    finally:
        if not keep_wav:
            wav.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"error: {src} does not exist", file=sys.stderr)
        return 2
    if args.model and len(args.engine or []) > 1:
        print("error: --model cannot be combined with several engines", file=sys.stderr)
        return 2
    inputs = find_inputs(src, args.recursive)
    if not inputs:
        print("No supported media files found.")
        return 0

    language = args.language.strip().lower()
    language = None if language in {"", "auto"} else language
    engines = args.engine or default_engines(language)
    outroot = Path(args.outdir).expanduser().resolve()
    names = output_names(inputs)
    print(f"[info] {len(inputs)} file(s)")
    failed = 0
    summary: list[str] = []

    for engine_name in engines:
        outdir = outroot / engine_name if len(engines) > 1 else outroot
        outdir.mkdir(parents=True, exist_ok=True)
        todo = [
            p for p in inputs
            if args.overwrite
            or not all((outdir / f"{names[p]}.{f}").exists() for f in args.formats)
        ]
        for p in set(inputs) - set(todo):
            print(f"[skip] {p.name}: outputs exist (use --overwrite)")
        if not todo:
            continue

        t_load = time.monotonic()
        try:
            engine = create_engine(engine_name, EngineOptions(
                model=args.model, device=args.device, compute=args.compute,
                beam_size=args.beam_size, vad=not args.no_vad, prompt=args.prompt,
            ))
        except ImportError as exc:
            print(f"error: engine '{engine_name}' is not installed ({exc}).\n"
                  f"  install it with: uv sync --extra {engine_name}", file=sys.stderr)
            failed += 1
            continue
        print(f"\n[engine] {engine.description} (loaded in {time.monotonic() - t_load:.1f}s)")

        wav_dir = outdir if args.keep_wav else Path(tempfile.mkdtemp(prefix="transcriber-"))
        try:
            for i, p in enumerate(todo, start=1):
                print(f"\n[{i}/{len(todo)}] {p.name}", flush=True)
                t0 = time.monotonic()
                try:
                    segments = transcribe_file(
                        engine, p, wav_dir, language, max(1.0, args.progress_step),
                        args.enhance_audio, args.keep_wav,
                    )
                    for fmt in args.formats:
                        write_atomic(outdir / f"{names[p]}.{fmt}", render(segments, fmt, p.name))
                except Exception as exc:  # keep going with the remaining files
                    failed += 1
                    print(f"  [error] {p.name}: {exc}", file=sys.stderr)
                    continue
                took = time.monotonic() - t0
                summary.append(f"{engine_name}: {p.name} in {hhmmss(took)}")
                print(f"  done in {hhmmss(took)} -> {outdir}")
        finally:
            engine.close()
            if not args.keep_wav:
                try:
                    wav_dir.rmdir()
                except OSError:
                    pass

    if summary:
        print("\nSummary:\n  " + "\n  ".join(summary))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

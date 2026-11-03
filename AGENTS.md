# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

`transcriber` is a CLI that turns local audio/video files into timestamped text
(`txt`, `jsonl`, `srt`). Recognition engines are pluggable and selected with
`--engine` (default: `gigaam` for `--language ru`, `whisper` otherwise): `whisper` (faster-whisper, multilingual) and `gigaam` (GigaAM v3,
Russian). Several engines can be run in one call to compare quality.

## Layout

```text
src/transcriber/
  cli.py          argument parsing, batch loop, progress, error handling
  media.py        input discovery, ffprobe/ffmpeg helpers
  writers.py      txt / jsonl / srt rendering, atomic writes
  formatting.py   timestamp and file-name helpers
  types.py        Segment(start, end, text)
  engines/
    base.py       Engine protocol, EngineOptions
    whisper.py    faster-whisper backend
    gigaam.py     GigaAM backend (Silero VAD chunking, phrase splitting)
    chunking.py   pure helpers: VAD span merging, word -> phrase grouping
tests/            pytest; no models, GPU or network required
```

## Commands

```sh
uv sync --extra whisper --extra gigaam   # install engines (either extra alone is fine)
uv run pytest                            # tests
uv run ruff check .                      # lint
uv run transcriber <file|dir> --engine whisper gigaam --language ru --outdir transcripts
docker compose run --rm gigaam            # Russian; `whisper` service for other languages
```

`ffmpeg` and `ffprobe` must be on `PATH`.

## Conventions

- Python 3.10+ syntax, type hints, `ruff` clean (line length 100).
- Engines import their heavy dependencies lazily inside the engine module, so
  the CLI and the tests work with no engine installed. A new engine means: a
  module in `engines/`, a branch in `engines/__init__.py::create_engine`, an
  optional-dependency extra in `pyproject.toml`, tests for any pure logic.
- Keep output formats stable: TXT `M:SS text`, JSONL keys
  `start,end,text,source`, SRT with sequential cues. Add a test when touching them.
- Never fail a whole batch because of one file; report and continue, exit code 1.
- Existing outputs are skipped unless `--overwrite`; writes are atomic.
- Pin versions that matter in `pyproject.toml` and commit `uv.lock`.
  Known pins: `av<16` (faster-whisper 1.2.x is incompatible with PyAV 16+),
  GigaAM from a pinned git revision (the PyPI release is outdated).
  `engines/gigaam.py` calls GigaAM's private `forward`/`_decode`; re-check them
  when bumping that revision.

## Privacy and hygiene

This is a public project. Do not commit:

- user media, transcripts, model files, `.env` files, tokens, or absolute
  paths/usernames/hostnames from a local machine (in code, docs, tests, logs
  or examples);
- recordings of real people. Tests and examples must use synthetic audio
  (generate it with ffmpeg) or clearly licensed public material.

`videos/`, `transcripts/`, `models/`, `*.wav` and `.env*` are git-ignored; keep
local experiments there or outside the repository. Secrets, if ever needed
(e.g. `HF_TOKEN`), come from environment variables and are never printed.

## Verification expectations

Run `uv run pytest` and `uv run ruff check .` before reporting work done. Engine
changes also need a real run on a short clip (state which engine and device).
Say plainly what was not run (GPU, Docker, etc.).

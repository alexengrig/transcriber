# Project context

This document captures the current implementation before an upgrade. Update it
when behavior, dependencies, or operating assumptions change. It describes the
existing project; the upgrade ideas below are candidates, not an approved plan.

Baseline: inspected on 2026-09-30 at commit `6c2d214` on `main`.
Sources: [transcriber.py](transcriber.py), [README.md](README.md),
[Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml),
[requirements.txt](requirements.txt), and the committed demo outputs.

## Purpose and current scope

`transcriber` is a command-line tool for transcribing local audio and video files
with `faster-whisper`. It accepts one file or a directory, processes files
sequentially, and produces timestamped text, JSON Lines, and/or SubRip subtitles.
Docker with an NVIDIA GPU is the documented operating path. The CLI also exposes
CPU execution, but Compose always requests GPUs.

There is no web interface, API server, database, job queue, or background service.
The program does not download source videos, identify speakers, expose translation
as a CLI option, or export word-level timestamps.

## Repository map

| File or directory | Responsibility |
| --- | --- |
| `transcriber.py` | Entire application: arguments, input discovery, audio preparation, model invocation, progress, output writing, and WAV cleanup |
| `requirements.txt` | Direct Python dependency pins |
| `Dockerfile` | CUDA runtime, Python, FFmpeg, dependency installation, and CLI entrypoint |
| `docker-compose.yml` | GPU worker and host mounts for inputs, outputs, and model cache |
| `README.md` | Docker usage, CLI options, output examples, and historical model comparisons |
| `videos/demo.mp4` | Committed sample input, approximately 5.3 MiB |
| `transcripts/demo.{txt,jsonl,srt}` | Committed sample outputs with 17 corresponding segments |
| `.gitignore` | Ignores `.idea/`, `.venv/`, `videos/`, and `transcripts/`; already tracked demos remain tracked |
| `LICENSE` | MIT license |

No automated tests, CI configuration, Python package metadata, or dependency
lockfile are present in the inspected checkout.

## Processing flow

```text
file or directory
  -> discover inputs
  -> load one WhisperModel for the batch
  -> for each input:
       FFmpeg -> mono 16 kHz PCM WAV
       FFprobe -> duration for progress estimates
       WhisperModel.transcribe -> consume segment iterator into a list
       segment list -> selected TXT / JSONL / SRT files
       delete WAV unless --keep_wav
```

The main seams in `transcriber.py` are:

- `main()`: parse arguments, resolve paths, create the output directory, load the
  model once, and run the batch.
- `iter_inputs()`: accept an explicit file without checking its extension; for a
  directory, sort supported files in that directory only. Discovery is not recursive.
- `prepare_wav()`: invoke FFmpeg with overwrite enabled, disable video, and convert
  to mono, 16,000 Hz, signed 16-bit PCM WAV.
- `ffprobe_duration()`: read duration from the prepared WAV. A nonzero FFprobe exit
  or unparsable result returns zero, suppressing duration-based progress. A missing
  executable still raises an exception.
- `transcribe_one()`: prepare audio, invoke transcription, collect segments, report
  progress, write formats, and remove the intermediate WAV after success.
- `write_segments_one_format()`: serialize nonempty, stripped segment text.
- `safe_stem()`, `ts()`, `fmt_hhmmss()`, and `format_srt_timestamp()`: output naming
  and timestamp helpers.

Audio enhancement is enabled by default. The FFmpeg filter chain is
`highpass=f=80,lowpass=f=8000,afftdn,loudnorm=I=-16:LRA=11:TP=-1.5`.
This applies frequency filtering, noise reduction, and loudness normalization;
the repository does not contain measurements proving its effect on accuracy.

The model receives `language`, `vad_filter`, `beam_size`, and the fixed temperature
fallback list `[0.0, 0.2, 0.4, 0.6]`. Returned transcription metadata is discarded.
All segments are retained in memory before any transcript is written, allowing the
same segments to be exported in several formats.

## CLI contract

| Argument | Current default / behavior |
| --- | --- |
| `input` | Required local file or directory; expands `~` and resolves the path |
| `--outdir` | `/transcripts`; created automatically |
| `--model` | `large-v2`; passed through to `WhisperModel` |
| `--device` | `cuda`; passed through to the model |
| `--compute` | `float16`; passed as `compute_type` |
| `--language` | `auto`; blank or `auto` becomes `None`, other values are stripped and lowercased |
| `--beam_size` | `10` |
| `--no_vad` | Disable voice activity detection, which is enabled by default |
| `--progress_step` | `10.0` seconds of processed audio, internally clamped to at least one second |
| `--keep_wav` | Keep the prepared WAV; otherwise remove it after successful output writing |
| `--no_enhance_audio` | Disable the default FFmpeg filters |
| `--formats` | One or more of `txt`, `jsonl`, `srt`; default is only `txt` |

Directory discovery recognizes `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.mp3`,
`.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`, `.opus`, and `.wma`, case-insensitively.

Progress uses the latest segment end time divided by WAV duration. The displayed
`rtf` is processed audio seconds divided by elapsed wall time, so a larger value
means faster processing. Updates depend on arriving segments, not a wall-clock
timer, and a final 100% update is not guaranteed. The per-file `[DONE]` timer starts
after WAV preparation and duration probing; it includes transcription and writing,
but excludes audio preparation and initial model loading.

## Output contracts

All formats use UTF-8 and skip segments whose stripped text is empty.

| Format | Structure |
| --- | --- |
| TXT | One line per segment: start timestamp plus text. Timestamp is `M:SS`, or `H:MM:SS` for durations of at least one hour; fractional seconds are truncated. |
| JSONL | One JSON object per line with `start`, `end`, `text`, and `source`. Times are seconds rounded to two decimal places; `source` is the input filename, without its directory. Unicode is preserved. |
| SRT | Consecutive cue numbers starting at one, `HH:MM:SS,mmm` start/end times rounded to milliseconds, text, and a blank line. |

Example JSONL record:

```json
{"start": 0.11, "end": 5.31, "text": "Example speech.", "source": "demo.mp4"}
```

Output naming starts with the stripped input stem, replaces characters outside
Unicode word characters, hyphens, dots, and spaces with `_`, and truncates it to
200 characters. WAV naming appends `.wav`, while transcript naming uses
`Path.with_suffix()`. Consequently, `meeting.v1.mp4` and `meeting.v2.mp4` both
produce `meeting.txt` when TXT is selected. Equal stems, sanitization, and
truncation can also cause collisions. Existing files are overwritten.

## Runtime and deployment

- Direct Python pins: `faster-whisper==1.0.3` and `requests==2.31.0`.
  `requests` is not imported by application code. Transitive dependencies are not
  locked by this repository.
- Docker base: `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`.
- Docker apt version patterns: Python `3.10.*`, pip `22.0.*`, FFmpeg `7:4.4.*`,
  plus CA certificates. Pip is subsequently upgraded to `23.3.2`.
- The entrypoint is `python3 /app/transcriber.py`; Compose service `worker` builds
  the local Dockerfile and uses image name `transcriber`.
- Compose requests `gpus: all`, mounts `./videos` at `/videos`, `./transcripts` at
  `/transcripts`, and `~/.cache/huggingface` at `/root/.cache/huggingface`.
- Compose sets `HF_HUB_DISABLE_TELEMETRY=1` and contains a commented-out optional
  `HF_TOKEN` placeholder. Model acquisition/cache behavior belongs to the library;
  the application has no download or offline-mode management of its own.

From the repository root, the existing Docker usage is:

```sh
docker compose build worker
docker compose run --rm worker /videos --formats txt jsonl srt
docker compose run --rm worker /videos/demo.mp4 --model medium --language en --formats txt jsonl srt
```

For a host Python environment with dependencies and FFmpeg/FFprobe installed,
an explicit CPU invocation is:

```sh
python3 transcriber.py videos/demo.mp4 --outdir ./transcripts --device cpu --compute int8 --model tiny --formats txt jsonl srt
```

These are usage examples, not evidence of successful execution in this inspection.
Choosing `--device cpu` does not automatically change the default `--compute
float16`, and the default output directory remains `/transcripts` on the host.
Docker GPU execution requires a suitable host driver and container GPU support;
the README's CUDA guidance and dependency compatibility need separate verification
before changing versions.

## Constraints and upgrade candidates

The following are implementation findings, not changes made during this context
collection:

- **Naming and overwrite behavior:** there is no collision detection or overwrite
  policy. Prepared WAVs also use deterministic names in the output directory. If a
  WAV input shares its location and name with the intermediate WAV, conversion
  targets the input itself; there is no guard for this case.
- **Failure handling:** FFmpeg failures raise an exception; model and file-writing
  errors propagate. One failed file stops the batch. Cleanup is not in a `finally`
  block, so failures can leave WAVs or partial outputs. There are no retries,
  resume markers, per-file result summaries, or atomic transcript writes.
- **Input handling:** no recursive discovery, media probing before conversion,
  duplicate detection, or friendly handling of missing input paths. An empty
  supported directory prints a message and returns successfully.
- **Performance and observability:** sequential execution, full in-memory segment
  buffering, approximate progress, and no total batch timing or structured logs.
  Model metadata such as detected language is not exported.
- **Maintenance baseline:** one module, no automated regression suite or CI, and
  direct dependency pins without a full lock. The current documentation examples
  are illustrative; README transcript excerpts differ from the committed demo.

Before implementing an upgrade, decide the intended workflow (personal CLI,
larger batch processing, or another interface), target hardware, quality/speed
requirements, output compatibility, and overwrite/failure policy. Candidate first
slices are characterization checks for existing output contracts, safer filenames
and intermediate files, clearer errors and batch behavior, or a verified runtime
dependency update. Their order depends on the upgrade objective.

## Evidence and verification limits

During context collection:

- Read every tracked source/configuration file and inspected the demo outputs.
- Compiled Python source in memory successfully, without importing the application.
- Parsed all 17 demo JSONL records and checked schema, start/end ordering, source
  names, matching segment counts, and corresponding text across TXT/JSONL/SRT.
- Reproduced the dotted-stem transcript naming collision using the existing helper
  and `Path.with_suffix()` without processing media.
- Found host Python `3.12.3` and a Docker executable. `faster_whisper`, FFmpeg,
  and FFprobe were unavailable in the inspected host environment.

No container build, model download, GPU/CPU transcription, or accuracy/performance
benchmark was run. Docker daemon and host GPU readiness were not checked. The
README reports approximately 9–10 minutes per hour of media on an RTX 2060 with
`large-v2`; that is historical documentation, not a reproduced benchmark, and
the repository does not provide a benchmark harness or complete run configuration.

# transcriber

Local CLI for transcribing audio and video into timestamped text, with a choice
of speech-recognition engines:

| Engine | Model (default) | Good for |
| --- | --- | --- |
| `whisper` | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `large-v3-turbo` | 99 languages, punctuation, CPU or NVIDIA GPU |
| `gigaam` | [GigaAM](https://github.com/salute-developers/GigaAM) `v3_e2e_rnnt` (MIT) | Russian; punctuation included; fast on CPU |

Everything runs on your machine; the only network access is the one-time model download.

## Install

Requires [uv](https://docs.astral.sh/uv/) and `ffmpeg` on `PATH`.

```sh
uv sync --extra whisper            # or: --extra gigaam, or both
```

## Usage

The engine is picked from the language: `--language ru` uses GigaAM, anything
else (including auto-detect) uses Whisper. Override it with `--engine`.

```sh
# English
uv run transcriber talk.mp4 --language en --formats txt srt

# Russian (GigaAM)
uv run transcriber talk.mp4 --language ru --formats txt srt

# Any other language, or let Whisper detect it
uv run transcriber talk.mp4 --language de
uv run transcriber talk.mp4

# A whole directory, recursively
uv run transcriber ./recordings --recursive --outdir out --language ru
```

Compare engines on the same files (results go to `out/whisper/` and `out/gigaam/`,
the summary lists time per file):

```sh
uv run transcriber talk.mp4 --engine whisper gigaam --language ru --outdir out
```

Supported inputs: `.mp4 .mkv .avi .mov .webm .mp3 .wav .m4a .aac .flac .ogg .opus .wma`.
Existing outputs are skipped unless `--overwrite` is given; a failure on one file
does not stop the batch (exit code 1 at the end).

### Options

```text
input                 file or directory
--outdir DIR          output directory (default: ./transcripts)
--engine E [E ...]    whisper | gigaam (default: gigaam for ru, whisper otherwise)
--model NAME          engine-specific model (whisper: tiny … large-v3, large-v3-turbo;
                      gigaam: v3_e2e_rnnt, v3_rnnt, v3_e2e_ctc, …)
--device              auto | cpu | cuda (default: auto)
--compute TYPE        whisper compute type: auto, float16, int8, int8_float16, float32
--language CODE       ru, en, de, … or auto (default; GigaAM: ru only)
--prompt TEXT         whisper: names/terms to bias recognition ("Acme, Jane Doe, ProjectX")
--beam_size N         whisper beam size (default: 5)
--no_vad              disable voice activity detection
--formats F [F ...]   txt | jsonl | srt (default: txt)
--recursive           search directories recursively
--overwrite           overwrite existing transcripts
--progress_step SEC   progress interval in seconds of audio (default: 30)
--keep_wav            keep the converted WAV in the output directory
--enhance_audio       ffmpeg denoise + loudness normalization before recognition
```

## Output formats

TXT (YouTube-like):

```text
0:03 Hello and welcome to the weekly sync.
0:07 Let's start with the status of the release.
0:12 The migration is done, and the tests are green.
```

[JSON Lines](https://jsonlines.org/): `{"start": 3.1, "end": 6.8, "text": "Hello and welcome to the weekly sync.", "source": "talk.mp4"}`
per line. [SRT](https://en.wikipedia.org/wiki/SubRip): standard subtitles.

## NVIDIA GPU

Install a current NVIDIA driver. CUDA libraries are delivered through pip wheels,
so no CUDA Toolkit is needed. On Windows + WSL2, install the driver on Windows
only; `nvidia-smi` inside WSL should then show the card. Without a GPU the tool
falls back to CPU automatically.

## Docker

Each engine is a compose service, so a run is one short command. Put files into
`./videos`; results appear in `./transcripts`.

```sh
docker compose build                               # once

docker compose run --rm gigaam                     # Russian (GigaAM)
docker compose run --rm whisper --language en      # English (Whisper)
docker compose run --rm whisper --language de      # any other language
docker compose run --rm whisper                    # auto-detect the language
```

Extra arguments replace the defaults in `docker-compose.yml` (`--formats txt srt`,
and `--language ru` for `gigaam`), so repeat what you still need:

```sh
docker compose run --rm gigaam --language ru --formats txt jsonl srt --overwrite
```

Models are cached in the `models` volume. Remove `gpus: all` on machines without an
NVIDIA GPU. The image is large (about 12 GB) because it contains PyTorch and the CUDA
libraries for both engines; set `ENGINES` in `docker-compose.yml` to a single engine
to build a smaller one.

## Development

```sh
uv sync --extra whisper --extra gigaam
uv run pytest && uv run ruff check .
```

## License

MIT

from collections.abc import Iterator
from pathlib import Path

from transcriber.engines.base import EngineOptions
from transcriber.engines.chunking import plan_chunks, split_phrases
from transcriber.types import Segment

DEFAULT_MODEL = "v3_e2e_rnnt"  # e2e variants add punctuation and text normalization
SAMPLE_RATE = 16000
MAX_CHUNK_SECONDS = 20.0  # GigaAM accepts up to 25 s per piece
BATCH_SIZE = 8


class GigaAMEngine:
    name = "gigaam"

    def __init__(self, options: EngineOptions):
        import gigaam
        import torch

        device = options.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = options.model or DEFAULT_MODEL
        self._torch = torch
        self._vad = options.vad
        self.description = f"GigaAM {model_name} on {device}"
        self._model = gigaam.load_model(model_name, device=device)

    def _chunks(self, audio, total: float):
        """Split audio into <=20 s pieces at silences (Silero VAD)."""
        if not self._vad:
            n = max(1, -int(-total // MAX_CHUNK_SECONDS))
            step = total / n
            return [(i * step, (i + 1) * step) for i in range(n)]
        from silero_vad import get_speech_timestamps, load_silero_vad

        spans = get_speech_timestamps(
            self._torch.from_numpy(audio),
            load_silero_vad(),
            sampling_rate=SAMPLE_RATE,
            return_seconds=True,
            max_speech_duration_s=MAX_CHUNK_SECONDS,
            min_silence_duration_ms=300,
        )
        return plan_chunks(
            [(s["start"], s["end"]) for s in spans], max_len=MAX_CHUNK_SECONDS, total=total
        )

    def transcribe(self, wav: Path, language: str | None) -> Iterator[Segment]:
        import soundfile as sf

        torch = self._torch
        if language not in (None, "ru"):
            raise ValueError("GigaAM v3 supports Russian only; use --language ru or auto.")
        audio, sr = sf.read(str(wav), dtype="float32", always_2d=False)
        if sr != SAMPLE_RATE:
            raise ValueError(f"Expected {SAMPLE_RATE} Hz audio, got {sr}")
        chunks = self._chunks(audio, len(audio) / SAMPLE_RATE)

        model = self._model
        device, dtype = model._device, model._dtype
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            wavs = [
                torch.from_numpy(audio[int(a * SAMPLE_RATE) : int(b * SAMPLE_RATE)])
                for a, b in batch
            ]
            lengths = torch.tensor([len(w) for w in wavs], dtype=torch.long)
            padded = torch.zeros(len(wavs), int(lengths.max()), dtype=torch.float32)
            for j, w in enumerate(wavs):
                padded[j, : len(w)] = w
            with torch.inference_mode():
                padded, lengths = padded.to(device).to(dtype), lengths.to(device)
                encoded, encoded_len = model.forward(padded, lengths)
                decoded = model._decode(encoded, encoded_len, lengths, word_timestamps=True)
            for (a, b), (text, words) in zip(batch, decoded, strict=True):
                if not words:
                    yield Segment(a, b, text)
                    continue
                timed = [(a + w.start, a + w.end, w.text) for w in words]
                for start, end, phrase in split_phrases(timed):
                    yield Segment(start, end, phrase)

    def close(self) -> None:
        self._model = None
        if self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()

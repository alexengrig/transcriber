import ctypes
import glob
import importlib.util
import os
import sys
from collections.abc import Iterator
from pathlib import Path

from transcriber.engines.base import EngineOptions
from transcriber.types import Segment

DEFAULT_MODEL = "large-v3-turbo"


def _preload_cuda_libs() -> None:
    """Make CUDA libs from the `nvidia-*` pip wheels visible to CTranslate2 (Linux)."""
    if sys.platform != "linux":
        return
    spec = importlib.util.find_spec("nvidia")
    if spec is None or not spec.submodule_search_locations:
        return
    for root in spec.submodule_search_locations:
        for pattern in ("cublas/lib/libcublasLt.so.12", "cublas/lib/libcublas.so.12",
                        "cudnn/lib/libcudnn.so.9"):
            for lib in glob.glob(os.path.join(root, pattern)):
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class WhisperEngine:
    name = "whisper"

    def __init__(self, options: EngineOptions):
        _preload_cuda_libs()
        from faster_whisper import WhisperModel

        device = options.device
        if device == "auto":
            device = "cuda" if _cuda_available() else "cpu"
        compute = options.compute
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        model_name = options.model or DEFAULT_MODEL

        self._beam_size = options.beam_size
        self._vad = options.vad
        self._prompt = options.prompt
        self.description = f"faster-whisper {model_name} on {device} ({compute})"
        self._model = WhisperModel(model_name, device=device, compute_type=compute)

    def transcribe(self, wav: Path, language: str | None) -> Iterator[Segment]:
        segments, _info = self._model.transcribe(
            str(wav),
            language=language,
            beam_size=self._beam_size,
            vad_filter=self._vad,
            initial_prompt=self._prompt,
            # Avoids runaway repetition loops on long recordings.
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4, 0.6],
        )
        for seg in segments:
            yield Segment(seg.start, seg.end, seg.text)

    def close(self) -> None:
        self._model = None

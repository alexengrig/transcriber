"""Speech-recognition engines. Heavy dependencies are imported lazily."""

from transcriber.engines.base import Engine, EngineOptions

ENGINE_NAMES = ("whisper", "gigaam")


def create_engine(name: str, options: EngineOptions) -> Engine:
    if name == "whisper":
        from transcriber.engines.whisper import WhisperEngine

        return WhisperEngine(options)
    if name == "gigaam":
        from transcriber.engines.gigaam import GigaAMEngine

        return GigaAMEngine(options)
    raise ValueError(f"Unknown engine: {name}")


__all__ = ["ENGINE_NAMES", "Engine", "EngineOptions", "create_engine"]

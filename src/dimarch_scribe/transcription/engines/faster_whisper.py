from pathlib import Path

from .base import BaseEngine


class FasterWhisperEngine(BaseEngine):
    """CPU fallback engine. Used when whisper-cli (Vulkan) is unavailable."""

    def is_available(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe(
        self,
        audio_path: Path,
        language: str,
        model: str,
        timestamps: bool = False,
    ) -> str:
        raise NotImplementedError("faster-whisper engine not yet implemented")

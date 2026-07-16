from abc import ABC, abstractmethod
from pathlib import Path


class BaseEngine(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: str,
        model: str,
        timestamps: bool = False,
    ) -> str: ...

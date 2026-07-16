from dataclasses import dataclass, field
from pathlib import Path

from ..config import DEFAULT_LANGUAGE, DEFAULT_MODEL


@dataclass
class TranscriptionJob:
    source: Path
    output: Path
    language: str = DEFAULT_LANGUAGE
    model: str = DEFAULT_MODEL
    force: bool = False
    verbose: bool = False
    timestamps: bool = False

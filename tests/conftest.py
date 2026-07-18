import array
import wave
from pathlib import Path

import pytest

FRAMERATE = 16000


def _write_stereo_wav(path: Path, left: list[int], right: list[int]) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(FRAMERATE)
        interleaved = array.array("h")
        for l, r in zip(left, right):
            interleaved.append(l)
            interleaved.append(r)
        wf.writeframes(interleaved.tobytes())


def _tone(seconds: float, amplitude: int = 8000, freq: float = 440.0) -> list[int]:
    import math
    n = int(seconds * FRAMERATE)
    return [int(amplitude * math.sin(2 * math.pi * freq * i / FRAMERATE)) for i in range(n)]


def _silence(seconds: float) -> list[int]:
    return [0] * int(seconds * FRAMERATE)


@pytest.fixture
def make_wav(tmp_path):
    """Factory fixture: make_wav(name, left_samples, right_samples) -> Path.

    Writes a 16kHz 16-bit stereo PCM WAV, matching the format `extract_audio()`
    produces (see audio.py) — no ffmpeg needed for these unit tests.
    """
    def _make(name: str, left: list[int], right: list[int] | None = None) -> Path:
        path = tmp_path / name
        _write_stereo_wav(path, left, right if right is not None else left)
        return path
    return _make


@pytest.fixture
def tone():
    return _tone


@pytest.fixture
def silence():
    return _silence

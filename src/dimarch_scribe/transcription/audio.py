import shutil
import subprocess
import tempfile
from pathlib import Path

from ..errors import AudioExtractionError


def extract_audio(source: Path, tmp_dir: str) -> Path:
    if not shutil.which("ffmpeg"):
        raise AudioExtractionError(
            "ffmpeg not found. Install: sudo pacman -S ffmpeg"
        )

    wav_path = Path(tmp_dir) / "audio.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(wav_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioExtractionError(
            f"ffmpeg failed (exit {result.returncode}):\n{result.stderr}"
        )

    return wav_path

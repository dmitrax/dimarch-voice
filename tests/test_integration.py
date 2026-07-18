import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from dimarch_scribe.config import MODELS_DIR, WHISPER_CLI

_DSCRIBE = shutil.which("dscribe")
_HAS_WHISPER = bool(shutil.which(WHISPER_CLI)) and (MODELS_DIR / "ggml-medium.bin").exists()

pytestmark = pytest.mark.skipif(
    not (_DSCRIBE and _HAS_WHISPER),
    reason="dscribe / whisper-cli / ggml-medium.bin not available on this machine",
)


def _make_test_wav(path: Path, tone_seconds: float = 3.0, silence_seconds: float = 8.0) -> None:
    import array
    import math

    framerate = 16000
    tone_frames = int(tone_seconds * framerate)
    silence_frames = int(silence_seconds * framerate)
    samples = array.array("h")
    for i in range(tone_frames):
        v = int(6000 * math.sin(2 * math.pi * 440.0 * i / framerate))
        samples.append(v)
        samples.append(v)
    samples.extend([0] * (silence_frames * 2))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(samples.tobytes())


def _run_dscribe(wav_path: Path, out_dir: Path) -> str:
    result = subprocess.run(
        [_DSCRIBE, "transcribe", str(wav_path), "--out", str(out_dir), "--force"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    output_md = out_dir / f"{wav_path.stem}.md"
    return output_md.read_text(encoding="utf-8")


def test_trailing_silence_does_not_produce_hallucinated_text(tmp_path):
    wav = tmp_path / "tone_then_silence.wav"
    _make_test_wav(wav, tone_seconds=3.0, silence_seconds=8.0)

    text = _run_dscribe(wav, tmp_path)

    # a pure sine tone + real silence must not produce boilerplate
    # hallucination text like "Редактор субтитров" / "Субтитры" etc.
    lowered = text.lower()
    for hallucination in ["редактор субтитров", "корректор", "подписывайтесь", "субтитры"]:
        assert hallucination not in lowered


def test_output_is_deterministic_across_runs(tmp_path):
    wav = tmp_path / "determinism.wav"
    _make_test_wav(wav, tone_seconds=2.0, silence_seconds=1.0)

    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    out_a.mkdir()
    out_b.mkdir()

    text_a = _run_dscribe(wav, out_a)
    text_b = _run_dscribe(wav, out_b)

    # strip the `date:` frontmatter line (the only expected difference)
    def _strip_date(t):
        return "\n".join(line for line in t.splitlines() if not line.startswith("date:"))

    assert _strip_date(text_a) == _strip_date(text_b)

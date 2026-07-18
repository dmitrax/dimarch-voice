import array
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from ..errors import AudioExtractionError

# Dual-mono (a mono source ffmpeg just duplicated to both channels) measures
# a diff-energy ratio of exactly 0.0; real stereo separation, even a subtly
# panned mix, measured ~0.008 on a real recording. 0.001 leaves comfortable
# margin above encoding noise while still catching true dual-mono.
STEREO_DIFF_RATIO_THRESHOLD = 0.001
STEREO_CHECK_SECONDS = 10

# whisper.cpp loses punctuation on long continuous decodes (measured: ~0/100w
# over a 20-min run vs. 16-43/100w on the same content decoded standalone —
# see wiki/whisper-long-runs-lose-punctuation-chunking-is-the-fix). A fresh
# whisper-cli subprocess per chunk resets whatever decode context causes the
# degradation. 300s is the lower/safer end of the ~5-10min range that tested
# well isolated — no measured need yet to push higher.
CHUNK_SECONDS = 300

# Calibrated on a real recording's trailing dead air: true silence measured
# RMS 0.0 for 12+ continuous seconds, while natural inter-word pauses in
# speech briefly dipped as high as ~175 (never sustained). 300 sits with
# margin above real pauses and well above the silence floor.
SILENCE_RMS_THRESHOLD = 300
SILENCE_WINDOW_SECONDS = 0.2
TRAILING_SILENCE_PAD_SECONDS = 1.0


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
        # Stereo, not mono: whisper-cli's -di (stereo diarization) needs real
        # channel separation to detect speaker changes. Mono sources are just
        # duplicated to both channels by ffmpeg — diarization degrades to "no
        # signal" gracefully, it doesn't break anything.
        "-ac", "2",
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


def has_stereo_separation(wav_path: Path) -> bool:
    """Check whether the two channels carry actually different audio.

    whisper-cli's -di (stereo diarization) is a channel-energy heuristic —
    on dual-mono audio (a mono source just duplicated to both channels by
    extract_audio) it has no signal to work with and should not be trusted.
    """
    with wave.open(str(wav_path), "rb") as wf:
        if wf.getnchannels() != 2:
            return False
        n_frames = min(wf.getnframes(), STEREO_CHECK_SECONDS * wf.getframerate())
        raw = wf.readframes(n_frames)

    samples = array.array("h")
    samples.frombytes(raw[: len(raw) - len(raw) % 4])
    left = samples[0::2]
    right = samples[1::2]
    if not left:
        return False

    diff_energy = sum((l - r) ** 2 for l, r in zip(left, right))
    total_energy = sum(l * l + r * r for l, r in zip(left, right)) or 1
    return (diff_energy / total_energy) > STEREO_DIFF_RATIO_THRESHOLD


def trim_trailing_silence(wav_path: Path, tmp_dir: str) -> Path:
    """Cut dead air off the end of a WAV.

    whisper.cpp is known to hallucinate "subtitle credits"-style text
    (e.g. "Редактор субтитров...") when a decode ends on near-silence.
    Chunking exposes this: the true trailing silence of a long recording
    used to be a small, harmless piece inside one long continuous decode;
    now it sits right at the edge of the last chunk's independent decode,
    where whisper.cpp hallucinates on it. Trimming the silence removes the
    trigger instead of trying to deny-list every possible hallucinated
    phrase.
    """
    with wave.open(str(wav_path), "rb") as wf:
        params = wf.getparams()
        framerate = wf.getframerate()
        total_frames = wf.getnframes()
        window_frames = max(1, int(SILENCE_WINDOW_SECONDS * framerate))

        frame = total_frames
        while frame > 0:
            start = max(0, frame - window_frames)
            wf.setpos(start)
            raw = wf.readframes(frame - start)
            samples = array.array("h")
            samples.frombytes(raw[: len(raw) - len(raw) % 2])
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5 if samples else 0
            if rms > SILENCE_RMS_THRESHOLD:
                break
            frame = start

        keep_frames = min(total_frames, frame + int(TRAILING_SILENCE_PAD_SECONDS * framerate))
        if keep_frames >= total_frames:
            return wav_path

        wf.setpos(0)
        raw = wf.readframes(keep_frames)

    trimmed_path = Path(tmp_dir) / "trimmed.wav"
    with wave.open(str(trimmed_path), "wb") as out:
        out.setparams(params)
        out.writeframes(raw)
    return trimmed_path


def chunk_audio(
    wav_path: Path, tmp_dir: str, chunk_seconds: int = CHUNK_SECONDS
) -> list[tuple[Path, float]]:
    """Split a WAV into fixed-length chunks. Returns (chunk_path, start_offset_seconds).

    Files shorter than one chunk are returned unchanged (no copy) — chunking
    only matters for the long continuous runs where whisper.cpp's punctuation
    degrades.
    """
    with wave.open(str(wav_path), "rb") as wf:
        params = wf.getparams()
        framerate = wf.getframerate()
        total_frames = wf.getnframes()
        frames_per_chunk = chunk_seconds * framerate

        if total_frames <= frames_per_chunk:
            return [(wav_path, 0.0)]

        chunks = []
        frame_pos = 0
        idx = 0
        while frame_pos < total_frames:
            data = wf.readframes(frames_per_chunk)
            chunk_path = Path(tmp_dir) / f"chunk_{idx:03d}.wav"
            with wave.open(str(chunk_path), "wb") as out:
                out.setparams(params)
                out.writeframes(data)
            chunks.append((chunk_path, frame_pos / framerate))
            frame_pos += frames_per_chunk
            idx += 1
        return chunks

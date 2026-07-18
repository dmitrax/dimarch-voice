import wave

from dimarch_scribe.transcription.audio import (
    chunk_audio,
    has_stereo_separation,
    trim_trailing_silence,
)


def _frame_count(path):
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes()


def test_chunk_audio_short_file_returns_unchanged(make_wav, tone, tmp_path):
    wav = make_wav("short.wav", tone(3.0))
    chunks = chunk_audio(wav, str(tmp_path))
    assert chunks == [(wav, 0.0)]


def test_chunk_audio_splits_long_file_and_preserves_all_frames(make_wav, tone, tmp_path):
    total_seconds = 10.0
    wav = make_wav("long.wav", tone(total_seconds))
    original_frames = _frame_count(wav)

    chunks = chunk_audio(wav, str(tmp_path), chunk_seconds=3)

    assert len(chunks) == 4  # ceil(10/3)
    offsets = [offset for _, offset in chunks]
    assert offsets == [0.0, 3.0, 6.0, 9.0]

    total_chunked_frames = sum(_frame_count(path) for path, _ in chunks)
    assert total_chunked_frames == original_frames


def test_trim_trailing_silence_shortens_file_with_real_dead_air(make_wav, tone, silence, tmp_path):
    speech = tone(5.0)
    dead_air = silence(6.0)
    wav = make_wav("trailing_silence.wav", speech + dead_air)

    trimmed = trim_trailing_silence(wav, str(tmp_path))

    original_frames = _frame_count(wav)
    trimmed_frames = _frame_count(trimmed)
    assert trimmed_frames < original_frames
    # speech (5s) plus the 1.0s pad must survive; most of the 6s dead air is gone
    assert trimmed_frames > 5.0 * 16000


def test_trim_trailing_silence_noop_when_no_trailing_silence(make_wav, tone, tmp_path):
    wav = make_wav("no_silence.wav", tone(3.0))
    trimmed = trim_trailing_silence(wav, str(tmp_path))
    assert trimmed == wav


def test_has_stereo_separation_false_for_dual_mono(make_wav, tone, tmp_path):
    samples = tone(2.0)
    wav = make_wav("dual_mono.wav", samples, samples)
    assert has_stereo_separation(wav) is False


def test_has_stereo_separation_true_for_real_stereo(make_wav, tone, silence, tmp_path):
    left = tone(2.0, amplitude=8000)
    right = silence(2.0)
    wav = make_wav("real_stereo.wav", left, right)
    assert has_stereo_separation(wav) is True


def test_has_stereo_separation_false_for_mono_file(make_wav, tone, tmp_path):
    # a genuinely mono WAV (1 channel) — has_stereo_separation must not
    # crash and must report no separation
    import array
    path = tmp_path / "mono.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        arr = array.array("h", tone(1.0))
        wf.writeframes(arr.tobytes())
    assert has_stereo_separation(path) is False

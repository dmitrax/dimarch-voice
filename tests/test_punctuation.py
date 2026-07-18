import re

from dimarch_scribe.transcription.punctuation import restore_punctuation
from dimarch_scribe.transcription.segments import Segment


def _words_only(text: str) -> list[str]:
    """Strip everything restore_punctuation is allowed to add (inserted
    punctuation marks, capitalization) to recover the original word
    sequence for comparison — the verbatim invariant under test.
    """
    return [w.strip(".,!?;:").lower() for w in text.split()]


def test_restore_punctuation_preserves_word_sequence():
    segments = [
        Segment(start=0.0, end=2.0, speaker=None,
                text="привет как дела у меня все хорошо"),
        Segment(start=2.5, end=5.0, speaker=None,
                text="а у тебя как дела дома все в порядке"),
        Segment(start=5.5, end=8.0, speaker=None,
                text="да все отлично спасибо что спросил"),
    ]
    original_words = []
    for seg in segments:
        original_words.extend(seg.text.split())

    result = restore_punctuation(segments)

    assert _words_only(result) == [w.lower() for w in original_words]


def test_restore_punctuation_never_emits_unk():
    segments = [
        Segment(start=0.0, end=3.0, speaker=None,
                text="что-то кто-то из-за наконец-то это все дефисные слова"),
    ]
    result = restore_punctuation(segments)
    assert "<unk>" not in result.lower()
    assert "�" not in result  # unicode replacement char


def test_restore_punctuation_empty_segments_returns_empty():
    assert restore_punctuation([]) == ""


def test_restore_punctuation_only_appends_marks_or_capitalizes():
    """Stronger check than word-equality: every character of the result,
    with inserted punctuation/capitalization undone, must appear in the
    same relative order as the source — nothing reordered or substituted
    mid-word.
    """
    segments = [
        Segment(start=0.0, end=2.0, speaker=None, text="одно два три"),
        Segment(start=2.0, end=4.0, speaker=None, text="четыре пять шесть"),
    ]
    source_words = "одно два три четыре пять шесть".split()
    result = restore_punctuation(segments)
    result_words = re.findall(r"\S+", result)
    # same number of tokens, each token's lowercased-alnum core matches source
    assert len(result_words) == len(source_words)
    for src, res in zip(source_words, result_words):
        assert res.strip(".,!?;:").lower() == src.lower()

from dimarch_scribe.transcription.output import (
    MAX_PARAGRAPH_CHARS,
    MIN_PARAGRAPH_WORDS,
    _capitalize_first,
    _group_into_paragraphs,
    _merge_short_paragraphs,
    _split_run_into_paragraphs,
)
from dimarch_scribe.transcription.segments import Segment

_SENTENCE = "Это простое предложение для проверки группировки в абзацы. "


def test_group_into_paragraphs_short_text_returned_unchanged():
    text = "Короткий текст."
    assert _group_into_paragraphs(text) == [text]


def test_group_into_paragraphs_preserves_word_sequence():
    text = (_SENTENCE * 20).strip()
    assert len(text) > MAX_PARAGRAPH_CHARS  # ensure the split path is exercised

    paragraphs = _group_into_paragraphs(text)

    assert len(paragraphs) > 1
    reconstructed_words = " ".join(paragraphs).split()
    assert reconstructed_words == text.split()


def test_group_into_paragraphs_respects_hard_maximum():
    text = (_SENTENCE * 20).strip()
    paragraphs = _group_into_paragraphs(text)
    for p in paragraphs:
        assert len(p) <= MAX_PARAGRAPH_CHARS


def test_group_into_paragraphs_no_empty_paragraphs():
    text = (_SENTENCE * 20).strip()
    paragraphs = _group_into_paragraphs(text)
    assert all(p.strip() for p in paragraphs)


def test_merge_short_paragraphs_folds_trivial_fragments():
    paragraphs = ["A normal paragraph with enough words to stand alone here.", "one"]
    merged = _merge_short_paragraphs(paragraphs)
    assert len(merged) == 1
    assert "one" in merged[0]


def test_merge_short_paragraphs_keeps_paragraphs_above_threshold():
    long_enough = " ".join(["word"] * MIN_PARAGRAPH_WORDS)
    paragraphs = [long_enough, long_enough]
    merged = _merge_short_paragraphs(paragraphs)
    assert merged == paragraphs


def test_capitalize_first_only_touches_first_character():
    assert _capitalize_first("привет мир") == "Привет мир"
    assert _capitalize_first("") == ""
    assert _capitalize_first("Уже с большой") == "Уже с большой"


def test_split_run_into_paragraphs_short_run_stays_one_paragraph():
    segments = [
        Segment(start=0.0, end=1.0, speaker=None, text="привет"),
        Segment(start=1.0, end=2.0, speaker=None, text="как дела"),
    ]
    paragraphs = _split_run_into_paragraphs(segments)
    assert len(paragraphs) == 1
    assert paragraphs[0][0].isupper()

import re
from dataclasses import dataclass

_TIMESTAMP_RE = re.compile(
    r"\[(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s*"
    r"(?:\(speaker (\S+)\)\s*)?(.*)"
)

# Common Russian discourse markers/fillers — excluded from chunk-boundary
# dedup because they legitimately repeat in spontaneous speech independent
# of any chunk cut (confirmed on real data: "вот... вот эта обложка",
# "Анна Иванова" used repeatedly as a running example name). Only content
# words are deduped — see dedupe_chunk_boundary().
_FILLER_WORDS = {
    "вот", "ну", "да", "и", "а", "но", "же", "ведь", "то", "есть",
    "так", "короче", "типа", "слушай", "смотри", "смотрите", "давай",
    "давайте", "блин", "ок", "окей", "просто", "как", "бы",
}

_LEADING_WORD_RE = re.compile(r"(\S+)(\s*)(.*)", re.DOTALL)
_TRAILING_PUNCT_STRIP = ".,!?;:…"


@dataclass
class Segment:
    start: float
    end: float
    speaker: str | None
    text: str
    chunk: int = 0


def dedupe_chunk_boundary(prev_text: str, next_segment: Segment) -> None:
    """Drop a word-level duplicate at a whisper.cpp chunk-boundary cut.

    Confirmed on real data (see wiki/decision-dedupe-chunk-boundary-words):
    when a content word is spoken exactly at a hard 300s chunk cut,
    whisper.cpp sometimes transcribes it twice — once trailing off at the
    end of one chunk's decode, again at the start of the next chunk's own
    decode (e.g. "...если нет готовности..." / "готовности. Да, сейчас...").
    Only fires when the repeated word is not a common filler/discourse
    marker (those repeat legitimately in spontaneous speech regardless of
    chunking) — deleting a genuinely-spoken word would violate this
    project's verbatim guarantee, worse than leaving a rare duplicate in.
    Mutates `next_segment.text` in place; no-op if nothing to strip.
    """
    if not prev_text or not next_segment.text:
        return
    prev_word = prev_text.split()[-1] if prev_text.split() else ""
    match = _LEADING_WORD_RE.match(next_segment.text)
    if not match:
        return
    first_word, _, rest = match.groups()

    prev_clean = prev_word.strip(_TRAILING_PUNCT_STRIP).lower()
    first_clean = first_word.strip(_TRAILING_PUNCT_STRIP).lower()
    if not prev_clean or prev_clean != first_clean:
        return
    if prev_clean in _FILLER_WORDS:
        return
    next_segment.text = rest


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_segments(raw: str) -> list[Segment]:
    segments = []
    for line in raw.splitlines():
        match = _TIMESTAMP_RE.match(line.strip())
        if not match:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2, speaker, text = match.groups()
        text = text.strip()
        if not text:
            continue
        segments.append(Segment(
            start=_to_seconds(h1, m1, s1, ms1),
            end=_to_seconds(h2, m2, s2, ms2),
            speaker=speaker,
            text=text,
        ))
    return segments

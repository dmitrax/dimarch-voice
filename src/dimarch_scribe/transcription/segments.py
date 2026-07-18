import re
from dataclasses import dataclass

_TIMESTAMP_RE = re.compile(
    r"\[(\d{2}):(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s*"
    r"(?:\(speaker (\S+)\)\s*)?(.*)"
)


@dataclass
class Segment:
    start: float
    end: float
    speaker: str | None
    text: str
    chunk: int = 0


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

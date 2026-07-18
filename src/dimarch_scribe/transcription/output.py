from pathlib import Path

from .punctuation import _get_sat, restore_punctuation
from .segments import Segment

# wtpsplit's length constraints are in characters, not words. Target range
# picked from real data (see _group_into_paragraphs docstring): median
# 68-86 words/paragraph, single-sentence paragraphs down to 1-14%, on two
# real transcripts (59-min multi-speaker webinar, 3-hour monologue).
MAX_PARAGRAPH_CHARS = 600
MIN_PARAGRAPH_CHARS = 200
MIN_SEGMENTS_FOR_SPLIT = 4
MIN_PARAGRAPH_WORDS = 6


def _capitalize_first(text: str) -> str:
    """Capitalize a paragraph's first letter — whisper.cpp's own
    capitalization is inconsistent between chunks (same "decode mode" quirk
    as the punctuation-loss bug), and every paragraph start should look like
    one. A cheap, zero-risk step: unlike a punctuation-restoration model
    (evaluated and rejected — see
    wiki/whisper-long-runs-lose-punctuation-chunking-is-the-fix — it
    measurably corrupted real words, e.g. "Мы" -> "<UNK>Ы", and mangled
    common hyphenated words like "что-то" -> "что<unk>то"), this only ever
    touches one character and can't drop or replace content.
    """
    return text[0].upper() + text[1:] if text else text


def _format_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    h, total_ms = divmod(total_ms, 3_600_000)
    m, total_ms = divmod(total_ms, 60_000)
    s, ms = divmod(total_ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _speaker_runs(segments: list[Segment]) -> list[tuple[str | None, list[Segment]]]:
    """Group segments into runs, breaking only on confirmed speaker changes.

    Ambiguous tags ("?" or None) never trigger a break and don't overwrite
    the current confirmed speaker — whisper-cli's diarization flickers
    between "?" and a real id even mid-turn, so only a transition between
    two different confirmed ids counts as a real speaker change.
    """
    runs: list[tuple[str | None, list[Segment]]] = []
    current_run: list[Segment] = []
    current_speaker: str | None = None
    for seg in segments:
        confirmed = seg.speaker if seg.speaker and seg.speaker != "?" else None
        if confirmed is not None and current_speaker is not None and confirmed != current_speaker:
            runs.append((current_speaker, current_run))
            current_run = []
        current_run.append(seg)
        if confirmed is not None:
            current_speaker = confirmed
    if current_run:
        runs.append((current_speaker, current_run))
    return _merge_short_runs(runs)


def _merge_short_runs(
    runs: list[tuple[str | None, list[Segment]]],
) -> list[tuple[str | None, list[Segment]]]:
    """Fold trivially short runs into the previous one.

    Diarization flickers mid-thought (a real speaker change gets falsely
    confirmed for one or two segments); without this, that produces
    one-word paragraphs that break up a single train of thought for no
    reason.
    """
    if not runs:
        return runs
    merged = [runs[0]]
    for speaker, run_segments in runs[1:]:
        word_count = sum(len(seg.text.split()) for seg in run_segments)
        if word_count < MIN_PARAGRAPH_WORDS:
            prev_speaker, prev_segments = merged[-1]
            merged[-1] = (prev_speaker, prev_segments + run_segments)
        else:
            merged.append((speaker, run_segments))
    return merged


def _merge_short_paragraphs(paragraphs: list[str]) -> list[str]:
    """Fold trivially short paragraphs into the previous one.

    wtpsplit's own paragraph boundaries aren't guaranteed to produce a
    minimum size — it can carve a one-word fragment off a longer run on its
    own, independent of any speaker-change logic.
    """
    merged: list[str] = []
    for p in paragraphs:
        if merged and len(p.split()) < MIN_PARAGRAPH_WORDS:
            merged[-1] = f"{merged[-1]} {p}"
        else:
            merged.append(p)
    return merged


def _group_into_paragraphs(text: str) -> list[str]:
    """Split a speaker run's text into paragraphs via wtpsplit's native
    length-constrained segmentation (Viterbi search over a length prior).

    Replaces `do_paragraph_segmentation`/`paragraph_threshold` (used until
    2026-07-18). Confirmed in wtpsplit 2.2.1 source (`SaT._predict_proba`):
    without a `style`/`lang_code` mixture (never passed anywhere in this
    codebase), `clf` is `None` and the library falls back to
    `sentence_probs = newline_probs = newline_probability_fn(logits)` — the
    literal same array, not two correlated signals. `paragraph_threshold`
    was therefore just a stricter threshold on plain sentence-boundary
    probability, which is why raising it (tested 0.5 through 0.999 on real
    data) never reduced the paragraph count much: it produced ~1 paragraph
    per sentence by construction, not because of any domain mismatch.
    External audit (2026-07-18, see
    raw/gpt-audit-request-v0.2-paragraph-grouping-2026-07-18.md and its
    response) caught this; verified directly against the installed source
    before accepting it.
    Length-constrained segmentation guarantees "".join(pieces) == text — no
    risk of silently dropping or duplicating words — same mechanism already
    used in this project to split over-long paragraphs, now the only
    mechanism.
    """
    if len(text) <= MAX_PARAGRAPH_CHARS:
        return [text]
    sat = _get_sat()
    pieces = sat.split(
        text,
        min_length=MIN_PARAGRAPH_CHARS,
        max_length=MAX_PARAGRAPH_CHARS,
        prior_type="uniform",
        algorithm="viterbi",
    )
    return [p.strip() for p in pieces if p.strip()]


def _split_run_into_paragraphs(segments: list[Segment]) -> list[str]:
    text = restore_punctuation(segments)
    if len(segments) < MIN_SEGMENTS_FOR_SPLIT:
        return [_capitalize_first(text)]

    paragraphs = _group_into_paragraphs(text)
    return [_capitalize_first(p) for p in _merge_short_paragraphs(paragraphs)]


def format_body(segments: list[Segment], timestamps: bool, show_speakers: bool = False) -> str:
    if timestamps:
        lines = []
        for seg in segments:
            speaker_tag = f"(speaker {seg.speaker}) " if seg.speaker else ""
            lines.append(
                f"[{_format_timestamp(seg.start)} --> {_format_timestamp(seg.end)}]   {speaker_tag}{seg.text}"
            )
        return "\n".join(lines) + "\n"

    blocks = []
    # whisper-cli's own speaker ids are 0-indexed ("speaker 0", "speaker 1");
    # renumber to 1-indexed for display, in order of first appearance.
    speaker_numbers: dict[str, int] = {}
    for speaker, run_segments in _speaker_runs(segments):
        paragraphs = [p for p in _split_run_into_paragraphs(run_segments) if p]
        if not paragraphs:
            continue
        if show_speakers:
            # Label only the first paragraph of a turn — repeating it on
            # every wtpsplit sub-paragraph within the same speaker's turn
            # is noise, not signal.
            if speaker:
                speaker_numbers.setdefault(speaker, len(speaker_numbers) + 1)
                label = f"Speaker {speaker_numbers[speaker]}"
            else:
                label = "Speaker ?"
            paragraphs[0] = f"**{label}:** {paragraphs[0]}"
        blocks.extend(paragraphs)

    return "\n\n".join(blocks) + "\n"


def write_markdown(text: str, output: Path, meta: dict | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if meta:
        frontmatter = "---\n"
        for key, value in meta.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        text = frontmatter + text
    output.write_text(text, encoding="utf-8")

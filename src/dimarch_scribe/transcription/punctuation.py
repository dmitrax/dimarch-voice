import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm
import yaml
from huggingface_hub import hf_hub_download

from .segments import Segment

_PUNCT_REPO = "1-800-BAD-CODE/punct_cap_seg_47_language"
_PUNCT_ONNX_FILE = "punct_cap_seg_47lang.onnx"
_PUNCT_SPM_FILE = "spe_unigram_64k_lowercase_47lang.model"
_PUNCT_CONFIG_FILE = "config.yaml"

_SENTENCE_FINAL_LABELS = {".", "!"}
_QUESTION_LABELS = {"?"}
_COMMA_LABELS = {",", ";"}
_TRAILING_PUNCT = ".,!?;:…"

# First-pass thresholds on wtpsplit's per-character sentence-boundary probability,
# picked from a small real-text sample (see plan doc). Not learned — pending
# calibration against the full real test file per project convention (same as
# audio.py's RMS/energy-ratio thresholds).
SAT_HIGH = 0.6
SAT_MID = 0.3
SAT_LOW = 0.15
SAT_COMMA_HIGH = 0.2
SAT_COMMA_LOW = 0.08

# The model's own max_length (128) minus room for BOS/EOS.
_MAX_PUNCT_TOKENS = 126

_sat_model = None
_punct_model = None


def _get_sat():
    global _sat_model
    if _sat_model is None:
        from wtpsplit import SaT
        _sat_model = SaT("sat-3l-sm", ort_providers=["CPUExecutionProvider"])
    return _sat_model


@dataclass
class _PunctModel:
    session: ort.InferenceSession
    sp: spm.SentencePieceProcessor
    post_labels: list[str]


def _get_punct_model() -> "_PunctModel":
    global _punct_model
    if _punct_model is None:
        onnx_path = hf_hub_download(repo_id=_PUNCT_REPO, filename=_PUNCT_ONNX_FILE)
        spm_path = hf_hub_download(repo_id=_PUNCT_REPO, filename=_PUNCT_SPM_FILE)
        config_path = hf_hub_download(repo_id=_PUNCT_REPO, filename=_PUNCT_CONFIG_FILE)
        config = yaml.safe_load(Path(config_path).read_text())
        _punct_model = _PunctModel(
            session=ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"]),
            sp=spm.SentencePieceProcessor(model_file=spm_path),
            post_labels=config["post_labels"],
        )
    return _punct_model


def _punct_token_labels(text: str) -> list[tuple[int, int, str]]:
    """Per-token (char_start, char_end, post_label) aligned to `text`.

    Uses SentencePiece's `proto` output to get each token's exact original-text
    `surface` (never a lowercased/normalized reconstruction), and derives char
    offsets by summing surface lengths in order — verified empirically to
    reproduce `text` exactly, including through hyphenated words and pieces the
    tokenizer treats as unknown (unknown-token pieces still carry a correct
    `surface`, so their span is never touched, only their label is used).
    """
    pm = _get_punct_model()
    pieces = list(pm.sp.encode(text, out_type="proto").pieces)
    if not pieces:
        return []

    spans = []
    cursor = 0
    for piece in pieces:
        start = cursor
        cursor += len(piece.surface)
        spans.append((start, cursor))

    results = []
    for w_start in range(0, len(pieces), _MAX_PUNCT_TOKENS):
        window = pieces[w_start : w_start + _MAX_PUNCT_TOKENS]
        ids = [pm.sp.bos_id()] + [p.id for p in window] + [pm.sp.eos_id()]
        input_ids = np.array([ids], dtype=np.int64)
        _pre, post_preds, _cap, _seg = pm.session.run(None, {"input_ids": input_ids})
        labels = post_preds[0, 1:-1]
        for offset, label_id in enumerate(labels):
            label = pm.post_labels[label_id]
            if label != "<NULL>":
                start, end = spans[w_start + offset]
                results.append((start, end, label))
    return results


def _decide_mark(
    gap_start: int,
    sat_probs: np.ndarray,
    pause_by_gap_start: dict[int, float],
    punct_labels: dict[int, str],
) -> str | None:
    sat_prob = float(sat_probs[gap_start - 1]) if gap_start > 0 else 0.0
    pause = pause_by_gap_start.get(gap_start, 0.0)
    punct_label = punct_labels.get(gap_start)

    if punct_label in _QUESTION_LABELS and sat_prob > SAT_LOW:
        return "?"
    if (
        sat_prob > SAT_HIGH
        or (sat_prob > SAT_MID and pause > 0)
        or (punct_label in _SENTENCE_FINAL_LABELS and sat_prob > SAT_LOW)
    ):
        return "."
    if sat_prob > SAT_COMMA_HIGH or (punct_label in _COMMA_LABELS and sat_prob > SAT_COMMA_LOW):
        return ","
    return None


def restore_punctuation(segments: list[Segment]) -> str:
    """Insert sentence-final/comma marks and capitalize following words, fusing
    three signals: wtpsplit's continuous sentence-boundary probability, pause
    duration at segment boundaries, and a punctuation model's per-token vote.

    Safety invariant: this function only ever (a) appends one punctuation
    character immediately after a word, or (b) upper-cases a word's first
    letter. It never alters, drops, or reorders any other character — original
    words are copied through byte-for-byte via `\\S+` token matches, so no
    signal here (including the punctuation model, whose own text
    reconstruction was the source of a prior corruption bug) can ever rewrite
    ASR content.
    """
    if not segments:
        return ""

    text_parts = []
    pause_by_gap_start: dict[int, float] = {}
    cursor = 0
    for i, seg in enumerate(segments):
        text_parts.append(seg.text)
        cursor += len(seg.text)
        if i < len(segments) - 1:
            pause_by_gap_start[cursor] = max(0.0, segments[i + 1].start - seg.end)
            cursor += 1  # the joining space
    text = " ".join(text_parts)

    sat_probs = _get_sat().predict_proba(text)
    punct_labels = {end: label for _, end, label in _punct_token_labels(text)}

    words = list(re.finditer(r"\S+", text))
    result = []
    force_cap_next = False
    for i, m in enumerate(words):
        word = m.group()
        if force_cap_next:
            word = word[:1].upper() + word[1:]
            force_cap_next = False
        result.append(word)
        if i < len(words) - 1:
            gap_start = m.end()
            gap_end = words[i + 1].start()
            mark = None
            if not word or word[-1] not in _TRAILING_PUNCT:
                mark = _decide_mark(gap_start, sat_probs, pause_by_gap_start, punct_labels)
            if mark:
                result.append(mark)
                if mark in (".", "?"):
                    force_cap_next = True
            result.append(text[gap_start:gap_end])

    return "".join(result)

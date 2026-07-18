# Changelog

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

## [Unreleased]

### Added
- `--save` directory now also configurable via `[paths] save_dir` in
  `~/.config/dimarch-scribe/config.toml`, not just `SCRIBE_SAVE_DIR` env var
  (env var takes priority when both are set)
- Readable output formatting: default (non-`--timestamps`) output now breaks
  into paragraphs instead of one unbroken block of text. Uses
  [wtpsplit](https://github.com/segment-any-text/wtpsplit) (local ONNX model,
  CPU-only) length-constrained segmentation (`min_length`/`max_length`,
  Viterbi) to group sentences into human-sized paragraphs — a fixed
  silence-pause timer was tried first and rejected (real conversational
  audio rarely has pauses long enough to trigger it), and wtpsplit's own
  `do_paragraph_segmentation`/`paragraph_threshold` was tried next and also
  rejected: without a `style`/`lang_code` mixture (never used in this
  codebase), wtpsplit's source falls back to `sentence_probs = newline_probs`
  — literally the same array — so the "paragraph" threshold was just a
  stricter cutoff on plain sentence-boundary probability, producing ~1
  paragraph per sentence on real data regardless of threshold (caught by
  external audit, verified against the installed source). New required
  dependency: `wtpsplit[onnx-cpu]`.
- `--speakers`: best-effort speaker labels via whisper-cli's stereo
  diarization (`-di`, always enabled — free, same transcription pass). A
  confirmed speaker change is also used silently (without `--speakers`) as
  an extra paragraph-break signal alongside wtpsplit's topic boundaries.
- Audio chunking: files longer than 5 minutes are now split into fixed-length
  chunks and transcribed as separate whisper-cli invocations, with segment
  timestamps re-offset before stitching. Fixes whisper.cpp losing punctuation
  on long continuous decodes (measured near-zero punctuation over a 20-min
  run vs. 16-43/100 words for the same content decoded standalone) — a fresh
  subprocess per chunk resets whatever decode context causes the
  degradation. Verified end-to-end on a real 59-minute Zoom recording:
  punctuation density went from 0.5/100 words (single continuous decode) to
  21.5/100 words (chunked) — same range as isolated short-clip decodes.
  Word-level dedup at chunk boundaries (`segments.dedupe_chunk_boundary()`):
  whisper.cpp sometimes transcribes a content word twice when it's spoken
  exactly at a hard chunk cut — once trailing off at the end of one chunk's
  decode, again at the start of the next (confirmed on real data, e.g.
  "...если нет готовности..." / "готовности. Да, сейчас..."). Found during
  acceptance testing (2 confirmed duplicates across 47 chunk boundaries on
  two real files). Fix drops the repeated word from the start of the new
  chunk's segment, but only for non-filler words — common discourse markers
  ("вот", "ну", "да", ...) are left alone, since those legitimately repeat
  in spontaneous speech regardless of chunking, and silently deleting a
  genuinely-spoken word would violate this project's verbatim guarantee.
- Trailing-silence trim: dead air at the end of the audio is now cut before
  transcription. Chunking exposed a whisper.cpp quirk where a decode ending
  on near-silence gets hallucinated "subtitle credits" text appended
  (e.g. "Редактор субтитров... Корректор...") — harmless before chunking
  because that silence used to be a small piece inside one long decode, now
  a trigger sitting right at the edge of the last chunk's own decode.
  Threshold calibrated on real data: true silence measured RMS 0.0 for 12+
  continuous seconds, natural inter-word pauses in speech never sustained
  above ~175.
- Fusion punctuation restoration (`transcription/punctuation.py`): fixes
  whisper.cpp's punctuation/capitalization style drifting between chunks
  (confirmed on real data: a style switch lined up exactly with a chunk
  boundary at 00:10:00.000). Combines three signals per word gap — wtpsplit's
  continuous sentence-boundary probability, pause duration at segment
  boundaries, and a punctuation model's per-token vote — into a threshold
  gate that decides whether to insert `.`/`,`/`?` and capitalize the next
  word. An earlier attempt at this (`punct_cap_seg_47_language`'s own text
  reconstruction) was evaluated and rejected: it measurably corrupted real
  words ("Мы" → "<UNK>Ы") and mangled hyphenated words ("что-то" →
  "что<unk>то", "из-за" → "из<unk>за"). This version reuses the same
  ONNX model but bypasses its text reconstruction entirely — only its
  per-token classification is used, aligned to exact character offsets in
  the original verbatim text via SentencePiece's own `surface` field, so the
  model can never rewrite a word, only cause a punctuation mark to be
  inserted at a word boundary or a letter to be uppercased. No `torch`/
  `transformers` dependency (unlike the rejected attempt) — direct
  `onnxruntime` + `sentencepiece` inference. Verified end-to-end on two real
  files (a multi-speaker crosstalk webinar and a 3-hour single-speaker
  monologue): zero corrupted words, exact original word count preserved,
  punctuation density in the healthy 20-31/100 words range. Full writeup:
  wiki/whisper-long-runs-lose-punctuation-chunking-is-the-fix.
- `--keep-temp`: keep intermediate WAV files (extracted/trimmed/chunked
  audio) instead of deleting them after the run, for debugging the audio
  pipeline.

### Changed
- Audio preprocessing now extracts stereo (`-ac 2`) instead of mono — needed
  for `-di` to have real channel separation to work with. Mono sources are
  just duplicated to both channels by ffmpeg; diarization degrades to "no
  speaker signal" without erroring.
- Project renamed: `dimarch-voice` → `dimarch-scribe`. `voice` implied voice
  interactivity (assistant, dialogue, TTS) the project never had or will
  have — it is one-way speech-to-text. `scribe` describes the actual role.
  CLI: `dvoice` → `dscribe` (`scribe` shortcut unchanged). Env vars:
  `DVOICE_MODELS_DIR`/`DVOICE_SAVE_DIR` → `SCRIBE_MODELS_DIR`/`SCRIBE_SAVE_DIR`.
  Default paths: `~/.local/share/dimarch-scribe/models`,
  `~/.config/dimarch-scribe`.

## [0.1.0] — 2026-07-16

### Added
- Batch mode: `scribe`/`dvoice transcribe` accept multiple source paths
  (shell globs work naturally); skip-existing-unless-`--force`, per-file
  error isolation, and an end-of-run summary

### Fixed
- `--timestamps` was silently producing clean text with no timecodes.
  whisper-cli's `.txt` output never contains timestamps regardless of
  `-nt` — they only appear on stdout. Now reads stdout when
  `--timestamps` is set.

## [0.0.1] — 2026-06-28

### Added
- Project scaffold: pyproject.toml, README, LICENSE, .gitignore
- `scripts/build-whisper-cpp-vulkan.sh` — build whisper.cpp with Vulkan support
- `scripts/check-system.sh` — verify system dependencies
- `scribe FILE` — transcribe local audio/video to clean Markdown
- `dvoice transcribe FILE` — full command equivalent
- `dvoice doctor` — system readiness check (6 checks)
- `--save NAME` via `DVOICE_SAVE_DIR` env var or config
- `--out`, `--lang`, `--model`, `--force`, `--verbose`, `--dry-run`, `--timestamps` flags
- whisper.cpp Vulkan backend: AMD RX 580 (RADV POLARIS10) confirmed, GPU active in pipeline
- ffmpeg audio extraction: WAV mono 16kHz PCM s16le
- Engine abstraction: `BaseEngine` interface, `WhisperCppEngine`, `FasterWhisperEngine` (placeholder)
- Clean Markdown output: no timestamps by default, UTF-8

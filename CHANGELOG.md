# Changelog

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

## [Unreleased]

### Added
- `--save` directory now also configurable via `[paths] save_dir` in
  `~/.config/dimarch-scribe/config.toml`, not just `SCRIBE_SAVE_DIR` env var
  (env var takes priority when both are set)

### Changed
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

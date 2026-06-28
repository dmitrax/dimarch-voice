# Changelog

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

## [Unreleased]

### v0.1.0 — Local file transcription
- `--timestamps` flag — optional timestamped output (.srt, .vtt, .md)
- Batch mode via shell globs
- Full test on 23 puzzlebot-voronka videos

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

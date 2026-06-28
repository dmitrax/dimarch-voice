# Changelog

All notable changes to this project will be documented in this file.

Format: [Semantic Versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`

## [Unreleased]

### v0.1.0 — Local file transcription (in progress)
- `scribe FILE` — transcribe local audio/video to clean Markdown
- `scribe FILE --save NAME` — save to puzzlebot-voronka transcripts dir
- `dvoice transcribe FILE` — full command equivalent
- `dvoice doctor` — system readiness check
- whisper.cpp Vulkan backend (RX 580 / RADV)
- ffmpeg audio extraction pipeline

## [0.0.1] — 2026-06-28

### Added
- Project scaffold: pyproject.toml, scripts, .gitignore
- `scripts/build-whisper-cpp-vulkan.sh` — build whisper.cpp with Vulkan support
- `scripts/check-system.sh` — verify system dependencies
- whisper.cpp Vulkan backend confirmed working on AMD RX 580 (RADV POLARIS10)
- ggml-medium model integration tested: 11 sec audio → 2.5 sec transcription

# dimarch-scribe

Local speech-to-text toolkit for Arch Linux. Transcribes audio and video to clean Markdown. Clean text by default — timestamps optional.

```bash
scribe lecture.mp4
scribe interview.ogg --lang ru --save my-notes
scribe https://youtube.com/watch?v=...   # coming in v0.3
dscribe dictate                          # coming in v0.5
```

**Platform:** Arch Linux only (Wayland/Hyprland, PipeWire, AMD GPU via Vulkan/RADV).  
On macOS use [MacWhisper](https://goodsnooze.gumroad.com/l/macwhisper).

---

## Quick Start

```bash
# Transcribe a file — result appears next to the source
scribe video.mp4
# → video.md

# Save to a specific folder
scribe video.mp4 --out ~/Documents/

# Process multiple files — shell glob, skips files already transcribed
scribe ~/Videos/*.mp4 --out ~/Documents/transcripts/
```

That's it. No configuration required for basic use.

---

## Workflows

### One-off transcription
```bash
scribe video.mp4
```
Output: `video.md` next to the source file.

### Save to a project folder
Set your transcripts directory once:
```bash
# Add to ~/.zshrc
export SCRIBE_SAVE_DIR=~/Documents/transcripts
```
Then use `--save` to name the output:
```bash
scribe video.mp4 --save meeting-notes
# → ~/Documents/transcripts/meeting-notes.md
```

### Batch processing
```bash
scribe ~/Videos/*.mp4 --out ~/Documents/transcripts/
```
Files that already have a matching `.md` output are skipped; pass `--force`
to re-transcribe them. One failing file doesn't stop the rest — a summary
line at the end reports how many were transcribed, skipped, and failed.
`--save` only works with a single file (one name can't apply to many outputs).

### Check quality before saving
```bash
scribe video.mp4 --dry-run        # shows planned output path, does nothing
scribe video.mp4 --model large-v3 # use largest model for best accuracy
```

---

## Features

| Version | Feature | Status |
|---------|---------|--------|
| v0.1 | Local files (mp4, mp3, ogg, mkv, ...) | done |
| v0.1 | `--timestamps` — optional timestamped output | done |
| v0.1 | Batch mode — multiple files via shell glob | done |
| v0.2 | Readable formatting — sentence/length-based paragraphs (wtpsplit), not one text block | done |
| v0.2 | `--speakers` — best-effort speaker labels (stereo diarization) | done |
| v0.3 | Visual timeline — slide screenshots synced to transcript | planned |
| v0.4 | YouTube / web (yt-dlp) | planned |
| v0.5 | Telegram channels & chats (telethon) | planned |
| v0.6 | Dictation — mic → clipboard / type | planned |
| v0.7 | Meeting mode — mic + system audio | planned |
| v0.8 | Idea digest — local LLM summary (llama.cpp Vulkan) | planned |
| v1.0 | GTK4 GUI | planned |

---

## Requirements

- Arch Linux (primary platform)
- Python 3.12+
- ffmpeg
- whisper.cpp built with Vulkan support (see below)
- AMD GPU with RADV driver (RX 470/480/580 and newer recommended)

---

## Install

### 1. Install system dependencies (Arch Linux)

```bash
sudo pacman -S python python-pipx ffmpeg cmake vulkan-headers spirv-headers
pipx ensurepath
```

### 2. Build whisper.cpp with Vulkan

```bash
bash scripts/build-whisper-cpp-vulkan.sh
```

This clones whisper.cpp into `~/builds/whisper.cpp`, builds with `-DGGML_VULKAN=1`, and installs `whisper-cli` to `~/.local/bin/`.

### 3. Download a model

```bash
mkdir -p ~/.local/share/dimarch-scribe/models
bash ~/builds/whisper.cpp/models/download-ggml-model.sh medium \
     ~/.local/share/dimarch-scribe/models/
```

Available models: `tiny`, `base`, `small`, `medium` (default), `large-v3`.

### 4. Install dscribe / scribe

```bash
pipx install dimarch-scribe --python /usr/bin/python
```

For development (editable install):

```bash
git clone https://github.com/dmitrax/dimarch-scribe
cd dimarch-scribe
pipx install -e . --python /usr/bin/python
```

### 5. Verify

```bash
bash scripts/check-system.sh
scribe --help
```

---

## Usage

```bash
# Transcribe a file — output next to source
scribe video.mp4

# Save to custom directory
scribe video.mp4 --out ~/Desktop

# Save to configured save_dir as NAME.md
scribe video.mp4 --save my-notes

# Choose model and language
scribe audio.ogg --model large-v3 --lang ru

# Overwrite existing output
scribe video.mp4 --force

# Verbose mode (show progress)
scribe video.mp4 --verbose

# Show best-effort speaker labels (stereo diarization)
scribe meeting.mp4 --speakers

# Batch mode — multiple files, skips existing outputs unless --force
scribe ~/Videos/*.mp4 --out ~/Documents/transcripts/

# Full command equivalent
dscribe transcribe video.mp4

# System check
dscribe doctor
```

### Configure --save

`--save NAME` saves `NAME.md` to a directory you configure:

```bash
# via environment variable
export SCRIBE_SAVE_DIR=~/Documents/transcripts

# or in ~/.config/dimarch-scribe/config.toml
[paths]
save_dir = "~/Documents/transcripts"
```

The environment variable takes priority if both are set.

### Output format

Clean UTF-8 Markdown, no timestamps, broken into readable paragraphs by
sentence boundaries and length (local model,
[wtpsplit](https://github.com/segment-any-text/wtpsplit) — not a fixed pause
timer, which doesn't work for continuous speech like a busy call). This
groups sentences into human-sized blocks; it doesn't detect topic changes —
recognized words are never altered, dropped, or reordered:

```
Привет, меня зовут Дима и я хочу рассказать вам о системе которая
изменила мой подход к рекрутингу...

Сегодня я покажу три конкретных шага, с которых можно начать уже сегодня...
```

With `--speakers`, paragraphs also break on a detected speaker change and get
a label — best-effort, based on whisper.cpp's stereo channel diarization
(`-di`), not real speaker-ID:

```
**Speaker 1:** Привет, меня зовут Дима...

**Speaker 2:** Круто, давай подробнее...
```

---

## Stack

| Component | Tool |
|-----------|------|
| Transcription (GPU) | [whisper.cpp](https://github.com/ggerganov/whisper.cpp) with Vulkan/RADV |
| Transcription (CPU fallback) | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) |
| Audio processing | ffmpeg |
| YouTube / web | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Telegram | [telethon](https://github.com/LonamiWebs/Telethon) |
| CLI | [typer](https://typer.tiangolo.com/) + [rich](https://github.com/Textualize/rich) |
| Installation | [pipx](https://pipx.pypa.io/) |

---

## Hardware note

Developed and tested on AMD RX 580 (Polaris, gfx803) via RADV.

**ROCm is not used** — it does not work reliably on gfx803 with ROCm 6.x.  
Vulkan via RADV is the correct GPU path for this hardware.

---

## Development

```bash
pipx inject dimarch-scribe pytest   # or: pip install -e .[dev]
pytest
```

Integration tests that need `whisper-cli` + a downloaded model are skipped
automatically if either is missing.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

## License

MIT

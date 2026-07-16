import os
from pathlib import Path

DEFAULT_LANGUAGE = "ru"
DEFAULT_MODEL = "medium"
WHISPER_CLI = "whisper-cli"

MODELS_DIR = Path(os.environ.get("SCRIBE_MODELS_DIR", Path.home() / ".local/share/dimarch-scribe/models"))
CONFIG_DIR = Path.home() / ".config/dimarch-scribe"

# Directory used by --save NAME. Set via config.toml or SCRIBE_SAVE_DIR env var.
# Example config.toml:
#   [paths]
#   save_dir = "~/Documents/transcripts"
SAVE_DIR: Path | None = (
    Path(os.environ["SCRIBE_SAVE_DIR"]).expanduser()
    if "SCRIBE_SAVE_DIR" in os.environ
    else None
)

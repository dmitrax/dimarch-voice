import os
from pathlib import Path

DEFAULT_LANGUAGE = "ru"
DEFAULT_MODEL = "medium"
WHISPER_CLI = "whisper-cli"

MODELS_DIR = Path(os.environ.get("DVOICE_MODELS_DIR", Path.home() / ".local/share/dimarch-voice/models"))
CONFIG_DIR = Path.home() / ".config/dimarch-voice"

# Directory used by --save NAME. Set via config.toml or DVOICE_SAVE_DIR env var.
# Example config.toml:
#   [paths]
#   save_dir = "~/Documents/transcripts"
SAVE_DIR: Path | None = (
    Path(os.environ["DVOICE_SAVE_DIR"]).expanduser()
    if "DVOICE_SAVE_DIR" in os.environ
    else None
)

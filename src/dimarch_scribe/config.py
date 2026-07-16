import os
import tomllib
from pathlib import Path

from .errors import ScribeError

DEFAULT_LANGUAGE = "ru"
DEFAULT_MODEL = "medium"
WHISPER_CLI = "whisper-cli"

MODELS_DIR = Path(os.environ.get("SCRIBE_MODELS_DIR", Path.home() / ".local/share/dimarch-scribe/models"))
CONFIG_DIR = Path.home() / ".config/dimarch-scribe"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _load_config_file() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with CONFIG_FILE.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ScribeError(f"Invalid TOML in {CONFIG_FILE}: {e}") from e


def _resolve_save_dir() -> Path | None:
    if "SCRIBE_SAVE_DIR" in os.environ:
        return Path(os.environ["SCRIBE_SAVE_DIR"]).expanduser()
    save_dir = _load_config_file().get("paths", {}).get("save_dir")
    return Path(save_dir).expanduser() if save_dir else None


# Directory used by --save NAME. SCRIBE_SAVE_DIR env var takes priority over
# [paths] save_dir in ~/.config/dimarch-scribe/config.toml.
SAVE_DIR: Path | None = _resolve_save_dir()

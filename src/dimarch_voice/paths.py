from pathlib import Path

from .config import SAVE_DIR
from .errors import DvoiceError, OutputExistsError, SourceNotFoundError


def resolve_source(source: str) -> Path:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise SourceNotFoundError(f"Source not found: {path}")
    return path


def resolve_output(
    source: Path,
    save: str | None = None,
    out: str | None = None,
    force: bool = False,
) -> Path:
    if save is not None:
        if SAVE_DIR is None:
            raise DvoiceError(
                "--save requires a save directory.\n"
                "Set DVOICE_SAVE_DIR env var or add [paths] save_dir to ~/.config/dimarch-voice/config.toml"
            )
        name = save if save.endswith(".md") else f"{save}.md"
        output = SAVE_DIR / name
    elif out is not None:
        output = Path(out).expanduser() / source.with_suffix(".md").name
    else:
        output = source.with_suffix(".md")

    if output.exists() and not force:
        raise OutputExistsError(
            f"[!] Output exists: {output}\n    Use --force to overwrite."
        )

    return output

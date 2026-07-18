from typing import Annotated, Optional

import typer

from .config import DEFAULT_LANGUAGE, DEFAULT_MODEL
from .cli import _run_transcribe

app = typer.Typer(name="scribe", help="Transcribe audio/video to clean Markdown.", no_args_is_help=True)


@app.command()
def main(
    sources: Annotated[list[str], typer.Argument(help="Audio/video file(s) to transcribe — pass multiple paths or a shell glob (e.g. *.mp4) for batch mode")],
    save: Annotated[Optional[str], typer.Option("--save", help="Save as NAME.md in configured save_dir (SCRIBE_SAVE_DIR)")] = None,
    out: Annotated[Optional[str], typer.Option("--out", help="Output directory")] = None,
    lang: Annotated[str, typer.Option("--lang", help="Language code")] = DEFAULT_LANGUAGE,
    model: Annotated[str, typer.Option("--model", help="Whisper model name")] = DEFAULT_MODEL,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing output")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show progress")] = False,
    timestamps: Annotated[bool, typer.Option("--timestamps", help="Include timestamps in output")] = False,
    speakers: Annotated[bool, typer.Option("--speakers", help="Show speaker labels (stereo diarization, best-effort)")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print planned actions without running")] = False,
) -> None:
    _run_transcribe(sources, save, out, lang, model, force, verbose, timestamps, speakers, dry_run)

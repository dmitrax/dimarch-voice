from typing import Annotated, Optional

import typer
from rich.console import Console

from .config import DEFAULT_LANGUAGE, DEFAULT_MODEL
from .errors import DvoiceError
from .paths import resolve_output, resolve_source
from .cli import _run_job
from .transcription.job import TranscriptionJob

app = typer.Typer(name="scribe", help="Transcribe audio/video to clean Markdown.", no_args_is_help=True)
err = Console(stderr=True)


@app.command()
def main(
    source: Annotated[str, typer.Argument(help="Audio/video file to transcribe")],
    save: Annotated[Optional[str], typer.Option("--save", help="Save as NAME.md in configured save_dir (DVOICE_SAVE_DIR)")] = None,
    out: Annotated[Optional[str], typer.Option("--out", help="Output directory")] = None,
    lang: Annotated[str, typer.Option("--lang", help="Language code")] = DEFAULT_LANGUAGE,
    model: Annotated[str, typer.Option("--model", help="Whisper model name")] = DEFAULT_MODEL,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing output")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show progress")] = False,
    timestamps: Annotated[bool, typer.Option("--timestamps", help="Include timestamps in output")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print planned actions without running")] = False,
) -> None:
    try:
        src = resolve_source(source)
        output = resolve_output(src, save=save, out=out, force=force)

        if dry_run:
            from rich.console import Console
            console = Console()
            console.print(f"Source:  {src}")
            console.print(f"Output:  {output}")
            console.print(f"Model:   {model}  Lang: {lang}  Timestamps: {timestamps}")
            return

        _run_job(TranscriptionJob(
            source=src,
            output=output,
            language=lang,
            model=model,
            force=force,
            verbose=verbose,
            timestamps=timestamps,
        ))

    except DvoiceError as e:
        err.print(f"[red][✗][/red] {e}")
        raise typer.Exit(1)

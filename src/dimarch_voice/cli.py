import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from . import __version__
from .config import DEFAULT_LANGUAGE, DEFAULT_MODEL, MODELS_DIR, WHISPER_CLI
from .errors import DvoiceError
from .paths import resolve_output, resolve_source
from .transcription.audio import extract_audio
from .transcription.engines.whisper_cpp import WhisperCppEngine
from .transcription.job import TranscriptionJob
from .transcription.output import clean_text, write_markdown

app = typer.Typer(
    name="dvoice",
    help="Local voice toolkit for Arch Linux.",
    no_args_is_help=True,
)
console = Console()
err = Console(stderr=True)


def _run_job(job: TranscriptionJob) -> None:
    engine = WhisperCppEngine()

    with tempfile.TemporaryDirectory() as tmp:
        if job.verbose:
            console.print(f"[dim]Extracting audio from {job.source.name}...[/dim]")
        wav = extract_audio(job.source, tmp)

        if job.verbose:
            console.print(f"[dim]Transcribing with model {job.model}...[/dim]")
        raw = engine.transcribe(wav, job.language, job.model, job.timestamps, job.verbose)

    text = clean_text(raw)
    meta = {
        "source": job.source.name,
        "date": date.today().isoformat(),
        "lang": job.language,
        "model": job.model,
    }
    write_markdown(text, job.output, meta=meta)
    console.print(f"[green]→[/green] {job.output}")


@app.command()
def transcribe(
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
    """Transcribe an audio or video file to clean Markdown."""
    try:
        src = resolve_source(source)
        output = resolve_output(src, save=save, out=out, force=force)

        if dry_run:
            console.print(f"Source:  {src}")
            console.print(f"Output:  {output}")
            console.print(f"Model:   {model}  Lang: {lang}  Timestamps: {timestamps}")
            return

        job = TranscriptionJob(
            source=src,
            output=output,
            language=lang,
            model=model,
            force=force,
            verbose=verbose,
            timestamps=timestamps,
        )
        _run_job(job)

    except DvoiceError as e:
        err.print(f"[red][✗][/red] {e}")
        raise typer.Exit(1)


@app.command()
def doctor() -> None:
    """Check system readiness for dvoice."""
    ok = 0
    warn = 0
    fail = 0

    def check(label: str, cond: bool, hint: str = "", warning: bool = False) -> None:
        nonlocal ok, warn, fail
        if cond:
            console.print(f"[green][✓][/green] {label}")
            ok += 1
        elif warning:
            console.print(f"[yellow][!][/yellow] {label}")
            if hint:
                console.print(f"    {hint}")
            warn += 1
        else:
            console.print(f"[red][✗][/red] {label}")
            if hint:
                console.print(f"    {hint}")
            fail += 1

    check("ffmpeg", bool(shutil.which("ffmpeg")), "sudo pacman -S ffmpeg")
    check("whisper-cli", bool(shutil.which(WHISPER_CLI)), "bash scripts/build-whisper-cpp-vulkan.sh")
    check("pipx", bool(shutil.which("pipx")), "sudo pacman -S python-pipx && pipx ensurepath")

    vulkan_ok = bool(shutil.which("vulkaninfo"))
    check("vulkaninfo", vulkan_ok, "sudo pacman -S vulkan-tools", warning=not vulkan_ok)

    check("models dir", MODELS_DIR.is_dir(), f"mkdir -p {MODELS_DIR}")

    default_model = MODELS_DIR / f"ggml-{DEFAULT_MODEL}.bin"
    check(
        f"model: {DEFAULT_MODEL}",
        default_model.exists(),
        f"bash ~/builds/whisper.cpp/models/download-ggml-model.sh {DEFAULT_MODEL} {MODELS_DIR}/",
        warning=not default_model.exists(),
    )

    console.print()
    console.print(f"Results: {ok} ok · {warn} warnings · {fail} missing")
    if fail:
        raise typer.Exit(1)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"dvoice {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    pass

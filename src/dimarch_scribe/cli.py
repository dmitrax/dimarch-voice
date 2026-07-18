import shutil
import sys
import tempfile
from contextlib import nullcontext
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from . import __version__
from .config import DEFAULT_LANGUAGE, DEFAULT_MODEL, MODELS_DIR, WHISPER_CLI
from .errors import ScribeError, OutputExistsError
from .paths import resolve_output, resolve_source
from .transcription.audio import chunk_audio, extract_audio, has_stereo_separation, trim_trailing_silence
from .transcription.engines.whisper_cpp import WhisperCppEngine
from .transcription.job import TranscriptionJob
from .transcription.output import format_body, write_markdown
from .transcription.segments import dedupe_chunk_boundary, parse_segments

app = typer.Typer(
    name="dscribe",
    help="Local speech-to-text toolkit for Arch Linux.",
    no_args_is_help=True,
)
console = Console()
err = Console(stderr=True)


def _run_job(job: TranscriptionJob) -> None:
    engine = WhisperCppEngine()

    tmp_ctx = nullcontext(tempfile.mkdtemp(prefix="dscribe-")) if job.keep_temp else tempfile.TemporaryDirectory(prefix="dscribe-")
    with tmp_ctx as tmp:
        if job.verbose:
            console.print(f"[dim]Extracting audio from {job.source.name}...[/dim]")
        wav = trim_trailing_silence(extract_audio(job.source, tmp), tmp)
        diarize = has_stereo_separation(wav)
        if job.verbose and not diarize:
            console.print("[dim]No real stereo separation detected — skipping diarization[/dim]")

        chunks = chunk_audio(wav, tmp)
        if job.verbose:
            note = f" ({len(chunks)} chunks)" if len(chunks) > 1 else ""
            console.print(f"[dim]Transcribing with model {job.model}{note}...[/dim]")

        segments = []
        for i, (chunk_path, offset) in enumerate(chunks):
            if job.verbose and len(chunks) > 1:
                console.print(f"[dim]  chunk {i + 1}/{len(chunks)}[/dim]")
            raw = engine.transcribe(chunk_path, job.language, job.model, job.timestamps, job.verbose, diarize)
            chunk_segments = parse_segments(raw)
            for seg in chunk_segments:
                seg.start += offset
                seg.end += offset
                seg.chunk = i
            if segments and chunk_segments:
                dedupe_chunk_boundary(segments[-1].text, chunk_segments[0])
            segments.extend(chunk_segments)

        if job.keep_temp:
            console.print(f"[dim]Kept temp files: {tmp}[/dim]")

    text = format_body(segments, timestamps=job.timestamps, show_speakers=job.speakers)
    meta = {
        "source": job.source.name,
        "date": date.today().isoformat(),
        "lang": job.language,
        "model": job.model,
    }
    write_markdown(text, job.output, meta=meta)
    console.print(f"[green]→[/green] {job.output}")


def _run_transcribe(
    sources: list[str],
    save: Optional[str],
    out: Optional[str],
    lang: str,
    model: str,
    force: bool,
    verbose: bool,
    timestamps: bool,
    speakers: bool,
    dry_run: bool,
    keep_temp: bool,
) -> None:
    if save is not None and len(sources) > 1:
        err.print("[red][✗][/red] --save can only be used with a single file")
        raise typer.Exit(1)

    batch = len(sources) > 1
    transcribed = skipped = failed = 0

    def fail(raw_source: str, e: ScribeError) -> None:
        nonlocal failed
        prefix = f"{raw_source}: " if batch else ""
        err.print(f"[red][✗][/red] {prefix}{e}")
        if not batch:
            raise typer.Exit(1)
        failed += 1

    for raw_source in sources:
        try:
            src = resolve_source(raw_source)
            output = resolve_output(src, save=save, out=out, force=force)
        except OutputExistsError as e:
            if batch:
                console.print(f"[yellow][skip][/yellow] {raw_source} → exists, use --force to overwrite")
                skipped += 1
                continue
            fail(raw_source, e)
            continue
        except ScribeError as e:
            fail(raw_source, e)
            continue

        if dry_run:
            console.print(f"Source:  {src}")
            console.print(f"Output:  {output}")
            console.print(f"Model:   {model}  Lang: {lang}  Timestamps: {timestamps}")
            transcribed += 1
            continue

        try:
            _run_job(TranscriptionJob(
                source=src,
                output=output,
                language=lang,
                model=model,
                force=force,
                verbose=verbose,
                timestamps=timestamps,
                speakers=speakers,
                keep_temp=keep_temp,
            ))
            transcribed += 1
        except ScribeError as e:
            fail(raw_source, e)

    if batch:
        verb = "would transcribe" if dry_run else "transcribed"
        console.print(f"\n{len(sources)} files: {transcribed} {verb} · {skipped} skipped · {failed} failed")

    if failed:
        raise typer.Exit(1)


@app.command()
def transcribe(
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
    keep_temp: Annotated[bool, typer.Option("--keep-temp", help="Keep intermediate WAV files (extracted/trimmed/chunked audio) instead of deleting them")] = False,
) -> None:
    """Transcribe one or more audio/video files to clean Markdown."""
    _run_transcribe(sources, save, out, lang, model, force, verbose, timestamps, speakers, dry_run, keep_temp)


@app.command()
def doctor() -> None:
    """Check system readiness for dscribe."""
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
        console.print(f"dscribe {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    pass

"""Entry-point wiring tests.

dscribe (cli.py) and scribe (scribe.py) both define their own Typer
callback and independently forward every argument to _run_transcribe().
A parameter added to one call site and missed in the other doesn't fail
mypy on its own module and slips past tests that only call
_run_transcribe() directly — it must be caught by exercising each CLI
entry point for real. See scribe.py's missing `keep_temp` regression
(2026-07-19).
"""

from typer.testing import CliRunner

from dimarch_scribe.cli import app as dscribe_app
from dimarch_scribe.scribe import app as scribe_app

runner = CliRunner()


def test_dscribe_transcribe_dry_run(tmp_path):
    source = tmp_path / "input.wav"
    source.write_bytes(b"")

    result = runner.invoke(dscribe_app, ["transcribe", str(source), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Source:" in result.output


def test_scribe_dry_run(tmp_path):
    source = tmp_path / "input.wav"
    source.write_bytes(b"")

    result = runner.invoke(scribe_app, [str(source), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Source:" in result.output


def test_scribe_dry_run_with_keep_temp(tmp_path):
    """Regression: scribe.py once called _run_transcribe() without
    keep_temp, raising TypeError on every invocation regardless of flags."""
    source = tmp_path / "input.wav"
    source.write_bytes(b"")

    result = runner.invoke(scribe_app, [str(source), "--dry-run", "--keep-temp"])

    assert result.exit_code == 0, result.output

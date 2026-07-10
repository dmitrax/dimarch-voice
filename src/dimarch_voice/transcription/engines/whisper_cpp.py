import shutil
import subprocess
import tempfile
from pathlib import Path

from ...config import MODELS_DIR, WHISPER_CLI
from ...errors import EngineNotFoundError, ModelNotFoundError, TranscriptionError
from .base import BaseEngine


class WhisperCppEngine(BaseEngine):
    def is_available(self) -> bool:
        return shutil.which(WHISPER_CLI) is not None

    def transcribe(
        self,
        audio_path: Path,
        language: str,
        model: str,
        timestamps: bool = False,
        verbose: bool = False,
    ) -> str:
        if not self.is_available():
            raise EngineNotFoundError(
                f"{WHISPER_CLI} not found. Run: bash scripts/build-whisper-cpp-vulkan.sh"
            )

        model_file = MODELS_DIR / f"ggml-{model}.bin"
        if not model_file.exists():
            raise ModelNotFoundError(
                f"Model not found: {model_file}\n"
                f"Download: bash ~/builds/whisper.cpp/models/download-ggml-model.sh {model} {MODELS_DIR}/"
            )

        with tempfile.TemporaryDirectory() as tmp:
            out_base = Path(tmp) / "result"
            cmd = [
                WHISPER_CLI,
                "-m", str(model_file),
                "-f", str(audio_path),
                "-l", language,
                "-otxt",
                "-of", str(out_base),
            ]
            if not timestamps:
                cmd.append("-nt")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if verbose:
                gpu_line = next(
                    (l for l in result.stderr.splitlines() if "using Vulkan" in l or "use gpu" in l),
                    None,
                )
                if gpu_line:
                    import sys
                    print(f"  [{gpu_line.strip()}]", file=sys.stderr)

            if result.returncode != 0:
                raise TranscriptionError(
                    f"whisper-cli failed (exit {result.returncode}):\n{result.stderr}"
                )

            if timestamps:
                # whisper-cli's -otxt file never contains timestamps regardless
                # of -nt; the bracketed [start --> end] markers only appear on
                # stdout when -nt is omitted.
                return result.stdout

            out_file = out_base.with_suffix(".txt")
            if not out_file.exists():
                raise TranscriptionError("whisper-cli produced no output file")

            return out_file.read_text(encoding="utf-8")

import shutil
import subprocess
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
        diarize: bool = False,
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

        cmd = [
            WHISPER_CLI,
            "-m", str(model_file),
            "-f", str(audio_path),
            "-l", language,
        ]
        if diarize:
            # Stereo diarization: same pass, no extra cost. Caller only sets
            # this when the audio has real channel separation to work with —
            # it's a channel-energy heuristic, not real speaker ID, and gives
            # no useful signal (just noisy "?" tags) on dual-mono audio.
            cmd.append("-di")

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

        # Segment-level [start --> end] markers only appear on stdout — the
        # -otxt file never contains them regardless of -nt — and paragraph
        # formatting needs those timestamps even when the final output is
        # timestamp-free, to know where the natural pauses are.
        return result.stdout

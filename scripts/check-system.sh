#!/usr/bin/env bash
# Check system readiness for dimarch-voice.
# Run this before using dvoice or building whisper.cpp.
set -euo pipefail

MODELS_DIR="${HOME}/.local/share/dimarch-voice/models"
DEFAULT_MODEL="ggml-medium.bin"

echo "=== dvoice system check ==="
echo ""

OK=0
WARN=0
FAIL=0

check_cmd() {
    local name="$1" cmd="$2" hint="$3"
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "[✓] $name"
        (( OK++ )) || true
    else
        echo "[✗] $name not found. Install: $hint"
        (( FAIL++ )) || true
    fi
}

check_file() {
    local name="$1" path="$2" hint="$3"
    if [ -f "$path" ]; then
        echo "[✓] $name"
        (( OK++ )) || true
    else
        echo "[!] $name not found: $path"
        echo "    $hint"
        (( WARN++ )) || true
    fi
}

check_dir() {
    local name="$1" path="$2" hint="$3"
    if [ -d "$path" ]; then
        echo "[✓] $name"
        (( OK++ )) || true
    else
        echo "[!] $name not found: $path"
        echo "    $hint"
        (( WARN++ )) || true
    fi
}

# Required binaries
check_cmd "ffmpeg"      ffmpeg      "sudo pacman -S ffmpeg"
check_cmd "whisper-cli" whisper-cli "run scripts/build-whisper-cpp-vulkan.sh"
check_cmd "pipx"        pipx        "sudo pacman -S python-pipx && pipx ensurepath"

# Vulkan
if command -v vulkaninfo >/dev/null 2>&1; then
    if vulkaninfo 2>/dev/null | grep -q "GPU id"; then
        echo "[✓] Vulkan GPU detected"
        (( OK++ )) || true
    else
        echo "[!] Vulkan installed but no GPU detected"
        (( WARN++ )) || true
    fi
else
    echo "[!] vulkaninfo not found (sudo pacman -S vulkan-tools) — cannot verify GPU"
    (( WARN++ )) || true
fi

# Models
check_dir "models dir"     "$MODELS_DIR"                   "mkdir -p $MODELS_DIR"
check_file "medium model"  "$MODELS_DIR/$DEFAULT_MODEL"    "run: bash ~/builds/whisper.cpp/models/download-ggml-model.sh medium $MODELS_DIR/"

echo ""
echo "Results: ${OK} ok · ${WARN} warnings · ${FAIL} missing"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Fix missing items before running dvoice."
    exit 1
fi

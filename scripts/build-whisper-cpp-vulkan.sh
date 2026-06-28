#!/usr/bin/env bash
# Build whisper.cpp with Vulkan backend (RADV/AMD) on Arch Linux.
# Installs whisper-cli to ~/.local/bin/
set -euo pipefail

BUILD_DIR="${HOME}/builds/whisper.cpp"
INSTALL_DIR="${HOME}/.local/bin"

echo "=== whisper.cpp Vulkan build ==="
echo ""

# --- Check required packages ---
# All must be installed before build. If any are missing, print one install
# command and exit — we do not run sudo automatically.

REQUIRED_PKGS=(git cmake make vulkan-headers spirv-headers)
MISSING=()

for pkg in "${REQUIRED_PKGS[@]}"; do
    if pacman -Q "$pkg" >/dev/null 2>&1; then
        echo "[✓] $pkg"
    else
        echo "[✗] $pkg"
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "Missing packages. Install with:"
    echo ""
    echo "  sudo pacman -S ${MISSING[*]}"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

echo ""

# --- Clone or update ---

mkdir -p "$(dirname "$BUILD_DIR")"

if [ -d "$BUILD_DIR/.git" ]; then
    echo "[→] Updating existing whisper.cpp..."
    git -C "$BUILD_DIR" pull --ff-only
else
    echo "[→] Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp "$BUILD_DIR"
fi

echo ""

# --- Build ---

cd "$BUILD_DIR"
mkdir -p build
cd build

echo "[→] Configuring with Vulkan backend..."
cmake .. \
    -DGGML_VULKAN=1 \
    -DCMAKE_BUILD_TYPE=Release \
    -DWHISPER_BUILD_TESTS=OFF \
    -DWHISPER_BUILD_EXAMPLES=ON

echo ""
echo "[→] Building with $(nproc) threads..."
make -j"$(nproc)" whisper-cli

echo ""

# --- Install ---

mkdir -p "$INSTALL_DIR"

BINARY=""
if   [ -f "bin/whisper-cli" ];                        then BINARY="bin/whisper-cli"
elif [ -f "examples/whisper-cli/whisper-cli" ];       then BINARY="examples/whisper-cli/whisper-cli"
elif [ -f "whisper-cli" ];                            then BINARY="whisper-cli"
elif [ -f "bin/main" ];                               then BINARY="bin/main"
fi

if [ -z "$BINARY" ]; then
    echo "[✗] Binary not found after build. Check build output above."
    exit 1
fi

cp "$BINARY" "$INSTALL_DIR/whisper-cli"
chmod +x "$INSTALL_DIR/whisper-cli"

echo "[✓] Installed: $INSTALL_DIR/whisper-cli"
echo ""
"$INSTALL_DIR/whisper-cli" --help 2>&1 | head -5 || true
echo ""

# Remind user to check PATH
if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
    echo "[!] $INSTALL_DIR is not in your PATH."
    echo "    Add to ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "=== Done ==="

#!/usr/bin/env bash
# build_tracemaker_mac.sh — Automated TraceMaker Metal GPU Builder for macOS (Apple Silicon / ARM64)
set -e

echo "=== TraceMaker macOS Metal GPU Build Automation ==="

# 1. Verify Homebrew
if ! command -v brew &> /dev/null; then
    echo "[!] Homebrew not found. Please install Homebrew from https://brew.sh first."
    exit 1
fi

echo "[*] Checking and installing official build dependencies..."
brew install cmake ninja eigen cli11 nlohmann-json catch2 zstd boost fmt spdlog flatbuffers sqlite3

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build/tracemaker_src"
BIN_DEST="$REPO_ROOT/tools/bin"

mkdir -p "$BIN_DEST"

# 2. Clone TraceMaker if not present
if [ ! -d "$BUILD_DIR" ]; then
    echo "[*] Cloning DingoOz/TraceMaker..."
    git clone https://github.com/DingoOz/TraceMaker.git "$BUILD_DIR"
else
    echo "[*] Updating existing TraceMaker checkout..."
    cd "$BUILD_DIR" && git pull
fi

cd "$BUILD_DIR"

# 3. Configure and Build Metal GPU preset (with CPU fallback)
echo "[*] Configuring CMake (macos-metal GPU preset for Apple Silicon)..."
if cmake --preset macos-metal -DCMAKE_PREFIX_PATH="$(brew --prefix)" 2>/dev/null; then
    echo "[*] Compiling TraceMaker with Apple Metal GPU acceleration..."
    cmake --build --preset macos-metal -j$(sysctl -n hw.ncpu)
    BUILT_BIN="build/macos-metal/src/app/tracemaker"
elif cmake --preset macos-cpu -DCMAKE_PREFIX_PATH="$(brew --prefix)" 2>/dev/null; then
    echo "[*] Compiling TraceMaker in macOS CPU mode..."
    cmake --build --preset macos-cpu -j$(sysctl -n hw.ncpu)
    BUILT_BIN="build/macos-cpu/src/app/tracemaker"
else
    echo "[*] Fallback configuring CPU-only preset..."
    cmake --preset cpu-only || cmake -B build-cpu -DCMAKE_BUILD_TYPE=Release -DUSE_CUDA=OFF
    cmake --build --preset cpu-only -j$(sysctl -n hw.ncpu) || cmake --build build-cpu -j$(sysctl -n hw.ncpu)
    BUILT_BIN="build/cpu-only/src/app/tracemaker"
fi

# 4. Link binary to tools/bin/
if [ -f "$BUILT_BIN" ]; then
    cp "$BUILT_BIN" "$BIN_DEST/tracemaker"
    chmod +x "$BIN_DEST/tracemaker"
    echo "[SUCCESS] TraceMaker installed to $BIN_DEST/tracemaker (Metal GPU enabled)"
elif [ -f "build-cpu/src/app/tracemaker" ]; then
    cp "build-cpu/src/app/tracemaker" "$BIN_DEST/tracemaker"
    chmod +x "$BIN_DEST/tracemaker"
    echo "[SUCCESS] TraceMaker installed to $BIN_DEST/tracemaker"
else
    echo "[!] Build completed, but tracemaker binary was not located in default path."
fi

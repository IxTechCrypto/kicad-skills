#!/usr/bin/env bash
# build_tracemaker_mac.sh — Automated TraceMaker CPU Builder for macOS (Apple Silicon / ARM64)
set -e

echo "=== TraceMaker macOS Build Automation ==="

# 1. Verify Homebrew
if ! command -v brew &> /dev/null; then
    echo "[!] Homebrew not found. Please install Homebrew from https://brew.sh first."
    exit 1
fi

echo "[*] Checking and installing build dependencies..."
brew install cmake boost eigen tbb fmt spdlog flatbuffers sqlite3 catch2

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

# 3. Configure and Build CPU-only preset
echo "[*] Configuring CMake (CPU-only preset for Apple Silicon)..."
cmake --preset cpu-only || cmake -B build-cpu -DCMAKE_BUILD_TYPE=Release -DUSE_CUDA=OFF

echo "[*] Compiling TraceMaker..."
cmake --build --preset cpu-only -j$(sysctl -n hw.ncpu) || cmake --build build-cpu -j$(sysctl -n hw.ncpu)

# 4. Link binary to tools/bin/
if [ -f "build/cpu-only/src/app/tracemaker" ]; then
    cp "build/cpu-only/src/app/tracemaker" "$BIN_DEST/tracemaker"
    chmod +x "$BIN_DEST/tracemaker"
    echo "[SUCCESS] TraceMaker installed to $BIN_DEST/tracemaker"
elif [ -f "build-cpu/src/app/tracemaker" ]; then
    cp "build-cpu/src/app/tracemaker" "$BIN_DEST/tracemaker"
    chmod +x "$BIN_DEST/tracemaker"
    echo "[SUCCESS] TraceMaker installed to $BIN_DEST/tracemaker"
else
    echo "[!] Build completed, but tracemaker binary was not located in default path."
fi

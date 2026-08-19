#!/bin/bash
# Build whisper.cpp and install the tiny English model for TouchPlayer.

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this script with sudo: sudo $0"
    exit 1
fi

WHISPER_DIR="${WHISPER_DIR:-/opt/whisper.cpp}"
MODEL_DIR="${MODEL_DIR:-/opt/touchplayer/models}"
MODEL_PATH="${MODEL_DIR}/ggml-tiny.en.bin"
MODEL_URL="${WHISPER_MODEL_URL:-https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin}"
BUILD_JOBS="${WHISPER_BUILD_JOBS:-2}"

install -d -o pi -g pi "$MODEL_DIR"

if [[ ! -d "$WHISPER_DIR/.git" ]]; then
    rm -rf "$WHISPER_DIR"
    git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
fi

cmake -S "$WHISPER_DIR" -B "$WHISPER_DIR/build" \
    -DWHISPER_BUILD_TESTS=OFF \
    -DWHISPER_BUILD_EXAMPLES=ON \
    -DWHISPER_BUILD_SERVER=OFF
cmake --build "$WHISPER_DIR/build" --config Release --target whisper-cli -j"$BUILD_JOBS"

WHISPER_BIN="$WHISPER_DIR/build/bin/whisper-cli"
if [[ ! -x "$WHISPER_BIN" ]]; then
    echo "whisper-cli was not produced at $WHISPER_BIN" >&2
    exit 1
fi
install -m 755 "$WHISPER_BIN" /usr/local/bin/whisper-cli

if [[ ! -s "$MODEL_PATH" ]]; then
    temp_model="${MODEL_PATH}.part"
    rm -f "$temp_model"
    curl -fL --retry 3 --retry-delay 2 "$MODEL_URL" -o "$temp_model"
    test -s "$temp_model"
    mv "$temp_model" "$MODEL_PATH"
fi
chown pi:pi "$MODEL_PATH"
chmod 644 "$MODEL_PATH"

echo "Whisper installed: /usr/local/bin/whisper-cli"
echo "Whisper model ready: $MODEL_PATH"

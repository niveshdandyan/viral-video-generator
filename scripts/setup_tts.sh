#!/usr/bin/env bash
# Setup Piper TTS - neural text-to-speech engine
# Installs piper-tts and downloads the voice model if not already present

set -euo pipefail

PIPER_BIN="/home/node/.local/bin/piper"
VOICE_DIR="/tmp/piper-voices"
VOICE_MODEL="en_US-amy-medium"
VOICE_FILE="${VOICE_DIR}/${VOICE_MODEL}.onnx"
VOICE_JSON="${VOICE_DIR}/${VOICE_MODEL}.onnx.json"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"

echo "=== Piper TTS Setup ==="

# Install piper-tts if not present
if ! command -v piper &>/dev/null && [ ! -f "$PIPER_BIN" ]; then
    echo "Installing piper-tts..."
    pip install piper-tts pathvalidate --break-system-packages --quiet
    echo "Piper TTS installed."
else
    echo "Piper TTS already installed."
fi

# Download voice model if not present
mkdir -p "$VOICE_DIR"

if [ ! -f "$VOICE_FILE" ]; then
    echo "Downloading voice model: ${VOICE_MODEL}..."
    curl -sL "${HF_BASE}/${VOICE_MODEL}.onnx" -o "$VOICE_FILE"
    echo "Voice model downloaded ($(du -sh "$VOICE_FILE" | cut -f1))."
else
    echo "Voice model already present."
fi

if [ ! -f "$VOICE_JSON" ]; then
    echo "Downloading voice config..."
    curl -sL "${HF_BASE}/${VOICE_MODEL}.onnx.json" -o "$VOICE_JSON"
    echo "Voice config downloaded."
else
    echo "Voice config already present."
fi

# Setup ffmpeg if not present
FFMPEG_DIR="/tmp/ffmpeg-7.0.2-amd64-static"
FFMPEG_BIN="${FFMPEG_DIR}/ffmpeg"

if [ ! -f "$FFMPEG_BIN" ]; then
    echo "Downloading ffmpeg static build..."
    curl -sL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" -o /tmp/ffmpeg-static.tar.xz
    cd /tmp && tar xf ffmpeg-static.tar.xz
    rm -f /tmp/ffmpeg-static.tar.xz
    echo "ffmpeg installed at ${FFMPEG_BIN}."
else
    echo "ffmpeg already present at ${FFMPEG_BIN}."
fi

echo ""
echo "=== Setup Complete ==="
echo "Piper: ${PIPER_BIN}"
echo "Voice: ${VOICE_FILE}"
echo "ffmpeg: ${FFMPEG_BIN}"
echo "ffprobe: ${FFMPEG_DIR}/ffprobe"

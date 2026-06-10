#!/bin/bash

# BYOVA AI Simulator - Startup Script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CODE_DIR="$SCRIPT_DIR/code"

# Check system dependencies required for STT/TTS (pydub + SpeechRecognition)
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠️  ffmpeg not found. Install it: brew install ffmpeg"
    exit 1
fi
if ! command -v flac &>/dev/null; then
    echo "⚠️  flac not found. Install it: brew install flac"
    exit 1
fi
if ! brew list libsndfile &>/dev/null 2>&1; then
    echo "⚠️  libsndfile not found. Install it: brew install libsndfile"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv "$SCRIPT_DIR/.venv"
    echo "Virtual environment created."
fi

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r "$CODE_DIR/requirements.txt" --quiet

# Fetch proto schemas from GitHub
echo "Fetching proto schemas..."
cd "$CODE_DIR"
python fetch_proto_schema.py

# Generate Python code from proto files
echo "Generating gRPC code from proto files..."
cd "$CODE_DIR/src"
python -m grpc_tools.protoc -I./proto --python_out=./proto --grpc_python_out=./proto ./proto/*.proto

# Start the gRPC server
echo "Starting BYOVA AI Simulator server..."
cd "$SCRIPT_DIR"
python "$CODE_DIR/src/server/AIAgentServer.py"

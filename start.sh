#!/bin/bash
# Launcher for AnimeUnity Downloader
# Usage:
#   ./start.sh          — desktop GUI (tkinter)
#   ./start.sh --web    — web GUI (browser, FastAPI)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not found. Creating it with the system Python..."
    /usr/bin/python3 -m venv "$SCRIPT_DIR/.venv"
fi

if [ "$1" = "--web" ]; then
    echo "Starting AnimeUnity Downloader (web GUI)..."
    exec "$VENV_PYTHON" "$SCRIPT_DIR/web_gui.py"
else
    echo "Starting AnimeUnity Downloader..."
    exec "$VENV_PYTHON" "$SCRIPT_DIR/launch_gui.py"
fi

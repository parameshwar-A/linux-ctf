#!/usr/bin/env bash
# Linux CTF - TUI Launcher Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Ensure venv exists
if [ ! -f ".venv/bin/python" ]; then
    echo "[*] Initializing virtual environment with uv..."
    if command -v uv >/dev/null 2>&1; then
        uv venv .venv
        uv pip install --python .venv/bin/python -r requirements.txt
    else
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt
    fi
fi

exec .venv/bin/python -m linux_ctf

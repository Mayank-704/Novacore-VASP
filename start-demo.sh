#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r backend/requirements.txt
printf '\nOpen http://127.0.0.1:8000 in your browser. Stop with Ctrl+C.\n'
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

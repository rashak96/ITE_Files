#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -q -r requirements_web.txt
python build_live.py
exec python -m uvicorn main:app --host 0.0.0.0 --port 8080

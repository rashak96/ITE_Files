"""
Render / uvicorn entrypoint (repo root).
Keeps start command simple: uvicorn main:app
"""
from live_ite.app import app

__all__ = ["app"]

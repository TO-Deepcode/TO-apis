"""FastAPI entrypoint shim for Vercel framework detection."""

from api.index import app, handler

__all__ = ["app", "handler"]

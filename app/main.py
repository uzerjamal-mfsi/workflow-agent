"""Minimal application entry point."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

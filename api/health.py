"""GET /api/health — quick env + version probe for the frontend."""

from __future__ import annotations

import os

from fastapi import FastAPI

from sherlock import __version__

app = FastAPI()


@app.get("/api/health")
def health() -> dict:
    return {
        "version": __version__,
        "has_anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "has_apollo_key": bool(os.getenv("APOLLO_API_KEY")),
    }

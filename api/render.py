"""POST /api/render — pure render. Pass in the dossier + section bodies,
get back the styled HTML brief. No LLM calls, finishes in well under
a second.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sherlock.dossier import dossier_from_dict
from sherlock.render.html import render_html
from sherlock.render.markdown import render_markdown

app = FastAPI()


class RenderRequest(BaseModel):
    dossier: dict
    sections: dict[str, str]
    format: str = "html"  # "html" | "md"


@app.post("/api/render")
def render(req: RenderRequest) -> dict:
    try:
        dossier = dossier_from_dict(req.dossier)
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Malformed dossier: {exc}",
        ) from exc

    if req.format == "md":
        return {"format": "md", "content": render_markdown(req.sections, dossier)}
    return {"format": "html", "content": render_html(req.sections, dossier)}

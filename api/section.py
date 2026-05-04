"""POST /api/section — generate one brief section against a dossier.

The frontend fans out 8 parallel calls for sections 1-7 and 9, then
makes one sequential call for section 8 (psychographic) with the
parallel section bodies as prior_sections, then one final synthesis
call for executive_read with all nine prior bodies. Each call accepts
any registered section_id; routing happens via the prompt loader.

Each call is ~10-20s. Comfortable inside Vercel's 60s Hobby cap.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sherlock.dossier import dossier_from_dict
from sherlock.researcher import generate_section

app = FastAPI()


class SectionRequest(BaseModel):
    section_id: str
    dossier: dict
    prior_sections: str = ""
    model: Optional[str] = None


@app.post("/api/section")
async def section(req: SectionRequest) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Server is missing ANTHROPIC_API_KEY.",
        )

    try:
        dossier = dossier_from_dict(req.dossier)
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Malformed dossier: {exc}",
        ) from exc

    body, repaired = await generate_section(
        dossier=dossier,
        section_id=req.section_id,
        prior_sections=req.prior_sections,
        model=req.model,
    )

    return {
        "section_id": req.section_id,
        "body": body,
        "repaired": repaired,
    }

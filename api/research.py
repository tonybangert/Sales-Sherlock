"""POST /api/research — parse paste, fetch company website, optional
Apollo enrichment. NO web search. Returns the base dossier; the
frontend orchestrates per-category /api/search calls to populate
sources within the Hobby plan's 60s per-function cap.

Wall time: ~3-5s for company fetch, ~3s for Apollo, paste parse is
instant. Comfortably under 60s.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sherlock.dossier import Dossier, dossier_to_dict
from sherlock.sources.apollo import enrich_with_apollo
from sherlock.sources.linkedin import parse_linkedin_paste
from sherlock.sources.web import fetch_company_summary
from sherlock.validation import DEFAULT_MIN_PASTE_CHARS, check_linkedin_paste

app = FastAPI()


class ResearchRequest(BaseModel):
    linkedin_text: str
    company: str
    context: str = "Discovery call"
    positioning: Optional[str] = None
    no_apollo: bool = False
    min_paste_chars: int = DEFAULT_MIN_PASTE_CHARS


@app.post("/api/research")
async def research(req: ResearchRequest) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Server is missing ANTHROPIC_API_KEY.",
        )

    paste_check = check_linkedin_paste(
        req.linkedin_text, min_chars=req.min_paste_chars
    )
    if not paste_check.ok:
        raise HTTPException(status_code=400, detail=paste_check.reason)

    linkedin = parse_linkedin_paste(req.linkedin_text)
    company_summary = await fetch_company_summary(req.company)

    apollo = None
    if not req.no_apollo and os.getenv("APOLLO_API_KEY"):
        try:
            apollo = await enrich_with_apollo(
                person_name=linkedin.name,
                company_domain=req.company,
            )
        except Exception:  # noqa: BLE001
            apollo = None

    dossier = Dossier(
        linkedin=linkedin,
        company=company_summary,
        context=req.context,
        positioning=req.positioning,
        apollo=apollo,
    )

    return {
        "dossier": dossier_to_dict(dossier),
        "source_count": 0,
    }

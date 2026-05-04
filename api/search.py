"""POST /api/search — single web_search call for one source category.

The frontend orchestrates 5 of these (news, funding, jobs,
linkedin_company, interviews), batching them to stay under the
per-minute token cap. Each call is one Haiku web_search and finishes
in ~8-15s.
"""

from __future__ import annotations

import os
from typing import Optional

from anthropic import AsyncAnthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sherlock.sources.funding import find_funding
from sherlock.sources.interviews import find_interviews
from sherlock.sources.jobs import find_jobs
from sherlock.sources.linkedin_company import find_linkedin_company
from sherlock.sources.news import find_news

app = FastAPI()


class SearchRequest(BaseModel):
    kind: str  # "news" | "funding" | "jobs" | "linkedin_company" | "interviews"
    company: str
    contact_name: Optional[str] = None


@app.post("/api/search")
async def search(req: SearchRequest) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="Server is missing ANTHROPIC_API_KEY.",
        )

    client = AsyncAnthropic()

    try:
        if req.kind == "news":
            hits = await find_news(client, req.company)
        elif req.kind == "funding":
            hits = await find_funding(client, req.company)
        elif req.kind == "jobs":
            hits = await find_jobs(client, req.company)
        elif req.kind == "linkedin_company":
            hits = await find_linkedin_company(client, req.company)
        elif req.kind == "interviews":
            if not req.contact_name:
                return {"kind": req.kind, "hits": []}
            hits = await find_interviews(client, req.contact_name, req.company)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown kind: {req.kind}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        # Non-fatal: return empty so the brief degrades gracefully.
        print(f"[search:{req.kind}] failed: {type(exc).__name__}: {exc}")
        return {"kind": req.kind, "hits": []}

    return {
        "kind": req.kind,
        "hits": [
            {"title": h.title, "url": h.url, "summary": h.summary}
            for h in hits
        ],
    }

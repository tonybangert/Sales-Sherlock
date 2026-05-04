"""Open job postings — reveals priorities, tech stack, team gaps."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from sherlock.sources.web_search import WebHit, web_search


async def find_jobs(
    client: AsyncAnthropic,
    company: str,
) -> list[WebHit]:
    """Find currently-open roles. Hiring patterns are a tell."""
    topic = (
        f"Currently-open job postings at {company}. Look at the company "
        f"careers page, LinkedIn Jobs, and recent listings on aggregators. "
        f"Summarize: which functions are hiring most aggressively, any "
        f"specific technologies or tools mentioned in requirements, and "
        f"any senior or executive roles that suggest a new function being "
        f"built or an existing leader being replaced."
    )
    return await web_search(client, topic, max_uses=2)

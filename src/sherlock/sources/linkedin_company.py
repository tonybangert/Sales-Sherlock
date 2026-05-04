"""Company-level LinkedIn page lookup.

Unlike personal profiles, LinkedIn company pages are usually fetchable via
search. We delegate to web_search rather than direct httpx so we sidestep
the bot-blocking layer.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from sherlock.sources.web_search import WebHit, web_search


async def find_linkedin_company(
    client: AsyncAnthropic,
    company: str,
) -> list[WebHit]:
    """Find the company's LinkedIn page and pull headcount + recent activity."""
    topic = (
        f"LinkedIn company page for {company}. Pull: official headcount range, "
        f"industry classification, headquarters, employee growth signal "
        f"(LinkedIn 'employee growth' percentage if visible), and any recent "
        f"company-page posts or shared activity. Return the LinkedIn URL."
    )
    return await web_search(client, topic, max_uses=2)

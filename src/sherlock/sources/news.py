"""Recent news + press coverage about the company."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from sherlock.sources.web_search import WebHit, web_search


async def find_news(
    client: AsyncAnthropic,
    company: str,
) -> list[WebHit]:
    """Find recent news, press releases, and major announcements."""
    topic = (
        f"Recent news, press releases, and major announcements about "
        f"{company} in the past 18 months. Prioritize: leadership changes, "
        f"product launches, layoffs, expansions, controversies, partnerships. "
        f"Skip blog posts written by the company itself."
    )
    return await web_search(client, topic, max_uses=2)

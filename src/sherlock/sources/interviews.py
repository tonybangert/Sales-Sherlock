"""Podcast / conference / op-ed appearances by the contact.

This is the highest-leverage psychographic signal outside the LinkedIn
paste itself. How someone talks unscripted on a podcast reveals more about
decision style than any career summary ever will.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from sherlock.sources.web_search import WebHit, web_search


async def find_interviews(
    client: AsyncAnthropic,
    name: str,
    company: str,
) -> list[WebHit]:
    """Find interviews, podcasts, talks, op-eds, or quoted statements."""
    topic = (
        f"Public appearances, interviews, podcast episodes, conference talks, "
        f"or published articles by {name} (currently or recently at {company}). "
        f"Include op-eds, guest posts, panel quotes, and any video or audio "
        f"recordings where they speak unscripted. Skip the company's own blog."
    )
    return await web_search(client, topic, max_uses=4)

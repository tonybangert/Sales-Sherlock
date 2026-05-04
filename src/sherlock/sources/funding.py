"""Ownership structure, funding history, and M&A activity."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from sherlock.sources.web_search import WebHit, web_search


async def find_funding(
    client: AsyncAnthropic,
    company: str,
) -> list[WebHit]:
    """Find ownership / funding / M&A signal.

    Ownership structure is a critical buying signal — PE-backed buys
    differently than founder-owned. Includes parent company relationships
    and recent acquisitions in either direction.
    """
    topic = (
        f"Ownership and funding history for {company}. Cover: "
        f"investors and lead investors by round, total raised, valuation, "
        f"whether the company is PE-backed, VC-backed, public, or "
        f"founder-owned, parent company if a subsidiary, acquisitions made "
        f"or received, and any recent SEC filings if public. Cite Crunchbase, "
        f"PitchBook, SEC, or reputable news where possible."
    )
    return await web_search(client, topic, max_uses=4)

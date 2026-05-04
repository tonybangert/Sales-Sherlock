"""Anthropic-hosted web search wrapper.

Reads structured citations directly from `web_search_tool_result` blocks
returned by the Anthropic web_search tool, rather than asking the model
to render them in a custom text format. Much more reliable than parsing
free-form prose.

Uses Haiku by default for searches: web_search tool_result blocks can be
heavy (full page text), so the per-minute input-token budget is the
binding constraint, and Haiku has a separate token-rate pool from Sonnet.
That lets the writing stage (Sonnet) run unbothered while research is in
flight.

Failures are non-fatal — the caller catches and proceeds with whatever
sources did come back.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from anthropic import AsyncAnthropic


@dataclass
class WebHit:
    title: str
    url: Optional[str]
    summary: str


SEARCH_SYSTEM = (
    "You are a research assistant. Use the web_search tool to find the "
    "most relevant primary sources for the topic. Issue search queries "
    "until you have a strong set of citations, then stop. Do not "
    "summarize at the end - the citations are the deliverable."
)

# Haiku has its own per-minute token pool, separate from Sonnet, so
# search-stage tool_result inflation does not eat the writing-stage budget.
SEARCH_MODEL = os.getenv("SHERLOCK_SEARCH_MODEL", "claude-haiku-4-5-20251001")
SEARCH_MAX_TOKENS = int(os.getenv("SHERLOCK_SEARCH_MAX_TOKENS", "1024"))


async def web_search(
    client: AsyncAnthropic,
    topic: str,
    max_uses: int = 2,
) -> list[WebHit]:
    """Run an Anthropic-hosted web search for a single topic."""
    if os.getenv("SHERLOCK_NO_WEB_SEARCH"):
        return []

    try:
        message = await client.messages.create(
            model=SEARCH_MODEL,
            max_tokens=SEARCH_MAX_TOKENS,
            system=SEARCH_SYSTEM,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": max_uses,
                }
            ],
            messages=[{"role": "user", "content": topic}],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[web_search] {topic[:60]!r} failed: {type(exc).__name__}: {exc}")
        return []

    return _extract_hits(message)


MAX_HITS_PER_TOPIC = 5


def _extract_hits(message) -> list[WebHit]:
    """Pull structured citations out of `web_search_tool_result` blocks.

    Returns at most MAX_HITS_PER_TOPIC hits to keep the dossier compact.
    The model's final synthesis text (if any) is attached as a shared
    summary across every returned hit, so the section writer has prose
    context to ground claims in regardless of which source it cites.
    """
    hits: list[WebHit] = []
    seen_urls: set[str] = set()

    for block in message.content:
        block_type = getattr(block, "type", None)
        if block_type != "web_search_tool_result":
            continue

        results = getattr(block, "content", None) or []
        for item in results:
            url = _attr_or_key(item, "url")
            title = _attr_or_key(item, "title") or url or "(untitled)"
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            page_age = _attr_or_key(item, "page_age")
            snippet = f"({page_age})" if page_age else ""
            hits.append(WebHit(title=str(title), url=str(url), summary=snippet))

            if len(hits) >= MAX_HITS_PER_TOPIC:
                break
        if len(hits) >= MAX_HITS_PER_TOPIC:
            break

    # The model's synthesis text is the single best piece of grounded
    # prose from this search. Attach it to every hit so the section
    # writer has substantive content next to whichever URL it cites.
    text_parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(getattr(block, "text", ""))
    final_text = " ".join(t.strip() for t in text_parts if t).strip()
    if final_text and hits:
        synthesis = final_text[:1200]
        hits = [
            WebHit(
                title=h.title,
                url=h.url,
                summary=(h.summary + " " + synthesis).strip()
                if not h.summary
                else h.summary,
            )
            for h in hits
        ]
        # Always seed hit 1's summary with the synthesis (it had no real
        # snippet to begin with, just page_age at best).
        hits[0] = WebHit(
            title=hits[0].title,
            url=hits[0].url,
            summary=synthesis,
        )

    return hits


def _attr_or_key(obj, name):
    """Read either `obj.name` (pydantic model) or `obj[name]` (dict)."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name)
    return None

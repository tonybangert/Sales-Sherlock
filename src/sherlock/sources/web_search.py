"""Anthropic-hosted web search wrapper.

Issues a Claude call with the `web_search_20250305` tool enabled and a tight
system prompt asking for a structured summary of what was found. The wrapper
returns a list of (title, url, summary) triples that the caller turns into
Source records with the right `kind`.

Failures are non-fatal — the caller catches exceptions and proceeds with
whatever sources did come back.
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
    "You are a research assistant. You are given a single search topic. "
    "Use the web_search tool to find the most relevant primary sources. "
    "Return ONLY a numbered list, one entry per finding, in this exact format:\n\n"
    "1. TITLE: <title>\n"
    "   URL: <full url>\n"
    "   SUMMARY: <one to three tight sentences of factual content>\n\n"
    "Do not editorialize. Do not include findings that lack a real URL. "
    "Cap at 5 entries. If nothing relevant exists, return only the line 'NONE'."
)

SEARCH_MODEL = os.getenv("SHERLOCK_SEARCH_MODEL", "claude-sonnet-4-6")
SEARCH_MAX_TOKENS = int(os.getenv("SHERLOCK_SEARCH_MAX_TOKENS", "1500"))


async def web_search(
    client: AsyncAnthropic,
    topic: str,
    max_uses: int = 3,
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
    except Exception:  # noqa: BLE001
        return []

    text_parts: list[str] = []
    for block in message.content:
        if hasattr(block, "text") and block.text:
            text_parts.append(block.text)
    raw = "\n".join(text_parts).strip()
    if not raw or raw.upper().startswith("NONE"):
        return []

    return _parse_search_output(raw)


def _parse_search_output(raw: str) -> list[WebHit]:
    """Parse the strict TITLE/URL/SUMMARY format the system prompt asks for."""
    hits: list[WebHit] = []
    current: dict[str, str] = {}

    def flush() -> None:
        if current.get("title"):
            hits.append(
                WebHit(
                    title=current.get("title", "").strip(),
                    url=(current.get("url") or "").strip() or None,
                    summary=current.get("summary", "").strip(),
                )
            )

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        # New numbered entry like "1. TITLE: Foo"
        if (
            stripped[:1].isdigit()
            and "TITLE:" in upper
        ):
            flush()
            current = {}
            current["title"] = stripped.split("TITLE:", 1)[1].strip()
        elif upper.startswith("TITLE:"):
            flush()
            current = {"title": stripped.split(":", 1)[1].strip()}
        elif upper.startswith("URL:"):
            current["url"] = stripped.split(":", 1)[1].strip()
        elif upper.startswith("SUMMARY:"):
            current["summary"] = stripped.split(":", 1)[1].strip()
        else:
            # Continuation of the previous summary line
            if "summary" in current:
                current["summary"] += " " + stripped
    flush()

    return [h for h in hits if h.title]

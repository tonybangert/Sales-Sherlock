"""Brief generation — orchestrates parallel Claude calls per section."""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from anthropic import AsyncAnthropic

from sherlock.dossier import Dossier
from sherlock.prompts import load_prompts

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1500

SECTION_ORDER: list[str] = [
    "tldr",
    "company_snapshot",
    "person_role",
    "three_things",
    "opening_questions",
    "discovery_questions",
    "risk_flag",
]


async def generate_brief(
    dossier: Dossier,
    model: Optional[str] = None,
) -> dict[str, str]:
    """Generate every brief section in parallel against the dossier.

    Returns a dict keyed by section id (matching SECTION_ORDER), each value
    being the rendered markdown body of that section.
    """
    model = model or os.getenv("SHERLOCK_MODEL", DEFAULT_MODEL)
    max_tokens = int(os.getenv("SHERLOCK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))

    client = AsyncAnthropic()
    prompts = load_prompts()
    research_block = dossier.to_research_block()

    async def _gen_section(section_id: str) -> tuple[str, str]:
        template = prompts.get(section_id)
        if template is None:
            return section_id, f"_(missing prompt template for `{section_id}`)_"

        prompt = template.replace("{{research}}", research_block)

        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in message.content if hasattr(block, "text")
        ).strip()
        return section_id, text

    results = await asyncio.gather(*(_gen_section(sid) for sid in SECTION_ORDER))
    return dict(results)

"""Two-stage brief generation.

Stage 1 — Research:
  Run in parallel: company website fetch, LinkedIn company page,
  news, funding, jobs, interviews. Each produces zero or more Source
  records that get registered on the dossier.

Stage 2 — Writing:
  Sections 1, 2, 3, 4, 5, 6, 7, 9 generate in parallel. Each is run
  through a confidence-tag validator; if a section comes back with
  too few tags, it gets a single repair pass.

  Section 8 (psychographic) runs LAST, sequentially, with the other
  eight sections passed in as `<prior_sections>`. This is the section
  that most differentiates a great brief from an okay one — synthesis,
  not parallel pattern-matching.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from anthropic import AsyncAnthropic

from sherlock.dossier import Dossier
from sherlock.prompts import load_prompts
from sherlock.sources.funding import find_funding
from sherlock.sources.interviews import find_interviews
from sherlock.sources.jobs import find_jobs
from sherlock.sources.linkedin_company import find_linkedin_company
from sherlock.sources.news import find_news
from sherlock.sources.web_search import WebHit
from sherlock.validation import needs_repair

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1500

PARALLEL_SECTIONS: list[str] = [
    "company_overview",
    "company_history",
    "investment_ownership",
    "growth_revenue_signals",
    "industry_competitive",
    "contact_professional",
    "contact_personal",
    "hooks_and_risks",
]
SEQUENTIAL_SECTIONS: list[str] = ["psychographic"]
ALL_SECTIONS: list[str] = PARALLEL_SECTIONS + SEQUENTIAL_SECTIONS

# Friendly headings used when we paste prior section bodies into the
# psychographic prompt's <prior_sections> block.
SECTION_PRIOR_HEADINGS: dict[str, str] = {
    "company_overview": "Company Overview",
    "company_history": "Company History",
    "investment_ownership": "Investment and Ownership",
    "growth_revenue_signals": "Growth and Revenue Signals",
    "industry_competitive": "Industry and Competitive Landscape",
    "contact_professional": "Contact Professional Profile",
    "contact_personal": "Contact Personal and Public Profile",
    "hooks_and_risks": "Conversational Hooks and Risks",
}


async def run_research_stage(
    client: AsyncAnthropic,
    dossier: Dossier,
) -> None:
    """Populate `dossier.sources` from web search across all categories.

    All searches dispatch in parallel. Failures are non-fatal — a category
    that returns nothing simply contributes no sources.
    """
    if os.getenv("SHERLOCK_NO_WEB_SEARCH"):
        return

    company = dossier.company.url
    name = dossier.linkedin.name or ""

    coros = [
        find_news(client, company),
        find_funding(client, company),
        find_jobs(client, company),
        find_linkedin_company(client, company),
    ]
    if name:
        coros.append(find_interviews(client, name, company))

    results = await asyncio.gather(*coros, return_exceptions=True)

    kinds = ["news", "funding", "jobs", "linkedin_company"]
    if name:
        kinds.append("interviews")

    for kind, result in zip(kinds, results):
        if isinstance(result, Exception):
            continue
        for hit in result:
            if not isinstance(hit, WebHit):
                continue
            dossier.add_source(
                kind=kind,
                url=hit.url,
                title=hit.title,
                content=hit.summary,
            )


async def generate_brief(
    dossier: Dossier,
    model: Optional[str] = None,
) -> dict[str, str]:
    """Generate every brief section against the dossier.

    Returns a dict keyed by section id, each value the rendered markdown
    body of that section. Section order matches ALL_SECTIONS.
    """
    model = model or os.getenv("SHERLOCK_MODEL", DEFAULT_MODEL)
    max_tokens = int(os.getenv("SHERLOCK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))

    client = AsyncAnthropic()

    # Run the research stage on the same client so any web_search calls
    # share connection pools with the writing stage.
    await run_research_stage(client, dossier)

    prompts = load_prompts()
    sources_index = dossier.to_sources_index()
    research_block = dossier.to_research_block()

    async def _gen_one(section_id: str, prior_sections: str = "") -> tuple[str, str]:
        template = prompts.get(section_id)
        if template is None:
            return section_id, f"_(missing prompt template for `{section_id}`)_"

        prompt = (
            template.replace("{{sources}}", sources_index)
            .replace("{{research}}", research_block)
            .replace("{{prior_sections}}", prior_sections)
        )

        text = await _call_claude(client, model, max_tokens, prompt)

        if needs_repair(text, section_id):
            text = await _repair_section(
                client, model, max_tokens, prompt, text, section_id
            )
        return section_id, text

    parallel_results = await asyncio.gather(
        *(_gen_one(sid) for sid in PARALLEL_SECTIONS)
    )
    parallel_dict = dict(parallel_results)

    prior_block = _build_prior_sections_block(parallel_dict)

    psy_id, psy_text = await _gen_one(
        "psychographic", prior_sections=prior_block
    )

    out: dict[str, str] = dict(parallel_dict)
    out[psy_id] = psy_text
    return out


async def _call_claude(
    client: AsyncAnthropic,
    model: str,
    max_tokens: int,
    prompt: str,
) -> str:
    message = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in message.content if hasattr(block, "text")
    ).strip()


async def _repair_section(
    client: AsyncAnthropic,
    model: str,
    max_tokens: int,
    original_prompt: str,
    draft: str,
    section_id: str,
) -> str:
    """One-shot repair for sections that came back missing confidence tags."""
    repair_instruction = (
        "The draft below is missing confidence tags. Every factual claim "
        "must end with `[Verified - S#]`, `[Reported - S#]`, or `[Inferred]`. "
        "Rewrite the draft to add the missing tags. Do not change the facts. "
        "Do not add new claims. Return only the repaired section body.\n\n"
        f"Original draft:\n\n{draft}"
    )
    repair_prompt = (
        original_prompt
        + "\n\n## Repair pass\n\n"
        + repair_instruction
    )
    repaired = await _call_claude(client, model, max_tokens, repair_prompt)
    # If the repair somehow comes back even worse, fall back to the draft.
    if needs_repair(repaired, section_id):
        return draft
    return repaired


def _build_prior_sections_block(sections: dict[str, str]) -> str:
    """Format the parallel sections for injection into the psy prompt."""
    parts: list[str] = []
    for sid in PARALLEL_SECTIONS:
        body = sections.get(sid, "").strip()
        if not body:
            continue
        heading = SECTION_PRIOR_HEADINGS.get(sid, sid)
        parts.append(f"### {heading}\n\n{body}")
    return "\n\n".join(parts)

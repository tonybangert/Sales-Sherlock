"""Two-stage brief generation.

Stage 1 — Research:
  Run in parallel: company website fetch, LinkedIn company page,
  news, funding, jobs, interviews. Each produces zero or more Source
  records that get registered on the dossier.

Stage 2 — Writing:
  Sections 1, 2, 3, 4, 5, 6, 7, 9 generate in parallel. Each is run
  through a confidence-tag validator; if a section comes back with
  too few tags, it gets a single repair pass.

  Section 8 (psychographic) runs LAST among the nine numbered sections,
  sequentially, with the other eight sections passed in as
  `<prior_sections>`. This is the section that most differentiates a
  great brief from an okay one — synthesis, not parallel pattern-matching.

Stage 3 — Executive read:
  After all nine sections complete, a final synthesis pass produces the
  page-one executive read (quick stats, three priorities, entry
  hypothesis, three high-leverage questions). It receives all nine
  prior sections as context.
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
SYNTHESIS_SECTIONS: list[str] = ["executive_read"]
ALL_SECTIONS: list[str] = PARALLEL_SECTIONS + SEQUENTIAL_SECTIONS + SYNTHESIS_SECTIONS

# Friendly headings used when we paste prior section bodies into a
# downstream prompt's <prior_sections> block. Keys cover every section
# that can appear as prior context for another section.
SECTION_PRIOR_HEADINGS: dict[str, str] = {
    "company_overview": "Company Overview",
    "company_history": "Company History",
    "investment_ownership": "Investment and Ownership",
    "growth_revenue_signals": "Growth and Revenue Signals",
    "industry_competitive": "Industry and Competitive Landscape",
    "contact_professional": "Contact Professional Profile",
    "contact_personal": "Contact Personal and Public Profile",
    "hooks_and_risks": "Conversational Hooks and Risks",
    "psychographic": "Psychographic and Decision-Making Profile",
}

# Order in which prior sections are formatted into the executive_read
# prior block. Mirrors the final brief reading order.
EXECUTIVE_READ_PRIOR_ORDER: list[str] = [
    "company_overview",
    "company_history",
    "investment_ownership",
    "growth_revenue_signals",
    "industry_competitive",
    "contact_professional",
    "contact_personal",
    "psychographic",
    "hooks_and_risks",
]


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

    # Sequential rather than parallel: web_search tool_result blocks
    # can be 5-10K input tokens each, and parallel queries blow past
    # the per-minute token cap on developer-tier Anthropic accounts.
    queries = [
        ("news", lambda: find_news(client, company)),
        ("funding", lambda: find_funding(client, company)),
        ("jobs", lambda: find_jobs(client, company)),
        ("linkedin_company", lambda: find_linkedin_company(client, company)),
    ]
    if name:
        queries.append(("interviews", lambda: find_interviews(client, name, company)))

    for kind, runner in queries:
        try:
            result = await runner()
        except Exception:  # noqa: BLE001
            continue
        for hit in result or []:
            if not isinstance(hit, WebHit):
                continue
            dossier.add_source(
                kind=kind,
                url=hit.url,
                title=hit.title,
                content=hit.summary,
            )


async def generate_section(
    dossier: Dossier,
    section_id: str,
    prior_sections: str = "",
    model: Optional[str] = None,
    client: Optional[AsyncAnthropic] = None,
) -> tuple[str, bool]:
    """Generate a single brief section.

    Used by the web frontend, which fans out one HTTP request per section
    to stay under Vercel's 60s function cap. The CLI continues to use
    generate_brief() which orchestrates internally.

    Returns (body, repaired) where `repaired` is True if the validator
    triggered a one-shot repair pass.
    """
    model = model or os.getenv("SHERLOCK_MODEL", DEFAULT_MODEL)
    max_tokens = int(os.getenv("SHERLOCK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))

    own_client = client is None
    if own_client:
        client = AsyncAnthropic()

    prompts = load_prompts()
    template = prompts.get(section_id)
    if template is None:
        return f"_(missing prompt template for `{section_id}`)_", False

    prompt = (
        template.replace("{{sources}}", dossier.to_sources_index())
        .replace("{{research}}", dossier.to_research_block())
        .replace("{{prior_sections}}", prior_sections)
    )

    text = await _call_claude(client, model, max_tokens, prompt)

    repaired = False
    if needs_repair(text, section_id):
        text = await _repair_section(
            client, model, max_tokens, prompt, text, section_id
        )
        repaired = True

    return text, repaired


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

    psy_prior_block = _build_prior_sections_block(parallel_dict, PARALLEL_SECTIONS)
    psy_id, psy_text = await _gen_one(
        "psychographic", prior_sections=psy_prior_block
    )

    out: dict[str, str] = dict(parallel_dict)
    out[psy_id] = psy_text

    exec_prior_block = _build_prior_sections_block(out, EXECUTIVE_READ_PRIOR_ORDER)
    exec_id, exec_text = await _gen_one(
        "executive_read", prior_sections=exec_prior_block
    )
    out[exec_id] = exec_text

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


def _build_prior_sections_block(
    sections: dict[str, str],
    order: list[str],
) -> str:
    """Format prior sections for injection into a downstream prompt.

    `order` controls which section ids are included and in what sequence.
    Sections missing from `sections` (or empty) are skipped silently.
    """
    parts: list[str] = []
    for sid in order:
        body = sections.get(sid, "").strip()
        if not body:
            continue
        heading = SECTION_PRIOR_HEADINGS.get(sid, sid)
        parts.append(f"### {heading}\n\n{body}")
    return "\n\n".join(parts)

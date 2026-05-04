"""Prompt templates — the hackable core of Sherlock.

Each section of the brief is a single markdown file in this directory.
Files use exactly one placeholder, `{{research}}`, where the dossier
gets injected. Every file is loadable via `load_prompts()`.

Set `SHERLOCK_PROMPTS_DIR` to override prompts at runtime — useful for
team-specific playbooks without forking the repo.
"""

from __future__ import annotations

import os
from pathlib import Path

PROMPT_FILES: dict[str, str] = {
    "company_overview": "01_company_overview.md",
    "company_history": "02_company_history.md",
    "investment_ownership": "03_investment_ownership.md",
    "growth_revenue_signals": "04_growth_revenue_signals.md",
    "industry_competitive": "05_industry_competitive.md",
    "contact_professional": "06_contact_professional.md",
    "contact_personal": "07_contact_personal.md",
    "psychographic": "08_psychographic.md",
    "hooks_and_risks": "09_hooks_and_risks.md",
}

_BUNDLED_DIR = Path(__file__).parent


def load_prompts() -> dict[str, str]:
    """Load all prompt templates. Honors SHERLOCK_PROMPTS_DIR override.

    For each section, checks the override directory first (if set),
    falling back to the bundled prompts.
    """
    override_dir_str = os.getenv("SHERLOCK_PROMPTS_DIR")
    override_dir = Path(override_dir_str) if override_dir_str else None

    out: dict[str, str] = {}
    for section_id, filename in PROMPT_FILES.items():
        if override_dir:
            override_path = override_dir / filename
            if override_path.exists():
                out[section_id] = override_path.read_text(encoding="utf-8")
                continue
        bundled_path = _BUNDLED_DIR / filename
        if bundled_path.exists():
            out[section_id] = bundled_path.read_text(encoding="utf-8")
    return out

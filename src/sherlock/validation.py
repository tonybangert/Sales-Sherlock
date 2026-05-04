"""Input validation + confidence-tag enforcement.

Two responsibilities:

1. **Paste density check.** The skill is explicit: do not silently produce
   a brief from a thin LinkedIn paste. Below the threshold (or missing the
   key sections), refuse and ask the user for more.

2. **Confidence tag scan.** Every factual claim in the brief must carry a
   `[Verified]`, `[Reported]`, or `[Inferred]` tag. After each section is
   generated, we scan for tags. If a section comes back without enough
   tags, the researcher runs a single repair pass on just that section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_MIN_PASTE_CHARS = 800

CONFIDENCE_TAG_RE = re.compile(
    r"\[(Verified|Reported|Inferred)(?:\s*[-—]\s*S\d+)?\]"
)


@dataclass
class PasteCheckResult:
    ok: bool
    char_count: int
    has_about: bool
    has_experience: bool
    reason: str = ""


def check_linkedin_paste(
    text: str,
    min_chars: int = DEFAULT_MIN_PASTE_CHARS,
) -> PasteCheckResult:
    """Refuse thin LinkedIn pastes early, before any research kicks off."""
    char_count = len(text.strip())
    lower = text.lower()
    has_about = "about" in lower
    has_experience = "experience" in lower

    if char_count < min_chars:
        return PasteCheckResult(
            ok=False,
            char_count=char_count,
            has_about=has_about,
            has_experience=has_experience,
            reason=(
                f"LinkedIn paste is too thin ({char_count} chars, "
                f"minimum {min_chars}). Open the contact's LinkedIn profile, "
                f"press Cmd/Ctrl+A then Cmd/Ctrl+C, and paste the full page "
                f"text — including About, Experience, Education, and recent "
                f"posts. The brief quality is bounded by the paste quality."
            ),
        )

    if not has_about and not has_experience:
        return PasteCheckResult(
            ok=False,
            char_count=char_count,
            has_about=has_about,
            has_experience=has_experience,
            reason=(
                "LinkedIn paste is missing the About and Experience sections. "
                "Make sure you scroll the full profile before copying so those "
                "sections render in the page text."
            ),
        )

    return PasteCheckResult(
        ok=True,
        char_count=char_count,
        has_about=has_about,
        has_experience=has_experience,
    )


def count_confidence_tags(text: str) -> int:
    """How many `[Verified]` / `[Reported]` / `[Inferred]` tags appear."""
    return len(CONFIDENCE_TAG_RE.findall(text))


def needs_repair(
    section_text: str,
    section_id: str,
    min_tags: int = 2,
) -> bool:
    """Decide whether a section should be sent back for a repair pass.

    Hooks and Risks is structurally light on factual claims (it's a list
    of conversational hooks); we only require 1 tag. Same for the
    psychographic section, which is dominated by [Inferred] reads — but
    those reads should still be tagged.
    """
    if section_id in {"hooks_and_risks"}:
        min_tags = 1
    return count_confidence_tags(section_text) < min_tags

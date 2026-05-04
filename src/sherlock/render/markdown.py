"""Markdown render — stitches the seven Claude-generated sections into a brief."""

from __future__ import annotations

from datetime import datetime

from sherlock.dossier import Dossier

SECTION_HEADINGS: dict[str, str] = {
    "tldr": "TL;DR",
    "company_snapshot": "Company snapshot",
    "person_role": "Their role",
    "three_things": "Three things in their world right now",
    "opening_questions": "Three opening questions",
    "discovery_questions": "Three discovery questions",
    "risk_flag": "Watch for",
}

SECTION_ORDER: list[str] = list(SECTION_HEADINGS.keys())


def render_markdown(sections: dict[str, str], dossier: Dossier) -> str:
    """Render a complete brief as a single markdown document."""
    name = dossier.linkedin.name or "(unknown)"
    company_label = dossier.company.title or dossier.company.url
    when = datetime.now().strftime("%B %d, %Y")

    out: list[str] = [
        f"# Pre-call brief — {name} @ {company_label}",
        "",
        f"*Meeting:* {dossier.context}  ",
        f"*Generated:* {when} via [Sherlock](https://github.com/tonybangert/sherlock)",
        "",
        "---",
        "",
    ]

    for section_id in SECTION_ORDER:
        body = sections.get(section_id)
        if not body:
            continue
        out.append(f"## {SECTION_HEADINGS[section_id]}")
        out.append("")
        out.append(body.strip())
        out.append("")

    out.append("---")
    out.append("")
    out.append(
        "*Built on [Claude](https://anthropic.com) by "
        "[PerformanceLabs.AI](https://performancelabs.ai). "
        "Want help rolling tools like this out across your revenue stack? "
        "[Let's talk](https://performancelabs.ai).*"
    )

    return "\n".join(out)

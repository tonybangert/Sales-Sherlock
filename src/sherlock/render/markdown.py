"""Markdown render — stitches the nine Claude-generated sections into a brief.

After the section bodies, appends a numbered Sources index so the inline
[Verified - S3] citations resolve for the reader.
"""

from __future__ import annotations

from datetime import datetime

from sherlock.dossier import Dossier

SECTION_HEADINGS: dict[str, str] = {
    "company_overview": "1. Company Overview",
    "company_history": "2. Company History",
    "investment_ownership": "3. Investment and Ownership",
    "growth_revenue_signals": "4. Growth and Revenue Signals",
    "industry_competitive": "5. Industry and Competitive Landscape",
    "contact_professional": "6. Contact Professional Profile",
    "contact_personal": "7. Contact Personal and Public Profile",
    "psychographic": "8. Psychographic and Decision-Making Profile",
    "hooks_and_risks": "9. Conversational Hooks and Risks",
}

SECTION_ORDER: list[str] = list(SECTION_HEADINGS.keys())


def render_markdown(sections: dict[str, str], dossier: Dossier) -> str:
    """Render a complete brief as a single markdown document."""
    name = dossier.linkedin.name or "(unknown)"
    title = dossier.linkedin.headline or dossier.linkedin.current_role or ""
    company_label = dossier.company.title or dossier.company.url
    when = datetime.now().strftime("%B %d, %Y")

    out: list[str] = [
        f"# Pre-call brief",
        "",
        f"**Company:** {company_label}",
    ]
    contact_line = f"**Contact:** {name}"
    if title:
        contact_line += f", {title}"
    out.append(contact_line)
    if dossier.context:
        out.append(f"**Meeting Context:** {dossier.context}")
    if dossier.positioning:
        out.append(f"**Your Positioning:** {dossier.positioning}")
    out.append(f"**Prepared:** {when}")
    out.append("")
    out.append("---")
    out.append("")

    for section_id in SECTION_ORDER:
        body = sections.get(section_id)
        if not body:
            continue
        out.append(f"## {SECTION_HEADINGS[section_id]}")
        out.append("")
        out.append(body.strip())
        out.append("")

    if dossier.sources:
        out.append("## Sources")
        out.append("")
        for s in dossier.sources:
            line = f"- **{s.id}** [{s.kind}] {s.title}"
            if s.url:
                line += f" - <{s.url}>"
            out.append(line)
        out.append("- **LinkedIn paste** [linkedin_paste] Pasted by user (not retransmitted)")
        out.append("")

    return "\n".join(out)

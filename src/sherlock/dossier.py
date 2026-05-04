"""Research dossier — the structured input every prompt sees.

The dossier holds three things:

1. A list of `Source` records (numbered S1, S2, ...) that prompts cite by ID.
2. The parsed LinkedIn profile from the user's paste (always preserved verbatim).
3. The meeting context and the user's optional positioning, so the writing
   stage can flag rapport hooks that match the user's own background.

Each Source has a stable ID assigned at registration time; the prompts use
those IDs for inline citation tags like `[Verified - S3]`. The render stage
appends a numbered Sources index at the end of the brief so the citations
resolve for the reader.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


SourceKind = str


@dataclass
class Source:
    """One piece of researched evidence the brief can cite.

    Kinds:
      - website: company's own website (about page, product, etc.)
      - linkedin_company: the company's LinkedIn page
      - news: press / coverage / announcements
      - funding: Crunchbase, PitchBook, public filings about ownership/capital
      - jobs: company careers page or job board listings
      - interviews: podcasts, conference talks, op-eds by the contact
      - apollo: structured firmographics from Apollo.io
      - linkedin_paste: the contact's LinkedIn profile pasted by the user
    """

    id: str
    kind: SourceKind
    url: Optional[str]
    title: str
    content: str
    fetched_at: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d")
    )


@dataclass
class LinkedInProfile:
    """Parsed LinkedIn profile from pasted text."""

    raw: str
    name: Optional[str] = None
    headline: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None


@dataclass
class CompanySummary:
    """Summary fetched from a company website."""

    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    text: Optional[str] = None


@dataclass
class ApolloEnrichment:
    """Optional structured enrichment from Apollo.io."""

    person: dict[str, Any] = field(default_factory=dict)
    organization: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dossier:
    """The full research dossier passed to every prompt."""

    linkedin: LinkedInProfile
    company: CompanySummary
    context: str
    positioning: Optional[str] = None
    apollo: Optional[ApolloEnrichment] = None
    sources: list[Source] = field(default_factory=list)

    def add_source(
        self,
        kind: SourceKind,
        url: Optional[str],
        title: str,
        content: str,
    ) -> Source:
        """Register a source. Assigns a stable S{n} ID for citation."""
        next_id = f"S{len(self.sources) + 1}"
        src = Source(id=next_id, kind=kind, url=url, title=title, content=content)
        self.sources.append(src)
        return src

    def to_sources_index(self) -> str:
        """Compact reference list — what evidence the model has, by ID."""
        if not self.sources:
            return "(no external sources gathered)"
        rows: list[str] = []
        for s in self.sources:
            label = f"{s.id} [{s.kind}] {s.title}"
            if s.url:
                label += f" ({s.url})"
            rows.append(label)
        return "\n".join(rows)

    def to_research_block(self) -> str:
        """Render the dossier as XML — Claude reads this well."""
        parts: list[str] = ["<research>"]

        parts.append(f"<meeting_context>{self.context}</meeting_context>")
        if self.positioning:
            parts.append(
                f"<user_positioning>{self.positioning}</user_positioning>"
            )

        parts.append("<linkedin_profile_paste>")
        parts.append(self.linkedin.raw.strip())
        parts.append("</linkedin_profile_paste>")

        parts.append(f"<company_url>{self.company.url}</company_url>")
        if self.company.title:
            parts.append(f"<company_title>{self.company.title}</company_title>")
        if self.company.description:
            parts.append(
                f"<company_meta_description>{self.company.description}</company_meta_description>"
            )
        if self.company.text:
            parts.append("<company_website_text>")
            parts.append(self.company.text)
            parts.append("</company_website_text>")

        if self.sources:
            parts.append("<sources>")
            for s in self.sources:
                parts.append(f'<source id="{s.id}" kind="{s.kind}">')
                parts.append(f"<title>{s.title}</title>")
                if s.url:
                    parts.append(f"<url>{s.url}</url>")
                parts.append(f"<fetched_at>{s.fetched_at}</fetched_at>")
                parts.append("<content>")
                parts.append(s.content)
                parts.append("</content>")
                parts.append("</source>")
            parts.append("</sources>")

        if self.apollo and (self.apollo.person or self.apollo.organization):
            parts.append("<apollo_enrichment>")
            if self.apollo.organization:
                parts.append("<organization>")
                parts.append(json.dumps(self.apollo.organization, indent=2, default=str))
                parts.append("</organization>")
            if self.apollo.person:
                parts.append("<person>")
                parts.append(json.dumps(self.apollo.person, indent=2, default=str))
                parts.append("</person>")
            parts.append("</apollo_enrichment>")

        parts.append("</research>")
        return "\n".join(parts)

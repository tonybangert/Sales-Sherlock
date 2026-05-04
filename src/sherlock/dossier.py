"""Research dossier — the structured input every prompt sees."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LinkedInProfile:
    """Parsed LinkedIn profile from pasted text.

    The raw text is always preserved and passed to Claude verbatim;
    the parsed fields are best-effort heuristics for use in the brief
    header and for Apollo enrichment lookups.
    """

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
    text: Optional[str] = None  # cleaned, capped main-text


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
    apollo: Optional[ApolloEnrichment] = None

    def to_research_block(self) -> str:
        """Render the dossier as XML — Claude reads this well."""
        parts: list[str] = ["<research>"]

        parts.append(f"<meeting_context>{self.context}</meeting_context>")

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

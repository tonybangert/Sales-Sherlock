"""Lightweight parser for pasted LinkedIn profile text.

We never scrape LinkedIn — that's a ToS violation. This module takes the
plain text the user pasted from their browser (Cmd/Ctrl+A then Cmd/Ctrl+C
on a profile page) and pulls out a few useful fields heuristically.

The full raw paste is always preserved and handed to Claude in the dossier,
so even when the heuristics miss, the model sees the same text the user did.
"""

from __future__ import annotations

import re

from sherlock.dossier import LinkedInProfile

_SECTION_HEADINGS = {
    "about",
    "experience",
    "education",
    "skills",
    "activity",
    "licenses & certifications",
    "volunteer experience",
    "recommendations",
    "publications",
    "projects",
    "courses",
    "honors & awards",
    "languages",
    "interests",
}


def parse_linkedin_paste(text: str) -> LinkedInProfile:
    """Best-effort parse of pasted LinkedIn profile text.

    The model still sees the raw paste, so heuristic misses are non-fatal.
    """
    profile = LinkedInProfile(raw=text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return profile

    profile.name = _guess_name(lines)
    profile.headline = _guess_headline(lines, profile.name)
    profile.location = _guess_location(lines)
    profile.current_role, profile.current_company = _guess_current_position(lines)
    profile.about = _extract_about(lines)

    return profile


def _guess_name(lines: list[str]) -> str | None:
    """Name is usually 2-5 words, capitalized, in the first ~20 lines."""
    for line in lines[:20]:
        words = line.split()
        if not (2 <= len(words) <= 5):
            continue
        if any(c in line for c in ["·", "•", "@", "http", "/"]):
            continue
        if not line[0].isupper():
            continue
        # Avoid section headings
        if line.lower() in _SECTION_HEADINGS:
            continue
        # Most words should look like proper names (start uppercase, no digits)
        if all(w[0].isupper() and not any(d.isdigit() for d in w) for w in words):
            return line
    return None


def _guess_headline(lines: list[str], name: str | None) -> str | None:
    """Headline is typically the line right after the name."""
    if not name:
        return None
    for i, line in enumerate(lines):
        if line == name and i + 1 < len(lines):
            candidate = lines[i + 1]
            if 5 < len(candidate) < 250 and candidate.lower() not in _SECTION_HEADINGS:
                return candidate
    return None


def _guess_location(lines: list[str]) -> str | None:
    """Location often looks like 'City, ST, Country' or 'Greater X Area'."""
    location_pattern = re.compile(
        r"^(?:[\w\s\.\-']+,\s*)+[\w\s\.\-']+$|^Greater\s+[\w\s]+\s+Area$",
        re.IGNORECASE,
    )
    for line in lines[:50]:
        if len(line) > 80:
            continue
        if line.lower() in _SECTION_HEADINGS:
            continue
        if location_pattern.match(line):
            return line
    return None


def _guess_current_position(lines: list[str]) -> tuple[str | None, str | None]:
    """The current role + company appear right under 'Experience'."""
    for i, line in enumerate(lines):
        if line.lower() == "experience" and i + 2 < len(lines):
            role = lines[i + 1]
            company = lines[i + 2]
            # Strip trailing tenure like "· Full-time" or " · 2 yrs"
            company = re.split(r"\s+·\s+", company, maxsplit=1)[0].strip()
            role = re.split(r"\s+·\s+", role, maxsplit=1)[0].strip()
            return role, company
    return None, None


def _extract_about(lines: list[str]) -> str | None:
    """Pull text under the 'About' heading until the next section."""
    for i, line in enumerate(lines):
        if line.lower() == "about":
            collected: list[str] = []
            for next_line in lines[i + 1 : i + 40]:
                if next_line.lower() in _SECTION_HEADINGS:
                    break
                collected.append(next_line)
            joined = " ".join(collected).strip()
            return joined[:1500] if joined else None
    return None

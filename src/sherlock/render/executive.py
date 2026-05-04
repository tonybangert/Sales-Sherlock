"""Parser for the executive_read section's structured markdown output.

The 00_executive_read.md prompt produces four blocks under fixed `###`
headings: Quick stats, Three likely priorities, Entry hypothesis, Three
high-leverage questions. The HTML render needs them as structured data
so it can lay them out as the page-one editorial card. This module
converts the raw markdown to an `ExecutiveRead` dataclass.

Tolerant by design: if a heading is missing, that block comes back
empty rather than raising. Better to render a partial card than to
crash the whole brief on a model that broke format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class QuickStat:
    label: str
    value: str  # raw markdown, may include `[Verified - S#]` style tags


@dataclass
class ExecutiveRead:
    quick_stats: list[QuickStat] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    hypothesis: str = ""
    questions: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (
            not self.quick_stats
            and not self.priorities
            and not self.hypothesis
            and not self.questions
        )


# Match `### Heading` blocks. The block body extends until the next `###`
# heading or end-of-string. (?ms) so `^` anchors per-line and `.` matches
# newlines inside the body capture.
_HEADING_RE = re.compile(
    r"(?ms)^###\s+(.+?)\s*$\n+(.*?)(?=^###\s+|\Z)"
)

# Quick-stat bullet: "- **Label:** value [tag]"
_STAT_BULLET_RE = re.compile(
    r"(?m)^\s*[-*]\s+\*\*(?P<label>[^*]+?):\*\*\s+(?P<value>.+?)\s*$"
)

# Numbered list item: "1. text" or "1) text"
_NUMBERED_RE = re.compile(r"(?m)^\s*\d+[.)]\s+(.+?)\s*$")


def parse_executive_read(text: str) -> ExecutiveRead:
    """Parse the executive_read section body into structured fields."""
    if not text or not text.strip():
        return ExecutiveRead()

    blocks = _split_blocks(text)
    out = ExecutiveRead()

    for heading, body in blocks.items():
        h = heading.lower()
        if "quick stats" in h or "stats" == h:
            out.quick_stats = _parse_quick_stats(body)
        elif "priorit" in h:
            out.priorities = _parse_numbered_list(body)
        elif "hypothesis" in h:
            out.hypothesis = body.strip()
        elif "question" in h:
            out.questions = _parse_numbered_list(body)

    return out


def _split_blocks(text: str) -> dict[str, str]:
    """Return {heading: body} for every `### Heading` block in the text."""
    out: dict[str, str] = {}
    for m in _HEADING_RE.finditer(text):
        heading = m.group(1).strip()
        body = m.group(2).strip()
        out[heading] = body
    return out


def _parse_quick_stats(body: str) -> list[QuickStat]:
    """Parse `- **Label:** value [tag]` bullets into QuickStat records."""
    stats: list[QuickStat] = []
    for m in _STAT_BULLET_RE.finditer(body):
        label = m.group("label").strip()
        value = m.group("value").strip()
        if label and value:
            stats.append(QuickStat(label=label, value=value))
    return stats


def _parse_numbered_list(body: str) -> list[str]:
    """Pull `1. ...`, `2. ...`, etc. items into a list of strings."""
    items: list[str] = []
    for m in _NUMBERED_RE.finditer(body):
        item = m.group(1).strip()
        if item:
            items.append(item)
    return items

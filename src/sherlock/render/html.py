"""HTML render — a single-file styled page suitable for screenshotting.

Adds confidence-tag pills (green for [Verified], amber for [Reported],
slate for [Inferred]) and a numbered Sources appendix.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime

from sherlock.dossier import Dossier
from sherlock.render.markdown import SECTION_HEADINGS, SECTION_ORDER

try:
    from markdown_it import MarkdownIt

    _md = MarkdownIt("commonmark", {"breaks": True, "html": False})

    def _md_to_html(text: str) -> str:
        return _md.render(text)

except ImportError:  # pragma: no cover

    def _md_to_html(text: str) -> str:
        paragraphs = [
            _html.escape(p).replace("\n", "<br>")
            for p in text.split("\n\n")
            if p.strip()
        ]
        return "\n".join(f"<p>{p}</p>" for p in paragraphs)


_TAG_RE = re.compile(
    r"\[(Verified|Reported|Inferred)(\s*[-—]\s*S\d+|\s*[-—]\s*LinkedIn paste)?\]"
)


def _stylize_tags(html_body: str) -> str:
    """Wrap [Verified|Reported|Inferred] tags in styled <span> pills.

    Runs after markdown -> HTML so that the literal tags survive any
    markdown-time processing. Tags are escaped before the regex match
    via the renderer, so we operate on the rendered HTML form.
    """

    def _replace(m: re.Match[str]) -> str:
        kind = m.group(1).lower()
        suffix = (m.group(2) or "").strip()
        body = m.group(1)
        if suffix:
            body += f" {suffix.lstrip('-—').strip()}"
        return f'<span class="tag tag-{kind}">{_html.escape(body)}</span>'

    return _TAG_RE.sub(_replace, html_body)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Pre-call brief - {name} @ {company}</title>
<style>
  :root {{
    --ink: #0f172a;
    --muted: #64748b;
    --line: #e2e8f0;
    --accent: #0ea5e9;
    --bg: #ffffff;
    --tag-verified-bg: #dcfce7;
    --tag-verified-fg: #166534;
    --tag-reported-bg: #fef3c7;
    --tag-reported-fg: #92400e;
    --tag-inferred-bg: #e2e8f0;
    --tag-inferred-fg: #475569;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: var(--ink);
    background: var(--bg);
    line-height: 1.55;
    max-width: 820px;
    margin: 48px auto;
    padding: 0 24px;
  }}
  header {{
    border-bottom: 1px solid var(--line);
    padding-bottom: 24px;
    margin-bottom: 32px;
  }}
  h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0 0 12px;
  }}
  .header-meta div {{
    color: var(--muted);
    font-size: 13px;
    margin: 2px 0;
  }}
  .header-meta strong {{ color: var(--ink); }}
  h2 {{
    font-size: 14px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    margin: 36px 0 8px;
  }}
  h3 {{
    font-size: 15px;
    font-weight: 700;
    color: var(--ink);
    margin: 20px 0 6px;
  }}
  p, li {{ font-size: 15px; }}
  ol, ul {{ padding-left: 24px; }}
  hr {{
    border: 0;
    border-top: 1px solid var(--line);
    margin: 40px 0 20px;
  }}
  .tag {{
    display: inline-block;
    padding: 1px 7px;
    margin-left: 3px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    vertical-align: 1px;
    white-space: nowrap;
  }}
  .tag-verified {{ background: var(--tag-verified-bg); color: var(--tag-verified-fg); }}
  .tag-reported {{ background: var(--tag-reported-bg); color: var(--tag-reported-fg); }}
  .tag-inferred {{ background: var(--tag-inferred-bg); color: var(--tag-inferred-fg); }}
  .sources-list {{ font-size: 13px; color: var(--muted); }}
  .sources-list a {{ color: var(--accent); text-decoration: none; }}
  footer {{
    color: var(--muted);
    font-size: 13px;
    text-align: center;
  }}
  footer a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
<header>
  <h1>Pre-call brief</h1>
  <div class="header-meta">
    <div><strong>Company:</strong> {company}</div>
    <div><strong>Contact:</strong> {name}{title_suffix}</div>
    {context_line}
    {positioning_line}
    <div><strong>Prepared:</strong> {when}</div>
  </div>
</header>

{body}

{sources}

<hr>
<footer>
  Built on <a href="https://anthropic.com">Claude</a> by
  <a href="https://performancelabs.ai">PerformanceLabs.AI</a>.<br>
  Want help rolling tools like this out across your revenue stack?
  <a href="https://performancelabs.ai">Let's talk</a>.
</footer>
</body>
</html>
"""


def render_html(sections: dict[str, str], dossier: Dossier) -> str:
    name = _html.escape(dossier.linkedin.name or "(unknown)")
    title = dossier.linkedin.headline or dossier.linkedin.current_role
    title_suffix = f", {_html.escape(title)}" if title else ""
    company_label = _html.escape(dossier.company.title or dossier.company.url)
    when = datetime.now().strftime("%B %d, %Y")

    context_line = (
        f'<div><strong>Meeting Context:</strong> {_html.escape(dossier.context)}</div>'
        if dossier.context
        else ""
    )
    positioning_line = (
        f'<div><strong>Your Positioning:</strong> {_html.escape(dossier.positioning)}</div>'
        if dossier.positioning
        else ""
    )

    body_parts: list[str] = []
    for section_id in SECTION_ORDER:
        body = sections.get(section_id)
        if not body:
            continue
        body_parts.append(
            f"<h2>{_html.escape(SECTION_HEADINGS[section_id])}</h2>"
        )
        body_parts.append(_stylize_tags(_md_to_html(body.strip())))

    sources_html = ""
    if dossier.sources:
        rows: list[str] = []
        for s in dossier.sources:
            label = f"<strong>{_html.escape(s.id)}</strong> [{_html.escape(s.kind)}] {_html.escape(s.title)}"
            if s.url:
                label += f' - <a href="{_html.escape(s.url)}">{_html.escape(s.url)}</a>'
            rows.append(f"<li>{label}</li>")
        rows.append(
            "<li><strong>LinkedIn paste</strong> [linkedin_paste] Pasted by user (not retransmitted)</li>"
        )
        sources_html = (
            "<h2>Sources</h2><ul class=\"sources-list\">"
            + "".join(rows)
            + "</ul>"
        )

    return _HTML_TEMPLATE.format(
        name=name,
        title_suffix=title_suffix,
        company=company_label,
        context_line=context_line,
        positioning_line=positioning_line,
        when=when,
        body="\n".join(body_parts),
        sources=sources_html,
    )

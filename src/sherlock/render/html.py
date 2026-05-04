"""HTML render — a single-file styled page suitable for screenshotting."""

from __future__ import annotations

import html as _html
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


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Pre-call brief — {name} @ {company}</title>
<style>
  :root {{
    --ink: #0f172a;
    --muted: #64748b;
    --line: #e2e8f0;
    --accent: #0ea5e9;
    --bg: #ffffff;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: var(--ink);
    background: var(--bg);
    line-height: 1.55;
    max-width: 760px;
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
    margin: 0 0 8px;
  }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .meta a {{ color: var(--accent); text-decoration: none; }}
  h2 {{
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin: 36px 0 8px;
  }}
  p, li {{ font-size: 15.5px; }}
  ol, ul {{ padding-left: 24px; }}
  em {{ color: var(--muted); }}
  hr {{
    border: 0;
    border-top: 1px solid var(--line);
    margin: 40px 0 20px;
  }}
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
  <h1>Pre-call brief — {name} @ {company}</h1>
  <div class="meta">
    {context} · Generated {when} via
    <a href="https://github.com/tonybangert/sherlock">Sherlock</a>
  </div>
</header>

{body}

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
    company_label = _html.escape(dossier.company.title or dossier.company.url)
    context = _html.escape(dossier.context)
    when = datetime.now().strftime("%B %d, %Y")

    body_parts: list[str] = []
    for section_id in SECTION_ORDER:
        body = sections.get(section_id)
        if not body:
            continue
        body_parts.append(
            f"<h2>{_html.escape(SECTION_HEADINGS[section_id])}</h2>"
        )
        body_parts.append(_md_to_html(body.strip()))

    return _HTML_TEMPLATE.format(
        name=name,
        company=company_label,
        context=context,
        when=when,
        body="\n".join(body_parts),
    )

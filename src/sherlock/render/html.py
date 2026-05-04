"""HTML render — a single-file styled page that reads like a printed document.

Branded for PerformanceLabs.AI: deep navy header band with the "Sales
Sherlock" wordmark and an inline SVG magnifying glass, warm cream paper
body, gold accent rule. Confidence-tag pills (green/amber/slate) stay
semantic but are tuned to read on the cream background.

Override the palette by editing the CSS variables at the top of the
template. Five vars cover the brand surface; the semantic pill colors
sit underneath.
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
    """Wrap [Verified|Reported|Inferred] tags in styled <span> pills."""

    def _replace(m: re.Match[str]) -> str:
        kind = m.group(1).lower()
        suffix = (m.group(2) or "").strip()
        body = m.group(1)
        if suffix:
            body += f" {suffix.lstrip('-—').strip()}"
        return f'<span class="tag tag-{kind}">{_html.escape(body)}</span>'

    return _TAG_RE.sub(_replace, html_body)


# Inline SVG magnifying glass. Sized via CSS to match the wordmark cap
# height. Slight rotation for visual interest. Lens has a subtle
# highlight crescent so it reads as a polished glass element.
_MAGNIFIER_SVG = """\
<svg class="magnifier" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <g transform="rotate(-22 32 32)">
    <circle cx="26" cy="26" r="16"
            fill="rgba(201,164,90,0.10)"
            stroke="var(--brand-2)" stroke-width="3.5"/>
    <path d="M21 17 a13 13 0 0 0 -7 11"
          stroke="rgba(255,255,255,0.55)" stroke-width="2"
          stroke-linecap="round" fill="none"/>
    <line x1="38" y1="38" x2="55" y2="55"
          stroke="var(--brand-2)" stroke-width="6" stroke-linecap="round"/>
    <line x1="38" y1="38" x2="55" y2="55"
          stroke="rgba(255,255,255,0.25)" stroke-width="2" stroke-linecap="round"/>
  </g>
</svg>
"""


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Sales Sherlock - Pre-call brief - {name} @ {company}</title>
<style>
  /* ===== Brand palette (override hex codes here to match your real palette) ===== */
  :root {{
    --brand:        #0B1F3A;   /* Deep navy header band */
    --brand-2:      #C9A45A;   /* Warm gold accent */
    --ink:          #1A1A1A;   /* Body text */
    --muted:        #6B6B6B;   /* Meta / muted text */
    --paper:        #F8F5EE;   /* Warm off-white paper */
    --paper-edge:   #ECE6D5;   /* Slightly darker rim */
    --page:         #2A2520;   /* Desk background behind the paper */
    --rule:         #DCD5C6;   /* Paper rule line */
    --accent-soft:  rgba(201,164,90,0.18);

    --tag-verified-bg:  #E5F0E0;
    --tag-verified-fg:  #2F5E2A;
    --tag-reported-bg:  #F6E9C8;
    --tag-reported-fg:  #7A5314;
    --tag-inferred-bg:  #E5DECF;
    --tag-inferred-fg:  #4A4536;
  }}

  * {{ box-sizing: border-box; }}

  html, body {{ margin: 0; padding: 0; }}

  body {{
    background: var(--page);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
    line-height: 1.55;
    padding: 48px 16px 64px;
  }}

  .paper {{
    max-width: 820px;
    margin: 0 auto;
    background: var(--paper);
    border: 1px solid var(--paper-edge);
    border-radius: 4px;
    box-shadow:
      0 1px 0 rgba(255,255,255,0.04) inset,
      0 30px 60px -20px rgba(0,0,0,0.55),
      0 8px 18px rgba(0,0,0,0.35);
    overflow: hidden;
  }}

  /* ===== Brand header band ===== */
  .brand-band {{
    background: linear-gradient(180deg, var(--brand) 0%, #08172B 100%);
    color: #F1ECDB;
    padding: 28px 56px 22px;
    border-bottom: 2px solid var(--brand-2);
    position: relative;
  }}
  .brand-band::after {{
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: -2px;
    height: 2px;
    background: linear-gradient(90deg,
      var(--brand-2) 0%,
      rgba(201,164,90,0.55) 60%,
      rgba(201,164,90,0) 100%);
  }}

  .wordmark {{
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: ui-serif, "Iowan Old Style", "Apple Garamond", Baskerville,
                 "Times New Roman", Georgia, serif;
    font-size: 34px;
    font-weight: 600;
    letter-spacing: 0.01em;
    line-height: 1;
    margin: 0;
  }}
  .wordmark .word {{
    background: linear-gradient(180deg, #FBF6E5 0%, #E6D9B4 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }}
  .magnifier {{
    width: 38px;
    height: 38px;
    flex-shrink: 0;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.45));
  }}

  .brand-tagline {{
    margin-top: 6px;
    color: rgba(241, 236, 219, 0.65);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 500;
  }}

  /* ===== Document body ===== */
  .doc {{
    padding: 38px 56px 48px;
  }}

  .doc-title {{
    font-family: ui-serif, "Iowan Old Style", "Apple Garamond", Baskerville,
                 Georgia, serif;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.005em;
    color: var(--ink);
    margin: 0 0 18px;
  }}

  .header-meta {{
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 16px;
    font-size: 14px;
    color: var(--ink);
    padding-bottom: 18px;
    border-bottom: 1px solid var(--rule);
  }}
  .header-meta dt {{
    color: var(--muted);
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding-top: 3px;
  }}
  .header-meta dd {{ margin: 0; }}

  h2 {{
    font-family: ui-serif, "Iowan Old Style", Georgia, serif;
    font-size: 16px;
    font-weight: 700;
    color: var(--brand);
    margin: 36px 0 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--rule);
    letter-spacing: 0.005em;
  }}
  h2::before {{
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    background: var(--brand-2);
    border-radius: 50%;
    vertical-align: 4px;
    margin-right: 10px;
  }}

  h3, .doc strong {{ color: var(--ink); }}
  h3 {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
    font-size: 14px;
    font-weight: 700;
    margin: 18px 0 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--brand);
  }}

  p, li {{ font-size: 14.5px; }}
  p {{ margin: 0 0 12px; }}
  ul, ol {{ padding-left: 22px; margin: 0 0 14px; }}
  li {{ margin-bottom: 6px; }}

  a {{ color: var(--brand); text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 2px; }}

  /* ===== Confidence-tag pills ===== */
  .tag {{
    display: inline-block;
    padding: 1px 8px;
    margin: 0 1px 0 3px;
    border-radius: 999px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
    vertical-align: 2px;
    white-space: nowrap;
    border: 1px solid transparent;
  }}
  .tag-verified {{ background: var(--tag-verified-bg); color: var(--tag-verified-fg); border-color: rgba(47,94,42,0.20); }}
  .tag-reported {{ background: var(--tag-reported-bg); color: var(--tag-reported-fg); border-color: rgba(122,83,20,0.22); }}
  .tag-inferred {{ background: var(--tag-inferred-bg); color: var(--tag-inferred-fg); border-color: rgba(74,69,54,0.18); }}

  /* ===== Sources appendix ===== */
  .sources-list {{
    list-style: none;
    padding: 0;
    margin: 0;
    font-size: 12.5px;
    color: var(--muted);
  }}
  .sources-list li {{ padding: 4px 0; border-bottom: 1px dotted var(--rule); }}
  .sources-list li:last-child {{ border-bottom: 0; }}
  .sources-list a {{ color: var(--brand); }}

  /* ===== Footer band ===== */
  .footer-band {{
    margin-top: 42px;
    padding: 22px 56px;
    background: var(--brand);
    color: rgba(241, 236, 219, 0.78);
    font-size: 12.5px;
    letter-spacing: 0.02em;
    text-align: center;
    border-top: 2px solid var(--brand-2);
  }}
  .footer-band a {{
    color: var(--brand-2);
    text-decoration: none;
    font-weight: 600;
  }}
  .footer-band a:hover {{ text-decoration: underline; }}

  /* ===== Print ===== */
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .paper {{ box-shadow: none; border: none; max-width: none; }}
    .brand-band, .footer-band {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
  <main class="paper">
    <div class="brand-band">
      <h1 class="wordmark">
        <span class="word">Sales Sherlock</span>
        {magnifier}
      </h1>
      <div class="brand-tagline">A PerformanceLabs.AI pre-call research tool</div>
    </div>

    <div class="doc">
      <h2 class="doc-title">Pre-call brief</h2>
      <dl class="header-meta">
        <dt>Company</dt><dd>{company}</dd>
        <dt>Contact</dt><dd>{name}{title_suffix}</dd>
        {context_row}
        {positioning_row}
        <dt>Prepared</dt><dd>{when}</dd>
      </dl>

      {body}

      {sources}
    </div>

    <div class="footer-band">
      Built on <a href="https://anthropic.com">Claude</a> by
      <a href="https://performancelabs.ai">PerformanceLabs.AI</a>.
      &nbsp;&middot;&nbsp;
      Want this rolled out across your revenue stack?
      <a href="https://performancelabs.ai">Let's talk</a>.
    </div>
  </main>
</body>
</html>
"""


def render_html(sections: dict[str, str], dossier: Dossier) -> str:
    name = _html.escape(dossier.linkedin.name or "(unknown)")
    title = dossier.linkedin.headline or dossier.linkedin.current_role
    title_suffix = f", {_html.escape(title)}" if title else ""
    company_label = _html.escape(dossier.company.title or dossier.company.url)
    when = datetime.now().strftime("%B %d, %Y")

    context_row = (
        f"<dt>Meeting</dt><dd>{_html.escape(dossier.context)}</dd>"
        if dossier.context
        else ""
    )
    positioning_row = (
        f"<dt>Positioning</dt><dd>{_html.escape(dossier.positioning)}</dd>"
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
            label = (
                f"<strong>{_html.escape(s.id)}</strong> "
                f"<span style=\"color:var(--brand-2);font-weight:600;\">[{_html.escape(s.kind)}]</span> "
                f"{_html.escape(s.title)}"
            )
            if s.url:
                label += (
                    f' &nbsp;<a href="{_html.escape(s.url)}">'
                    f'{_html.escape(s.url)}</a>'
                )
            rows.append(f"<li>{label}</li>")
        rows.append(
            "<li><strong>LinkedIn paste</strong> "
            "<span style=\"color:var(--brand-2);font-weight:600;\">[linkedin_paste]</span> "
            "Pasted by user (not retransmitted)</li>"
        )
        sources_html = (
            "<h2>Sources</h2><ul class=\"sources-list\">"
            + "".join(rows)
            + "</ul>"
        )

    return _HTML_TEMPLATE.format(
        magnifier=_MAGNIFIER_SVG,
        name=name,
        title_suffix=title_suffix,
        company=company_label,
        context_row=context_row,
        positioning_row=positioning_row,
        when=when,
        body="\n".join(body_parts),
        sources=sources_html,
    )

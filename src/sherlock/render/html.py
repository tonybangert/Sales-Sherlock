"""HTML render — a designed two-page editorial brief.

On screen: long-scroll, single column, paper-feel. On print/PDF: snaps
to a 2-3 page layout where the Executive Read anchors page one and the
nine numbered sections flow across pages 2-3 in two columns.

Brand palette is defined as CSS variables at the top of the template.
Five vars cover the brand surface; semantic confidence-tag colors sit
underneath.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime

from sherlock.dossier import Dossier
from sherlock.render.executive import ExecutiveRead, parse_executive_read
from sherlock.render.markdown import SECTION_HEADINGS

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


# Sections that flow into the two-column dossier on pages 2-3.
_DOSSIER_SECTION_ORDER: list[str] = [
    "company_overview",
    "company_history",
    "investment_ownership",
    "growth_revenue_signals",
    "industry_competitive",
    "contact_professional",
    "contact_personal",
    "psychographic",
    "hooks_and_risks",
]


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
  /* ===== Brand palette ===== */
  :root {{
    --brand:        #0B1F3A;
    --brand-2:      #C9A45A;
    --ink:          #1A1A1A;
    --muted:        #6B6B6B;
    --paper:        #F8F5EE;
    --paper-edge:   #ECE6D5;
    --paper-inset:  #FFFDF7;
    --page:         #2A2520;
    --rule:         #DCD5C6;
    --accent-soft:  rgba(201,164,90,0.18);

    --tag-verified-bg:  #E5F0E0;
    --tag-verified-fg:  #2F5E2A;
    --tag-reported-bg:  #F6E9C8;
    --tag-reported-fg:  #7A5314;
    --tag-inferred-bg:  #E5DECF;
    --tag-inferred-fg:  #4A4536;

    --serif: ui-serif, "Iowan Old Style", "Apple Garamond", Baskerville,
             "Times New Roman", Georgia, serif;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui,
            sans-serif;
  }}

  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}

  body {{
    background: var(--page);
    color: var(--ink);
    font-family: var(--sans);
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

  /* ===== Brand band ===== */
  .brand-band {{
    background: linear-gradient(180deg, var(--brand) 0%, #08172B 100%);
    color: #F1ECDB;
    padding: 26px 56px 20px;
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
    font-family: var(--serif);
    font-size: 32px;
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
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.45));
  }}
  .brand-tagline {{
    margin-top: 6px;
    color: rgba(241, 236, 219, 0.65);
    font-size: 11.5px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 500;
  }}

  /* ===== Article ===== */
  .brief {{
    padding: 36px 56px 44px;
  }}

  /* ===== Masthead ===== */
  .brief-masthead {{
    margin: 0 0 24px;
    padding-bottom: 18px;
    border-bottom: 1px solid var(--rule);
  }}
  .company-name {{
    font-family: var(--serif);
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--ink);
    margin: 0 0 4px;
    line-height: 1.15;
  }}
  .meta-line {{
    font-size: 13px;
    color: var(--muted);
    letter-spacing: 0.01em;
    margin: 0;
  }}
  .meta-line .meta-sep {{
    color: var(--brand-2);
    margin: 0 8px;
    font-weight: 700;
  }}

  /* ===== Executive Read card ===== */
  .executive-read {{
    margin: 0 0 32px;
  }}
  .exec-eyebrow {{
    font-family: var(--sans);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: var(--brand-2);
    margin: 0 0 14px;
  }}

  .stat-strip {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    list-style: none;
    padding: 0;
    margin: 0 0 22px;
  }}
  .stat {{
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: 9px 12px 10px;
    background: var(--paper-inset);
  }}
  .stat-label {{
    display: block;
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 3px;
  }}
  .stat-value {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
    line-height: 1.35;
  }}
  @media (max-width: 640px) {{
    .stat-strip {{ grid-template-columns: repeat(2, 1fr); }}
  }}

  .exec-block {{
    margin-bottom: 16px;
  }}
  .exec-block h3 {{
    font-family: var(--sans);
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--brand);
    margin: 0 0 6px;
  }}
  .exec-block ol {{
    margin: 0;
    padding-left: 22px;
    font-size: 14px;
  }}
  .exec-block ol li {{
    margin-bottom: 4px;
  }}

  .exec-hypothesis p {{
    font-family: var(--serif);
    font-size: 16px;
    font-style: italic;
    line-height: 1.5;
    color: var(--ink);
    margin: 0;
    padding: 14px 0 12px;
    border-top: 1px solid var(--brand-2);
    border-bottom: 1px solid var(--rule);
  }}

  /* ===== Dossier (pages 2-3) ===== */
  .dossier {{
    margin-top: 8px;
  }}
  .brief-section {{
    margin-bottom: 18px;
  }}
  .brief-section h2 {{
    font-family: var(--serif);
    font-size: 16px;
    font-weight: 700;
    color: var(--brand);
    margin: 12px 0 8px;
    padding-bottom: 5px;
    border-bottom: 1px solid var(--rule);
    letter-spacing: 0.005em;
  }}
  .brief-section h2::before {{
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    background: var(--brand-2);
    border-radius: 50%;
    vertical-align: 4px;
    margin-right: 9px;
  }}
  .brief-section h3 {{
    font-family: var(--sans);
    font-size: 12px;
    font-weight: 700;
    margin: 14px 0 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--brand);
  }}
  .brief-section p,
  .brief-section li {{
    font-size: 13.5px;
    line-height: 1.55;
  }}
  .brief-section p {{ margin: 0 0 10px; }}
  .brief-section ul,
  .brief-section ol {{
    padding-left: 20px;
    margin: 0 0 12px;
  }}
  .brief-section li {{ margin-bottom: 4px; }}
  .brief-section strong {{ color: var(--ink); }}

  a {{
    color: var(--brand);
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 2px;
  }}

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

  /* ===== Sources ===== */
  .sources {{
    margin-top: 28px;
    padding-top: 16px;
    border-top: 1px solid var(--rule);
  }}
  .sources h2 {{
    font-family: var(--serif);
    font-size: 14px;
    font-weight: 700;
    color: var(--brand);
    margin: 0 0 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .sources-list {{
    list-style: none;
    padding: 0;
    margin: 0;
    font-size: 11.5px;
    color: var(--muted);
  }}
  .sources-list li {{
    padding: 4px 0;
    border-bottom: 1px dotted var(--rule);
  }}
  .sources-list li:last-child {{ border-bottom: 0; }}
  .sources-list a {{ color: var(--brand); }}
  .source-kind {{ color: var(--brand-2); font-weight: 600; }}

  /* ===== Footer band ===== */
  .footer-band {{
    margin-top: 0;
    padding: 18px 56px;
    background: var(--brand);
    color: rgba(241, 236, 219, 0.78);
    font-size: 12px;
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

  /* ===== Print: snap to 2-3 pages ===== */
  @media print {{
    @page {{
      size: letter;
      margin: 0.55in 0.6in;
    }}

    body {{
      background: #fff;
      padding: 0;
      font-size: 11pt;
    }}
    .paper {{
      box-shadow: none;
      border: none;
      border-radius: 0;
      max-width: none;
      overflow: visible;
    }}
    .brand-band, .footer-band {{
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .brand-band {{
      padding: 18px 0 14px;
    }}
    .brief {{
      padding: 18px 0 0;
    }}
    .brief-masthead {{
      margin: 0 0 14px;
      padding-bottom: 10px;
    }}
    .company-name {{ font-size: 22pt; }}
    .meta-line {{ font-size: 9.5pt; }}

    .exec-eyebrow {{ margin-bottom: 8px; }}
    .stat-strip {{ gap: 6px; margin-bottom: 14px; }}
    .stat {{ padding: 6px 9px 7px; }}
    .stat-label {{ font-size: 7.5pt; }}
    .stat-value {{ font-size: 9pt; }}
    .exec-block {{ margin-bottom: 10px; }}
    .exec-block h3 {{ font-size: 8pt; }}
    .exec-block ol {{ font-size: 10pt; }}
    .exec-hypothesis p {{ font-size: 11.5pt; padding: 10px 0 9px; }}

    /* Page-1 break: dossier and sources start on new pages when the
       executive read is present. Class added by the renderer only when
       there is a non-empty executive_read to anchor page 1. */
    .dossier--page2 {{
      break-before: page;
      page-break-before: always;
    }}

    /* Two-column flow for the nine sections in print only. */
    .dossier-grid {{
      column-count: 2;
      column-gap: 0.32in;
      column-fill: balance;
    }}
    .brief-section {{
      break-inside: avoid;
      page-break-inside: avoid;
      margin-bottom: 10px;
    }}
    .brief-section h2 {{
      font-size: 10.5pt;
      margin: 4px 0 5px;
      padding-bottom: 3px;
    }}
    .brief-section h3 {{
      font-size: 8pt;
      margin: 8px 0 3px;
    }}
    .brief-section p,
    .brief-section li {{ font-size: 9.5pt; line-height: 1.4; }}
    .brief-section p {{ margin: 0 0 6px; }}
    .brief-section ul,
    .brief-section ol {{ margin: 0 0 7px; padding-left: 16px; }}

    .tag {{ font-size: 7.5pt; padding: 0 6px; }}

    .sources {{
      break-before: page;
      page-break-before: always;
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }}
    .sources h2 {{ font-size: 10pt; }}
    .sources-list {{ font-size: 8.5pt; }}

    .footer-band {{
      padding: 10px 0;
      font-size: 8pt;
    }}
  }}
</style>
</head>
<body>
  <main class="paper">
    <header class="brand-band">
      <h1 class="wordmark">
        <span class="word">Sales Sherlock</span>
        {magnifier}
      </h1>
      <div class="brand-tagline">Pre-call research, in 60 seconds</div>
    </header>

    <article class="brief">
      <header class="brief-masthead">
        <h2 class="company-name">{company}</h2>
        <p class="meta-line">{meta_line}</p>
      </header>

      {executive_read_html}

      <section class="{dossier_class}">
        <div class="dossier-grid">
          {dossier_html}
        </div>
      </section>

      {sources_html}
    </article>

    <footer class="footer-band">
      Built on <a href="https://anthropic.com">Claude</a>.
    </footer>
  </main>
</body>
</html>
"""


def render_html(sections: dict[str, str], dossier: Dossier) -> str:
    name = dossier.linkedin.name or "(unknown)"
    title = dossier.linkedin.headline or dossier.linkedin.current_role
    company_label = dossier.company.title or dossier.company.url
    when = datetime.now().strftime("%B %d, %Y")

    meta_line = _build_meta_line(name, title, dossier.context, when)

    exec_read = parse_executive_read(sections.get("executive_read", ""))
    executive_read_html = _render_executive_read(exec_read)
    dossier_class = (
        "dossier dossier--page2" if not exec_read.is_empty else "dossier"
    )

    dossier_html = _render_dossier_sections(sections)
    sources_html = _render_sources(dossier)

    return _HTML_TEMPLATE.format(
        magnifier=_MAGNIFIER_SVG,
        name=_html.escape(name),
        company=_html.escape(company_label),
        meta_line=meta_line,
        executive_read_html=executive_read_html,
        dossier_class=dossier_class,
        dossier_html=dossier_html,
        sources_html=sources_html,
    )


def _build_meta_line(
    name: str,
    title: str | None,
    context: str | None,
    when: str,
) -> str:
    """Single-line meta string under the company name."""
    parts: list[str] = []
    contact = _html.escape(name)
    if title:
        contact += f", {_html.escape(title)}"
    parts.append(contact)
    if context:
        parts.append(_html.escape(context))
    parts.append(f"Prepared {_html.escape(when)}")
    sep = '<span class="meta-sep">&middot;</span>'
    return sep.join(parts)


def _render_executive_read(er: ExecutiveRead) -> str:
    """Render the page-one Executive Read card. Empty string if no data."""
    if er.is_empty:
        return ""

    parts: list[str] = ['<section class="executive-read">']
    parts.append('<div class="exec-eyebrow">Executive Read</div>')

    if er.quick_stats:
        parts.append('<ul class="stat-strip">')
        for stat in er.quick_stats:
            value_html = _stylize_tags(_html.escape(stat.value))
            parts.append(
                '<li class="stat">'
                f'<span class="stat-label">{_html.escape(stat.label)}</span>'
                f'<span class="stat-value">{value_html}</span>'
                '</li>'
            )
        parts.append('</ul>')

    if er.priorities:
        parts.append('<div class="exec-block exec-priorities">')
        parts.append('<h3>Three likely priorities</h3>')
        parts.append('<ol>')
        for item in er.priorities:
            parts.append(f'<li>{_stylize_tags(_html.escape(item))}</li>')
        parts.append('</ol>')
        parts.append('</div>')

    if er.hypothesis:
        parts.append('<div class="exec-block exec-hypothesis">')
        parts.append('<h3>Entry hypothesis</h3>')
        parts.append(f'<p>{_stylize_tags(_html.escape(er.hypothesis))}</p>')
        parts.append('</div>')

    if er.questions:
        parts.append('<div class="exec-block exec-questions">')
        parts.append('<h3>Three high-leverage questions</h3>')
        parts.append('<ol>')
        for item in er.questions:
            parts.append(f'<li>{_html.escape(item)}</li>')
        parts.append('</ol>')
        parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


def _render_dossier_sections(sections: dict[str, str]) -> str:
    """Render the nine numbered sections, each in its own break-safe article."""
    parts: list[str] = []
    for section_id in _DOSSIER_SECTION_ORDER:
        body = sections.get(section_id)
        if not body:
            continue
        heading = SECTION_HEADINGS.get(section_id, section_id)
        body_html = _stylize_tags(_md_to_html(body.strip()))
        parts.append(
            f'<article class="brief-section">'
            f'<h2>{_html.escape(heading)}</h2>'
            f'{body_html}'
            f'</article>'
        )
    return "\n".join(parts)


def _render_sources(dossier: Dossier) -> str:
    if not dossier.sources:
        return ""
    rows: list[str] = []
    for s in dossier.sources:
        label = (
            f"<strong>{_html.escape(s.id)}</strong> "
            f'<span class="source-kind">[{_html.escape(s.kind)}]</span> '
            f"{_html.escape(s.title)}"
        )
        if s.url:
            label += (
                f' &nbsp;<a href="{_html.escape(s.url)}">'
                f'{_html.escape(s.url)}</a>'
            )
        rows.append(f"<li>{label}</li>")
    rows.append(
        '<li><strong>LinkedIn paste</strong> '
        '<span class="source-kind">[linkedin_paste]</span> '
        'Pasted by user (not retransmitted)</li>'
    )
    return (
        '<section class="sources">'
        '<h2>Sources</h2>'
        '<ul class="sources-list">'
        + "".join(rows)
        + '</ul></section>'
    )

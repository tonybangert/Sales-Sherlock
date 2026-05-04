"""Fetch a company website and extract the main text + meta."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from sherlock.dossier import CompanySummary

USER_AGENT = (
    "Mozilla/5.0 (compatible; SherlockBot/0.1; "
    "+https://github.com/tonybangert/sherlock)"
)

# Cap the extracted text so we don't blow up the prompt context
MAX_TEXT_CHARS = 6000


async def fetch_company_summary(
    url_or_domain: str,
    timeout: float = 12.0,
) -> CompanySummary:
    """Fetch a company website. Title + meta description + cleaned body text."""
    url = url_or_domain.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")

    summary = CompanySummary(url=url)

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:  # noqa: BLE001
        summary.text = f"(Unable to fetch {url}: {exc})"
        return summary

    soup = BeautifulSoup(html, "html.parser")

    if soup.title and soup.title.get_text(strip=True):
        summary.title = soup.title.get_text(strip=True)

    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and desc_tag.get("content"):
        summary.description = desc_tag["content"].strip()
    else:
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            summary.description = og_desc["content"].strip()

    # Strip non-content elements before extracting text
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    text = " ".join(soup.get_text(" ", strip=True).split())
    summary.text = text[:MAX_TEXT_CHARS]

    return summary

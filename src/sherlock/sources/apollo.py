"""Optional enrichment via Apollo.io.

Activated automatically when APOLLO_API_KEY is set. Two API calls:
  - POST /v1/organizations/enrich  — firmographics by domain
  - POST /v1/people/match          — person enrichment by name + domain

Failures are non-fatal — the caller catches and warns the user. The dossier
just won't have an `<apollo_enrichment>` block in that case.

API docs: https://docs.apollo.io/reference/
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from sherlock.dossier import ApolloEnrichment

APOLLO_BASE = "https://api.apollo.io/v1"


async def enrich_with_apollo(
    person_name: Optional[str] = None,
    company_domain: Optional[str] = None,
    timeout: float = 15.0,
) -> ApolloEnrichment:
    """Enrich a person + company via Apollo. Requires APOLLO_API_KEY."""
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        raise RuntimeError("APOLLO_API_KEY not set")

    enrichment = ApolloEnrichment()
    domain = _normalize_domain(company_domain) if company_domain else None

    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        if domain:
            enrichment.organization = await _enrich_organization(client, domain)

        if person_name and domain:
            enrichment.person = await _enrich_person(client, person_name, domain)

    return enrichment


def _normalize_domain(raw: str) -> str:
    """Strip protocol, trailing slash, and any path."""
    domain = raw.strip()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix) :]
    domain = domain.lstrip("/").split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


async def _enrich_organization(client: httpx.AsyncClient, domain: str) -> dict:
    try:
        resp = await client.post(
            f"{APOLLO_BASE}/organizations/enrich",
            json={"domain": domain},
        )
        if resp.status_code != 200:
            return {}
        org = (resp.json() or {}).get("organization") or {}
    except Exception:  # noqa: BLE001
        return {}

    # Keep the prompt small — only fields useful to the brief
    return {
        "name": org.get("name"),
        "industry": org.get("industry"),
        "estimated_num_employees": org.get("estimated_num_employees"),
        "annual_revenue_printed": org.get("annual_revenue_printed"),
        "founded_year": org.get("founded_year"),
        "short_description": org.get("short_description"),
        "keywords": (org.get("keywords") or [])[:10],
        "technologies": [
            t.get("name") for t in (org.get("current_technologies") or [])[:15]
        ],
        "linkedin_url": org.get("linkedin_url"),
        "website_url": org.get("website_url"),
        "city": org.get("city"),
        "state": org.get("state"),
        "country": org.get("country"),
        "publicly_traded_symbol": org.get("publicly_traded_symbol"),
        "total_funding_printed": org.get("total_funding_printed"),
        "latest_funding_stage": org.get("latest_funding_stage"),
        "latest_funding_round_date": org.get("latest_funding_round_date"),
    }


async def _enrich_person(
    client: httpx.AsyncClient,
    person_name: str,
    domain: str,
) -> dict:
    parts = person_name.strip().split()
    if not parts:
        return {}
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    try:
        resp = await client.post(
            f"{APOLLO_BASE}/people/match",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain,
                "reveal_personal_emails": False,
                "reveal_phone_number": False,
            },
        )
        if resp.status_code != 200:
            return {}
        person = (resp.json() or {}).get("person") or {}
    except Exception:  # noqa: BLE001
        return {}

    return {
        "name": person.get("name"),
        "title": person.get("title"),
        "headline": person.get("headline"),
        "city": person.get("city"),
        "state": person.get("state"),
        "country": person.get("country"),
        "seniority": person.get("seniority"),
        "departments": person.get("departments"),
        "subdepartments": person.get("subdepartments"),
        "linkedin_url": person.get("linkedin_url"),
        "twitter_url": person.get("twitter_url"),
        "github_url": person.get("github_url"),
        "employment_history": [
            {
                "title": e.get("title"),
                "organization_name": e.get("organization_name"),
                "start_date": e.get("start_date"),
                "end_date": e.get("end_date"),
                "current": e.get("current"),
            }
            for e in (person.get("employment_history") or [])[:6]
        ],
    }

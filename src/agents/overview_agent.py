"""Overview agent: gathers sourced factual claims about a company."""
from __future__ import annotations
import time
from ..models import CitedClaim, ConfidenceLevel, CompanyIdentity
from ..tools.search import ddg_search
from ..tools.scraper import fetch_page_text
from ..llm import llm_json

_SYSTEM = """You are a financial research analyst extracting facts for an investor one-pager.

Given a web source about a company, extract factual claims suitable for a company overview.

Return ONLY this JSON (no markdown):
{
  "claims": [
    {
      "value": "One clear factual statement about the company",
      "snippet": "The EXACT sentence or phrase from the source that proves this claim",
      "confidence": "HIGH" or "MEDIUM" or "LOW"
    }
  ]
}

CONFIDENCE LEVELS:
- HIGH: Company's own website, official annual report, or stock exchange filing
- MEDIUM: Reputable news outlet (Reuters, ET, BS, Moneycontrol) or credible database
- LOW: Blog, forum, aggregator, or the fact is loosely implied

EXTRACT claims about:
- What the company does / core business
- How it operates (manufacturing, B2B/B2C, export/domestic split)
- Key geographies or markets served
- Scale indicators (employees, plants, countries, etc.)
- Revenue model

STRICT RULES:
1. ONLY include claims with direct textual evidence in the source (include the exact snippet)
2. Do NOT extrapolate, infer, or combine information
3. Do NOT include financial figures (handled separately)
4. Maximum 5 claims per source
5. If nothing useful is in the source, return {"claims": []}"""


def _extract_claims(content: str, url: str, title: str, company_name: str) -> list[CitedClaim]:
    if not content or len(content.strip()) < 50:
        return []

    data = llm_json(
        _SYSTEM,
        f"Company: {company_name}\nSource URL: {url}\nSource Title: {title}\n\nContent:\n{content[:4000]}",
    )
    if not data or "claims" not in data:
        return []

    claims: list[CitedClaim] = []
    for c in data["claims"]:
        try:
            claims.append(CitedClaim(
                value=c["value"],
                source_url=url,
                source_title=title,
                snippet=c.get("snippet", "")[:300],
                confidence=ConfidenceLevel(c.get("confidence", "MEDIUM")),
            ))
        except Exception:
            continue
    return claims


def gather_overview(identity: CompanyIdentity) -> list[CitedClaim]:
    print(f"[Overview] Gathering overview for: {identity.canonical_name}")

    queries = [
        f"{identity.canonical_name} company business overview operations",
        f"{identity.canonical_name} annual report products revenue model customers",
        f"{identity.canonical_name} about us manufacturing exports",
    ]
    if identity.website:
        queries.append(f"site:{identity.website} about company business")

    all_claims: list[CitedClaim] = []
    seen: set[str] = set()

    for query in queries[:3]:
        results = ddg_search(query, max_results=4)
        for r in results[:2]:
            url = r.get("href", "")
            title = r.get("title", "Unknown")
            snippet = r.get("body", "")

            # Prefer full page text; fall back to search snippet
            full_text = fetch_page_text(url, max_chars=4500) if url else None
            content = full_text if full_text and len(full_text) > len(snippet) else snippet

            new_claims = _extract_claims(content, url, title, identity.canonical_name)
            for claim in new_claims:
                key = claim.value.lower()[:80]
                if key not in seen:
                    seen.add(key)
                    all_claims.append(claim)

            time.sleep(2)   # Polite delay between LLM calls

        time.sleep(1.5)     # Polite delay between search batches

    print(f"[Overview] {len(all_claims)} unique claims gathered")
    return all_claims[:15]  # Cap at 15 to keep the one-pager tight

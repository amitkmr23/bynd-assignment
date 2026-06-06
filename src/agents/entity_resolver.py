"""Entity resolver: confirms company identity from a name and returns structured identifiers."""
from __future__ import annotations
import time
from ..models import CompanyIdentity
from ..tools.search import ddg_search
from ..llm import llm_json

_SYSTEM = """You are a company research assistant. Given web search results about a company, extract its key identifiers.

Return ONLY this JSON structure (no markdown, no extra text):
{
  "canonical_name": "full official company name",
  "website": "official website URL or null",
  "ticker": "stock ticker with exchange suffix e.g. BHARATFORG.NS — null if not listed or uncertain",
  "exchange": "e.g. NSE/BSE or null",
  "sector": "broad business sector e.g. Industrials",
  "industry": "specific industry e.g. Auto Components",
  "hq": "City, Country",
  "is_listed": true or false
}

RULES:
- Only return a ticker if it is EXPLICITLY mentioned in the search results
- If the company is unlisted / private, set is_listed=false and ticker=null
- Do not guess or invent any field — use null if uncertain"""


def resolve_entity(company_name: str) -> CompanyIdentity:
    print(f"[EntityResolver] Identifying: {company_name}")
    queries = [
        f'"{company_name}" company official website sector listed',
        f"{company_name} NSE BSE ticker stock exchange India",
    ]

    all_results: list[dict] = []
    for q in queries:
        all_results.extend(ddg_search(q, max_results=4))
        time.sleep(1.5)

    source_url = all_results[0].get("href", "") if all_results else ""

    search_text = "\n\n".join(
        f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSnippet: {r.get('body', '')}"
        for r in all_results[:6]
    )

    data = llm_json(
        _SYSTEM,
        f"Company to identify: {company_name}\n\nSearch results:\n{search_text}",
    )

    if not data:
        print(f"[EntityResolver] LLM returned nothing — using bare input name")
        return CompanyIdentity(
            name=company_name,
            canonical_name=company_name,
            search_source=source_url,
        )

    return CompanyIdentity(
        name=company_name,
        canonical_name=data.get("canonical_name") or company_name,
        website=data.get("website"),
        ticker=data.get("ticker"),
        exchange=data.get("exchange"),
        sector=data.get("sector"),
        industry=data.get("industry"),
        hq=data.get("hq"),
        is_listed=bool(data.get("is_listed", False)),
        search_source=source_url,
    )

"""Products & clients agent: extracts verified product names and customer relationships."""
from __future__ import annotations
import time
from ..models import ProductInfo, ClientInfo, CitedClaim, ConfidenceLevel, CompanyIdentity
from ..tools.search import ddg_search
from ..tools.scraper import fetch_page_text
from ..llm import llm_json

_SYSTEM = """You are a financial analyst building an investor one-pager.

Extract products/services and named clients from the provided source content.

Return ONLY this JSON:
{
  "products": [
    {
      "name": "product or service name",
      "description": "brief description of what it is / what it does",
      "snippet": "EXACT text from the source that names this product"
    }
  ],
  "clients": [
    {
      "name": "client or customer company name",
      "relationship": "what they buy or the nature of the supply relationship",
      "snippet": "EXACT text from the source naming this client"
    }
  ]
}

CONFIDENCE: set to "HIGH" if from company's own site/filing, "MEDIUM" for credible 3rd-party news, "LOW" otherwise.

STRICT RULES:
1. Only include products/clients EXPLICITLY NAMED in the source text
2. Do NOT infer clients from industry context ("likely supplies to X" is NOT acceptable)
3. Do NOT list generic industry categories as products — only named product lines or offerings
4. If nothing is found, return {"products": [], "clients": []}
5. Include the exact snippet so the claim can be verified"""


def _parse_source(
    content: str,
    url: str,
    title: str,
    company_name: str,
    confidence_default: str = "MEDIUM",
) -> tuple[list[ProductInfo], list[ClientInfo]]:
    if not content or len(content.strip()) < 50:
        return [], []

    # Infer confidence from domain
    high_domains = ["bharatforge.com", "brakesindia.com", "bse.india.com",
                    "nseindia.com", "annualreport", "ir."]
    conf = "HIGH" if any(d in url.lower() for d in high_domains) else confidence_default

    data = llm_json(
        _SYSTEM,
        f"Company: {company_name}\nSource URL: {url}\nSource Title: {title}\n"
        f"Default confidence: {conf}\n\nContent:\n{content[:4000]}",
    )
    if not data:
        return [], []

    products: list[ProductInfo] = []
    for p in data.get("products", []):
        name = (p.get("name") or "").strip()
        if not name:
            continue
        try:
            products.append(ProductInfo(
                name=name,
                description=CitedClaim(
                    value=p.get("description") or name,
                    source_url=url,
                    source_title=title,
                    snippet=p.get("snippet", "")[:250],
                    confidence=ConfidenceLevel(conf),
                ),
            ))
        except Exception:
            continue

    clients: list[ClientInfo] = []
    for c in data.get("clients", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        try:
            clients.append(ClientInfo(
                name=name,
                relationship=CitedClaim(
                    value=c.get("relationship") or f"Customer of {company_name}",
                    source_url=url,
                    source_title=title,
                    snippet=c.get("snippet", "")[:250],
                    confidence=ConfidenceLevel(conf),
                ),
            ))
        except Exception:
            continue

    return products, clients


def gather_products_and_clients(
    identity: CompanyIdentity,
) -> tuple[list[ProductInfo], list[ClientInfo]]:
    print(f"[Products] Gathering products & clients for: {identity.canonical_name}")

    queries = [
        f"{identity.canonical_name} products portfolio key customers OEM clients",
        f"{identity.canonical_name} product range manufacturing supply",
        f"{identity.canonical_name} key customers buyers contracts",
    ]
    if identity.website:
        domain = identity.website.replace("https://", "").replace("http://", "").split("/")[0]
        queries.append(f"site:{domain} products customers")

    all_products: dict[str, ProductInfo] = {}
    all_clients: dict[str, ClientInfo] = {}

    for query in queries[:3]:
        results = ddg_search(query, max_results=4)
        for r in results[:2]:
            url = r.get("href", "")
            title = r.get("title", "Unknown")
            snippet = r.get("body", "")

            full_text = fetch_page_text(url, max_chars=4500) if url else None
            content = full_text if full_text and len(full_text) > len(snippet) else snippet

            prods, clients = _parse_source(content, url, title, identity.canonical_name)

            for p in prods:
                if p.name not in all_products:
                    all_products[p.name] = p

            for c in clients:
                if c.name not in all_clients:
                    all_clients[c.name] = c

            time.sleep(2)

        time.sleep(1.5)

    print(f"[Products] {len(all_products)} products, {len(all_clients)} clients found")
    return list(all_products.values())[:10], list(all_clients.values())[:10]

"""Financial agent: pulls multi-year financials from yfinance (listed) or web search (unlisted)."""
from __future__ import annotations
import time
from ..models import FinancialSnapshot, FinancialRow, CompanyIdentity
from ..tools.search import ddg_search
from ..tools.scraper import fetch_page_text
from ..tools.financial import get_yfinance_data, extract_annual_rows
from ..llm import llm_json


# ── Listed company: use yfinance ──────────────────────────────────────────────

def _yfinance_snapshot(ticker: str) -> FinancialSnapshot:
    print(f"[Financial] Fetching via yfinance: {ticker}")
    data = get_yfinance_data(ticker)

    if data.get("error"):
        print(f"[Financial] yfinance error: {data['error']}")
        return _empty_snapshot("yfinance returned an error", data["error"])

    source_url = data["source"]
    source_title = f"Yahoo Finance / NSE-BSE Filings ({ticker})"

    rows, years = extract_annual_rows(
        data.get("income_statement", {}),
        data.get("cash_flow", {}),
        source_url,
        source_title,
    )

    info = data.get("info", {})
    mkt_cap = info.get("marketCap")
    if mkt_cap:
        from datetime import datetime
        yr = f"FY{str(datetime.now().year)[2:]}"
        from ..tools.financial import format_crore
        rows.append(FinancialRow(
            metric="Market Cap (live)",
            values={yr: format_crore(float(mkt_cap))},
            source_url=f"https://finance.yahoo.com/quote/{ticker}",
            source_title=f"Yahoo Finance ({ticker}) — live quote",
        ))

    notes = ["Values in INR Crores (Cr). FY = Financial Year ending March."]
    if not rows:
        notes = [f"No financial data retrieved from yfinance for {ticker}. "
                 "The ticker may be incorrect or data unavailable."]

    return FinancialSnapshot(
        rows=rows,
        data_source=f"yfinance / Yahoo Finance (NSE: {ticker})",
        years=years,
        notes=notes,
    )


# ── Unlisted company: web search fallback ─────────────────────────────────────

_SYSTEM_FIN = """You are a financial analyst. Extract financial figures from the web content below.

Return ONLY this JSON:
{
  "rows": [
    {
      "metric": "metric name e.g. Revenue, Net Profit, EBITDA",
      "year": "fiscal year label e.g. FY24 or FY2024",
      "value": "value with units e.g. ₹3,200 Cr",
      "source_url": "the URL this figure came from",
      "snippet": "exact text from the source mentioning this figure"
    }
  ],
  "not_found": ["list every key metric NOT found: Revenue, Gross Profit, EBITDA, Net Income, Net Margin"]
}

STRICT RULES:
- ONLY include figures EXPLICITLY stated in the text — do NOT calculate or estimate
- If a figure is not mentioned, it goes in not_found, never in rows
- Each row needs a snippet proving the number appears in that source"""


def _web_search_snapshot(company_name: str) -> FinancialSnapshot:
    print(f"[Financial] Web search fallback for unlisted company: {company_name}")

    queries = [
        f"{company_name} revenue turnover annual financial results crore",
        f"{company_name} profit EBITDA financial performance",
        f"site:screener.in {company_name} financial",
        f"{company_name} MCA annual report turnover",
    ]

    content_chunks: list[str] = []
    source_urls: list[str] = []

    for query in queries[:3]:
        results = ddg_search(query, max_results=3)
        for r in results[:2]:
            url = r.get("href", "")
            body = r.get("body", "")
            title = r.get("title", "")
            if body:
                content_chunks.append(f"[Source: {title}] ({url})\n{body}")
                source_urls.append(url)
            # Try scraping screener.in or similar financial pages
            if any(s in url for s in ["screener.in", "moneycontrol", "tofler", "zauba"]):
                full = fetch_page_text(url, max_chars=3000)
                if full:
                    content_chunks.append(f"[Scraped: {title}] ({url})\n{full}")
        time.sleep(1.5)

    if not content_chunks:
        return _empty_snapshot(
            "web search",
            "No financial data found in publicly available sources. "
            "This company is unlisted; financials are not publicly accessible.",
        )

    combined = "\n\n---\n\n".join(content_chunks[:8])
    data = llm_json(_SYSTEM_FIN, f"Company: {company_name}\n\n{combined}")

    rows: list[FinancialRow] = []
    notes: list[str] = []
    years_found: set[str] = set()

    if data:
        for r in data.get("rows", []):
            yr = r.get("year", "Unknown")
            years_found.add(yr)
            rows.append(FinancialRow(
                metric=r.get("metric", ""),
                values={yr: r.get("value")},
                source_url=r.get("source_url", source_urls[0] if source_urls else ""),
                source_title=r.get("snippet", "")[:120],
            ))

        not_found = data.get("not_found", [])
        if not_found:
            notes.append(
                f"Could not verify in available public sources: {', '.join(not_found)}"
            )

    if not rows:
        notes.append(
            "No financial figures found in publicly available sources. "
            "Company is unlisted; detailed financials are not publicly disclosed."
        )

    return FinancialSnapshot(
        rows=rows,
        data_source="web search (unlisted company)",
        years=sorted(years_found),
        notes=notes,
    )


def _empty_snapshot(source: str, note: str) -> FinancialSnapshot:
    return FinancialSnapshot(rows=[], data_source=source, years=[], notes=[note])


# ── Public API ────────────────────────────────────────────────────────────────

def gather_financials(identity: CompanyIdentity) -> FinancialSnapshot:
    if identity.is_listed and identity.ticker:
        snap = _yfinance_snapshot(identity.ticker)
        if snap.rows:
            return snap
        print("[Financial] yfinance returned no rows — falling back to web search")

    return _web_search_snapshot(identity.canonical_name)

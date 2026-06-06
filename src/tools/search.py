"""DuckDuckGo search — no API key, completely free."""
from __future__ import annotations
import time
from typing import Optional


def ddg_search(query: str, max_results: int = 5, region: str = "in-en") -> list[dict]:
    """
    Search DuckDuckGo. Returns list of dicts with keys: title, href, body.
    Falls back to wt-wt (worldwide) region on failure.
    """
    from duckduckgo_search import DDGS

    for attempt, reg in enumerate([region, "wt-wt"]):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results, region=reg))
            if results:
                return results
        except Exception as e:
            msg = str(e).lower()
            if "ratelimit" in msg or "202" in msg:
                wait = 10 * (attempt + 1)
                print(f"[Search] Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"[Search] Error for '{query}': {e}")
    return []


def ddg_news(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo news. Returns list of dicts with keys: title, url, body, source.
    """
    from duckduckgo_search import DDGS

    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
        # Normalise key: news uses 'url' not 'href'
        for r in results:
            if "url" in r and "href" not in r:
                r["href"] = r["url"]
        return results
    except Exception as e:
        print(f"[News] Error for '{query}': {e}")
        return []

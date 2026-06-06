"""Web page scraper using httpx + BeautifulSoup4."""
from __future__ import annotations
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_SKIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]


def fetch_page_text(url: str, max_chars: int = 5000) -> Optional[str]:
    """
    Fetch a URL and return cleaned plain text (up to max_chars).
    Returns None on any error — never raises.
    """
    try:
        with httpx.Client(timeout=15, follow_redirects=True, headers=_HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(_SKIP_TAGS):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]

    except Exception as e:
        print(f"[Scraper] Could not fetch {url}: {e}")
        return None


def fetch_meta_description(url: str) -> Optional[str]:
    """Extract the <meta name='description'> tag from a page."""
    try:
        with httpx.Client(timeout=10, follow_redirects=True, headers=_HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        tag = soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        return None
    except Exception:
        return None

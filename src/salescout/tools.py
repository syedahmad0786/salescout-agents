"""Web tools the researcher agent uses: polite fetching, text extraction,
key-page discovery, and free news/web search (DuckDuckGo — no API key)."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import PAGE_CHAR_BUDGET

USER_AGENT = (
    "Mozilla/5.0 (compatible; SaleScoutBot/0.1; "
    "+https://github.com/syedahmad0786/salescout-agents)"
)

# Paths that usually hold the highest-signal company info.
KEY_PATH_HINTS = re.compile(
    r"(about|company|product|pricing|service|solution|platform|team|customers|case-stud)",
    re.I,
)


def normalize_domain(domain: str) -> str:
    """Accept 'acme.com', 'www.acme.com' or a full URL; return bare host."""
    domain = domain.strip()
    if "://" in domain:
        domain = urlparse(domain).netloc
    return domain.strip("/").removeprefix("www.")


def fetch(url: str, timeout: float = 15.0) -> str:
    """GET a page with redirects and a proper UA. Raises on HTTP errors."""
    with httpx.Client(
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def fetch_homepage(domain: str) -> tuple[str, str]:
    """Try https then http. Returns (final_url, html)."""
    last_err: Exception | None = None
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            return url, fetch(url)
        except Exception as exc:  # noqa: BLE001 — report upstream
            last_err = exc
    raise ConnectionError(f"Could not reach {domain}: {last_err}")


def extract_text(html: str, max_chars: int = PAGE_CHAR_BUDGET) -> str:
    """Strip boilerplate and return readable page text within budget."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    return text[:max_chars]


def find_key_pages(html: str, base_url: str, limit: int = 3) -> list[str]:
    """Discover same-site pages worth reading (about, pricing, products...)."""
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(base_url).netloc
    seen: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"]).split("#")[0].rstrip("/")
        parsed = urlparse(href)
        if parsed.netloc != host or not KEY_PATH_HINTS.search(parsed.path):
            continue
        if href not in seen and href != base_url.rstrip("/"):
            seen.append(href)
        if len(seen) >= limit:
            break
    return seen


def search_news(query: str, max_results: int = 6) -> list[dict]:
    """Free news search via DuckDuckGo; falls back to web search."""
    from duckduckgo_search import DDGS

    try:
        with DDGS() as ddgs:
            hits = list(ddgs.news(query, max_results=max_results))
            if hits:
                return hits
            return list(ddgs.text(query, max_results=max_results))
    except Exception:  # noqa: BLE001 — search is best-effort
        return []

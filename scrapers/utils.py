"""
Shared utilities: rate limiting, safe HTTP requests, data storage, text processing.
"""

import csv
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import (
    MAX_RETRIES,
    OUTPUT_DIR,
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    USER_AGENTS,
)

logger = logging.getLogger("yuming_scraper")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Per-domain rate limiter with configurable delay."""

    def __init__(self, delay: float = RATE_LIMIT_DELAY):
        self._last_request: dict[str, float] = {}
        self._delay = delay

    def wait(self, domain: str) -> None:
        now = time.monotonic()
        if domain in self._last_request:
            elapsed = now - self._last_request[domain]
            if elapsed < self._delay:
                time.sleep(self._delay - elapsed)
        self._last_request[domain] = time.monotonic()


_rate_limiter = RateLimiter()


def rate_limit(domain: str) -> None:
    _rate_limiter.wait(domain)


# ---------------------------------------------------------------------------
# User-Agent rotation
# ---------------------------------------------------------------------------

_ua_index = 0


def get_headers(referer: Optional[str] = None) -> dict[str, str]:
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


# ---------------------------------------------------------------------------
# Safe HTTP request with retry
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(
        (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
    ),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_BACKOFF, min=2, max=30),
    reraise=True,
)
def safe_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    timeout: int = REQUEST_TIMEOUT,
    **kwargs,
) -> requests.Response:
    """HTTP request with retry, timeout, and rate limiting."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    rate_limit(domain)

    if headers is None:
        headers = get_headers()

    logger.debug("Requesting %s %s", method, url)
    resp = requests.request(
        method, url, headers=headers, params=params, timeout=timeout, **kwargs
    )
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()


def extract_text(soup: BeautifulSoup, max_chars: int = 5000) -> str:
    """Extract clean text from BeautifulSoup, truncating at max_chars."""
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)[:max_chars]


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def make_absolute_url(base: str, relative: str) -> str:
    from urllib.parse import urljoin
    return urljoin(base, relative)


def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Result storage
# ---------------------------------------------------------------------------

# Unified result schema as a typed dict-like comment for reference:
# {
#     "id": str,              # Unique hash of URL
#     "platform": str,        # "reddit", "news", "niche", "zhihu", etc.
#     "date": str,            # ISO format date string
#     "title": str,
#     "url": str,
#     "content": str,         # Snippet or full text
#     "author": str,
#     "relevance_score": float,  # 0.0 to 1.0
#     "keyword_group": str,   # Matching keyword group
#     "matched_keyword": str,  # Specific keyword that matched
#     "scraped_at": str,      # ISO timestamp of scraping
# }


def build_result(
    platform: str,
    date: str,
    title: str,
    url: str,
    content: str = "",
    author: str = "",
    relevance_score: float = 0.5,
    keyword_group: str = "",
    matched_keyword: str = "",
) -> dict[str, Any]:
    return {
        "id": url_hash(url),
        "platform": platform,
        "date": date,
        "title": title,
        "url": url,
        "content": content[:3000],
        "author": author,
        "relevance_score": relevance_score,
        "keyword_group": keyword_group,
        "matched_keyword": matched_keyword,
        "scraped_at": datetime.now().isoformat(),
    }


def save_results(
    results: list[dict],
    platform: str,
    output_dir: str = OUTPUT_DIR,
    extra_meta: Optional[dict] = None,
) -> tuple[str, str]:
    """Save results as CSV and JSON. Returns (csv_path, json_path)."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(output_dir, f"{platform}_{timestamp}.csv")
    json_path = os.path.join(output_dir, f"{platform}_{timestamp}.json")

    fieldnames = [
        "id", "platform", "date", "title", "url", "content",
        "author", "relevance_score", "keyword_group",
        "matched_keyword", "scraped_at",
    ]

    # CSV
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    # JSON
    payload: dict[str, Any] = {
        "platform": platform,
        "count": len(results),
        "generated_at": datetime.now().isoformat(),
    }
    if extra_meta:
        payload["meta"] = extra_meta
    payload["results"] = results

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("Saved %d results -> %s / %s", len(results), csv_path, json_path)
    return csv_path, json_path


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        rid = r.get("id") or url_hash(r["url"])
        if rid not in seen:
            seen.add(rid)
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def score_relevance(text: str, keywords: list[str]) -> float:
    """Simple keyword-density relevance score between 0 and 1."""
    if not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return min(1.0, hits / max(len(keywords), 1))

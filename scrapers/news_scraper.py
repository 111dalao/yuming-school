"""
News scraper — RSS feeds from local Bay Area outlets + Google News search.
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .config import (
    DATE_END,
    DATE_START,
    GOOGLE_NEWS_QUERIES,
    KEYWORD_GROUPS,
    NEARBY_LOCATIONS,
    NEARBY_NEWS_QUERIES,
    NEARBY_POI,
    NEWS_RSS_FEEDS,
    NEWS_RSS_FEEDS_EXTRA,
    REQUEST_TIMEOUT,
)
from .utils import (
    build_result,
    deduplicate,
    extract_text,
    get_headers,
    make_absolute_url,
    parse_html,
    safe_request,
    save_results,
    score_relevance,
    strip_html,
)

logger = logging.getLogger("yuming_scraper.news")

# Keywords to filter feed entries — expanded with nearby locations
_SCHOOL_KEYWORDS = [
    "yu ming", "yuming", "charter school", "oakland school",
    "bilingual", "mandarin immersion", "chinese immersion",
    "oakland unified", "oakland education",
]

_NEARBY_LOCATION_KEYWORDS = [
    # Core East Bay cities
    "oakland", "berkeley", "alameda", "piedmont", "emeryville",
    "albany", "el cerrito", "richmond", "san leandro", "castro valley",
    "orinda", "lafayette", "moraga", "walnut creek", "concord",
    "pleasant hill", "hayward", "union city", "fremont", "newark",
    "dublin", "pleasanton", "san ramon", "danville",
    # SF / Peninsula
    "san francisco", "daly city", "south san francisco", "san bruno",
    "millbrae", "burlingame", "san mateo", "redwood city",
    "menlo park", "palo alto", "stanford",
    # North Bay
    "sausalito", "mill valley", "san rafael", "novato", "vallejo",
]

_TOPIC_KEYWORDS = [
    # Education
    "school", "student", "teacher", "education", "charter", "bilingual",
    "immersion", "mandarin", "chinese", "classroom", "curriculum",
    "academic", "college", "university", "campus", "professor",
    # Housing
    "housing", "rent", "rental", "apartment", "landlord", "tenant",
    "eviction", "affordable housing", "real estate", "mortgage",
    # Safety
    "crime", "safety", "police", "robbery", "theft", "break-in",
    "burglary", "violence", "homicide", "shooting", "assault",
    # Transportation
    "BART", "AC Transit", "bus", "train", "transit", "commute",
    "bike lane", "pedestrian", "traffic", "parking",
    # Cost / Economy
    "cost of living", "expensive", "budget", "inflation", "price",
    "affordable", "grocery", "utilities",
    # Community / Culture
    "chinatown", "asian american", "chinese community", "immigrant",
    "cultural", "festival", "community center", "diversity",
    # Healthcare
    "hospital", "urgent care", "health insurance", "medical", "clinic",
    "doctor", "pharmacy", "emergency room",
    # International
    "international student", "exchange", "visa", "J-1", "F-1",
    "overseas", "foreign", "study abroad",
]


# ---------------------------------------------------------------------------
# Google News RSS
# ---------------------------------------------------------------------------

def _google_news_rss(
    query: str, max_items: int = 30
) -> list[dict]:
    """Search Google News via RSS and return results."""
    encoded = quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
    results: list[dict] = []

    try:
        feed = feedparser.parse(url)
    except Exception:
        logger.warning("Failed to parse Google News RSS for: %s", query)
        return results

    for entry in feed.entries[:max_items]:
        try:
            published = _parse_feed_date(entry)
            if published and (published < DATE_START or published > DATE_END):
                continue

        # Extract source
            source = entry.get("source", {})
            source_name = (
                source.get("title", "")
                if isinstance(source, dict)
                else getattr(source, "title", "")
            )

            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = strip_html(entry.get("summary", ""))

            results.append(
                build_result(
                    platform="google_news",
                    date=published.isoformat() if published else "",
                    title=title,
                    url=link,
                    content=summary[:2000],
                    author=source_name,
                    relevance_score=0.7,
                    keyword_group="news",
                    matched_keyword=query,
                )
            )
        except Exception:
            logger.debug("Error processing news entry", exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Local RSS Feeds
# ---------------------------------------------------------------------------

def _scrape_rss_feeds(
    feeds: list[dict],
    keywords: Optional[list[str]] = None,
    use_geo_filter: bool = False,
) -> list[dict]:
    """Parse RSS feeds, optionally using geo+topical filtering for broad feeds."""
    if keywords is None:
        keywords = _SCHOOL_KEYWORDS

    results: list[dict] = []

    for feed_cfg in feeds:
        logger.info("Parsing RSS: %s", feed_cfg["name"])
        try:
            feed = feedparser.parse(feed_cfg["url"])
        except Exception:
            logger.warning("Failed to parse feed: %s", feed_cfg["url"])
            continue

        for entry in feed.entries:
            try:
                published = _parse_feed_date(entry)
                if published and (published < DATE_START or published > DATE_END):
                    continue

                title = entry.get("title", "")
                summary = strip_html(entry.get("summary", ""))
                combined = f"{title} {summary}".lower()

                # For extra/broad feeds, use geo+topic filter
                if use_geo_filter:
                    if not (_is_geographically_relevant(combined)
                            and _is_topically_relevant(combined)):
                        continue
                else:
                    if not _is_relevant(combined, keywords):
                        continue

                link = entry.get("link", "")
                author = entry.get("author", "")

                full_text = ""
                if link:
                    full_text = _fetch_article_text(link)

                content = full_text[:2000] if full_text else summary[:2000]
                kg = _classify_keyword_group(f"{title} {content}")

                results.append(
                    build_result(
                        platform=f"news_{feed_cfg['name'].lower().replace(' ', '_')}",
                        date=published.isoformat() if published else "",
                        title=title,
                        url=link,
                        content=content,
                        author=author,
                        relevance_score=0.6,
                        keyword_group=kg,
                        matched_keyword="",
                    )
                )
            except Exception:
                logger.debug("Error processing feed entry", exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Article body extraction
# ---------------------------------------------------------------------------

def _fetch_article_text(url: str) -> str:
    """Lightweight article text extraction for news sites."""
    try:
        resp = safe_request(url, timeout=REQUEST_TIMEOUT)
        soup = parse_html(resp.text)
        # Common article containers
        for selector in ["article", '[role="main"]', ".post-content", ".entry-content", "main"]:
            container = soup.select_one(selector)
            if container:
                return extract_text(container, max_chars=3000)
        return extract_text(soup, max_chars=2000)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_feed_date(entry: Any) -> Optional[datetime]:
    """Parse published date from various feed entry formats."""
    for attr in ("published_parsed", "updated_parsed"):
        val = entry.get(attr) if isinstance(entry, dict) else getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6])
            except (TypeError, ValueError):
                pass

    # Fallback: try string date
    published_str = entry.get("published", "") or entry.get("updated", "")
    if published_str:
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.strptime(published_str, fmt)
            except ValueError:
                pass

    return None


def _is_relevant(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords."""
    return any(kw in text for kw in keywords)


def _is_geographically_relevant(text: str) -> bool:
    """Check if text mentions a location within 50km of Yu Ming."""
    return any(loc in text for loc in _NEARBY_LOCATION_KEYWORDS)


def _is_topically_relevant(text: str) -> bool:
    """Check if text covers a topic we care about."""
    return any(kw in text for kw in _TOPIC_KEYWORDS)


def _classify_keyword_group(text: str) -> str:
    """Map content to the most relevant keyword group."""
    mapping = {
        "international_students": [
            "international student", "exchange", "visa", "J-1", "F-1",
            "overseas", "foreign", "study abroad", "留学生",
        ],
        "housing": [
            "housing", "rent", "rental", "apartment", "landlord", "tenant",
            "eviction", "affordable housing", "real estate",
        ],
        "safety": [
            "crime", "safety", "police", "robbery", "theft", "break-in",
            "burglary", "violence", "homicide", "shooting",
        ],
        "transportation": [
            "BART", "AC Transit", "bus", "train", "transit", "commute",
            "bike", "pedestrian", "traffic", "parking",
        ],
        "education_system": [
            "charter school", "bilingual", "immersion", "mandarin",
            "chinese school", "curriculum", "teacher training",
        ],
        "community_life": [
            "chinatown", "asian american", "chinese community", "immigrant",
            "cultural", "festival", "diversity",
        ],
        "cost_of_living": [
            "cost of living", "expensive", "budget", "inflation",
            "affordable", "grocery", "utilities",
        ],
        "healthcare": [
            "hospital", "urgent care", "health insurance", "medical",
            "clinic", "doctor", "pharmacy",
        ],
        "school_core": [
            "yu ming", "yuming",
        ],
    }
    text_lower = text.lower()
    for group, kws in mapping.items():
        if any(kw in text_lower for kw in kws):
            return group
    return "community_life"


# ---------------------------------------------------------------------------
# Main scraper entry point
# ---------------------------------------------------------------------------

class NewsScraper:
    def scrape_all(self) -> list[dict]:
        results: list[dict] = []

        # 1. Google News — school-specific queries
        logger.info("--- Google News: school core ---")
        for query in GOOGLE_NEWS_QUERIES:
            items = _google_news_rss(query)
            logger.info("  Google News [%s]: %d", query, len(items))
            results.extend(items)

        # 2. Google News — nearby location + topic queries
        logger.info("--- Google News: nearby locations (%d queries) ---",
                     len(NEARBY_NEWS_QUERIES))
        for query in NEARBY_NEWS_QUERIES:
            items = _google_news_rss(query, max_items=15)
            if items:
                logger.debug("  Google News [%s]: %d", query, len(items))
            results.extend(items)

        # 3. Core RSS feeds (education-focused)
        logger.info("--- Core RSS feeds ---")
        rss_core = _scrape_rss_feeds(NEWS_RSS_FEEDS)
        logger.info("  Core RSS: %d", len(rss_core))
        results.extend(rss_core)

        # 4. Extra RSS feeds (geo+topical filter for broad feeds)
        logger.info("--- Extra RSS feeds (geo+topic filter) ---")
        rss_extra = _scrape_rss_feeds(NEWS_RSS_FEEDS_EXTRA, use_geo_filter=True)
        logger.info("  Extra RSS: %d", len(rss_extra))
        results.extend(rss_extra)

        # 5. Classify keyword groups for results that are still "news"
        for r in results:
            if r.get("keyword_group") in ("news", "all"):
                r["keyword_group"] = _classify_keyword_group(
                    f"{r.get('title', '')} {r.get('content', '')}"
                )

        unique = deduplicate(results)
        logger.info("News total (deduplicated): %d", len(unique))

        if unique:
            save_results(
                unique,
                "news",
                extra_meta={
                    "google_queries": GOOGLE_NEWS_QUERIES + NEARBY_NEWS_QUERIES,
                    "rss_feeds": [f["name"] for f in NEWS_RSS_FEEDS + NEWS_RSS_FEEDS_EXTRA],
                },
            )
        return unique

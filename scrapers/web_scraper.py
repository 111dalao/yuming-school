"""
Generic web scraper for school review sites, forums, and UGC platforms.

Targets:
- Niche.com — school reviews & ratings
- GreatSchools.org — parent reviews
- Yelp — school reviews
- YouTube — search + comments (via yt-dlp or direct)
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urljoin

from .config import (
    KEYWORD_GROUPS,
    NEARBY_LOCATIONS,
    NEARBY_POI,
    REQUEST_TIMEOUT,
    REVIEW_SITES,
    YU_MING_CAMPUSES,
)
from .utils import (
    build_result,
    deduplicate,
    extract_text,
    get_headers,
    parse_html,
    safe_request,
    save_results,
    score_relevance,
    strip_html,
)

logger = logging.getLogger("yuming_scraper.web")

MAX_PAGES = 5
MIN_RELEVANCE = 0.05


class WebScraper:
    def scrape_all(self) -> list[dict]:
        results: list[dict] = []

        results.extend(self._scrape_review_sites())
        results.extend(self._scrape_youtube())
        results.extend(self._scrape_general_forums())

        unique = deduplicate(results)
        logger.info("Web scraper total (deduplicated): %d", len(unique))

        if unique:
            save_results(unique, "web", extra_meta={"sites": list(REVIEW_SITES)})
        return unique

    # ------------------------------------------------------------------
    # Review sites (Niche, GreatSchools)
    # ------------------------------------------------------------------

    def _scrape_review_sites(self) -> list[dict]:
        results: list[dict] = []

        for site_key, site_cfg in REVIEW_SITES.items():
            logger.info("Scraping review site: %s", site_cfg["name"])
            try:
                resp = safe_request(site_cfg["url"], timeout=REQUEST_TIMEOUT)
                soup = parse_html(resp.text)

                # Extract overall rating if present
                rating = self._extract_rating(soup)

                # Extract reviews
                reviews = self._extract_reviews(soup, site_cfg["name"])
                for review in reviews:
                    title = review.get("title", "")[:200]
                    body = review.get("body", "")[:2000]
                    date = review.get("date", "")
                    author = review.get("author", "anonymous")

                    combined = f"{title} {body}"
                    relevance = score_relevance(
                        combined,
                        [kw for g in KEYWORD_GROUPS.values() for kw in g.get("en", [])],
                    )
                    if relevance < MIN_RELEVANCE:
                        continue

                    results.append(
                        build_result(
                            platform=site_key,
                            date=date,
                            title=title or f"{site_cfg['name']} Review",
                            url=site_cfg["url"],
                            content=body,
                            author=author,
                            relevance_score=relevance,
                            keyword_group="school_core",
                            matched_keyword="",
                        )
                    )

                if results:
                    logger.info(
                        "  %s: %d reviews, rating=%s",
                        site_cfg["name"], len(reviews), rating,
                    )
            except Exception:
                logger.warning(
                    "Failed to scrape %s", site_cfg["name"], exc_info=True
                )

        return results

    def _extract_rating(self, soup: Any) -> Optional[str]:
        """Try to find rating from review site pages."""
        for selector in [
            '[itemprop="ratingValue"]',
            ".rating-number",
            ".overall-rating",
            '[data-rating]',
            "meta[itemprop=ratingValue]",
        ]:
            el = soup.select_one(selector)
            if el:
                content = el.get("content", "") or el.text.strip()
                if content:
                    return content
        return None

    def _extract_reviews(self, soup: Any, site_name: str) -> list[dict]:
        """Generic review extraction by looking for review-like structures."""
        reviews: list[dict] = []

        # Try schema.org Review markup first
        for review_div in soup.select('[itemtype*="Review"], [itemprop="review"]'):
            try:
                title_el = review_div.select_one('[itemprop="name"]')
                body_el = review_div.select_one('[itemprop="reviewBody"], [itemprop="description"]')
                author_el = review_div.select_one('[itemprop="author"]')
                date_el = review_div.select_one('[itemprop="datePublished"]')

                reviews.append({
                    "title": title_el.text.strip() if title_el else "",
                    "body": body_el.text.strip() if body_el else "",
                    "author": author_el.text.strip() if author_el else "",
                    "date": date_el.get("content", "") if date_el else "",
                })
            except Exception:
                pass

        # Fallback: look for common review container classes
        if not reviews:
            for container in soup.select(
                ".review, .review-item, .user-review, .comment, "
                ".testimonial, .rating-item, article.review, "
                "div[class*=review], div[class*=Review]"
            ):
                text = container.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    reviews.append({
                        "title": text.split("\n")[0][:200],
                        "body": text[:2000],
                        "author": "",
                        "date": "",
                    })
                    if len(reviews) >= 50:
                        break

        return reviews

    # ------------------------------------------------------------------
    # YouTube search
    # ------------------------------------------------------------------

    def _scrape_youtube(self) -> list[dict]:
        """Search YouTube for Yu Ming and nearby location + topic videos."""
        results: list[dict] = []
        queries = [
            # School-specific
            "Yu Ming Charter School Oakland",
            "Yu Ming School Oakland",
            "Oakland Chinese immersion school",
            # Nearby + topic combinations
            "Oakland California living",
            "Oakland neighborhood tour",
            "Berkeley international student",
            "Oakland Chinatown food",
            "Bay Area Chinese school",
            "Oakland housing rental",
            "Bay Area safety tips",
            "BART Oakland commute",
            "UC Berkeley campus tour",
            "California bilingual education",
            "Oakland charter school review",
            "Bay Area Chinese community",
            "Lake Merritt Oakland",
            "East Bay living guide",
            "San Francisco Bay Area international student",
        ]

        for query in queries:
            logger.info("YouTube search: %s", query)
            try:
                encoded = quote(query)
                url = f"https://www.youtube.com/results?search_query={encoded}"
                resp = safe_request(url, timeout=REQUEST_TIMEOUT)
                soup = parse_html(resp.text)

                for script in soup.select("script"):
                    if "var ytInitialData" in (script.string or ""):
                        data = self._parse_yt_initial_data(script.string)
                        for video in data:
                            video["url"] = f"https://youtube.com/watch?v={video.get('id', '')}"
                            kg = self._classify_yt_group(
                                video.get("title", "") + " " + video.get("description", "")
                            )
                            results.append(
                                build_result(
                                    platform="youtube",
                                    date=video.get("date", ""),
                                    title=video.get("title", ""),
                                    url=video.get("url", ""),
                                    content=video.get("description", ""),
                                    author=video.get("channel", ""),
                                    relevance_score=0.6,
                                    keyword_group=kg,
                                    matched_keyword=query,
                                )
                            )
                        break
            except Exception:
                logger.debug("YouTube search error for: %s", query, exc_info=True)

        logger.info("YouTube: %d results", len(results))
        return results

    @staticmethod
    def _classify_yt_group(text: str) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["yu ming", "yuming", "charter", "immersion", "bilingual"]):
            return "school_core"
        if any(kw in text_lower for kw in ["international", "exchange", "visa", "留学生"]):
            return "international_students"
        if any(kw in text_lower for kw in ["housing", "rent", "apartment", "roommate", "租房"]):
            return "housing"
        if any(kw in text_lower for kw in ["safety", "crime", "dangerous", "safe", "治安"]):
            return "safety"
        if any(kw in text_lower for kw in ["bart", "transit", "commute", "交通"]):
            return "transportation"
        if any(kw in text_lower for kw in ["chinatown", "community", "living", "food", "生活"]):
            return "community_life"
        if any(kw in text_lower for kw in ["hospital", "clinic", "health", "medical", "看病"]):
            return "healthcare"
        if any(kw in text_lower for kw in ["cost", "expensive", "budget", "价格", "物价"]):
            return "cost_of_living"
        return "community_life"

    def _parse_yt_initial_data(self, script_text: str) -> list[dict]:
        """Extract video info from YouTube's ytInitialData JSON."""
        videos: list[dict] = []
        try:
            # Extract JSON between "var ytInitialData = " and the trailing ";"
            json_str = re.sub(
                r"^.*?var ytInitialData\s*=\s*", "", script_text
            )
            json_str = re.sub(r";\s*$", "", json_str)
            data = json.loads(json_str)

            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )
            for section in contents:
                items = (
                    section.get("itemSectionRenderer", {})
                    .get("contents", [])
                )
                for item in items:
                    video_renderer = item.get("videoRenderer", {})
                    if video_renderer:
                        videos.append({
                            "id": video_renderer.get("videoId", ""),
                            "title": (
                                video_renderer.get("title", {})
                                .get("runs", [{}])[0]
                                .get("text", "")
                            ),
                            "description": (
                                video_renderer.get("descriptionTextSnippet", {})
                                .get("runs", [{}])[0]
                                .get("text", "")
                            ),
                            "channel": (
                                video_renderer.get("ownerText", {})
                                .get("runs", [{}])[0]
                                .get("text", "")
                            ),
                            "date": video_renderer.get("publishedTimeText", {}).get("simpleText", ""),
                        })
        except Exception:
            logger.debug("Failed to parse ytInitialData", exc_info=True)
        return videos

    # ------------------------------------------------------------------
    # General forum / discussion searches
    # ------------------------------------------------------------------

    def _scrape_general_forums(self) -> list[dict]:
        """Search general discussion sites for school mentions.

        Searches limited to well-known public discussion sites that tolerate
        polite crawling. Each platform may return empty results if blocked.
        """
        results: list[dict] = []

        search_engines = [
            {
                "name": "duckduckgo",
                "url_template": "https://html.duckduckgo.com/html/?q={query}",
                "result_selector": ".result__body",
                "title_selector": ".result__title a",
                "link_selector": ".result__title a",
                "snippet_selector": ".result__snippet",
            },
        ]

        # Only search for core school keywords to keep volume manageable
        core_queries = [
            '"Yu Ming Charter School" Oakland',
            '"Yu Ming" school Oakland review',
            'Oakland charter school Chinese immersion',
        ]

        for engine in search_engines:
            for query in core_queries:
                try:
                    results.extend(
                        self._search_engine_scrape(engine, query)
                    )
                except Exception:
                    logger.debug(
                        "Search engine error: %s [%s]",
                        engine["name"], query, exc_info=True
                    )

        return results

    def _search_engine_scrape(
        self, engine: dict, query: str, max_results: int = 20
    ) -> list[dict]:
        results: list[dict] = []
        url = engine["url_template"].format(query=quote(query))

        resp = safe_request(url, timeout=REQUEST_TIMEOUT)
        soup = parse_html(resp.text)

        for item in soup.select(engine["result_selector"])[:max_results]:
            try:
                title_el = item.select_one(engine["title_selector"])
                link_el = item.select_one(engine["link_selector"])
                snippet_el = item.select_one(engine["snippet_selector"])

                title = title_el.get_text(strip=True) if title_el else ""
                link = link_el.get("href", "") if link_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                if not title or not link:
                    continue

                combined = f"{title} {snippet}".lower()
                relevance = score_relevance(
                    combined,
                    ["yu ming", "oakland", "charter", "chinese", "immersion"],
                )
                if relevance < 0.1:
                    continue

                results.append(
                    build_result(
                        platform="web_search",
                        date="",
                        title=title,
                        url=link,
                        content=snippet[:1000],
                        author="",
                        relevance_score=relevance,
                        keyword_group="school_core",
                        matched_keyword=query,
                    )
                )
            except Exception:
                continue

        return results

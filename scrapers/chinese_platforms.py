"""
Chinese community platform scrapers.

Targets:
- 一亩三分地 (1Point3Acres) — largest Chinese overseas student forum
- 知乎 (Zhihu) — Q&A platform
- 小红书 (Xiaohongshu/RED) — lifestyle / student-life sharing

These platforms employ aggressive anti-bot measures including:
- Cloudflare / Akamai CDN protection
- Dynamic content rendering (JS required)
- Login requirements beyond first page
- IP-based rate limiting (especially for non-China IPs)

This module provides a best-effort framework. For production use, consider:
- Residential proxies (US-based for these sites)
- Headless browser (Playwright/Selenium) for JS-rendered content
- Official APIs where available
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urlencode

from .config import (
    KEYWORD_GROUPS,
    NEARBY_LOCATIONS,
    NEARBY_POI,
    REQUEST_TIMEOUT,
    CHINESE_PLATFORM_CONFIG,
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

logger = logging.getLogger("yuming_scraper.chinese")


class ChinesePlatformScraper:
    def scrape_all(self) -> list[dict]:
        results: list[dict] = []

        results.extend(self._scrape_1point3acres())
        results.extend(self._scrape_zhihu())
        results.extend(self._scrape_xiaohongshu())

        unique = deduplicate(results)
        logger.info("Chinese platforms total (deduplicated): %d", len(unique))

        if unique:
            save_results(
                unique, "chinese_platforms",
                extra_meta={"platforms": ["1point3acres", "zhihu", "xiaohongshu"]},
            )
        return unique

    # ------------------------------------------------------------------
    # 一亩三分地 (1Point3Acres)
    # ------------------------------------------------------------------

    def _scrape_1point3acres(self) -> list[dict]:
        """Search 1point3acres for Oakland / Yu Ming related discussions.

        Notes:
        - The site uses Cloudflare anti-bot protection
        - Most content requires login
        - Search is restricted without an account
        - Results will likely be empty without a headless browser + proxy
        """
        results: list[dict] = []
        cfg = CHINESE_PLATFORM_CONFIG["1point3acres"]

        # Chinese-relevant search queries — expanded with nearby locations
        queries = [
            # School core
            "奥克兰 留学",
            "Oakland 学校",
            "加州 特许学校",
            "湾区 中文老师",
            "加州 中文沉浸",
            # Nearby cities + topics
            "湾区 中国留学生",
            "旧金山 留学生",
            "伯克利 留学",
            "加州 交换生",
            "奥克兰 租房",
            "旧金山 租房",
            "湾区 生活",
            "Oakland 安全",
            "奥克兰 治安",
            "美国 J-1 签证",
            "F-1 签证 体验",
            "加州大学伯克利 访问学者",
            "斯坦福 访问",
            "湾区 华人社区",
            "奥克兰 唐人街",
            "旧金山 唐人街",
            "湾区 中文教学",
            "美国中文沉浸式学校",
            "美国 双语学校",
            "湾区 看病",
            "美国 留学生 医保",
            "加州 生活费",
            "湾区 物价",
        ]

        for query in queries:
            try:
                search_url = f"{cfg['base_url']}search.php?mod=forum&searchsubmit=yes&srchtxt={quote(query)}"
                headers = get_headers()
                headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"

                resp = safe_request(search_url, timeout=REQUEST_TIMEOUT)
                soup = parse_html(resp.text)

                # Parse forum search results
                for item in soup.select(".pbw, .xs3, li.pbw, div.buddy"):
                    try:
                        title_el = item.select_one("a.xst, h3 a, a[href*=thread]")
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)
                        link = title_el.get("href", "")
                        if link and not link.startswith("http"):
                            link = f"https://www.1point3acres.com/bbs/{link.lstrip('/')}"

                        combined = title.lower()
                        relevance = score_relevance(
                            combined,
                            ["奥克兰", "oakland", "湾区", "中文", "学校", "留学", "老师"],
                        )
                        if relevance < 0.1:
                            continue

                        results.append(
                            build_result(
                                platform="1point3acres",
                                date="",
                                title=title,
                                url=link,
                                content="",
                                author="",
                                relevance_score=relevance,
                                keyword_group="community_life",
                                matched_keyword=query,
                            )
                        )
                    except Exception:
                        continue

                logger.info(
                    "  1point3acres [%s]: %d results", query, len(results)
                )
            except Exception:
                logger.debug(
                    "1point3acres search failed for: %s", query, exc_info=True
                )

        return results

    # ------------------------------------------------------------------
    # 知乎 (Zhihu)
    # ------------------------------------------------------------------

    def _scrape_zhihu(self) -> list[dict]:
        """Search Zhihu for Oakland / Yu Ming discussions.

        Notes:
        - Zhihu search page is accessible without login
        - Heavily rate-limited for non-China IPs
        - Dynamic content loading via JS; API endpoints may work better
        - Consider Zhihu API: https://www.zhihu.com/api/v4/search_v3
        """
        results: list[dict] = []
        cfg = CHINESE_PLATFORM_CONFIG["zhihu"]

        queries = [
            "奥克兰 留学",
            "加州奥克兰 生活",
            "美国 特许学校",
            "湾区 中文教学",
            "美国中文沉浸式学校",
            "奥克兰 治安",
            "加州湾区 租房",
            "J-1 签证",
            "美国交换教师",
            "伯克利 访问学者",
            "旧金山 留学生",
            "加州 交换项目",
            "美国 中文教师",
            "湾区 华人生活",
            "奥克兰 唐人街",
            "旧金山 生活成本",
            "伯克利 租房经验",
            "加州 双语教育",
            "美国 K-12 教育",
            "湾区 公立学校",
        ]

        for query in queries:
            try:
                params = {
                    "type": "content",
                    "q": query,
                }
                search_url = f"{cfg['search_url']}?{urlencode(params)}"
                headers = get_headers()
                headers["Accept-Language"] = "zh-CN,zh;q=0.9"

                resp = safe_request(search_url, timeout=REQUEST_TIMEOUT)
                soup = parse_html(resp.text)

                # Zhihu search results — try multiple selector patterns
                for item in soup.select(
                    ".SearchResultCard, .List-item, .ContentItem-card, "
                    "div[class*=SearchResult], article"
                ):
                    try:
                        title_el = (
                            item.select_one("h2 a, .ContentItem-title a, a[data-za-detail-view-element_name='Title']")
                        )
                        snippet_el = item.select_one(
                            ".RichText, .SearchResult-summary, .ContentItem-excerpt, span[class*=excerpt]"
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        link = title_el.get("href", "")
                        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                        combined = f"{title} {snippet}".lower()
                        relevance = score_relevance(
                            combined,
                            ["奥克兰", "oakland", "湾区", "中文", "学校", "留学", "教师", "美国"],
                        )
                        if relevance < 0.1:
                            continue

                        results.append(
                            build_result(
                                platform="zhihu",
                                date="",
                                title=title,
                                url=link if link.startswith("http") else f"https://www.zhihu.com{link}",
                                content=snippet[:1000],
                                author="",
                                relevance_score=relevance,
                                keyword_group="international_students",
                                matched_keyword=query,
                            )
                        )
                    except Exception:
                        continue

                logger.info("  Zhihu [%s]: %d results", query, len(results))
            except Exception:
                logger.debug("Zhihu search failed for: %s", query, exc_info=True)

        return results

    # ------------------------------------------------------------------
    # 小红书 (Xiaohongshu / RED)
    # ------------------------------------------------------------------

    def _scrape_xiaohongshu(self) -> list[dict]:
        """Search Xiaohongshu for student life / Oakland content.

        Notes:
        - Xiaohongshu has strong anti-scraping measures
        - Content rendered via React/JS — direct HTTP gets a skeleton page
        - Mobile API requires device registration and sign-in
        - Web search page is the most accessible entry point
        - For real scraping, use Playwright + logged-in session + mobile proxy
        """
        results: list[dict] = []
        cfg = CHINESE_PLATFORM_CONFIG["xiaohongshu"]

        queries = [
            "奥克兰留学",
            "加州湾区生活",
            "美国交换",
            "美国中文老师",
            "奥克兰生活",
            "湾区租房",
            "旧金山留学",
            "伯克利交换",
            "加州华人",
            "美国J1签证",
            "湾区中文学校",
            "奥克兰探店",
            "美国K12教育",
            "沉浸式中英文",
        ]

        for query in queries:
            try:
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}&source=web_search_result_notes"
                headers = get_headers()
                headers["Accept-Language"] = "zh-CN,zh;q=0.9"
                # Xiaohongshu specifically checks for these
                headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"

                resp = safe_request(search_url, timeout=REQUEST_TIMEOUT)
                soup = parse_html(resp.text)

                # Xiaohongshu embeds data in __INITIAL_STATE__ or similar JSON blobs
                for script in soup.select("script"):
                    script_text = script.string or ""
                    if "window.__INITIAL_STATE__" in script_text:
                        try:
                            # Extract JSON between __INITIAL_STATE__= and the next variable or script end
                            json_match = re.search(
                                r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*(?:window\.|</script>)",
                                script_text, re.DOTALL
                            )
                            if json_match:
                                json_str = json_match.group(1)
                                # Replace undefined (JS literal) with null (JSON literal)
                                json_str = json_str.replace("undefined", "null")
                                data = json.loads(json_str)

                                notes = (
                                    data.get("search", {})
                                    .get("note", {})
                                    .get("notes", [])
                                    or data.get("note", {}).get("notes", [])
                                    or []
                                )
                                for note in notes:
                                    note_card = note.get("noteCard", note)
                                    title = note_card.get("displayTitle", note_card.get("title", ""))
                                    desc = note_card.get("desc", "")
                                    note_id = note_card.get("noteId", "")
                                    user = note_card.get("user", {}).get("nickname", "")

                                    results.append(
                                        build_result(
                                            platform="xiaohongshu",
                                            date="",
                                            title=title,
                                            url=f"https://www.xiaohongshu.com/explore/{note_id}",
                                            content=desc[:1000],
                                            author=user,
                                            relevance_score=0.5,
                                            keyword_group="community_life",
                                            matched_keyword=query,
                                        )
                                    )
                        except json.JSONDecodeError:
                            continue

                logger.debug("  Xiaohongshu [%s]: scanned", query)
            except Exception:
                logger.debug("Xiaohongshu search failed for: %s", query, exc_info=True)

        if results:
            logger.info("  Xiaohongshu: %d results from embedded data", len(results))
        return results

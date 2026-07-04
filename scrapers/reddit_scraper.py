"""
PRAW-based Reddit scraper — searches subreddits for Yu Ming and Oakland topics.
"""

import logging
import os
from datetime import datetime
from math import floor
from typing import Any, Optional

import praw
from praw.models import Submission

from .config import (
    DATE_END,
    DATE_START,
    KEYWORD_GROUPS,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_SUBREDDITS,
    REDDIT_USER_AGENT,
)
from .utils import build_result, deduplicate, save_results, score_relevance

logger = logging.getLogger("yuming_scraper.reddit")

MAX_POSTS_PER_SEARCH = 50
MAX_COMMENTS_PER_POST = 10
MIN_SCORE = 1  # Skip posts below this score
MIN_RELEVANCE = 0.05


class RedditScraper:
    def __init__(self) -> None:
        client_id = os.getenv("REDDIT_CLIENT_ID", REDDIT_CLIENT_ID)
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", REDDIT_CLIENT_SECRET)

        if not client_id or not client_secret:
            logger.warning(
                "Reddit API credentials not set. "
                "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars. "
                "Skipping Reddit scraping."
            )
            self._reddit: Optional[praw.Reddit] = None
        else:
            self._reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=REDDIT_USER_AGENT,
            )

    def scrape_all(self) -> list[dict]:
        if self._reddit is None:
            return []

        all_results: list[dict] = []
        for subreddit_name in REDDIT_SUBREDDITS:
            logger.info("Searching r/%s ...", subreddit_name)
            results = self._scrape_subreddit(subreddit_name)
            logger.info("  r/%s: %d results", subreddit_name, len(results))
            all_results.extend(results)

        unique = deduplicate(all_results)
        logger.info("Reddit total (deduplicated): %d results", len(unique))

        if unique:
            save_results(
                unique,
                "reddit",
                extra_meta={
                    "subreddits": REDDIT_SUBREDDITS,
                    "keyword_groups": list(KEYWORD_GROUPS),
                },
            )
        return unique

    def _scrape_subreddit(self, subreddit_name: str) -> list[dict]:
        results: list[dict] = []
        subreddit = self._reddit.subreddit(subreddit_name)

        for group_key, group in KEYWORD_GROUPS.items():
            all_keywords = group["en"] + group.get("zh", [])
            for keyword in all_keywords:
                try:
                    posts = subreddit.search(
                        keyword,
                        sort="relevance",
                        time_filter="year",
                        limit=MAX_POSTS_PER_SEARCH,
                    )
                    for post in self._iter_posts(
                        posts, group_key, keyword, all_keywords
                    ):
                        if post:
                            results.append(post)
                except Exception:
                    logger.debug(
                        "Search error r/%s keyword=%s", subreddit_name, keyword,
                        exc_info=True,
                    )

        return results

    def _iter_posts(
        self,
        posts: Any,
        group_key: str,
        matched_kw: str,
        all_keywords: list[str],
    ):
        for post in posts:
            created = datetime.fromtimestamp(post.created_utc)
            if created < DATE_START or created > DATE_END:
                continue
            if post.score < MIN_SCORE:
                continue

            combined_text = f"{post.title}\n{post.selftext}"
            relevance = score_relevance(combined_text, all_keywords)
            if relevance < MIN_RELEVANCE:
                continue

            comments = self._fetch_comments(post, all_keywords)
            content = post.selftext[:2000]
            if comments:
                content += "\n\n--- Comments ---\n" + "\n---\n".join(comments[:3])

            result = build_result(
                platform="reddit",
                date=created.isoformat(),
                title=post.title,
                url=f"https://reddit.com{post.permalink}",
                content=content,
                author=str(post.author) if post.author else "[deleted]",
                relevance_score=relevance,
                keyword_group=group_key,
                matched_keyword=matched_kw,
            )
            result["reddit_score"] = post.score
            result["reddit_num_comments"] = post.num_comments
            result["reddit_subreddit"] = post.subreddit.display_name
            yield result

    def _fetch_comments(
        self, post: Submission, keywords: list[str]
    ) -> list[str]:
        try:
            post.comments.replace_more(limit=0)
            relevant: list[str] = []
            for c in post.comments.list()[:MAX_COMMENTS_PER_POST]:
                if c.score > 0:
                    text = c.body[:500]
                    if text:
                        relevant.append(text)
            return relevant
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Standalone: search only for Yu Ming core across all of Reddit
    # ------------------------------------------------------------------
    def search_all_reddit(self, query: str, limit: int = 100) -> list[dict]:
        """Broad search across the entire site (not scoped to subreddits)."""
        if self._reddit is None:
            return []

        results: list[dict] = []
        try:
            for post in self._reddit.subreddit("all").search(
                query, sort="relevance", time_filter="all", limit=limit
            ):
                created = datetime.fromtimestamp(post.created_utc)
                if created < DATE_START:
                    continue
                results.append(
                    build_result(
                        platform="reddit",
                        date=created.isoformat(),
                        title=post.title,
                        url=f"https://reddit.com{post.permalink}",
                        content=post.selftext[:2000],
                        author=str(post.author) if post.author else "[deleted]",
                        relevance_score=1.0,
                        keyword_group="school_core",
                        matched_keyword=query,
                    )
                )
        except Exception:
            logger.exception("Broad Reddit search failed for: %s", query)

        return results

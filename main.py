#!/usr/bin/env python3
"""
Yu Ming Charter School Discussion Scraper
==========================================
Collects online discussions about Yu Ming Charter School (Oakland, CA)
and surrounding community topics from 2023 to present.

Usage:
    python main.py                    # Run all scrapers
    python main.py --reddit-only      # Reddit only
    python main.py --news-only        # News only
    python main.py --web-only         # Review sites + general web
    python main.py --chinese-only     # Chinese platforms only
    python main.py --verbose          # Debug logging
    python main.py --dry-run          # Validate config only (no requests)
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import (
    ChinesePlatformScraper,
    NewsScraper,
    RedditScraper,
    WebScraper,
)
from scrapers.utils import deduplicate, save_results, setup_logging

logger = logging.getLogger("yuming_scraper.main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Yu Ming Charter School Discussion Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                         # Full scrape
  python main.py --reddit-only --verbose # Reddit only, debug output
  python main.py --dry-run               # Config check only
  python main.py --output ./my_results   # Custom output directory
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reddit-only", action="store_true", help="Run only Reddit scraper")
    group.add_argument("--news-only", action="store_true", help="Run only News scraper")
    group.add_argument("--web-only", action="store_true", help="Run only Web scraper")
    group.add_argument("--chinese-only", action="store_true", help="Run only Chinese platforms scraper")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without making requests")
    parser.add_argument("--output", default="output", help="Output directory (default: output)")
    return parser.parse_args()


def run_all(args: argparse.Namespace) -> dict[str, list[dict]]:
    """Execute all enabled scrapers, return {platform: results}."""
    all_data: dict[str, list[dict]] = {}

    if args.reddit_only:
        all_data["reddit"] = RedditScraper().scrape_all()
    elif args.news_only:
        all_data["news"] = NewsScraper().scrape_all()
    elif args.web_only:
        all_data["web"] = WebScraper().scrape_all()
    elif args.chinese_only:
        all_data["chinese"] = ChinesePlatformScraper().scrape_all()
    else:
        # Run all scrapers
        scrapers = [
            ("Reddit", RedditScraper()),
            ("News", NewsScraper()),
            ("Web", WebScraper()),
            ("Chinese Platforms", ChinesePlatformScraper()),
        ]

        for name, scraper in scrapers:
            logger.info("=" * 60)
            logger.info("Running %s scraper...", name)
            logger.info("=" * 60)
            try:
                results = scraper.scrape_all()
                key = name.lower().replace(" ", "_")
                all_data[key] = results
                logger.info("%s: %d results", name, len(results))
            except Exception:
                logger.exception("%s scraper failed", name)
                all_data[key] = []

    return all_data


def print_summary(all_data: dict[str, list[dict]]) -> None:
    """Print a human-readable summary of results."""
    print("\n" + "=" * 70)
    print("  SCRAPE SUMMARY")
    print("=" * 70)

    total = 0
    for platform, results in all_data.items():
        count = len(results)
        total += count
        groups: dict[str, int] = {}
        for r in results:
            g = r.get("keyword_group", "unknown")
            groups[g] = groups.get(g, 0) + 1
        print(f"\n  [{platform}]  {count} results")
        for g, c in sorted(groups.items(), key=lambda x: -x[1]):
            print(f"    - {g}: {c}")

    print(f"\n  TOTAL: {total} results")
    print(f"  Output directory: {os.path.abspath('output')}")
    print("=" * 70 + "\n")


def generate_master_report(all_data: dict[str, list[dict]], output_dir: str) -> None:
    """Combine all results into a single unified output file."""
    all_results: list[dict] = []
    for results in all_data.values():
        all_results.extend(results)

    unique = deduplicate(all_results)
    if unique:
        save_results(
            unique,
            "master_report",
            output_dir=output_dir,
            extra_meta={
                "platforms": list(all_data.keys()),
                "generated_at": datetime.now().isoformat(),
            },
        )
        print(f"Master report: {len(unique)} unique results across all platforms")


def dry_run() -> None:
    """Validate configuration without making network requests."""
    from scrapers.config import (
        DATE_END,
        DATE_START,
        KEYWORD_GROUPS,
        NEWS_RSS_FEEDS,
        REDDIT_SUBREDDITS,
    )

    print("=== DRY RUN: Configuration Validation ===\n")
    print(f"  Date range: {DATE_START.date()} to {DATE_END.date()}")
    print(f"  Reddit subreddits: {len(REDDIT_SUBREDDITS)}")
    for s in REDDIT_SUBREDDITS:
        print(f"    - r/{s}")
    print(f"  Keyword groups: {len(KEYWORD_GROUPS)}")
    for key, group in KEYWORD_GROUPS.items():
        kw_count = len(group["en"]) + len(group.get("zh", []))
        print(f"    - {key} ({group['label']}): {kw_count} keywords")
    print(f"  RSS feeds: {len(NEWS_RSS_FEEDS)}")
    for f in NEWS_RSS_FEEDS:
        print(f"    - {f['name']}")

    # Check env vars
    reddit_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if reddit_id and reddit_secret:
        print("\n  [OK] Reddit API credentials found in environment")
    else:
        print("\n  [WARN] Reddit API credentials not set")
        print("    Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET env vars")
        print("    Reddit scraping will be skipped.")

    print("\n=== Dry run complete. No requests made. ===\n")


def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    logger.info("Yu Ming Charter School Scraper starting...")

    if args.dry_run:
        dry_run()
        return

    all_data = run_all(args)
    print_summary(all_data)
    generate_master_report(all_data, args.output)

    logger.info("Scraping complete.")


if __name__ == "__main__":
    main()

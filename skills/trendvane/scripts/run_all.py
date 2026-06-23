"""Orchestrator: run all Tier 1 fetchers, then the scoring engine.

This script produces:
  - cache/raw_<source>_YYYYMMDD.json — per-source candidates
  - cache/picks_YYYYMMDD.json — top 3 picks with sub-scores

Then the skill (Claude) reads picks_*.json, generates briefs in the user's voice,
and pushes to Notion via the MCP tools.

Usage:
    python3 run_all.py            # full daily run
    python3 run_all.py --score    # skip fetching, just re-score from cached raw_*.json
"""

from __future__ import annotations

import argparse
import sys
import time

from common import get_logger

log = get_logger("orchestrator")


def run_fetchers() -> None:
    """Run all Tier 1 fetchers sequentially, swallowing per-source errors."""
    fetchers = [
        ("hackernews", "fetch_hackernews"),
        ("reddit", "fetch_reddit"),
        ("tiktok", "fetch_tiktok"),
        ("youtube", "fetch_youtube"),
        ("producthunt", "fetch_producthunt"),
        ("google_trends", "fetch_google_trends"),
    ]
    for label, mod_name in fetchers:
        t0 = time.time()
        try:
            mod = __import__(mod_name)
            items = mod.fetch()
            from common import dump_candidates

            dump_candidates(label, items)
            log.info(f"[{label}] {len(items)} candidates in {time.time()-t0:.1f}s")
        except Exception as e:
            log.warning(f"[{label}] failed: {e}")


def run_scoring() -> list[dict]:
    import score_trends

    return score_trends.run()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true", help="skip fetching, just re-score")
    args = ap.parse_args()

    if not args.score:
        log.info("=== running fetchers ===")
        run_fetchers()

    log.info("=== running scoring ===")
    picks = run_scoring()

    log.info(f"=== done. {len(picks)} picks ready for brief generation ===")
    for i, p in enumerate(picks, 1):
        print(f"#{i}  [{p['score']:.0f}] {p['canonical_title']}  ({p['category']}, {','.join(p['platforms'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Hacker News top stories fetcher.

Uses the official Firebase API (https://github.com/HackerNews/API). No auth.
Pulls top 50 stories, filters to score >= 100, returns as TrendCandidate.
"""

from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from common import TrendCandidate, dump_candidates, get_logger

log = get_logger("hackernews")

BASE = "https://hacker-news.firebaseio.com/v0"
TOP_LIMIT = 50
MIN_SCORE = 100


def _fetch(url: str) -> dict | list | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"fetch failed: {url} — {e}")
        return None


def fetch() -> list[TrendCandidate]:
    top_ids = _fetch(f"{BASE}/topstories.json")
    if not top_ids:
        return []

    candidates: list[TrendCandidate] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch, f"{BASE}/item/{i}.json"): i for i in top_ids[:TOP_LIMIT]}
        for fut in as_completed(futures):
            story = fut.result()
            if not story or story.get("type") != "story":
                continue
            score = story.get("score", 0)
            if score < MIN_SCORE:
                continue
            ts = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc).isoformat()
            url = story.get("url") or f"https://news.ycombinator.com/item?id={story['id']}"
            candidates.append(
                TrendCandidate(
                    source="hackernews",
                    platform="HackerNews",
                    title=story.get("title", "").strip(),
                    url=url,
                    raw_text=story.get("title", ""),
                    mention_count=score,
                    timestamp=ts,
                    extra={
                        "hn_url": f"https://news.ycombinator.com/item?id={story['id']}",
                        "comments": story.get("descendants", 0),
                        "by": story.get("by"),
                    },
                )
            )

    log.info(f"fetched {len(candidates)} stories (score >= {MIN_SCORE})")
    return candidates


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("hackernews", items)
    print(f"wrote {len(items)} candidates to {p}")

"""Reddit fetcher.

Uses Reddit's public .json endpoints (no auth required, but rate-limited).
Pulls /r/{subreddit}/hot.json for every subreddit listed in my_niches.json,
filters to score >= MIN_SCORE, returns normalized candidates.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from common import TrendCandidate, dump_candidates, get_logger, load_niches

log = get_logger("reddit")

USER_AGENT = "trend-radar/0.1 (open-source content research tool)"
MIN_SCORE = 200
LIMIT_PER_SUB = 25


def _fetch_sub(sub: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={LIMIT_PER_SUB}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
            return [child["data"] for child in data.get("data", {}).get("children", [])]
    except urllib.error.HTTPError as e:
        if e.code == 429:
            log.warning(f"r/{sub}: rate limited, backing off")
            time.sleep(5)
        else:
            log.warning(f"r/{sub}: HTTP {e.code}")
        return []
    except Exception as e:
        log.warning(f"r/{sub}: {e}")
        return []


def fetch() -> list[TrendCandidate]:
    niches = load_niches()
    subs: set[str] = set()
    for niche in niches.get("niches", []):
        subs.update(niche.get("subreddits", []))

    candidates: list[TrendCandidate] = []
    for sub in sorted(subs):
        posts = _fetch_sub(sub)
        time.sleep(1.2)  # be polite to public endpoint
        for p in posts:
            score = p.get("score", 0)
            if score < MIN_SCORE:
                continue
            if p.get("stickied") or p.get("over_18"):
                continue
            ts = datetime.fromtimestamp(
                p.get("created_utc", 0), tz=timezone.utc
            ).isoformat()
            permalink = "https://reddit.com" + p.get("permalink", "")
            candidates.append(
                TrendCandidate(
                    source="reddit",
                    platform="Reddit",
                    title=p.get("title", "").strip(),
                    url=p.get("url_overridden_by_dest") or permalink,
                    raw_text=(p.get("title", "") + "\n\n" + (p.get("selftext") or "")).strip(),
                    mention_count=score,
                    timestamp=ts,
                    extra={
                        "subreddit": sub,
                        "permalink": permalink,
                        "comments": p.get("num_comments", 0),
                        "upvote_ratio": p.get("upvote_ratio"),
                    },
                )
            )

    log.info(f"fetched {len(candidates)} posts across {len(subs)} subs (score >= {MIN_SCORE})")
    return candidates


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("reddit", items)
    print(f"wrote {len(items)} candidates to {p}")

"""YouTube Data API v3 fetcher.

Requires YT_API_KEY in memory/secrets.json or env. Free tier: 10k units/day.
A single call to videos.list?chart=mostPopular costs 1 unit.

Pulls top trending videos in US + UK + CA + AU, then searches by niche keywords.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from common import TrendCandidate, dump_candidates, env, get_logger, load_niches

log = get_logger("youtube")

API_KEY = env("YT_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"
REGIONS = ["US", "GB", "CA", "AU"]
PER_REGION = 25


def _get(path: str, params: dict) -> dict | None:
    params["key"] = API_KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"YT API failed: {path} — {e}")
        return None


def _to_candidate(item: dict, source_hint: str) -> TrendCandidate | None:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    vid = item.get("id")
    if isinstance(vid, dict):
        vid = vid.get("videoId")
    if not vid:
        return None
    return TrendCandidate(
        source="youtube",
        platform="YouTube",
        title=snippet.get("title", "").strip(),
        url=f"https://www.youtube.com/watch?v={vid}",
        raw_text=snippet.get("description", "")[:500],
        mention_count=int(stats.get("viewCount", 0)) if stats else None,
        timestamp=snippet.get("publishedAt", ""),
        extra={
            "channel": snippet.get("channelTitle"),
            "tags": snippet.get("tags", []),
            "category_id": snippet.get("categoryId"),
            "likes": int(stats.get("likeCount", 0)) if stats else None,
            "comments": int(stats.get("commentCount", 0)) if stats else None,
            "source_hint": source_hint,
        },
    )


def fetch() -> list[TrendCandidate]:
    if not API_KEY:
        log.warning("YT_API_KEY missing — skipping YouTube fetcher")
        return []

    candidates: list[TrendCandidate] = []

    # Strategy 1: mostPopular per region (1 unit each).
    for region in REGIONS:
        data = _get(
            "videos",
            {
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "regionCode": region,
                "maxResults": PER_REGION,
            },
        )
        if not data:
            continue
        for item in data.get("items", []):
            c = _to_candidate(item, f"mostPopular_{region}")
            if c:
                candidates.append(c)

    # Strategy 2: search.list by niche keywords (100 units per call — use sparingly).
    # Pull one tight query per high-weight niche.
    niches = load_niches().get("niches", [])
    high_weight = [n for n in niches if n.get("weight", 1) >= 2.0]
    for niche in high_weight:
        kw = " | ".join(niche.get("keywords", [])[:5])  # OR of top 5 keywords
        if not kw:
            continue
        data = _get(
            "search",
            {
                "part": "snippet",
                "q": kw,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": _iso_days_ago(7),
                "maxResults": 10,
                "relevanceLanguage": "en",
            },
        )
        if not data:
            continue
        for item in data.get("items", []):
            c = _to_candidate(item, f"search_{niche['id']}")
            if c:
                candidates.append(c)

    # Dedup by video URL
    by_url: dict[str, TrendCandidate] = {}
    for c in candidates:
        if c.url not in by_url or (c.mention_count or 0) > (by_url[c.url].mention_count or 0):
            by_url[c.url] = c

    out = list(by_url.values())
    log.info(f"fetched {len(out)} unique videos")
    return out


def _iso_days_ago(days: int) -> str:
    from datetime import timedelta

    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("youtube", items)
    print(f"wrote {len(items)} candidates to {p}")

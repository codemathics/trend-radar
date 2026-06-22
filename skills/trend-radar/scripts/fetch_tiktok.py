"""TikTok Creative Center fetcher.

TikTok exposes a (mostly) public API for the Creative Center trending data at
https://ads.tiktok.com/business/creativecenter/inspiration/popular/...

The endpoints below are the same ones the website itself calls. They don't
require auth but are subject to change — if TikTok updates the schema, this
fetcher logs a warning and returns [] so the daily run continues.

Pulls:
- Trending hashtags (top 50)
- Trending sounds (top 50)
- Trending videos (top 50)

All scoped to US + GB + CA + AU (in line with my_niches.json region setting).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from common import TrendCandidate, dump_candidates, get_logger, load_niches

log = get_logger("tiktok")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_REGIONS = ["US", "GB", "CA", "AU"]
HASHTAG_URL = (
    "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
)
SOUND_URL = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/song/list"
VIDEO_URL = "https://ads.tiktok.com/creative_radar_api/v1/top_ads/v2/list"


def _get(url: str, params: dict) -> dict | None:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"TikTok API failed: {url} — {e}")
        return None


def _fetch_hashtags(region: str) -> list[TrendCandidate]:
    data = _get(
        HASHTAG_URL,
        {
            "page": 1,
            "limit": 50,
            "period": 7,
            "country_code": region,
            "sort_by": "popular",
        },
    )
    if not data or data.get("code") != 0:
        return []
    out: list[TrendCandidate] = []
    for it in (data.get("data") or {}).get("list") or []:
        name = it.get("hashtag_name") or it.get("name")
        if not name:
            continue
        out.append(
            TrendCandidate(
                source="tiktok",
                platform="TikTok",
                title=f"#{name}",
                url=f"https://www.tiktok.com/tag/{name}",
                raw_text=name,
                mention_count=int(it.get("publish_cnt") or it.get("video_cnt") or 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                extra={
                    "kind": "hashtag",
                    "region": region,
                    "rank": it.get("rank"),
                    "rank_diff": it.get("rank_diff"),
                    "trend_type": it.get("trend_type"),
                },
            )
        )
    return out


def _fetch_sounds(region: str) -> list[TrendCandidate]:
    data = _get(
        SOUND_URL,
        {
            "page": 1,
            "limit": 50,
            "period": 7,
            "country_code": region,
            "rank_type": "popular",
        },
    )
    if not data or data.get("code") != 0:
        return []
    out: list[TrendCandidate] = []
    for it in (data.get("data") or {}).get("list") or []:
        title = it.get("title") or it.get("song_name")
        author = it.get("author")
        if not title:
            continue
        clip_id = it.get("clip_id") or it.get("song_id")
        url = (
            f"https://www.tiktok.com/music/{title.replace(' ', '-')}-{clip_id}"
            if clip_id
            else "https://www.tiktok.com/music/"
        )
        out.append(
            TrendCandidate(
                source="tiktok",
                platform="TikTok",
                title=f"🎵 {title}" + (f" - {author}" if author else ""),
                url=url,
                raw_text=title,
                mention_count=int(it.get("publish_cnt") or it.get("user_cnt") or 0),
                timestamp=datetime.now(timezone.utc).isoformat(),
                extra={
                    "kind": "sound",
                    "region": region,
                    "clip_id": clip_id,
                    "author": author,
                    "duration": it.get("duration"),
                    "rank": it.get("rank"),
                    "rank_diff": it.get("rank_diff"),
                },
            )
        )
    return out


def fetch() -> list[TrendCandidate]:
    cfg = load_niches()
    region_cfg = cfg.get("region", {})
    primary = region_cfg.get("primary", "US")
    secondary = region_cfg.get("secondary", ["GB", "CA", "AU"])
    regions = [primary] + [r for r in secondary if r != primary] if primary else DEFAULT_REGIONS

    all_items: list[TrendCandidate] = []
    for region in regions:
        all_items.extend(_fetch_hashtags(region))
        all_items.extend(_fetch_sounds(region))

    # Dedup by (kind, title) keeping max mention_count.
    by_key: dict[tuple[str, str], TrendCandidate] = {}
    for c in all_items:
        key = (c.extra.get("kind", ""), c.title)
        if key not in by_key or (c.mention_count or 0) > (by_key[key].mention_count or 0):
            by_key[key] = c

    out = list(by_key.values())
    log.info(f"fetched {len(out)} unique TikTok signals (hashtags + sounds)")
    return out


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("tiktok", items)
    print(f"wrote {len(items)} candidates to {p}")

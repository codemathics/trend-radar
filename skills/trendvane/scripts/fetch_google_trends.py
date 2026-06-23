"""Google Trends fetcher via pytrends.

pip install pytrends

Pulls rising / top related queries for each niche defined in my_niches.json.
Cheaper and more reliable than realtime trends (which has been flaky since 2024).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from common import TrendCandidate, dump_candidates, get_logger, load_niches

log = get_logger("google_trends")

try:
    from pytrends.request import TrendReq

    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


REGIONS = ["united_states", "united_kingdom", "canada", "australia"]


def fetch() -> list[TrendCandidate]:
    if not PYTRENDS_AVAILABLE:
        log.warning("pytrends not installed — run: pip install pytrends")
        return []

    pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.5)
    candidates: list[TrendCandidate] = []
    niches = load_niches().get("niches", [])

    # Pull related queries for a seed keyword per niche.
    for niche in niches:
        seed = (niche.get("keywords") or [None])[0]
        if not seed:
            continue
        try:
            pytrends.build_payload([seed], timeframe="now 7-d", geo="US")
            related = pytrends.related_queries()
            rising = (related.get(seed, {}) or {}).get("rising")
            if rising is None or rising.empty:
                continue
            for _, row in rising.head(10).iterrows():
                q = row.get("query")
                val = row.get("value")
                if not q:
                    continue
                candidates.append(
                    TrendCandidate(
                        source="google_trends",
                        platform="Google Trends",
                        title=str(q),
                        url=f"https://trends.google.com/trends/explore?q={q.replace(' ', '+')}",
                        raw_text=str(q),
                        mention_count=int(val) if val and val != "Breakout" else 9999,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        extra={"seed": seed, "niche": niche["id"], "rise_label": str(val)},
                    )
                )
            time.sleep(2)  # avoid 429
        except Exception as e:
            log.warning(f"pytrends failed for seed='{seed}': {e}")
            time.sleep(5)

    log.info(f"fetched {len(candidates)} rising queries")
    return candidates


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("google_trends", items)
    print(f"wrote {len(items)} candidates to {p}")

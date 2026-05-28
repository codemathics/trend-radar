"""Product Hunt fetcher (GraphQL v2).

Requires PH_TOKEN in memory/secrets.json or env. Get one at
https://www.producthunt.com/v2/oauth/applications (free).

Pulls today's posts ordered by votes.
"""

from __future__ import annotations

import json
import urllib.request

from common import TrendCandidate, dump_candidates, env, get_logger

log = get_logger("producthunt")

PH_TOKEN = env("PH_TOKEN")
ENDPOINT = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query TodaysTopPosts {
  posts(order: VOTES, first: 25) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        commentsCount
        createdAt
        topics(first: 5) {
          edges { node { name } }
        }
        thumbnail { url }
      }
    }
  }
}
"""


def fetch() -> list[TrendCandidate]:
    if not PH_TOKEN:
        log.warning("PH_TOKEN missing — skipping Product Hunt fetcher")
        return []

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": QUERY}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {PH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"PH API failed: {e}")
        return []

    edges = payload.get("data", {}).get("posts", {}).get("edges", [])
    candidates: list[TrendCandidate] = []
    for edge in edges:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
        candidates.append(
            TrendCandidate(
                source="producthunt",
                platform="Product Hunt",
                title=node["name"],
                url=node["url"],
                raw_text=(node.get("tagline", "") + "\n" + (node.get("description") or "")).strip(),
                mention_count=node.get("votesCount", 0),
                timestamp=node.get("createdAt", ""),
                extra={
                    "topics": topics,
                    "comments": node.get("commentsCount", 0),
                    "thumbnail": (node.get("thumbnail") or {}).get("url"),
                },
            )
        )

    log.info(f"fetched {len(candidates)} Product Hunt posts")
    return candidates


if __name__ == "__main__":
    items = fetch()
    p = dump_candidates("producthunt", items)
    print(f"wrote {len(items)} candidates to {p}")

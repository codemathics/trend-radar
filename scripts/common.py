"""Shared utilities for trend-radar fetchers.

Every fetcher returns a list of normalized trend candidates with this shape:

{
    "source": "tiktok" | "youtube" | "reddit" | "hackernews" | "producthunt" | "google_trends",
    "platform": "TikTok" | "YouTube" | "Reddit" | "HackerNews" | "Product Hunt" | "Google Trends",
    "title": str,                 # what the trend is about
    "url": str,                   # primary source link
    "raw_text": str,              # description / body for keyword matching
    "mention_count": int | None,  # views / upvotes / comments — comparable within source
    "timestamp": str,             # ISO-8601 of when it was created/posted
    "extra": dict,                # source-specific fields (e.g., tiktok sound_id)
}

The scoring engine consumes this normalized shape, so adding a new fetcher only
requires producing valid entries here.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / "memory"
CACHE = ROOT / "cache"
BRIEFINGS = ROOT / "briefings"
TEMPLATES = ROOT / "templates"

for d in (MEMORY, CACHE, BRIEFINGS, TEMPLATES):
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(os.environ.get("TREND_RADAR_LOG", "INFO"))
    return logger


# ---------------------------------------------------------------------------
# Normalized trend candidate
# ---------------------------------------------------------------------------

@dataclass
class TrendCandidate:
    source: str
    platform: str
    title: str
    url: str
    raw_text: str = ""
    mention_count: int | None = None
    timestamp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def cache_path(name: str) -> Path:
    return CACHE / f"{name}.json"


def write_cache(name: str, payload: Any) -> None:
    p = cache_path(name)
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def read_cache(name: str, max_age_seconds: int = 3600) -> Any | None:
    p = cache_path(name)
    if not p.exists():
        return None
    age = time.time() - p.stat().st_mtime
    if age > max_age_seconds:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Config access
# ---------------------------------------------------------------------------

def load_niches() -> dict[str, Any]:
    return json.loads((MEMORY / "my_niches.json").read_text(encoding="utf-8"))


def load_notion_config() -> dict[str, Any]:
    p = MEMORY / "notion_config.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def env(key: str, default: str | None = None) -> str | None:
    """Load a secret from env, falling back to memory/secrets.json."""
    val = os.environ.get(key)
    if val:
        return val
    secrets_path = MEMORY / "secrets.json"
    if secrets_path.exists():
        secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
        return secrets.get(key, default)
    return default


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def dump_candidates(name: str, candidates: Iterable[TrendCandidate]) -> Path:
    """Write the day's raw candidates from one source to cache."""
    payload = [c.to_dict() if isinstance(c, TrendCandidate) else c for c in candidates]
    p = CACHE / f"raw_{name}_{datetime.now().strftime('%Y%m%d')}.json"
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return p

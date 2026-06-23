"""Shared utilities for trendvane fetchers.

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
#
# Two roots, deliberately separated:
#
#   CODE_ROOT  - where the skill's shipped files live (scripts, templates, and
#                the template/default config). When installed via the skills
#                CLI this is inside ~/.claude/skills/trendvane and gets
#                REPLACED on every `skills update`. Treat it as read-only.
#
#   DATA_ROOT  - where the user's own data lives: their filled-in config, the
#                hook-rotation memory, the dedup cache, and the daily
#                briefings. This must survive skill updates, so it lives
#                outside the skill folder.
#
# When the repo is run in place (git clone, dev), DATA_ROOT == CODE_ROOT so
# everything stays in one folder and nothing changes for that workflow.

CODE_ROOT = Path(__file__).resolve().parent.parent


def _resolve_data_root() -> Path:
    """Pick where user data (config, cache, briefings) lives.

    Priority:
      1. TRENDVANE_DATA env var, if set (cron / power users). The legacy
         TREND_RADAR_DATA name is still honored as a fallback.
      2. If the skill is installed under ~/.claude/skills, use the stable
         ~/.claude/trendvane data dir so `skills update` can't wipe config.
      3. Otherwise (running from a clone), use the repo folder in place.
    """
    env_dir = os.environ.get("TRENDVANE_DATA") or os.environ.get("TREND_RADAR_DATA")
    if env_dir:
        return Path(env_dir).expanduser()

    # resolve() both sides so a symlinked home (e.g. /tmp -> /private/tmp on
    # macOS) doesn't break the "am I installed under ~/.claude/skills" check.
    claude_home = (Path.home() / ".claude").resolve()
    skills_home = claude_home / "skills"
    try:
        CODE_ROOT.relative_to(skills_home)
    except ValueError:
        return CODE_ROOT
    # Installed under ~/.claude/skills. Prefer the new data dir, but fall back to
    # the legacy ~/.claude/trend-radar when it exists and the new one doesn't, so
    # installs that predate the trendvane rename keep their config.
    new_data = claude_home / "trendvane"
    legacy_data = claude_home / "trend-radar"
    if not new_data.exists() and legacy_data.exists():
        return legacy_data
    return new_data


DATA_ROOT = _resolve_data_root()

# Templates always ship with the code (never user-edited).
TEMPLATES = CODE_ROOT / "templates"
# Config + state live with the user's data.
MEMORY = DATA_ROOT / "memory"
CACHE = DATA_ROOT / "cache"
BRIEFINGS = DATA_ROOT / "briefings"

for d in (MEMORY, CACHE, BRIEFINGS):
    d.mkdir(parents=True, exist_ok=True)

# Backwards-compat alias for any code that still imports ROOT.
ROOT = DATA_ROOT


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(os.environ.get("TRENDVANE_LOG", os.environ.get("TREND_RADAR_LOG", "INFO")))
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

def _config_path(name: str) -> Path:
    """Find a config file: prefer the user's data dir, fall back to the
    shipped default in the skill folder. Lets a fresh install read sensible
    defaults before the user has run setup."""
    user_copy = MEMORY / name
    if user_copy.exists():
        return user_copy
    return CODE_ROOT / "memory" / name


def load_niches() -> dict[str, Any]:
    return json.loads(_config_path("my_niches.json").read_text(encoding="utf-8"))


def load_notion_config() -> dict[str, Any]:
    p = _config_path("notion_config.json")
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def env(key: str, default: str | None = None) -> str | None:
    """Load a secret from env, falling back to memory/secrets.json."""
    val = os.environ.get(key)
    if val:
        return val
    secrets_path = _config_path("secrets.json")
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

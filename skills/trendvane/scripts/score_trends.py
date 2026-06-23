"""Score and rank trend candidates.

Pipeline:
  1. Load candidates from cache/raw_*_YYYYMMDD.json
  2. Apply brand-safe filter (drop politics, alcohol/drugs/gambling)
  3. Cluster cross-platform duplicates (same trend on TikTok + X + HN = one)
  4. Score each cluster:
       niche_fit       × 0.40
       velocity        × 0.25
       cross_platform  × 0.15
       recency         × 0.10
       originality     × 0.10
  5. Filter score >= 60
  6. Pick top 3 (forcing at least one AI-niche pick when available)

Final picks are written to cache/picks_YYYYMMDD.json for the brief generator.
"""

from __future__ import annotations

import glob
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import CACHE, MEMORY, get_logger, load_niches, now_iso

log = get_logger("score")

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

MIN_SCORE_FOR_PICK = 60
TARGET_PICKS = 3
SCORING = {
    "niche_fit": 0.40,
    "velocity": 0.25,
    "cross_platform": 0.15,
    "recency": 0.10,
    "originality": 0.10,
}
SEEN_TRENDS_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Cluster:
    """A trend, possibly appearing across multiple platforms."""

    canonical_title: str
    members: list[dict[str, Any]] = field(default_factory=list)
    keywords: set[str] = field(default_factory=set)

    # Computed scores (0..1 before weighting)
    niche_fit: float = 0.0
    velocity: float = 0.0
    cross_platform: float = 0.0
    recency: float = 0.0
    originality: float = 0.0
    final_score: float = 0.0

    # Decisions
    category: str = ""
    primary_platform: str = ""
    primary_url: str = ""
    velocity_label: str = "Rising"
    time_to_stale: str = "1 week"
    matched_niche_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_title": self.canonical_title,
            "category": self.category,
            "matched_niche_id": self.matched_niche_id,
            "platforms": sorted({m["platform"] for m in self.members}),
            "primary_url": self.primary_url,
            "source_urls": [m["url"] for m in self.members[:5]],
            "velocity_label": self.velocity_label,
            "time_to_stale": self.time_to_stale,
            "score": round(self.final_score * 100, 1),
            "sub_scores": {
                "niche_fit": round(self.niche_fit, 3),
                "velocity": round(self.velocity, 3),
                "cross_platform": round(self.cross_platform, 3),
                "recency": round(self.recency, 3),
                "originality": round(self.originality, 3),
            },
            "members": self.members,
        }


# ---------------------------------------------------------------------------
# Tokenization + brand-safe filter
# ---------------------------------------------------------------------------

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9'\-]+")


def tokenize(text: str) -> set[str]:
    return {w.lower() for w in WORD_RE.findall(text or "") if len(w) > 2}


def brand_safe_filter(candidates: list[dict], niches_cfg: dict) -> list[dict]:
    excl = niches_cfg.get("brand_safe_exclusions", {})
    blocked = {b.lower() for b in excl.get("blocked_topics", [])}
    regexes = [re.compile(p, re.IGNORECASE) for p in excl.get("blocked_keywords_regex", [])]

    out: list[dict] = []
    dropped = 0
    for c in candidates:
        text = f"{c.get('title','')} {c.get('raw_text','')}".lower()
        if any(b in text for b in blocked):
            dropped += 1
            continue
        if any(rx.search(text) for rx in regexes):
            dropped += 1
            continue
        out.append(c)
    log.info(f"brand-safe filter dropped {dropped}/{len(candidates)}")
    return out


# ---------------------------------------------------------------------------
# Loading candidates from cache
# ---------------------------------------------------------------------------

def load_today_candidates() -> list[dict]:
    today = datetime.now().strftime("%Y%m%d")
    files = glob.glob(str(CACHE / f"raw_*_{today}.json"))
    all_c: list[dict] = []
    for f in files:
        try:
            items = json.loads(Path(f).read_text(encoding="utf-8"))
            all_c.extend(items)
        except Exception as e:
            log.warning(f"failed to load {f}: {e}")
    log.info(f"loaded {len(all_c)} candidates from {len(files)} sources")
    return all_c


# ---------------------------------------------------------------------------
# Clustering across platforms
# ---------------------------------------------------------------------------

def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster_candidates(candidates: list[dict], min_overlap: float = 0.45) -> list[Cluster]:
    """Greedy clustering by token Jaccard on title+raw_text."""
    clusters: list[Cluster] = []
    for c in candidates:
        toks = tokenize(c.get("title", "") + " " + c.get("raw_text", ""))
        if not toks:
            continue
        # Find best matching cluster
        best, best_sim = None, 0.0
        for cl in clusters:
            sim = jaccard(toks, cl.keywords)
            if sim > best_sim:
                best, best_sim = cl, sim
        if best is not None and best_sim >= min_overlap:
            best.members.append(c)
            best.keywords |= toks
        else:
            clusters.append(Cluster(canonical_title=c.get("title", "").strip(), members=[c], keywords=toks))
    log.info(f"clustered {len(candidates)} candidates into {len(clusters)} groups")
    return clusters


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------

def score_niche_fit(cluster: Cluster, niches: list[dict]) -> tuple[float, str, str]:
    """Returns (score_0_1, matched_niche_id, category_label)."""
    text = (cluster.canonical_title + " " + " ".join(m.get("raw_text", "") for m in cluster.members)).lower()
    text_toks = tokenize(text)

    best_score, best_id, best_label = 0.0, "", ""
    for niche in niches:
        keywords = [k.lower() for k in niche.get("keywords", [])]
        weight = niche.get("weight", 1.0)
        # Count keyword hits (substring + token match)
        hits = 0
        for kw in keywords:
            if " " in kw:
                if kw in text:
                    hits += 1
            else:
                if kw in text_toks:
                    hits += 1
        if hits == 0:
            continue
        # Normalize: max possible is min(len(keywords), 8), weighted by niche weight
        raw = min(hits, 8) / 8.0
        weighted = raw * weight  # AI 3x, PD/Film 2x, others 1x
        if weighted > best_score:
            best_score = weighted
            best_id = niche["id"]
            best_label = niche["label"]
    # Cap at 1.0 even after niche weighting (the weight already differentiates picks)
    normalized = min(best_score / 3.0, 1.0)  # AI's 3x = 1.0 max
    # Map label -> Notion category select value
    label_to_cat = {
        "AI / LLMs / Models": "AI",
        "Product Design": "Product Design",
        "Filmmaking": "Filmmaking",
        "Tech / Software / Devices": "Tech",
        "How-To / Tutorials": "How-to",
        "Lifestyle / Creator": "Lifestyle",
        "Business / Investments": "Business",
    }
    return normalized, best_id, label_to_cat.get(best_label, "Tech")


def score_velocity(cluster: Cluster, all_clusters_by_source: dict[str, list[float]]) -> tuple[float, str, str]:
    """Velocity heuristic.

    Without time-series, we approximate velocity by:
    - TikTok hashtags/sounds: rank_diff (negative = rising in rank)
    - HN/Reddit: percentile of mention_count within source today
    - YouTube: percentile of viewCount within source today

    Returns (score_0_1, velocity_label, time_to_stale).
    """
    scores: list[float] = []
    sources_seen = set()
    for m in cluster.members:
        src = m.get("source", "")
        sources_seen.add(src)
        if src == "tiktok":
            diff = m.get("extra", {}).get("rank_diff")
            if isinstance(diff, (int, float)):
                # rank_diff: negative means moving up. Map -50..+50 → 1..0
                v = max(0.0, min(1.0, (-diff + 50) / 100))
                scores.append(v)
            else:
                scores.append(0.5)
        else:
            cnt = m.get("mention_count") or 0
            same_src = all_clusters_by_source.get(src, [])
            if same_src and cnt > 0:
                rank_above = sum(1 for x in same_src if cnt > x)
                pct = rank_above / max(1, len(same_src))
                scores.append(pct)
            else:
                scores.append(0.4)

    velocity = sum(scores) / len(scores) if scores else 0.4

    # Labeling
    if velocity >= 0.7:
        label = "Rising"
        tts = "< 3 days"
    elif velocity >= 0.4:
        label = "Peaking"
        tts = "1 week"
    else:
        label = "Fading"
        tts = "2+ weeks"
    return velocity, label, tts


def score_cross_platform(cluster: Cluster) -> float:
    """Bonus for appearing on multiple platforms."""
    platforms = {m["platform"] for m in cluster.members}
    # 1 platform = 0, 2 = 0.5, 3+ = 1.0
    return min(1.0, max(0, len(platforms) - 1) / 2)


def score_recency(cluster: Cluster) -> float:
    """Newer = higher. Most-recent timestamp in cluster."""
    now = datetime.now(timezone.utc)
    newest_age_hours = float("inf")
    for m in cluster.members:
        ts = m.get("timestamp")
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = (now - t).total_seconds() / 3600
            newest_age_hours = min(newest_age_hours, age)
        except Exception:
            continue
    if newest_age_hours == float("inf"):
        return 0.5
    # 0h = 1.0, 168h (7d) = 0.0
    return max(0.0, 1.0 - (newest_age_hours / 168))


def score_originality(cluster: Cluster, seen: dict[str, str]) -> float:
    """Penalize if the cluster's keywords overlap heavily with anything seen in the
    last 30 days."""
    toks = cluster.keywords
    if not toks:
        return 0.5
    worst = 0.0
    for prev_text in seen.values():
        prev_toks = tokenize(prev_text)
        worst = max(worst, jaccard(toks, prev_toks))
    return 1.0 - worst


# ---------------------------------------------------------------------------
# Seen-trends dedup cache
# ---------------------------------------------------------------------------

def load_seen() -> dict[str, str]:
    p = CACHE / "seen_trends.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    # Prune entries older than window
    cutoff = datetime.now(timezone.utc).timestamp() - SEEN_TRENDS_WINDOW_DAYS * 86400
    return {k: v["text"] for k, v in data.items() if v.get("ts", 0) >= cutoff}


def save_seen(seen_titles: list[str]) -> None:
    p = CACHE / "seen_trends.json"
    existing = {}
    if p.exists():
        try:
            existing = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    cutoff = datetime.now(timezone.utc).timestamp() - SEEN_TRENDS_WINDOW_DAYS * 86400
    existing = {k: v for k, v in existing.items() if v.get("ts", 0) >= cutoff}
    now_ts = datetime.now(timezone.utc).timestamp()
    for t in seen_titles:
        existing[t.lower()] = {"text": t, "ts": now_ts}
    p.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------

def run() -> list[dict]:
    cfg = load_niches()
    niches = cfg.get("niches", [])

    # 1. Load + brand-safe filter
    raw = load_today_candidates()
    safe = brand_safe_filter(raw, cfg)

    # 2. Cluster
    clusters = cluster_candidates(safe)

    # 3. Score each cluster
    by_source_mentions: dict[str, list[float]] = {}
    for cl in clusters:
        for m in cl.members:
            by_source_mentions.setdefault(m.get("source", ""), []).append(m.get("mention_count") or 0)

    seen = load_seen()

    for cl in clusters:
        cl.niche_fit, cl.matched_niche_id, cl.category = score_niche_fit(cl, niches)
        cl.velocity, cl.velocity_label, cl.time_to_stale = score_velocity(cl, by_source_mentions)
        cl.cross_platform = score_cross_platform(cl)
        cl.recency = score_recency(cl)
        cl.originality = score_originality(cl, seen)

        # Pick primary platform/url: the member with highest mention_count
        best_m = max(cl.members, key=lambda m: m.get("mention_count") or 0)
        cl.primary_platform = best_m["platform"]
        cl.primary_url = best_m["url"]

        cl.final_score = (
            cl.niche_fit * SCORING["niche_fit"]
            + cl.velocity * SCORING["velocity"]
            + cl.cross_platform * SCORING["cross_platform"]
            + cl.recency * SCORING["recency"]
            + cl.originality * SCORING["originality"]
        )

    # 4. Filter + pick top 3 (forcing one AI when available)
    ranked = sorted(clusters, key=lambda c: c.final_score, reverse=True)
    qualifying = [c for c in ranked if c.final_score * 100 >= MIN_SCORE_FOR_PICK and c.matched_niche_id]

    picks: list[Cluster] = []
    ai_picks = [c for c in qualifying if c.matched_niche_id == "ai"]
    if ai_picks:
        picks.append(ai_picks[0])

    for c in qualifying:
        if c in picks:
            continue
        if len(picks) >= TARGET_PICKS:
            break
        # Avoid duplicate categories in the daily 3 unless we have to
        if c.category in {p.category for p in picks} and len(picks) < TARGET_PICKS - 1:
            continue
        picks.append(c)

    # Backfill if we still have fewer than 3
    if len(picks) < TARGET_PICKS:
        for c in qualifying:
            if c in picks:
                continue
            picks.append(c)
            if len(picks) >= TARGET_PICKS:
                break

    log.info(
        f"picked {len(picks)}/{TARGET_PICKS} trends "
        f"(out of {len(qualifying)} qualifying, {len(clusters)} clusters)"
    )

    # 5. Write picks + update seen cache
    out_path = CACHE / f"picks_{datetime.now().strftime('%Y%m%d')}.json"
    payload = {
        "generated_at": now_iso(),
        "picks": [p.to_dict() for p in picks],
        "skipped_count": max(0, len(qualifying) - len(picks)),
        "total_candidates": len(raw),
        "total_clusters": len(clusters),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    save_seen([p.canonical_title for p in picks])
    log.info(f"wrote picks to {out_path}")

    return payload["picks"]


if __name__ == "__main__":
    picks = run()
    for i, p in enumerate(picks, 1):
        print(f"#{i}  [{p['score']}] {p['canonical_title']}  ({p['category']}, {','.join(p['platforms'])})")

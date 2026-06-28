"""Unit tests for the scoring + clustering engine.

These guard the hand-tuned heuristics (niche weighting, the Jaccard clustering
threshold, the brand-safe filter, velocity labels, and the config-driven pick
logic) so that tuning changes are made deliberately rather than by accident.

Run with the stdlib test runner (no extra deps):

    python3 -m unittest discover -s skills/trendvane/tests
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Isolate data dir BEFORE importing the skill modules: common.py creates the
# MEMORY/CACHE/BRIEFINGS dirs at import time, and we don't want that to touch
# the real repo/home folders during tests.
_TMP_DATA = tempfile.mkdtemp(prefix="trendvane-tests-")
os.environ["TRENDVANE_DATA"] = _TMP_DATA

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import score_trends as st  # noqa: E402
from score_trends import Cluster  # noqa: E402


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def make_member(**kw):
    """A normalized candidate with sensible defaults for the fields scoring reads."""
    base = {
        "source": "hackernews",
        "platform": "HackerNews",
        "title": "",
        "url": "https://example.com",
        "raw_text": "",
        "mention_count": 0,
        "timestamp": _iso(datetime.now(timezone.utc)),
        "extra": {},
    }
    base.update(kw)
    return base


# Minimal niche config used across tests - note categories are data-driven here.
NICHES = [
    {"id": "ai", "label": "AI", "category": "AI", "weight": 3.0,
     "keywords": ["ai", "llm", "claude", "gpt", "agent"]},
    {"id": "film", "label": "Filmmaking", "category": "Filmmaking", "weight": 2.0,
     "keywords": ["cinematography", "color grading", "b-roll"]},
    {"id": "biz", "label": "Business", "category": "Business", "weight": 1.0,
     "keywords": ["startup", "founder", "fundraise"]},
]


class TestTokenizeAndJaccard(unittest.TestCase):
    def test_tokenize_lowercases_and_drops_short_words(self):
        toks = st.tokenize("AI is a Big Deal")
        self.assertIn("big", toks)
        self.assertIn("deal", toks)
        # "AI", "is", "a" are all <= 2 chars and dropped
        self.assertNotIn("ai", toks)
        self.assertNotIn("is", toks)

    def test_jaccard_identical_and_disjoint(self):
        self.assertEqual(st.jaccard({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(st.jaccard({"a"}, {"b"}), 0.0)
        self.assertEqual(st.jaccard(set(), {"a"}), 0.0)

    def test_jaccard_partial_overlap(self):
        # {a,b,c} vs {b,c,d} -> intersection 2, union 4
        self.assertAlmostEqual(st.jaccard({"a", "b", "c"}, {"b", "c", "d"}), 0.5)


class TestBrandSafeFilter(unittest.TestCase):
    cfg = {
        "brand_safe_exclusions": {
            "blocked_topics": ["politics", "casino"],
            "blocked_keywords_regex": [r"\b(vote|ballot)\b"],
        }
    }

    def test_drops_blocked_topic_substring(self):
        cands = [
            make_member(title="New AI model released"),
            make_member(title="The politics of tech"),
        ]
        out = st.brand_safe_filter(cands, self.cfg)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["title"], "New AI model released")

    def test_drops_blocked_regex(self):
        cands = [make_member(title="Go vote today"), make_member(title="Build a startup")]
        out = st.brand_safe_filter(cands, self.cfg)
        self.assertEqual([c["title"] for c in out], ["Build a startup"])

    def test_no_exclusions_passes_everything(self):
        cands = [make_member(title="anything"), make_member(title="else")]
        self.assertEqual(len(st.brand_safe_filter(cands, {})), 2)


class TestClustering(unittest.TestCase):
    def test_similar_titles_merge(self):
        cands = [
            make_member(title="Claude releases new coding agent model"),
            make_member(title="New Claude coding agent model released", platform="Reddit"),
        ]
        clusters = st.cluster_candidates(cands, min_overlap=0.45)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0].members), 2)

    def test_dissimilar_titles_split(self):
        cands = [
            make_member(title="Claude releases new coding agent"),
            make_member(title="DaVinci Resolve color grading tutorial"),
        ]
        clusters = st.cluster_candidates(cands, min_overlap=0.45)
        self.assertEqual(len(clusters), 2)

    def test_empty_tokens_skipped(self):
        cands = [make_member(title="a"), make_member(title="")]
        self.assertEqual(st.cluster_candidates(cands), [])


class TestNicheFit(unittest.TestCase):
    def _cluster(self, title, raw=""):
        return Cluster(canonical_title=title, members=[make_member(title=title, raw_text=raw)],
                       keywords=st.tokenize(title + " " + raw))

    def test_matches_niche_and_returns_data_driven_category(self):
        cl = self._cluster("New Claude agent and llm tooling")
        score, niche_id, category = st.score_niche_fit(cl, NICHES)
        self.assertEqual(niche_id, "ai")
        self.assertEqual(category, "AI")
        self.assertGreater(score, 0.0)

    def test_highest_weight_niche_can_reach_full_fit(self):
        # 8+ distinct keyword hits saturate raw to 1.0; with weight == max weight
        # the normalized niche_fit tops out at 1.0.
        niches = [
            {"id": "ai", "label": "AI", "category": "AI", "weight": 3.0,
             "keywords": ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india"]},
            {"id": "biz", "label": "Business", "category": "Business", "weight": 1.0,
             "keywords": ["startup"]},
        ]
        cl = self._cluster("alpha bravo charlie delta echo foxtrot golf hotel india")
        score, niche_id, _ = st.score_niche_fit(cl, niches)
        self.assertEqual(niche_id, "ai")
        self.assertAlmostEqual(score, 1.0, places=3)

    def test_weight_cap_is_dynamic_not_hardcoded(self):
        # With only weight-1.0 niches, a saturated match should still reach 1.0
        # (the old code divided by a hardcoded 3.0 and capped non-AI niches at ~0.33).
        niches = [{"id": "biz", "label": "Business", "category": "Business", "weight": 1.0,
                   "keywords": ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]}]
        cl = self._cluster("alpha bravo charlie delta echo foxtrot golf hotel")
        score, niche_id, category = st.score_niche_fit(cl, niches)
        self.assertEqual(niche_id, "biz")
        self.assertEqual(category, "Business")
        self.assertAlmostEqual(score, 1.0, places=3)

    def test_no_match_returns_empty_id(self):
        cl = self._cluster("completely unrelated gardening content")
        score, niche_id, _ = st.score_niche_fit(cl, NICHES)
        self.assertEqual(niche_id, "")
        self.assertEqual(score, 0.0)

    def test_category_falls_back_to_label_map_when_absent(self):
        # Legacy niche with no explicit "category" still resolves via the label map.
        niches = [{"id": "ai", "label": "AI / LLMs / Models", "weight": 3.0,
                   "keywords": ["claude", "llm"]}]
        cl = self._cluster("Claude llm news")
        _, _, category = st.score_niche_fit(cl, niches)
        self.assertEqual(category, "AI")


class TestComponentScores(unittest.TestCase):
    def test_cross_platform_bonus(self):
        one = Cluster("t", members=[make_member(platform="HackerNews")])
        two = Cluster("t", members=[make_member(platform="HackerNews"),
                                    make_member(platform="Reddit")])
        three = Cluster("t", members=[make_member(platform="HackerNews"),
                                      make_member(platform="Reddit"),
                                      make_member(platform="YouTube")])
        self.assertEqual(st.score_cross_platform(one), 0.0)
        self.assertEqual(st.score_cross_platform(two), 0.5)
        self.assertEqual(st.score_cross_platform(three), 1.0)

    def test_recency_newer_scores_higher(self):
        now = datetime.now(timezone.utc)
        fresh = Cluster("t", members=[make_member(timestamp=_iso(now))])
        old = Cluster("t", members=[make_member(timestamp=_iso(now - timedelta(days=6)))])
        self.assertGreater(st.score_recency(fresh), st.score_recency(old))
        self.assertAlmostEqual(st.score_recency(fresh), 1.0, places=1)

    def test_recency_defaults_when_no_timestamp(self):
        cl = Cluster("t", members=[make_member(timestamp="")])
        self.assertEqual(st.score_recency(cl), 0.5)

    def test_originality_penalizes_seen_trends(self):
        cl = Cluster("t", keywords={"claude", "agent", "model"})
        seen = {"k": "claude agent model launch"}
        fresh_score = st.score_originality(cl, {})
        seen_score = st.score_originality(cl, seen)
        self.assertGreater(fresh_score, seen_score)

    def test_velocity_labels(self):
        rising = Cluster("t", members=[make_member(source="tiktok", extra={"rank_diff": -50})])
        v, label, _ = st.score_velocity(rising, {})
        self.assertEqual(label, "Rising")
        self.assertGreaterEqual(v, 0.7)

        fading = Cluster("t", members=[make_member(source="tiktok", extra={"rank_diff": 50})])
        v, label, _ = st.score_velocity(fading, {})
        self.assertEqual(label, "Fading")


class TestPriorityNicheResolution(unittest.TestCase):
    def test_explicit_priority_wins(self):
        cfg = {"priority_niche_id": "film"}
        self.assertEqual(st.resolve_priority_niche_id(cfg, NICHES), "film")

    def test_falls_back_to_highest_weight(self):
        # No explicit setting -> highest-weighted niche ("ai", weight 3.0).
        self.assertEqual(st.resolve_priority_niche_id({}, NICHES), "ai")

    def test_empty_when_no_niches(self):
        self.assertEqual(st.resolve_priority_niche_id({}, []), "")


class TestEndToEndRun(unittest.TestCase):
    """Exercise run() against a temp config + cache and a known candidate set."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trendvane-run-")
        os.environ["TRENDVANE_DATA"] = self.tmp
        # Rebind the module paths to the fresh temp dir.
        st.MEMORY = Path(self.tmp) / "memory"
        st.CACHE = Path(self.tmp) / "cache"
        for d in (st.MEMORY, st.CACHE):
            d.mkdir(parents=True, exist_ok=True)

        cfg = {
            "trends_per_day": 2,
            "min_score_for_pick": 1,  # keep the threshold low so picks survive in tests
            "priority_niche_id": "ai",
            "scoring_weights": st.DEFAULT_SCORING,
            "niches": NICHES,
            "brand_safe_exclusions": {"blocked_topics": ["casino"]},
        }
        (st.MEMORY / "my_niches.json").write_text(json.dumps(cfg), encoding="utf-8")
        # Point common.load_niches() at our temp config too.
        import common
        common.MEMORY = st.MEMORY

        now = datetime.now(timezone.utc)
        today = datetime.now().strftime("%Y%m%d")
        candidates = [
            make_member(title="Claude llm agent ships new model", raw_text="ai agent",
                        mention_count=500, timestamp=_iso(now)),
            make_member(title="Cinematography color grading b-roll guide", raw_text="film",
                        platform="YouTube", source="youtube", mention_count=300, timestamp=_iso(now)),
            make_member(title="Casino betting bonanza", raw_text="gambling",
                        mention_count=900, timestamp=_iso(now)),
        ]
        (st.CACHE / f"raw_test_{today}.json").write_text(json.dumps(candidates), encoding="utf-8")

    def test_run_filters_picks_and_forces_priority(self):
        picks = st.run()
        self.assertTrue(picks)
        titles = " ".join(p["canonical_title"].lower() for p in picks)
        # Brand-safe filter removed the casino candidate.
        self.assertNotIn("casino", titles)
        # The priority (AI) niche is represented in the picks.
        self.assertIn("ai", {p["matched_niche_id"] for p in picks})
        # Respects trends_per_day = 2.
        self.assertLessEqual(len(picks), 2)


if __name__ == "__main__":
    unittest.main()

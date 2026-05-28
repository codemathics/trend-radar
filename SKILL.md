---
name: trend-radar
description: Find what's actually working across TikTok, Instagram, YouTube, and X every morning. Log trends to Notion, generate shootable 45–90s content briefs (hook, script, shot list, audio, caption, hashtags) tuned to your niches and voice. Invoked daily by scheduled task or on-demand. Politics and alcohol/drugs/gambling filtered out.
---

# Trend Radar

You are the user's trend research and content ideation co-pilot. Your job: surface trends that are *actually* rising in their niches, then hand them 3 shootable briefs every morning.

## Setup (first-time only)

Before using this skill, copy and fill in your config files:

```bash
cp memory/notion_config.example.json memory/notion_config.json
cp memory/secrets.example.json memory/secrets.json
```

Edit `memory/my_niches.json` to match your content niches, weights, and brand-safe filters.
Edit `memory/voice_examples.md` to match your voice and writing style.

## When invoked

1. **Read these files first**, in this order:
   - `memory/my_niches.json`, weighted taxonomy, brand-safe filters, scoring weights
   - `memory/voice_examples.md`, your tone, voice rules, banned phrases
   - `memory/notion_config.json`, Notion data source IDs for writes
   - `templates/brief_template.md`, exact spec for the brief output
   - `templates/hook_patterns.md`, hook archetype library, rotation rules
   - `templates/script_structures.md`, 45/60/90s beat sheets
   - `memory/used_hooks.json`, last 14 days of hooks used (for rotation), if it exists
   - `cache/seen_trends.json`, 30-day dedup cache, if it exists

2. **Run Tier 1 fetchers** by calling `python3 scripts/run_all.py`. Sources that work with zero setup (these are the defaults):
   - Hacker News (public API)
   - Reddit (public JSON endpoints, hits all niche subreddits)
   - TikTok Creative Center (public endpoints, trending hashtags + sounds)

   Optional sources, automatically used IF a key is present in `memory/secrets.json`, silently skipped otherwise (no failure):
   - YouTube Data API (needs `YT_API_KEY`)
   - Product Hunt (needs `PH_TOKEN`)
   - Google Trends (needs `pytrends` pip installed)

3. **Score every candidate** with `scripts/score_trends.py`:
   - niche_fit × 0.40 + velocity × 0.25 + cross_platform × 0.15 + recency × 0.10 + originality × 0.10
   - Apply niche weights from `my_niches.json`
   - Drop anything matching `brand_safe_exclusions`

4. **Cluster duplicates** across platforms; same trend appearing on TikTok + X + HN = one entry with `platforms: [TikTok, X, HN]`.

5. **If fewer than 3 trends score ≥ 60**, escalate to Tier 2 via Claude in Chrome:
   - Check `mcp__Claude_in_Chrome__list_connected_browsers`. If none, log a warning and proceed with what Tier 1 gave you.
   - Otherwise, `select_browser`, get tab context, and `navigate` to:
     - `https://x.com/explore/tabs/for-you`, read trending topics
     - `https://www.instagram.com/explore/`, sample top reels
   - For each trending item, use `get_page_text` to pull the surface text. Add new candidates to the cluster set and re-run scoring.

6. **Pick the top 3.** Force at least one to be in the user's highest-weighted niche when available.

7. **For each of the 3, generate a content brief:**
   - 3 hook variants (rotating archetypes from `used_hooks.json`)
   - Script length picked by trend complexity (45/60/90s)
   - Beat-by-beat script with timestamps
   - Shot list / storyboard description
   - Trending audio link (or 2 alternatives)
   - Caption variants per platform (TikTok, IG, YT, X)
   - Hashtag stack per platform (3-tier: big / mid / niche)

8. **MANDATORY voice audit before any Notion write.** For every field of every brief (Trend, Hook Variants, Script, Shot List, Caption, Hashtags, page body content):
   - Apply the voice rules from `memory/voice_examples.md`.
   - Search for `—` (U+2014 em dash) and `–` (U+2013 en dash) in prose. Allow en dashes ONLY inside timestamp ranges like `0:00–0:03`; anywhere else, rewrite using a comma, period, line break, or two sentences.
   - Search for AI-tell phrases: delve, dive into, elevate, harness, unlock, seamless, robust, transform your workflow, in today's fast-paced world, let's dive in, game-changing, revolutionary, embark on, navigate the landscape. Rewrite anything that hits.
   - Verify each caption ends with a question or engagement prompt.
   - Verify the 3 hook variants use 3 different archetypes, and at least one differs from any archetype used in the last 2 days per `memory/used_hooks.json`.
   - If any check fails, fix and re-audit. Do NOT push until clean.

9. **Push to Notion** via the `notion-create-pages` MCP tool. **FILL EVERYTHING RULE**: populate every property AND the page body, so the table view is informative and the full brief is also readable as one continuous page.
   - Parent: `data_source_id` from `memory/notion_config.json` (`databases.trend_radar.data_source_id`).
   - **Properties to fill on every write**: Trend, Date Spotted, Platforms, Category, Velocity, Score, Time-to-stale, Status, Trending Audio, Hook Variants, Script, Shot List, Caption, Hashtags, Source URLs, Reference Clips, My Take.
   - **Leave empty (fill manually after posting)**: Posted URL, Performance.
   - **Page body (the brief, in readable form)**: the chosen hook in a callout, all 3 hook variants, the timestamped script in a code block, numbered shot list, per-platform captions with bold headers, per-platform hashtags, why-this-trend context, source URLs, reference clips, my take.
   - Status = `New`.
   - Log every hook to the Hook Library DB (`databases.hook_library.data_source_id`) with Archetype + Niche + Used Date.
   - Update `memory/used_hooks.json` and `cache/seen_trends.json`.

10. **Post the chat briefing** in the format shown below + save to `briefings/YYYY-MM-DD.md`.

## Briefing format

```
🌅 trend radar, {day}, {date}

#1  {trend name} (score: {N}, {velocity emoji} {velocity label})
    platforms: {list} · category: {niche} · time-to-stale: ~{N} days
    hook: "{top hook variant}"
    → full brief in notion

#2  ...

#3  ...

🗑  skipped {N} other trends (mostly {reason}).
```

## Hard rules

- **Never** generate trends in: politics, alcohol/drugs/gambling, or anything matching `brand_safe_exclusions` in `my_niches.json`.
- **Never** reuse a hook archetype 2 days in a row.
- **Never** recommend audio you can't link to (verify the TikTok sound URL resolves).
- **Always** caption-first scripts, assume viewer has sound off.
- **Always** prefer rising velocity over peak volume. A trend at 500 mentions doubling daily beats a trend at 50k that's flat.
- **Always** force one top-weighted niche trend per day when available. If none qualifies, log why and move on.
- **Always** apply the voice rules from `memory/voice_examples.md` to every output.

## On-demand mode

If invoked outside the schedule (the user asks "what's trending today?" or "find me a trend on X topic"):
- Skip the scheduled-task formatting
- Take the user's topic constraint into account
- Output 1–3 briefs based on what they asked for
- Still push to Notion unless told otherwise

## Failure modes to watch

- **TikTok scraper blocked** → log warning, continue with other sources, note in briefing.
- **Notion write fails** → save brief to `briefings/YYYY-MM-DD.md` and surface in chat with `[NOTION SYNC FAILED]` flag.
- **Less than 3 trends meet score ≥ 60 even after Tier 2** → deliver what you have, be honest about it, don't pad with noise.
- **Voice samples missing** → use the default voice from `script_structures.md` and flag in briefing.

## Files this skill writes

- `briefings/YYYY-MM-DD.md`, daily archive
- `cache/seen_trends.json`, rolling 30-day dedup
- `cache/picks_YYYYMMDD.json`, the day's scored picks
- `cache/notion_payload_YYYYMMDD.json`, the payload sent to Notion
- `memory/used_hooks.json`, last 14 days of hooks (for archetype rotation)
- Notion `Trend Radar` database, 3 rows per day
- Notion `Hook Library` database, every hook generated, for future dedup

## End-to-end command sequence

```bash
cd /path/to/trend-radar
# 1. Fetch + score (writes cache/picks_YYYYMMDD.json)
python3 scripts/run_all.py
```

Then, in the skill (Claude):
1. Read `cache/picks_YYYYMMDD.json`.
2. For each pick, generate the brief inline using `templates/brief_template.md` and `memory/voice_examples.md` as the voice source. Self-audit before writing.
3. Call `mcp__<notion-mcp-id>__notion-create-pages` with the data source ID from `memory/notion_config.json` (`databases.trend_radar.data_source_id`). One page per pick.
4. Log each hook to the Hook Library DB.
5. Save `briefings/YYYY-MM-DD.md` with the daily summary.
6. Post the briefing in chat using the format above.

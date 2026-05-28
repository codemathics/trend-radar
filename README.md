# Trend Radar — Claude Code Skill

A Claude Code skill that runs every morning, fetches what's actually trending across HackerNews, Reddit, TikTok, YouTube, Product Hunt, and Google Trends, scores each trend against your content niches, and drops 3 shootable video briefs into a Notion database — complete with hooks, timestamped scripts, shot lists, captions, and hashtag stacks.

Built to be cloned and configured for any creator. All the personalization lives in a handful of JSON and Markdown files.

---

## Table of Contents

- [How it works](#how-it-works)
- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Setup](#setup)
  - [1. Clone the repo](#1-clone-the-repo)
  - [2. Install Python dependencies](#2-install-python-dependencies)
  - [3. Configure your niches](#3-configure-your-niches)
  - [4. Write your voice profile](#4-write-your-voice-profile)
  - [5. Set up Notion](#5-set-up-notion)
  - [6. Add API keys (optional)](#6-add-api-keys-optional)
  - [7. Install the skill in Claude Code](#7-install-the-skill-in-claude-code)
- [Running the skill](#running-the-skill)
  - [Daily scheduled run](#daily-scheduled-run)
  - [On-demand](#on-demand)
- [Understanding the output](#understanding-the-output)
- [Scoring system](#scoring-system)
- [Hook rotation](#hook-rotation)
- [File structure](#file-structure)
- [Customization reference](#customization-reference)
- [Adding a new data source](#adding-a-new-data-source)
- [Failure modes](#failure-modes)

---

## How it works

The skill runs in two stages:

**Stage 1 — Python fetchers** (runs in your terminal)

```bash
python3 scripts/run_all.py
```

Six fetchers hit their respective APIs and public endpoints, normalize every item into the same shape, and write raw candidate lists to `cache/`. The scoring engine then clusters cross-platform duplicates, applies your niche weights and brand-safe filters, and picks the top 3. The picks land in `cache/picks_YYYYMMDD.json`.

**Stage 2 — Claude generates and publishes** (runs inside Claude Code)

Claude reads the picks file, generates a full content brief for each trend in your voice (using `memory/voice_examples.md`), self-audits for em dashes and AI-tell phrases, and pushes everything to your Notion database via the Notion MCP tool. It also saves a local archive to `briefings/YYYY-MM-DD.md` and posts a summary to the chat.

---

## What you get

For each of the 3 daily trend picks, Claude produces:

| Field | What it contains |
|---|---|
| **Trend** | A one-line, lowercase framing of the trend |
| **Hook Variants** | 3 hooks from different archetypes, ranked best to worst |
| **Script** | Beat-by-beat 45/60/90s script with timestamps, VO lines, and visual cues |
| **Shot List** | Scene-by-scene visual direction assuming a solo shoot |
| **Trending Audio** | A direct TikTok/IG sound link in the right category |
| **Captions** | Platform variants for TikTok, Instagram, YouTube Shorts, and X |
| **Hashtags** | 3-tier stacks (broad / mid / niche) per platform |
| **Source URLs** | Raw links from the fetcher cluster |
| **Reference Clips** | The actual viral posts driving the trend |
| **Score** | 0–100 composite score from the scoring engine |
| **Velocity** | Rising / Peaking / Fading |
| **Time-to-stale** | How long before the window closes |

Everything lands in Notion as both table properties (so your database view is filled) and as a full-length page body (so you can read it top to bottom without opening the properties panel).

---

## Requirements

- **Claude Code** — [claude.ai/code](https://claude.ai/code) or the CLI (`npm install -g @anthropic-ai/claude-code`)
- **Notion MCP** configured in your Claude Code setup (see [Step 5](#5-set-up-notion))
- **Python 3.10+**
- A Notion workspace with two databases: `Trend Radar` and `Hook Library` (templates below)

Optional (improves results but not required):
- YouTube Data API v3 key
- Product Hunt developer token

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/codemathics/trend-radar.git
cd trend-radar
```

### 2. Install Python dependencies

The only external dependency is `pytrends` for Google Trends. All other fetchers use Python's standard library.

```bash
pip install -r requirements.txt
```

If you're on a system Python (macOS, Ubuntu), add `--break-system-packages`:

```bash
pip install -r requirements.txt --break-system-packages
```

Test that the fetchers can run:

```bash
python3 scripts/run_all.py
```

You should see log output ending with `N picks ready for brief generation`. If a source fails (e.g., TikTok rate-limiting), it logs a warning and continues — one dead source does not stop the run.

### 3. Configure your niches

Copy the example and edit it:

```bash
cp memory/my_niches.json memory/my_niches.json   # already exists — edit it directly
```

Open `memory/my_niches.json`. The key fields:

```json
{
  "owner": "your-name",
  "niches": [
    {
      "id": "ai",
      "label": "AI / LLMs / Models",
      "weight": 3.0,
      "keywords": ["AI", "LLM", "Claude", "agent", "..."],
      "sources_priority": ["hackernews", "reddit_ai", "youtube"],
      "subreddits": ["LocalLLaMA", "ChatGPT", "ClaudeAI"]
    }
  ]
}
```

**`weight`** — how much to boost this niche's score relative to others. In the default config, AI is 3x, Product Design and Filmmaking are 2x, and everything else is 1x. Adjust to match your actual posting priorities.

**`keywords`** — the terms the scoring engine matches against trend text. Be specific. "AI coding" catches more signal than just "AI".

**`subreddits`** — which subreddits the Reddit fetcher hits for this niche.

**`brand_safe_exclusions`** — at the bottom of the file, a list of blocked topics (politics, alcohol, gambling) and regex patterns. Add anything you'd never want to post about.

**`scoring_weights`** — the five scoring dimensions and their weights:

| Dimension | Default weight | What it measures |
|---|---|---|
| `niche_fit` | 0.40 | How well the trend matches your keywords and niche weights |
| `velocity` | 0.25 | How fast the trend is growing (rank movement, mention percentile) |
| `cross_platform` | 0.15 | Bonus for appearing on multiple platforms simultaneously |
| `recency` | 0.10 | How fresh the content is (7-day decay) |
| `originality` | 0.10 | Penalty for trends you've already covered in the last 30 days |

### 4. Write your voice profile

```bash
cp memory/voice_examples.md memory/voice_examples.md   # already exists — fill it in
```

Open `memory/voice_examples.md`. This is the most important file for output quality. It tells Claude how you actually write — your opening patterns, sentence rhythm, casing rules, what you never say, emoji habits, and real examples from your posts.

The template has a section-by-section guide. The more real examples you paste in (actual captions from your posts), the closer the briefs will sound like you.

Claude reads this file before generating every brief and audits every line against your rules before pushing to Notion.

### 5. Set up Notion

You need two databases in Notion before the skill can write anything.

**Create the Trend Radar database** with these properties:

| Property name | Type |
|---|---|
| Trend | Title |
| Date Spotted | Date |
| Platforms | Multi-select |
| Category | Select (AI, Product Design, Filmmaking, Tech, How-to, Lifestyle, Business) |
| Velocity | Select (Rising, Peaking, Fading) |
| Score | Number |
| Time-to-stale | Select (< 3 days, 1 week, 2+ weeks) |
| Status | Select (New, Filming, Posted, Archived) |
| Trending Audio | URL |
| Hook Variants | Text |
| Script | Text |
| Shot List | Text |
| Caption | Text |
| Hashtags | Text |
| Source URLs | Text |
| Reference Clips | Text |
| My Take | Text |
| Posted URL | URL |
| Performance | Text |

**Create the Hook Library database** with these properties:

| Property name | Type |
|---|---|
| Hook | Title |
| Archetype | Select |
| Niche | Select |
| Used Date | Date |

**Connect the Notion MCP** to Claude Code. Follow the [Notion MCP setup guide](https://github.com/makenotion/notion-mcp-server) to get the integration token, then add it to your Claude Code MCP config. The skill uses the Notion MCP tool (`notion-create-pages`) to write — it does not use the Notion REST API directly.

**Fill in your Notion config:**

```bash
cp memory/notion_config.example.json memory/notion_config.json
```

Edit `memory/notion_config.json` with your workspace details:

```json
{
  "workspace_user": {
    "name": "Your Name",
    "email": "you@example.com",
    "user_id": "your-notion-user-id"
  },
  "parent_page": {
    "title": "Trend Radar",
    "url": "https://www.notion.so/your-parent-page-url",
    "id": "your-parent-page-id"
  },
  "databases": {
    "trend_radar": {
      "title": "Trend Radar",
      "url": "https://www.notion.so/your-trend-radar-db-url",
      "data_source_id": "your-trend-radar-data-source-id",
      "data_source_url": "collection://your-trend-radar-data-source-id"
    },
    "hook_library": {
      "title": "Hook Library",
      "url": "https://www.notion.so/your-hook-library-db-url",
      "data_source_id": "your-hook-library-data-source-id",
      "data_source_url": "collection://your-hook-library-data-source-id"
    }
  }
}
```

To find your database's `data_source_id`, open the database in Notion, click the three-dot menu, copy the link, and extract the UUID from the URL.

`notion_config.json` is gitignored — it will not be committed.

### 6. Add API keys (optional)

```bash
cp memory/secrets.example.json memory/secrets.json
```

Edit `memory/secrets.json`:

```json
{
  "YT_API_KEY": "AIza...",
  "PH_TOKEN": "your-product-hunt-token"
}
```

`secrets.json` is gitignored.

**Without keys:** HackerNews, Reddit, TikTok Creative Center all work with zero auth. You still get solid coverage.

**With keys:**
- `YT_API_KEY` — enables the YouTube Data API v3 fetcher. Get one at [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → YouTube Data API v3.
- `PH_TOKEN` — enables the Product Hunt fetcher. Get one at [api.producthunt.com/v2/docs](https://api.producthunt.com/v2/docs).

You can also pass keys as environment variables — the skill checks `os.environ` before `secrets.json`.

### 7. Install the skill in Claude Code

Copy `SKILL.md` into your Claude Code skills directory:

```bash
cp SKILL.md ~/.claude/skills/trend-radar.md
```

Or point Claude Code at the repo's skill file directly by adding it to your project's `.claude/` folder.

The skill is then available in Claude Code. You can invoke it on-demand or schedule it to run automatically each morning (see below).

---

## Running the skill

### Daily scheduled run

The intended workflow is a 5:30am Python fetch → 6:00am Claude brief.

**Step 1 — Schedule the Python fetchers** (cron or any scheduler):

```bash
# Example cron entry — runs at 5:30am every day
30 5 * * * cd /path/to/trend-radar && python3 scripts/run_all.py
```

**Step 2 — Schedule the Claude skill** using Claude Code's `/schedule` command or the built-in scheduled tasks feature. Set it to run at 6:00am and invoke the trend-radar skill.

Claude picks up the picks file from Step 1, generates the briefs, and pushes to Notion.

### On-demand

You can ask for briefs at any time inside a Claude Code session:

> "what's trending today?"

> "find me a trend on AI agents"

> "run trend radar for filmmaking only"

Claude skips the schedule formatting, applies any topic constraint you give it, and still pushes to Notion unless you tell it not to.

You can also re-run scoring without re-fetching (useful for testing niche config changes):

```bash
python3 scripts/run_all.py --score
```

---

## Understanding the output

After a successful run, Claude posts a briefing in chat:

```
🌅 trend radar, thursday, may 29

#1  cursor's agent mode is shipping real code now (score: 84, 📈 Rising)
    platforms: HackerNews, Reddit · category: AI · time-to-stale: < 3 days
    hook: "stop prompting. cursor's agent is coding for you now."
    → full brief in notion

#2  ...

#3  ...

🗑  skipped 12 other trends (mostly fading tech / politics filtered).
```

The full brief for each pick is in Notion as a page. The table view has all properties filled. The page body reads top to bottom: hook, script, shot list, captions, hashtags, context, sources.

Local archive files are saved to `briefings/YYYY-MM-DD.md` whether or not the Notion write succeeds.

---

## Scoring system

Every trend candidate goes through this pipeline:

```
raw candidates
    → brand-safe filter (drop blocked topics)
    → cross-platform clustering (Jaccard token similarity)
    → 5-dimension scoring
    → top 3 selection (with niche priority enforcement)
```

**Scoring formula:**

```
final_score = (niche_fit × 0.40)
            + (velocity  × 0.25)
            + (cross_platform × 0.15)
            + (recency   × 0.10)
            + (originality × 0.10)
```

Each dimension is 0–1 before weighting. The final score is multiplied by 100. Only trends scoring ≥ 60 qualify as picks.

**Niche fit** is computed by counting keyword hits in the trend's title and raw text, then multiplying by the niche's weight. A single AI-niche match outscores multiple matches in an unweighted niche.

**Velocity** is approximated without time-series data:
- TikTok: rank movement in the Creative Center trending list
- Reddit/HackerNews: percentile of mention count within today's source batch
- YouTube: percentile of view count within today's source batch

**Cross-platform** gives a bonus for trends appearing on more than one source simultaneously — these tend to have broader longevity.

**Recency** decays linearly over 7 days. Content older than a week scores 0.

**Originality** penalizes trends whose keywords overlap with anything you've already covered in the past 30 days (tracked in `cache/seen_trends.json`).

**Selection:** the top 3 qualifying clusters are chosen. At least one slot is reserved for your highest-weighted niche (by default, AI) when a qualifying trend exists in it. The remaining slots avoid duplicate categories unless there's no other option.

---

## Hook rotation

The skill tracks which hook archetypes were used each day in `memory/used_hooks.json`. The rules:

- Never use the same archetype 2 days in a row
- Never use the same archetype 3 times in a 7-day window
- If a trend strongly fits one archetype (e.g., a breaking product launch fits Bold Claim), override rotation but log it

The 7 archetypes available, defined in `templates/hook_patterns.md`:

| Archetype | Best for |
|---|---|
| Pattern Interrupt | Product design, AI, tech |
| Bold Claim / Hot Take | AI, tech, product design |
| Question Hook | How-to, AI, filmmaking |
| POV / Cold Open | Lifestyle, filmmaking, how-to |
| Stat Shock | Business, AI, tech |
| Direct Address / Callout | Product design, AI, how-to, filmmaking |
| Demonstration / Show-Don't-Tell | Filmmaking, AI, product design |

Every brief gets 3 variants from 3 different archetypes.

---

## File structure

```
trend-radar/
├── SKILL.md                      # The Claude Code skill definition
├── requirements.txt              # Python deps (just pytrends)
│
├── scripts/
│   ├── common.py                 # Shared utils, normalized TrendCandidate shape
│   ├── run_all.py                # Orchestrator: runs fetchers then scoring
│   ├── score_trends.py           # Scoring + clustering engine
│   ├── fetch_hackernews.py       # HN top/new stories (public API)
│   ├── fetch_reddit.py           # Reddit JSON endpoints (no auth)
│   ├── fetch_tiktok.py           # TikTok Creative Center (public)
│   ├── fetch_youtube.py          # YouTube Data API (needs YT_API_KEY)
│   ├── fetch_producthunt.py      # Product Hunt API (needs PH_TOKEN)
│   ├── fetch_google_trends.py    # Google Trends via pytrends
│   └── push_to_notion.py         # Notion write helpers (used by Claude)
│
├── templates/
│   ├── brief_template.md         # Field-by-field spec for briefs
│   ├── hook_patterns.md          # 7 hook archetypes with examples
│   └── script_structures.md      # 45/60/90s beat sheets
│
├── memory/
│   ├── my_niches.json            # Your niches, weights, keywords, filters
│   ├── voice_examples.md         # Your voice profile (fill this in)
│   ├── notion_config.json        # Your Notion workspace IDs (gitignored)
│   ├── notion_config.example.json # Template for notion_config.json
│   ├── secrets.json              # API keys (gitignored)
│   ├── secrets.example.json      # Template for secrets.json
│   └── used_hooks.json           # Last 14 days of hook archetype history
│
├── cache/                        # Gitignored. Written by the fetchers.
│   ├── raw_hackernews_YYYYMMDD.json
│   ├── raw_reddit_YYYYMMDD.json
│   ├── ...
│   ├── picks_YYYYMMDD.json       # The day's top 3 with scores
│   └── seen_trends.json          # 30-day dedup history
│
└── briefings/                    # Gitignored. Written by Claude.
    └── YYYY-MM-DD.md             # Daily brief archive
```

---

## Customization reference

### Change your niche weights

In `memory/my_niches.json`, edit the `weight` field on any niche. A niche with weight 3.0 gets 3x the scoring bonus of a niche with weight 1.0. There is no enforced maximum, but weights above 4.0 will almost always force that niche into the top pick regardless of other signals.

### Add a new niche

Add a new object to the `niches` array in `memory/my_niches.json`:

```json
{
  "id": "gaming",
  "label": "Gaming",
  "weight": 1.5,
  "keywords": ["gaming", "game dev", "Unity", "Unreal", "Steam", "indie game"],
  "sources_priority": ["reddit_gaming", "youtube", "tiktok"],
  "subreddits": ["gamedev", "gaming", "indiegaming"]
}
```

The scoring engine picks it up on the next run with no code changes.

### Change the scoring weights

In `memory/my_niches.json`, edit `scoring_weights`. They must sum to 1.0:

```json
"scoring_weights": {
  "niche_fit": 0.40,
  "velocity": 0.25,
  "cross_platform": 0.15,
  "recency": 0.10,
  "originality": 0.10
}
```

If velocity is most important to you (you only want fast-rising trends), bump it to 0.40 and trim `niche_fit` down.

### Change the minimum score threshold

In `scripts/score_trends.py`, line 37:

```python
MIN_SCORE_FOR_PICK = 60
```

Lower it to get more picks even from weaker signal days. Raise it to only publish when you have strong trending content.

### Change the dedup window

In `scripts/score_trends.py`, line 46:

```python
SEEN_TRENDS_WINDOW_DAYS = 30
```

Lower it to allow revisiting trends sooner.

---

## Adding a new data source

Every fetcher in `scripts/` follows the same contract. To add a new source:

1. Create `scripts/fetch_myplatform.py`
2. Export a `fetch()` function that returns a list of dicts (or `TrendCandidate` objects) matching the normalized shape:

```python
from common import TrendCandidate, now_iso

def fetch() -> list[TrendCandidate]:
    items = []
    # ... your fetching logic ...
    items.append(TrendCandidate(
        source="myplatform",
        platform="MyPlatform",
        title="Trend title",
        url="https://...",
        raw_text="Description or body text for keyword matching",
        mention_count=1234,     # views, upvotes, comments — anything comparable
        timestamp=now_iso(),
        extra={}                # any platform-specific fields
    ))
    return items
```

3. Add it to the `fetchers` list in `scripts/run_all.py`:

```python
("myplatform", "fetch_myplatform"),
```

The scoring engine picks it up automatically. If your source needs an API key, read it with `env("MY_KEY")` from `common.py` — it checks `os.environ` then `memory/secrets.json`.

---

## Failure modes

The skill is designed to degrade gracefully. These are the expected failure states and what happens:

| Failure | Behavior |
|---|---|
| A fetcher is blocked or rate-limited | Logged as a warning, run continues with other sources |
| Fewer than 3 trends score ≥ 60 | Claude delivers what it has, flags the count in the briefing |
| Claude in Chrome unavailable (Tier 2 escalation) | Logged, skipped — Tier 1 results are used |
| Notion write fails | Brief saved to `briefings/YYYY-MM-DD.md`, flagged as `[NOTION SYNC FAILED]` in chat |
| `voice_examples.md` is empty | Claude falls back to `script_structures.md` defaults, flags it in the briefing |
| `notion_config.json` missing | Claude skips the Notion write, saves locally, reports the issue |

---

## Credits

Built by [@codemathics](https://github.com/codemathics) as a personal content workflow tool, open-sourced as a template for any creator who wants to automate their trend research and brief generation with Claude Code.

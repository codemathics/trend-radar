# Content Brief, Template

This is the exact structure every brief should produce. The skill generates one of these per pick, then push_to_notion.py writes the fields into the Trendvane database.

**Layout rule (fill everything, both places):**
- Properties (table view): Trend, Date Spotted, Platforms, Category, Velocity, Score, Time-to-stale, Status, Trending Audio, Hook Variants, Script, Shot List, Caption, Hashtags, Source URLs, Reference Clips, My Take. Every text property gets filled.
- Page body (the brief): top hook callout, hook variants, script, shot list, captions, hashtags, why-this-trend, source URLs, reference clips, my take. Same content as properties but formatted for reading top to bottom.
- Leave empty (manual fill after posting): Posted URL, Performance.

The duplication is on purpose, so the table view is informative AND the page reads as one continuous brief.

**Voice rules:**

Casing and punctuation come from the user's voice profile (`memory/voice_examples.md`), not from this template. Follow whatever the profile specifies. **If no profile is set, default to sentence case with natural punctuation.** The examples below are written in one creator's lowercase voice purely to show structure, match the user's profile, not the casing of these samples.

The one rule that always applies regardless of profile: **no AI-tell phrasing** ("delve into", "elevate", "harness", "unlock", "seamless", "robust", "in today's fast-paced world", "let's dive in"). The skill self-audits every brief for tell-words before writing to Notion, and for any punctuation the user's profile bans (e.g. em dashes, if they asked for none). Strip them, rewrite the sentence, push.

---

## Field-by-field spec

### 1. Trend (title), TITLE
One sharp line in the user's voice. ~6–10 words. Frame it like a hook itself.

**Example (sentence-case default):** `Agents are starting to use your computer for you`

(The casing follows the user's profile, this example uses the sentence-case default. It should sound like a thought you'd say out loud.)

### 2. Hook Variants (RICH_TEXT)
Exactly 3 hooks, each from a DIFFERENT archetype, ranked best to worst.

**Format:**
```
1. [pattern interrupt] stop trying to prompt your way out of this.
2. [bold claim] cursor just did what every "AI IDE" promised in 2024.
3. [stat shock] 9 out of 10 agents fail at this one thing.
```

Always include the archetype label in brackets. Skill will log them to Hook Library DB.

### 3. Script, RICH_TEXT
Pick 45 / 60 / 90s based on trend complexity (rule of thumb in script_structures.md).

**Format:**
```
length: 60s
hook: hook variant #1 (read above)

0:00–0:03  hook        on-screen text: "stop trying to prompt your way out of this."
0:03–0:10  setup       me at desk, screen-rec rolling: "i've been letting cursor drive..."
0:10–0:35  payoff      [the actual demo / take]
0:35–0:50  twist       my pov: "but here's where it gets weird,"
0:50–0:57  recap       single line summary
0:57–1:00  cta         "would you let it ship to prod? comment yes or no."
```

Every beat must have a timestamp range, a label (hook/setup/payoff/twist/recap/cta), and either a visual cue or VO line.

### 4. Shot List, RICH_TEXT
Scene-by-scene visual direction. Match the script timestamps.

**Format:**
```
shot 1 (0:00–0:03), extreme close-up: terminal cursor blinking. snap zoom out on hit beat.
shot 2 (0:03–0:10), talking head, 35mm, 3/4 angle, key from window. handheld for energy.
shot 3 (0:10–0:35), screen recording sped 4x, cursor highlighted. cut to face every 4s.
shot 4 (0:35–0:50), over-the-shoulder of screen, dramatic music swell on reveal.
shot 5 (0:50–0:57), back to talking head, eye-line down at desk, more reflective tone.
shot 6 (0:57–1:00), title card with question, hold 3s.
```

Assume: solo shoot, iPhone or mirrorless, no crew. No "B-roll of city skyline" or any direction that requires production days.

### 5. Trending Audio, URL
A direct link to a TikTok sound (or IG sound) that's currently trending in this trend's category. If the pick came from TikTok with a clip_id in `extra`, use that. Otherwise propose one based on category vibe.

**Format:** `https://www.tiktok.com/music/<sound-slug>-<id>`

If no audio fits, leave empty and write a 1-line audio direction in the Caption field instead.

### 6. Caption, RICH_TEXT
Per-platform variants, in the user's voice (casing per their profile; sentence case by default).

**Format:**
```
tiktok: agents are using my computer now and i kinda love it. should i be worried?
instagram: 6 months ago i thought ai agents were vaporware. today one of them shipped a feature for me. swipe for the receipts ↓
youtube shorts: how i let an ai agent run my computer for an entire workday, full breakdown.
x: agents using your computer isn't a demo anymore. quick thread on what changed this week ↓
```

### 7. Hashtags, RICH_TEXT
Per-platform 3-tier stack: big (broad reach) / mid (niche) / specific (signal).

**Format:**
```
tiktok: #ai #aiagents #productdesign | #aitools #vibecoding #cursor | #computeruse #anthropic #agenticui
instagram: #productdesign #design #ai | #designertools #figma #uxdesign | #productdesigner #designprocess #designsystem
youtube: #aiagents #cursor #productivity
x: (no hashtags, kills reach on X)
```

### 8. Source URLs, RICH_TEXT
Newline-separated list of the URLs in the cluster's `source_urls`. Max 5.

### 9. Reference Clips, RICH_TEXT
1–3 links to the actual viral posts driving this trend. Pull from the cluster members.

### 10. Date Spotted, DATE
Today.

### 11. Platforms, MULTI_SELECT
Union of platforms across cluster members.

### 12. Category, SELECT
One of: AI, Product Design, Filmmaking, Tech, How-to, Lifestyle, Business. From the scoring engine.

### 13. Velocity, SELECT
One of: Rising, Peaking, Fading. From the scoring engine.

### 14. Score, NUMBER
0–100. From the scoring engine.

### 15. Time-to-stale, SELECT
One of: < 3 days, 1 week, 2+ weeks. From the scoring engine.

### 16. Status, SELECT
Always `New` on initial write.

---

## What good looks like

A brief is shippable if you can read it, walk to your desk, and start filming inside 10 minutes without having to:
- Re-write any hook
- Figure out what each shot means
- Look up the trending sound
- Translate it into their voice (it's already in their voice)

If any of those is required, the brief failed.

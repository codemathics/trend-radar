# Script Structures, Trendvane

Three lengths. Each has a beat sheet the generator fills in. The engine picks length based on trend complexity (heuristic below).

**Picking length:**
- 45s → single insight, demo-heavy, visual punch. (Hot take, one tool, one tip.)
- 60s → balanced. Setup + payoff + twist. (Standard tutorial, opinion piece.)
- 90s → multi-beat narrative, case study, layered argument. (Build-along, breakdown, story.)

Default to 60s unless the trend obviously needs more or less.

---

## 45s Structure, "The Punch"

Use when there's ONE thing to land. Tight, fast, no filler.

```
0:00–0:03  HOOK         Pattern interrupt or visual demo
0:03–0:08  SETUP        One sentence: what's the trend, why it matters
0:08–0:35  THE POINT    The actual demo / take / build, visual-heavy
0:35–0:42  TWIST/POV    Your take or unexpected angle (1 line)
0:42–0:45  CTA          Soft close, comment / save / follow
```

**Pacing:** cut every 1.2–1.5s. On-screen text every 2–3s. No section longer than 8s without a visual change.

**Best for:** AI tool demos, design hot takes, filmmaking quick tips.

---

## 60s Structure, "The Balanced Build"

The default. Setup → payoff → twist → close.

```
0:00–0:03  HOOK         One of the 7 archetypes
0:03–0:10  CONTEXT      Why this trend, why now (1–2 sentences)
0:10–0:35  PAYOFF       The meat, demo, breakdown, walkthrough
0:35–0:50  TWIST        Unexpected angle, my POV, or where it fails
0:50–0:57  RECAP        Reinforce the one takeaway
0:57–1:00  CTA          Question to drive comments
```

**Pacing:** cut every 1.5–2s. B-roll layered over VO 50%+ of the time. On-screen captions ALWAYS, assume sound-off.

**Best for:** Product design tutorials, AI workflow shares, "tools I use" content.

---

## 90s Structure, "The Story"

Three-act. Use when the trend requires real explanation or a case study.

```
0:00–0:03  HOOK              Strongest archetype available
0:03–0:12  ACT 1: SETUP      The problem / the question / the stakes
0:12–0:40  ACT 2A: ATTEMPT   What you tried / what most people do
0:40–1:05  ACT 2B: REVERSAL  Where it broke / the better way
1:05–1:25  ACT 3: PAYOFF     The full solution / the demo / the result
1:25–1:33  TWIST/REFLECT     What this means for the viewer
1:33–1:30  CTA               Specific ask (save, follow, link in bio)
```

**Pacing:** cut every 2–3s. Slow down for the reveal beat (1:05–1:25). Music shift at 0:40 and 1:25 to mark act transitions.

**Best for:** Build-alongs, case studies, AI/filmmaking deep-dives, portfolio breakdowns.

---

## Universal pacing rules

1. **Caption-first thinking.** Assume sound is OFF. Burned-in captions, large text, high contrast.
2. **Visual change every 3s or less.** Static frames die.
3. **B-roll ratio ≥ 50%.** Face-only kills retention after 0:15.
4. **Pacing accelerator at midpoint.** Cuts get faster around the 50% mark.
5. **Sound design > music.** Whooshes, clicks, transitions sells the pacing.
6. **End on a question, not a "thanks for watching".** Drives comments.

---

## Variables the generator fills

For each script, the engine populates:

- `{trend_name}`, what's happening
- `{trend_why_now}`, velocity context (rising, peaking, etc.)
- `{niche_lens}`, which niche frames the take
- `{tool_or_subject}`, the specific thing being demo'd
- `{my_pov}`, the contrarian or sharp angle
- `{cta}`, platform-appropriate close
- `{audio_cue}`, trending sound or recommended track
- `{shot_cue_1..n}`, visual direction at each timestamp

---

## Voice rules

Casing, punctuation, and emoji are **not** fixed by this skill. They come from the user's voice profile in `memory/voice_examples.md`, so the output sounds like the person using it, not like a preset. If their profile says all lowercase and no em dashes, do that. If it says sentence case with em dashes, do that instead.

**If the user hasn't set a voice profile yet, default to:**
- **Sentence case** (capitalize the start of sentences and proper nouns/acronyms). This is the default everywhere.
- Natural, normal punctuation (em dashes allowed unless the profile bans them).
- No emoji unless the content clearly calls for it.

**The one rule that always applies, regardless of profile:** no AI-tell phrasing. Skip "delve into", "elevate", "navigate the landscape", "harness the power of", "transform your workflow", "in today's fast-paced world", "let's dive in", "unlock the potential", "robust solution", "seamless experience". This is about sounding human, which every voice wants.

Other voice defaults (the profile overrides any of these):
- First person, direct, slightly dry
- No corporate-speak
- One joke or sharp aside per 30s
- Never "Hey guys" or "What's up everyone"
- Sentences can run-on or fragment, match natural speech, not English-class grammar

# Hook Patterns, Trendvane

The first 3 seconds are everything. Every brief gets 3 hook variants drawn from these archetypes. The skill rotates archetypes so we don't burn the same pattern twice in a week.

Hooks are tagged by archetype + niche affinity. When generating, the engine picks the archetype best matched to the trend AND least recently used.

> The example hooks below are written in one creator's lowercase voice to illustrate each archetype's *structure*. Casing follows the user's voice profile (`memory/voice_examples.md`); the default when no profile is set is sentence case. Copy the shape of these hooks, not their casing.

---

## Archetype 1: Pattern Interrupt

Opens by violating expectation. Works when the trend has a counterintuitive angle.

**Structure:** `[Common assumption] / [Sharp reversal]`

**Examples:**
- "Stop using Figma plugins. There's a better way."
- "Everyone's wrong about AI agents."
- "I deleted 12 design apps yesterday. Here's why."
- "Your portfolio isn't the problem."

**Best for:** Product design, AI, tech. Less good for lifestyle.

---

## Archetype 2: Bold Claim / Hot Take

Stakes a position immediately. High engagement, comments + saves.

**Structure:** `[Specific entity] just [verb] [specific thing]`

**Examples:**
- "Sora 2 just killed the stock footage industry."
- "Cursor is doing to coding what Figma did to design."
- "Apple's new chip just made every M1 obsolete."
- "Notion just became the best AI app on my computer."

**Best for:** AI, tech, product design. Use sparingly, must be defensible.

---

## Archetype 3: Question Hook

Sets a curiosity gap the rest of the video closes.

**Structure:** `What if [provocative scenario]?` or `Why does [observation]?`

**Examples:**
- "What if your prototype could ship itself?"
- "Why do all AI demos look the same?"
- "What does a product designer actually do all day?"
- "What if Sora knew what scene you were in?"

**Best for:** How-to, AI, filmmaking. Works across categories.

---

## Archetype 4: POV / Cold Open

No setup. Drops you mid-action. Visual-first hook, almost no VO in first 2s.

**Structure:** `[Action already in progress] + minimal on-screen text`

**Examples:**
- (Screen recording, fast cuts) "POV: you found a Figma plugin that actually works."
- (Camera POV, walking into studio) "POV: you have 4 hours to ship a portfolio."
- (Hands typing in Cursor) "POV: you let AI write your design system."
- (Sliding camera across desk) "POV: this is what a 2026 design setup looks like."

**Best for:** Lifestyle, filmmaking, how-to. Highest aesthetic ceiling.

---

## Archetype 5: Stat Shock

A number you can't ignore. Numbers must be real.

**Structure:** `[Surprising stat] [punchy follow]`

**Examples:**
- "Apple just spent $1B training one model."
- "I shipped 14 designs in 3 hours with this stack."
- "98% of AI tools die in 6 months. These 3 won't."
- "$0 to $40k MRR in 90 days, without a single ad."

**Best for:** Business, AI, tech. Avoid in lifestyle.

---

## Archetype 6: Direct Address / Callout

Names the viewer's specific situation. Highest retention when the trend is niche.

**Structure:** `If you're a [specific role] and [specific pain], watch this.`

**Examples:**
- "If you're a designer using AI wrong, this is for you."
- "Filmmakers, you don't need a $4k camera anymore."
- "Junior designers, your portfolio is missing this one section."
- "If your AI agent keeps failing, it's not the model."

**Best for:** Product design, AI, how-to, filmmaking. Niche-targeted retention.

---

## Archetype 7: Demonstration / Show-Don't-Tell

The hook IS the demo. No words for the first 2 seconds. Visual must be the hook.

**Structure:** `[Striking visual demo for 2s] → [one-line context drop at 0:02]`

**Examples:**
- (Screen splits, AI generating design in real-time) "I gave Claude my brand guide..."
- (Time-lapse of edit) "60 seconds. 1 take. No edit."
- (Side-by-side: my work vs AI's) "Can you tell which one I made?"
- (Hand sketches → Figma render in seconds) "From paper to prototype in 30 seconds."

**Best for:** Filmmaking, AI, product design. The single highest performer on TikTok and Reels.

---

## Rotation rules

- Track last 14 days of hooks used (`memory/used_hooks.json`).
- Never use the same archetype 2 days in a row.
- Never use the same archetype 3 times in a 7-day window.
- If a trend STRONGLY fits one archetype (e.g., a hot product launch fits "Bold Claim"), override rotation but log it.

---

## Anti-patterns (do NOT generate these)

- "In this video, I'll show you...", burns the hook on meta-talk.
- "Hey guys, today we're going to...", instant scroll.
- Long throat-clearing setup ("So I was thinking about...").
- Generic questions with no specificity ("Have you ever wondered...").
- Hooks that don't deliver, the rest of the video must pay off the promise.

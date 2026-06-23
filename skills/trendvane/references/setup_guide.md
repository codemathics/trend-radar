# trendvane setup guide

this is the first-run onboarding flow. follow it when the main skill detects that trendvane isn't configured yet (no `notion_config.json`, or `my_niches.json` still has placeholder values), or when the user explicitly asks to set up / reconfigure.

get the user to a working daily trend briefing in one session. do as much automatically as possible - create databases, write config files, run commands. only ask the user for things you genuinely cannot figure out yourself (their content topics, their voice, their notion workspace).

be warm, plain, and specific. no jargon unless the user is clearly technical. when something will take a moment, say so.

**casing: everything you say to the user uses standard sentence casing** (capital at the start of sentences, proper nouns capitalized: Notion, YouTube, Product Hunt, etc.). The example messages quoted below are written in that style on purpose, mirror it. The all-lowercase style is only for the generated content governed by the user's voice profile, never for the skill speaking to the user.

---

## before you start

**find the two locations.**

- **CODE_DIR** = where this skill is installed (the folder its `SKILL.md` lives in). holds `scripts/`, `templates/`, `references/`, and the default config. confirm with `ls <CODE_DIR>/scripts/run_all.py`.
- **DATA_DIR** = where the user's config and data live, so updates can't wipe them. resolve it the way the scripts do:
  - if `$TRENDVANE_DATA` is set, that path
  - else if CODE_DIR is under `~/.claude/skills/`, then `~/.claude/trendvane/`
  - else (running from a clone) DATA_DIR == CODE_DIR

  create it if missing, with subfolders `memory/`, `cache/`, `briefings/`.

**run the state check.** run `python3 <CODE_DIR>/scripts/validate_setup.py` and read the output. it prints the resolved data dir and tells you what's already done so you can skip those steps.

tell the user what you found - something like "Looks like Python is ready and you've got Notion connected. I just need to create the databases and set up your niches."

---

## the setup steps

work through these in order. skip any step the validator already shows as passing. whenever you write a config file, write it into `<DATA_DIR>/memory/`, never into CODE_DIR (CODE_DIR gets replaced on skill updates).

---

### step 1 - python dependencies

if the validator flagged missing deps:

run `python3 -m pip install -r <CODE_DIR>/requirements.txt`

if that fails, try `python3 -m pip install -r <CODE_DIR>/requirements.txt --break-system-packages`

confirm by re-running the validator. if it still fails, tell the user exactly what to paste in their terminal.

---

### step 2 - notion mcp connection

before anything notion-related, check whether you have notion mcp tools available. look for tools with names containing `notion` in your available tool list.

**if notion mcp is connected:** tell the user and move to step 3.

**if not connected:** paste this to the user word for word (adjust the formatting to chat):

---
To connect Notion to Claude Code, you need to do three things:

**1. Create a Notion integration**
- Go to notion.so/my-integrations
- Click "New integration"
- Give it any name, e.g. "Trendvane"
- Under capabilities, check: Read content, Update content, Insert content
- Click Save
- Copy the "Internal Integration Token" (it starts with `secret_`)

**2. Add the Notion MCP to Claude Code**
- Open Claude Code settings
- Go to MCP Servers
- Click Add Server
- Set command to: `npx -y @notionhq/notion-mcp-server`
- Add an environment variable:
  - key: `OPENAPI_MCP_HEADERS`
  - value: `{"Authorization": "Bearer <paste your token here>", "Notion-Version": "2022-06-28"}`
- Save and restart Claude Code

**3. Authorize your Notion pages**
- Open Notion and go to any page you want the tool to access
- Click the three-dot menu → Connections → connect to your integration

Once you've done all three, come back and type `/trendvane` and I'll pick up here.

---

stop here and wait for the user to confirm before continuing to step 3.

after they confirm, verify you can see notion tools. if still not available, ask them to check that the mcp server restarted and that the token is correct.

---

### step 3 - create notion databases

you need to create two databases: trendvane and hook library.

**find a parent page.** ask: "Which Notion page should I create the databases inside? Paste the page URL, or just say 'create a new page' and I'll make one."

use `notion-search` to find the page by url or name if they gave one. extract the page id. if they want a new page, create one with `notion-create-pages` first.

**create the trendvane database.** use `notion-create-database` with the parent page id and these exact properties:

```
title property:        Trend         (type: title)
date property:         Date Spotted  (type: date)
multi_select:          Platforms     (options: TikTok, Instagram, YouTube, HackerNews, Reddit, Product Hunt, Google Trends, X)
select:                Category      (options: AI, Product Design, Filmmaking, Tech, How-to, Lifestyle, Business)
select:                Velocity      (options: Rising, Peaking, Fading)
number:                Score
select:                Time-to-stale (options: < 3 days, 1 week, 2+ weeks)
select:                Status        (options: New, Filming, Posted, Archived)
url:                   Trending Audio
rich_text:             Hook Variants
rich_text:             Script
rich_text:             Shot List
rich_text:             Caption
rich_text:             Hashtags
rich_text:             Source URLs
rich_text:             Reference Clips
rich_text:             My Take
url:                   Posted URL
rich_text:             Performance
```

**create the hook library database.** same parent page, with:

```
title property:   Hook
select:           Archetype  (options: Pattern Interrupt, Bold Claim, Question Hook, POV / Cold Open, Stat Shock, Direct Address, Demonstration)
select:           Niche      (options: AI, Product Design, Filmmaking, Tech, How-to, Lifestyle, Business)
date:             Used Date
```

**write notion_config.json.** after creating both databases, you'll have their IDs from the api responses. write `<DATA_DIR>/memory/notion_config.json`:

```json
{
  "workspace_user": {
    "name": "",
    "email": "",
    "user_id": ""
  },
  "parent_page": {
    "title": "<parent page name>",
    "url": "<parent page url>",
    "id": "<parent page id>"
  },
  "databases": {
    "trend_radar": {
      "title": "trendvane",
      "url": "<url from api response>",
      "data_source_id": "<id from api response>",
      "data_source_url": "collection://<id from api response>"
    },
    "hook_library": {
      "title": "hook library",
      "url": "<url from api response>",
      "data_source_id": "<id from api response>",
      "data_source_url": "collection://<id from api response>"
    }
  }
}
```

optionally ask: "What's your name and email in Notion? I'll add it to the config." if they don't care, leave those fields empty.

tell the user: "Created both databases in Notion - you'll see them appear in your workspace now."

---

### step 4 - configure your niches

you're going to rewrite `<DATA_DIR>/memory/my_niches.json` with the user's actual content topics. current file has placeholder values - replace them.

ask these questions (can ask all at once):

1. "What topics do you make content about? List as many as you want - they can be broad (AI, tech) or specific (Figma tips, short film making)."
2. "Which one is your main niche - the one you post about most?"
3. "Where is most of your audience based? (e.g., US, UK, global)"
4. "Any topics you'd never want to post about, even if they're trending? (Politics and gambling are already filtered by default.)"

once you have their answers:
- rewrite `memory/my_niches.json` with their real niches
- set their primary niche weight to 3.0
- secondary niches to 1.5-2.0
- anything else to 1.0
- match subreddits to the actual topics (use common subreddit names for each topic)
- set `region.primary` to their main region (e.g., "US")
- add any extra blocked topics to `brand_safe_exclusions`

show them a summary: "Here's how I've set up your niches: [list them with weights]. Does this look right?" adjust if they want to change anything.

---

### step 5 - voice profile

read the current `<DATA_DIR>/memory/voice_examples.md`. if it still looks like a template (has "paste example" placeholders), walk them through filling it in.

ask:

1. "Paste 2-3 things you've actually written and posted - a caption, a thread, a description, whatever. Exactly as you wrote it." (this is the most important input - their real writing samples)
2. "Any words or phrases you'd never use? Add them to the list."
3. "Do you write all lowercase, sentence case, or something else?"
4. "Do you use emoji? Always, sometimes, or never? If sometimes, any specific ones?"

take their answers and rewrite `memory/voice_examples.md`:
- put their real examples in the examples sections
- add their banned phrases to the existing list
- note their casing preference
- document emoji habits

if they don't have examples handy, tell them it's optional: "You can add your real examples later - the skill will still work, it just might not sound exactly like you yet."

---

### step 6 - api keys (optional)

say: "Two optional API keys give you better coverage - YouTube Data API and Product Hunt. Want to add them now? You can always skip this and add them later."

if they want to:
- youtube: "Go to console.cloud.google.com - APIs & Services - YouTube Data API v3 - Create credentials - API Key. Paste it here."
- product hunt: "Go to api.producthunt.com/v2/docs, create a developer app, and get your API token."

write `<DATA_DIR>/memory/secrets.json`:
```json
{
  "YT_API_KEY": "<key or leave empty>",
  "PH_TOKEN": "<token or leave empty>"
}
```

if they skip: move on without any comment about it.

---

### step 7 - verify

run `python3 <CODE_DIR>/scripts/validate_setup.py` again.

if all checks pass (or only warnings remain): great - tell them and move on.

if there are errors: fix what you can automatically. for anything that needs user action, tell them exactly what to do with the exact command or url.

then do a quick test fetch: `python3 <CODE_DIR>/scripts/run_all.py`

show them the output summary - roughly how many candidates came in from each source and how many made it through scoring. if 0 picks came through, explain that their keywords probably need to be more specific and offer to adjust `my_niches.json` right now.

---

### step 8 - schedule (optional)

say: "Last thing - want to set up the automatic morning run? It fetches at 5:30am and you get briefs at 6am."

if yes:
- tell them to add this to their crontab (`crontab -e`), substituting the real absolute CODE_DIR path:
  ```
  30 5 * * * cd <CODE_DIR> && python3 scripts/run_all.py >> ~/.claude/trendvane/cache/run.log 2>&1
  ```
  (the scripts resolve the data dir on their own, so cache and briefings still land in `~/.claude/trendvane/`.)
- for the claude brief at 6am: offer to use `/schedule` to set it up if the user is in a session that supports it

if no: skip. don't mention it again.

---

## finishing up

tell the user:

"You're set up. Here's the quick reference:

**Daily (if scheduled):** 5:30am Python fetches, 6am Claude generates 3 briefs to Notion - no action needed from you.

**On demand:** just say 'what's trending today?' in Claude Code and I'll run the radar.

**To adjust later:**
- Change what topics you cover: edit `memory/my_niches.json`
- Update how you sound: edit `memory/voice_examples.md`
- Block a topic: add it to `brand_safe_exclusions` in `my_niches.json`"

---

## if something breaks mid-setup

if a step fails and you can't fix it automatically:
- be specific: say exactly what failed and exactly what the user needs to do, with the exact command or url
- tell them which step to return to: "Once you've done that, type /trendvane and I'll start from step [N]."
- never leave them without a clear next action

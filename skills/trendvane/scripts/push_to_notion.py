"""Push generated briefs to the Trendvane Notion database.

This script is normally NOT run directly — it's intended to be called by the
skill orchestrator (or by Claude via the Notion MCP tools during a skill run).
It exists so that the orchestrator has a single, testable surface for writes
and so the schema mapping lives in one place.

The skill itself uses the Notion MCP tools (notion-create-pages) directly,
because they're already authenticated to the user's workspace. This module
defines:
  - `build_page_payload(brief)`: maps a brief dict to the exact properties
    schema expected by the Trendvane database
  - `format_for_mcp(briefs)`: shapes a list of briefs into the MCP
    create-pages payload (parent + pages[])
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from common import MEMORY, load_notion_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _join_lines(items: list[str], limit: int = 5) -> str:
    return "\n".join(items[:limit])


# ---------------------------------------------------------------------------
# Property mapping
# ---------------------------------------------------------------------------

def build_page_properties(brief: dict[str, Any]) -> dict[str, Any]:
    """Convert a brief dict to the property map Notion expects.

    Brief schema (produced by Claude during the skill run):
    {
        "trend": str,
        "hook_variants": str,
        "script": str,
        "shot_list": str,
        "trending_audio": str | None,
        "caption": str,
        "hashtags": str,
        "source_urls": list[str],
        "reference_clips": list[str],
        "my_take": str,
        "category": "AI" | "Product Design" | ...,
        "platforms": list[str],
        "velocity_label": "Rising" | "Peaking" | "Fading",
        "score": float,
        "time_to_stale": "< 3 days" | "1 week" | "2+ weeks",
    }

    FILL EVERYTHING RULE: every text property gets filled. The page body
    duplicates the same content in a readable format. The duplication is on
    purpose so the table view is informative AND the page reads top to bottom.
    Posted URL and Performance are the only properties left empty (filled
    manually after posting).
    """
    props: dict[str, Any] = {
        # Short, scannable props
        "Trend": brief["trend"],
        "date:Date Spotted:start": _today_iso(),
        "Category": brief["category"],
        "Velocity": brief["velocity_label"],
        "Time-to-stale": brief["time_to_stale"],
        "Status": "New",
        "Platforms": json.dumps(brief.get("platforms", [])),
        "Score": brief["score"],
        "Trending Audio": brief.get("trending_audio") or "",
        # Long-form creative props (also rendered in the page body)
        "Hook Variants": (brief.get("hook_variants") or "").strip(),
        "Script": (brief.get("script") or "").strip(),
        "Shot List": (brief.get("shot_list") or "").strip(),
        "Caption": (brief.get("caption") or "").strip(),
        "Hashtags": (brief.get("hashtags") or "").strip(),
        "Source URLs": _join_lines(brief.get("source_urls", []), limit=5),
        "Reference Clips": _join_lines(brief.get("reference_clips", []), limit=5),
        "My Take": (brief.get("my_take") or "").strip(),
    }
    return props


def _extract_top_hook(hook_variants: str) -> str:
    """Pull the first hook variant out for the callout block."""
    for line in (hook_variants or "").splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading "1." and the [archetype] tag
        if line.startswith("1."):
            rest = line[2:].strip()
            if rest.startswith("[") and "]" in rest:
                rest = rest.split("]", 1)[1].strip()
            return rest
        return line
    return ""


def build_page_content(brief: dict[str, Any]) -> str:
    """Notion page body, the readable brief in one continuous page.

    Layout designed for scrollability:
      1. Callout with the top hook (so you see the strongest opener immediately)
      2. All 3 hook variants
      3. Timestamped script in a code block
      4. Numbered shot list
      5. Per-platform captions
      6. Per-platform hashtags
      7. Why-this-trend context
      8. Source URLs + reference clips
    """
    top_hook = _extract_top_hook(brief.get("hook_variants", ""))

    lines = [
        f"> 🎯 **top hook:** {top_hook}",
        "",
        "## hook variants",
        "",
        brief.get("hook_variants", "").strip(),
        "",
        "## script",
        "",
        "```",
        brief.get("script", "").strip(),
        "```",
        "",
        "## shot list",
        "",
        brief.get("shot_list", "").strip(),
        "",
        "## caption",
        "",
        brief.get("caption", "").strip(),
        "",
        "## hashtags",
        "",
        brief.get("hashtags", "").strip(),
    ]

    why = brief.get("why_this_trend") or brief.get("rationale")
    if why:
        lines += ["", "## why this trend", "", why.strip()]

    if brief.get("source_urls"):
        lines += ["", "## source urls", ""]
        for u in brief["source_urls"][:5]:
            lines.append(f"- {u}")

    if brief.get("reference_clips"):
        lines += ["", "## reference clips", ""]
        for u in brief["reference_clips"][:5]:
            lines.append(f"- {u}")

    if brief.get("my_take"):
        lines += ["", "## my take", "", brief["my_take"].strip()]

    return "\n".join(lines)


def format_for_mcp(briefs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the payload for the notion-create-pages MCP tool."""
    cfg = load_notion_config()
    ds_id = cfg["databases"]["trend_radar"]["data_source_id"]

    pages = []
    for b in briefs:
        pages.append(
            {
                "properties": build_page_properties(b),
                "icon": "📡",
                "content": build_page_content(b),
            }
        )
    return {
        "parent": {"type": "data_source_id", "data_source_id": ds_id},
        "pages": pages,
    }


def write_mcp_payload(briefs: list[dict[str, Any]]) -> Path:
    """Save the MCP payload to disk so the skill / orchestrator can read it."""
    payload = format_for_mcp(briefs)
    p = MEMORY.parent / "cache" / f"notion_payload_{datetime.now().strftime('%Y%m%d')}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


if __name__ == "__main__":
    # Smoke test with a fake brief
    fake = {
        "trend": "agents are starting to use your computer for you",
        "category": "AI",
        "velocity_label": "Rising",
        "time_to_stale": "< 3 days",
        "platforms": ["X", "HackerNews", "YouTube"],
        "score": 84.2,
        "trending_audio": "",
        "hook_variants": "1. [pattern interrupt] stop trying to prompt your way out of this.\n2. [bold claim] cursor just did what every 'AI IDE' promised.\n3. [stat shock] 9 out of 10 agents fail at this one thing.",
        "script": "length: 60s\nhook: variant #1\n\n0:00-0:03  hook\n0:03-0:10  setup\n...",
        "shot_list": "shot 1 — extreme close-up: cursor blinking\nshot 2 — talking head, 35mm",
        "caption": "tiktok: agents are using my computer now and i kinda love it.\ninstagram: 6 months ago...",
        "hashtags": "tiktok: #ai #aiagents | #aitools #cursor | #computeruse",
        "source_urls": ["https://news.ycombinator.com/item?id=1", "https://x.com/foo/bar"],
        "reference_clips": ["https://www.youtube.com/watch?v=xxx"],
    }
    p = write_mcp_payload([fake])
    print(f"smoke test ok — wrote {p}")

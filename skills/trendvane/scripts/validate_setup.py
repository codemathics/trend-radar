"""validate_setup.py - run this before your first trendvane run.

checks that all required config files exist and are filled in, python deps
are installed, and notion config has the expected keys.

usage:
    python3 scripts/validate_setup.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CODE_ROOT, DATA_ROOT, MEMORY  # noqa: E402

# SKILL.md ships with the code; templates too.
ROOT = CODE_ROOT

PASS = "  ok"
FAIL = "  missing"
WARN = "  warning"

errors: list[str] = []
warnings: list[str] = []


def check(label: str, ok: bool, error_msg: str, warn: bool = False) -> None:
    if ok:
        print(f"{PASS}  {label}")
    elif warn:
        print(f"{WARN}  {label} - {error_msg}")
        warnings.append(error_msg)
    else:
        print(f"{FAIL}  {label} - {error_msg}")
        errors.append(error_msg)


# ---------------------------------------------------------------------------
# 1. Python deps
# ---------------------------------------------------------------------------
print("\npython dependencies")

try:
    import pytrends  # noqa: F401
    check("pytrends", True, "")
except ImportError:
    check("pytrends", False, "run: pip install pytrends", warn=True)

# stdlib modules used by fetchers (always present in 3.10+)
check("python 3.10+", sys.version_info >= (3, 10), f"found python {sys.version.split()[0]}, need 3.10+")


# ---------------------------------------------------------------------------
# 2. Required config files
# ---------------------------------------------------------------------------
print("\nconfig files")

niches_path = MEMORY / "my_niches.json"
check("memory/my_niches.json exists", niches_path.exists(), "copy and fill in memory/my_niches.json (see README)")

if niches_path.exists():
    try:
        niches = json.loads(niches_path.read_text())
        has_owner = niches.get("owner") not in (None, "", "your-name")
        check("my_niches.json owner set", has_owner, "set 'owner' field in my_niches.json", warn=True)
        has_niches = len(niches.get("niches", [])) > 0
        check("my_niches.json has niches", has_niches, "add at least one niche to my_niches.json")
    except json.JSONDecodeError:
        check("my_niches.json valid json", False, "my_niches.json is not valid json")

notion_path = MEMORY / "notion_config.json"
check("memory/notion_config.json exists", notion_path.exists(), "copy notion_config.example.json to notion_config.json and fill it in")

if notion_path.exists():
    try:
        cfg = json.loads(notion_path.read_text())
        ds_id = (cfg.get("databases") or {}).get("trend_radar", {}).get("data_source_id", "")
        hl_id = (cfg.get("databases") or {}).get("hook_library", {}).get("data_source_id", "")
        check("notion trend_radar data_source_id set", bool(ds_id) and "your-" not in ds_id, "fill in databases.trend_radar.data_source_id in notion_config.json")
        check("notion hook_library data_source_id set", bool(hl_id) and "your-" not in hl_id, "fill in databases.hook_library.data_source_id in notion_config.json")
    except json.JSONDecodeError:
        check("notion_config.json valid json", False, "notion_config.json is not valid json")

voice_path = MEMORY / "voice_examples.md"
check("memory/voice_examples.md exists", voice_path.exists(), "fill in memory/voice_examples.md with your voice profile")
if voice_path.exists():
    content = voice_path.read_text()
    has_examples = "paste example" not in content.lower() and len(content.strip()) > 300
    check("voice_examples.md has content", has_examples, "voice_examples.md appears to be mostly template - add your real voice examples", warn=True)

skill_path = ROOT / "SKILL.md"
check("SKILL.md exists", skill_path.exists(), "SKILL.md is missing from repo root")


# ---------------------------------------------------------------------------
# 3. Optional secrets
# ---------------------------------------------------------------------------
print("\noptional api keys (skill works without these)")

secrets_path = MEMORY / "secrets.json"
if secrets_path.exists():
    try:
        secrets = json.loads(secrets_path.read_text())
        check("YT_API_KEY set", bool(secrets.get("YT_API_KEY")), "youtube fetcher will be skipped", warn=True)
        check("PH_TOKEN set", bool(secrets.get("PH_TOKEN")), "product hunt fetcher will be skipped", warn=True)
    except json.JSONDecodeError:
        check("secrets.json valid json", False, "secrets.json is not valid json")
else:
    print(f"{WARN}  secrets.json not found - youtube and product hunt fetchers will be skipped")
    warnings.append("no secrets.json - youtube and product hunt disabled")


# ---------------------------------------------------------------------------
# 4. Cache + briefings dirs (auto-created by common.py but check write perms)
# ---------------------------------------------------------------------------
print("\ndirectories")
print(f"  ->   user data dir: {DATA_ROOT}")

for d in ["cache", "briefings"]:
    p = DATA_ROOT / d
    try:
        p.mkdir(exist_ok=True)
        test = p / ".write_test"
        test.write_text("ok")
        test.unlink()
        check(f"{d}/ writable", True, "")
    except Exception as e:
        check(f"{d}/ writable", False, str(e))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if errors:
    print(f"setup incomplete - {len(errors)} error(s) to fix before running:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
elif warnings:
    print(f"setup ok with {len(warnings)} warning(s) - skill will run but some sources may be limited.")
else:
    print("all checks passed. run: python3 scripts/run_all.py")

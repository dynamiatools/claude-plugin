"""Merge (or remove) the ms-* hooks, status line and permission into a Claude Code settings.json."""
from __future__ import annotations

import copy
import json
import os
import shutil
import time
from pathlib import Path

from .core import die

SOURCE = Path(__file__).resolve().parents[2] / "settings" / "hooks.example.json"


def settings_path(project: bool = False) -> Path:
    if project:
        return Path.cwd() / ".claude" / "settings.json"
    return Path(os.environ.get("CLAUDE_HOME") or Path(os.environ.get("HOME", "~")).expanduser() / ".claude") / "settings.json"


def our_commands(src: dict) -> set[str]:
    return {h["command"] for groups in src.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])}


def installed_commands(settings: dict) -> set[str]:
    return {h.get("command", "") for groups in settings.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])}


def merge(settings: dict, src: dict) -> list[str]:
    """Add what is missing; never touch other entries. Returns a human-readable report."""
    report = []
    hooks = settings.setdefault("hooks", {})
    for event, groups in src.get("hooks", {}).items():
        target = hooks.setdefault(event, [])
        for g in groups:
            existing = next((x for x in target if x.get("matcher") == g.get("matcher")), None)
            label = f"{event}[{g.get('matcher', '*')}]"
            if existing is None:
                target.append(copy.deepcopy(g))
                report += [f"added    {label}: {h['command']}" for h in g["hooks"]]
                continue
            for h in g["hooks"]:
                if any(e.get("command") == h["command"] for e in existing.setdefault("hooks", [])):
                    report.append(f"present  {label}: {h['command']}")
                else:
                    existing["hooks"].append(copy.deepcopy(h))
                    report.append(f"added    {label}: {h['command']}")
    if src.get("statusLine"):
        cur = settings.get("statusLine")
        if not cur:
            settings["statusLine"] = copy.deepcopy(src["statusLine"])
            report.append(f"added    statusLine: {src['statusLine']['command']}")
        elif cur.get("command") == src["statusLine"]["command"]:
            report.append(f"present  statusLine: {cur['command']}")
        else:
            report.append(f"kept     statusLine already set to '{cur.get('command')}' (not overwritten; usage tracking needs ms-statusline)")
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for rule in src.get("permissions", {}).get("allow", []):
        if rule in allow:
            report.append(f"present  permission {rule}")
        else:
            allow.append(rule)
            report.append(f"added    permission {rule}")
    return report


def remove(settings: dict, src: dict) -> list[str]:
    report, cmds = [], our_commands(src)
    for event in list(settings.get("hooks", {})):
        groups = settings["hooks"][event]
        for g in groups:
            kept = [h for h in g.get("hooks", []) if h.get("command") not in cmds]
            report += [f"removed  {event}: {h['command']}" for h in g.get("hooks", []) if h.get("command") in cmds]
            g["hooks"] = kept
        settings["hooks"][event] = [g for g in groups if g.get("hooks")]
        if not settings["hooks"][event]:
            del settings["hooks"][event]
    if not settings.get("hooks"):
        settings.pop("hooks", None)
    if src.get("statusLine") and (settings.get("statusLine") or {}).get("command") == src["statusLine"]["command"]:
        del settings["statusLine"]
        report.append("removed  statusLine")
    allow = settings.get("permissions", {}).get("allow", [])
    for rule in src.get("permissions", {}).get("allow", []):
        if rule in allow:
            allow.remove(rule)
            report.append(f"removed  permission {rule}")
    return report


def cmd_setup_hooks(args: list[str]) -> int:
    dry = "--dry-run" in args
    undo = "--remove" in args
    project = "--project" in args
    source = SOURCE
    if "--source" in args:
        source = Path(args[args.index("--source") + 1])
    try:
        src = json.loads(source.read_text())
    except (OSError, ValueError) as e:
        die(f"cannot read {source}: {e}")
    target = settings_path(project)
    settings = {}
    if target.exists():
        try:
            settings = json.loads(target.read_text())
        except ValueError as e:
            die(f"{target} is not valid JSON ({e}); fix it first, nothing was changed")
    before = json.dumps(settings, sort_keys=True)
    report = remove(settings, src) if undo else merge(settings, src)
    changed = json.dumps(settings, sort_keys=True) != before
    print(f"{'(dry run) ' if dry else ''}{'Removing from' if undo else 'Merging into'} {target}")
    for line in report or ["nothing to do"]:
        print("  " + line)
    if not undo and shutil.which("ms-workspace") is None:
        print("  warning: ms-workspace is not in PATH, so the hooks would fail; run ./install.sh first")
    if changed and not dry:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            backup = target.with_name(f"{target.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
            shutil.copy2(target, backup)
            print(f"  backup: {backup}")
        target.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
        print("Done. Start a new Claude Code session to load the changes.")
    elif not changed:
        print("Already up to date." if not undo else "Nothing to remove.")
    return 0

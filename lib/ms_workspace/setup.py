"""Merge (or remove) the ms-* hooks, status line and permission into a Claude Code settings.json."""
from __future__ import annotations

import copy
import json
import os
import shutil
import time
from pathlib import Path

from .core import die

LEGACY_ALLOW = ["Bash(ms-workspace:*)"]  # earlier, too broad rule: it auto-approved ship, clean and env
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
    if not hooks:
        settings.pop("hooks", None)
    if src.get("statusLine"):
        cur = settings.get("statusLine")
        if not cur:
            settings["statusLine"] = copy.deepcopy(src["statusLine"])
            report.append(f"added    statusLine: {src['statusLine']['command']}")
        elif cur.get("command") == src["statusLine"]["command"]:
            report.append(f"present  statusLine: {cur['command']}")
        else:
            report.append(f"kept     statusLine already set to '{cur.get('command')}' (not overwritten; usage tracking needs ms-statusline)")
    perms = settings.setdefault("permissions", {})
    for kind in ("allow", "ask"):
        rules = perms.setdefault(kind, [])
        if kind == "allow":
            for old in LEGACY_ALLOW:
                if old in rules:
                    rules.remove(old)
                    report.append(f"removed  permission {old} (too broad; replaced by the narrower rules below)")
        for rule in src.get("permissions", {}).get(kind, []):
            if rule in rules:
                report.append(f"present  {kind} {rule}")
            else:
                rules.append(rule)
                report.append(f"added    {kind} {rule}")
        if not rules:
            del perms[kind]
    return report


def use_plugin_root(settings: dict, src: dict, root: str) -> list[str]:
    """Plugin mode: the plugin ships the hooks itself, so drop our copies from settings.json and
    point the status line at the plugin's script (a plugin's bin/ is not on the status line's PATH).
    shortcut: the path holds the plugin version, so /dynamia:setup must run again after an update."""
    report, cmds = [], our_commands(src)
    for event in list(settings.get("hooks", {})):
        for g in settings["hooks"][event]:
            report += [f"removed  {event}: {h['command']} (the plugin provides it)" for h in g.get("hooks", []) if h.get("command") in cmds]
            g["hooks"] = [h for h in g.get("hooks", []) if h.get("command") not in cmds]
        settings["hooks"][event] = [g for g in settings["hooks"][event] if g.get("hooks")]
        if not settings["hooks"][event]:
            del settings["hooks"][event]
    if not settings.get("hooks"):
        settings.pop("hooks", None)
    src["hooks"], src["statusLine"] = {}, None  # merge() then only adds the permissions
    line = {"type": "command", "command": f'"{root}/bin/ms-statusline"'}
    cur = (settings.get("statusLine") or {}).get("command", "")
    if cur == line["command"]:
        report.append(f"present  statusLine: {cur}")
    elif not cur or cur.strip('"').endswith("ms-statusline"):
        settings["statusLine"] = line
        report.append(f"{'updated' if cur else 'added  '}  statusLine: {line['command']}")
    else:
        report.append(f"kept     statusLine already set to '{cur}' (not overwritten; usage tracking needs ms-statusline)")
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
    if src.get("statusLine") and (settings.get("statusLine") or {}).get("command", "").strip('"').endswith(src["statusLine"]["command"]):
        del settings["statusLine"]
        report.append("removed  statusLine")
    perms = settings.get("permissions", {})
    for kind in ("allow", "ask"):
        rules = perms.get(kind, [])
        for rule in src.get("permissions", {}).get(kind, []) + (LEGACY_ALLOW if kind == "allow" else []):
            if rule in rules:
                rules.remove(rule)
                report.append(f"removed  {kind} {rule}")
        if kind in perms and not perms[kind]:
            del perms[kind]
    if "permissions" in settings and not settings["permissions"]:
        del settings["permissions"]
    return report


MD_BEGIN = "<!-- dynamia:begin (managed by /dynamia:setup; edit outside this block) -->"
MD_END = "<!-- dynamia:end -->"
BIN_NAMES = ("ms-workspace", "ms-statusline")


def claude_home() -> Path:
    return settings_path().parent


def bin_dir() -> Path:
    return Path(os.environ.get("BIN_DIR") or Path(os.environ.get("HOME", "~")).expanduser() / ".local" / "bin")


def _backup(path: Path, report: list[str]) -> None:
    backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    report.append(f"backup   {backup}")


def global_md(root: Path, dry: bool, undo: bool) -> list[str]:
    """Put the repo's global instructions in ~/.claude/CLAUDE.md as a marked block; the rest of the file is yours."""
    target, report = claude_home() / "CLAUDE.md", []
    block = f"{MD_BEGIN}\n{(root / 'CLAUDE.md').read_text().rstrip()}\n{MD_END}\n"
    linked = target.is_symlink()  # install.sh linked it to the repo file: never write through it
    text = target.read_text() if target.exists() else ""
    a, b = text.find(MD_BEGIN), text.find(MD_END)
    if (a == -1) != (b == -1) or b < a:
        die(f"{target} has a dynamia block start without an end marker (or the reverse); fix it by hand")
    if linked and text == (root / "CLAUDE.md").read_text():
        text, a, b = "", -1, -1  # a copy of our own file: the block replaces it
    if undo:
        if a == -1:
            return ["present  no dynamia block in CLAUDE.md (nothing to remove)"]
        new = (text[:a] + text[b + len(MD_END):].lstrip("\n")).rstrip() + "\n"
        report.append("removed  dynamia block from CLAUDE.md")
    elif a != -1:
        if text[a:b + len(MD_END)] + "\n" == block or text[a:b + len(MD_END)] == block.rstrip("\n"):
            return ["present  dynamia block in CLAUDE.md"]
        new = text[:a] + block.rstrip("\n") + text[b + len(MD_END):]
        report.append("updated  dynamia block in CLAUDE.md")
    else:
        new = text + ("" if not text or text.endswith("\n") else "\n") + ("\n" if text else "") + block
        report.append("added    dynamia block in CLAUDE.md" + (" (your content kept above it)" if text else ""))
    if not dry:
        if target.exists() or linked:
            if linked:
                target.unlink()
            else:
                _backup(target, report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new)
    return report


def global_bin(root: Path, dry: bool, undo: bool) -> list[str]:
    """Link ms-workspace and ms-statusline into ~/.local/bin; replace only links that already point to some plugin or repo bin/."""
    report, dest = [], bin_dir()
    for name in BIN_NAMES:
        src, dst = root / "bin" / name, dest / name
        ours = dst.is_symlink() and os.readlink(dst).endswith(f"/bin/{name}")
        if undo:
            if ours:
                report.append(f"removed  link {dst}")
                if not dry:
                    dst.unlink()
        elif ours and os.readlink(dst) == str(src):
            report.append(f"present  link {dst}")
        elif ours or not dst.exists() and not dst.is_symlink():
            report.append(f"{'updated' if ours else 'added  '}  link {dst} -> {src}")
            if not dry:
                dest.mkdir(parents=True, exist_ok=True)
                if ours:
                    dst.unlink()
                dst.symlink_to(src)
        else:
            report.append(f"kept     {dst} already exists and is not a link to this tool")
    if not undo and str(dest) not in os.environ.get("PATH", "").split(":"):
        report.append(f"note     {dest} is not in PATH; add it to your shell profile")
    return report


def cmd_setup_hooks(args: list[str]) -> int:
    dry = "--dry-run" in args
    undo = "--remove" in args
    project = "--project" in args
    source = SOURCE
    if "--source" in args:
        i = args.index("--source")
        if i + 1 >= len(args):
            die("--source needs a file")
        source = Path(args[i + 1])
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
    report = []
    if "--plugin-root" in args and not undo:
        i = args.index("--plugin-root")
        if i + 1 >= len(args):
            die("--plugin-root needs the plugin folder")
        report = use_plugin_root(settings, src, args[i + 1].rstrip("/"))
    report += remove(settings, src) if undo else merge(settings, src)
    changed = json.dumps(settings, sort_keys=True) != before
    print(f"{'(dry run) ' if dry else ''}{'Removing from' if undo else 'Merging into'} {target}")
    for line in report or ["nothing to do"]:
        print("  " + line)
    if "--global" in args:
        if project:
            die("--global works on your user-level files; drop --project")
        root = Path(args[args.index("--plugin-root") + 1]) if "--plugin-root" in args else SOURCE.parents[1]
        print(f"{'(dry run) ' if dry else ''}{'Removing' if undo else 'Setting up'} global files in {claude_home()} and {bin_dir()}")
        for line in global_md(root, dry, undo) + global_bin(root, dry, undo):
            print("  " + line)
    if not undo and "--plugin-root" not in args and shutil.which("ms-workspace") is None:
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

"""Plan usage (5h session and 7d week) from the snapshot that ms-statusline writes."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

from .core import Workspace, die

SESSION_LEN, WEEK_LEN = 18000, 604800


def cache_dir() -> Path:
    if os.environ.get("MS_CACHE_DIR"):
        return Path(os.environ["MS_CACHE_DIR"])
    base = os.environ.get("XDG_CACHE_HOME") or str(Path(os.environ.get("HOME", "~")).expanduser() / ".cache")
    return Path(base) / "ms-workspace"


def snapshot_path() -> Path:
    return cache_dir() / "usage.json"


def rnd(x: float) -> int:  # round half away from zero, like jq
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def num(x) -> str:
    return str(int(x)) if float(x) == int(x) else str(x)


def dur(s: float) -> str:
    s = int(math.floor(s))
    if s <= 0:
        return "0m"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h{(s % 3600) // 60}m"
    return f"{s // 86400}d{(s % 86400) // 3600}h"


def analyze(win, length: int, now: float) -> dict:
    if not win or win.get("used_percentage") is None:
        return {"state": "nodata"}
    left = win["resets_at"] - now
    if left <= 0:
        return {"state": "reset"}
    elapsed = length - left
    frac = elapsed / length
    used = win["used_percentage"]
    enough = frac >= 0.05  # too early in the window to extrapolate
    return {"state": "active", "used": used, "left": 100 - used, "resets_in": left,
            "pace": used / (frac * 100) if enough else None,
            "projected": used / frac if enough else None,
            "eta100": (100 - used) / (used / elapsed) if enough and used > 0 else None}


def level(a: dict, session: bool, warn: float, stop: float, need: float) -> int:
    if a["state"] != "active":
        return 0
    used, eta, proj = a["used"], a["eta100"], a["projected"]
    crit = (used >= stop or (session and need > 0 and used + need > 100)
            or (used >= 70 and eta is not None and eta < 1800 and eta < a["resets_in"]))
    warn_ = (used >= warn or (used >= 50 and proj is not None and proj > 100)
             or (session and need > 0 and used + need > stop))
    return 2 if crit else 1 if warn_ else 0


def line(name: str, a: dict) -> str:
    if a["state"] == "nodata":
        return f"{name}: no data"
    if a["state"] == "reset":
        return f"{name}: window reset since the last data (usage unknown, probably low)"
    out = f"{name}: {rnd(a['used'])}% used, {rnd(a['left'])}% left | resets in {dur(a['resets_in'])}"
    if a["pace"] is not None:
        out += f" | pace x{num(rnd(a['pace'] * 10) / 10)} | ~{rnd(a['projected'])}% at reset"
    else:
        out += " | too early to project"
    if a["eta100"] is not None and a["eta100"] < a["resets_in"]:
        out += f" | hits 100% in ~{dur(a['eta100'])}"
    return out


def evaluate(snap: dict, now: float, warn: float, stop: float, need: float) -> dict:
    s = analyze(snap.get("five_hour"), SESSION_LEN, now)
    w = analyze(snap.get("seven_day"), WEEK_LEN, now)
    lv = max(level(s, True, warn, stop, need), level(w, False, warn, stop, need))
    short = ("usage 5h " + (f"{rnd(s['used'])}% (resets in {dur(s['resets_in'])})" if s["state"] == "active" else "n/a")
             + ", 7d " + (f"{rnd(w['used'])}%" if w["state"] == "active" else "n/a")
             + " - " + ["ok", "WARN", "CRITICAL"][lv])
    return {"age_s": now - snap.get("captured_at", now), "session": s, "week": w, "level": lv,
            "verdict": ["ok", "warn", "critical"][lv], "nodata": s["state"] == "nodata" and w["state"] == "nodata",
            "text": "\n".join([line("5h session", s), line("7d week   ", w)]), "short": short}


def cmd_usage(ws: Workspace | None, args: list[str]) -> int:
    check, need, mode, need_note = False, 0.0, "text", ""
    it = iter(args)
    for a in it:
        if a == "--check":
            check = True
        elif a == "--need":
            raw = next(it, "")
            if raw == "auto":
                if ws is None:
                    die("--need auto needs a workspace (it learns from its action log)")
                from .insights import typical_cost
                need, n = typical_cost(ws)
                if n < 3:
                    die(f"--need auto needs history: only {n} completed batch(es) with usage data (need 3); give a number instead")
                need_note = f" (median of {n} past batches)"
            else:
                try:
                    need = float(raw)
                except ValueError:
                    die("--need needs a percentage or 'auto'")
        elif a == "--json":
            mode = "json"
        elif a == "--line":
            mode = "line"
        else:
            die(f"usage: unknown option {a}")
    warn = ws.get("usage", "warn_pct", default=70) if ws else 70
    stop = ws.get("usage", "stop_pct", default=90) if ws else 90
    stale = ws.get("usage", "stale_minutes", default=15) if ws else 15

    snap_file = snapshot_path()
    if not snap_file.is_file():
        if mode != "line":
            print("No usage data yet. Enable ms-statusline (see README) on a Pro/Max plan; data appears after the first reply of a session.", file=sys.stderr)
        return 3 if check else 0
    try:
        snap = json.loads(snap_file.read_text())
    except (OSError, ValueError):
        die(f"could not read {snap_file}")
    res = evaluate(snap, time.time(), warn, stop, need)
    if res["nodata"]:
        if mode != "line":
            print("Usage snapshot has no rate-limit data (API-key plans do not report it).", file=sys.stderr)
        return 3 if check else 0

    if mode == "json":
        print(json.dumps(res, separators=(",", ":")))
    elif mode == "line":
        print(res["short"])
    else:
        out = res["text"]
        if need > 0:
            out += f"\nplanned task: ~{num(need)}% of the 5h window{need_note}"
        lv = res["level"]
        advice = ("stop and confirm with the user before starting; do not leave work half done" if lv == 2
                  else "confirm with the user; prefer small steps that can be finished" if lv == 1 else "proceed")
        out += f"\nverdict: {res['verdict'].upper()} - {advice}"
        if res["age_s"] > stale * 60:
            out += f"\n(data is {int(res['age_s'] // 60)} min old; it refreshes while a Claude session is running)"
        print(out)
    return res["level"] if check else 0

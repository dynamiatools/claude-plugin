"""What the action log says: slow or flaky tests, time and plan usage per batch."""
from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict

from .core import Workspace, die


def load_events(ws: Workspace, days: float = 14) -> list[dict]:
    if not ws.log_dir.is_dir():
        return []
    cutoff = time.time() - days * 86400
    events = []
    for f in sorted(ws.log_dir.glob("*.jsonl")):
        if f.stat().st_mtime < cutoff:
            continue
        for l in f.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(l))
            except ValueError:
                pass
    return sorted(events, key=lambda e: e.get("ts", ""))


def batch_costs(events: list[dict], key: str = "u5") -> dict[str, float]:
    """Approximate plan usage per batch: the sum of positive jumps of u5/u7 between consecutive events of the batch.

    Drops (a window reset) are ignored. Other work done in parallel is attributed to the batch, hence 'approximate'."""
    by_batch = defaultdict(list)
    for e in events:
        if e.get("batch") and e.get(key) is not None:
            by_batch[e["batch"]].append(e[key])
    return {b: round(sum(max(0.0, y - x) for x, y in zip(v, v[1:])), 1) for b, v in by_batch.items() if len(v) > 1}


def completed_batches(events: list[dict]) -> set[str]:
    return {e["batch"] for e in events if e.get("batch") and e["action"] in ("ship", "clean") and e["status"] == "ok"}


def typical_cost(ws: Workspace) -> tuple[float, int]:
    """(median 5h-window cost, sample size) over completed batches with usage data."""
    ev = load_events(ws, 90)
    done = completed_batches(ev)
    costs = [c for b, c in batch_costs(ev).items() if b in done and c > 0]
    return (statistics.median(costs), len(costs)) if costs else (0.0, 0)


def analyze(ws: Workspace, days: float) -> dict:
    ev = load_events(ws, days)
    tests = defaultdict(lambda: {"runs": 0, "ok": 0, "fail": 0, "cached": 0, "secs": []})
    outcomes = defaultdict(set)  # (repo, key) -> {"ok", "fail"} for real runs
    slow = []
    for e in ev:
        if not e["action"].startswith("test.t") or e["action"] == "test.t2":
            continue
        t = tests[e["repo"]]
        t["runs"] += 1
        t[e["status"]] += 1 if e["status"] in ("ok", "fail") else 0
        if e.get("cached"):
            t["cached"] += 1
            continue
        if e.get("secs") is not None:
            t["secs"].append(e["secs"])
            slow.append((e["secs"], e["repo"], e["detail"]))
        if e.get("key"):
            outcomes[(e["repo"], e["key"])].add(e["status"])
    flaky = sorted({(r, k[:8]) for (r, k), v in outcomes.items() if {"ok", "fail"} <= v})
    spans = {}
    for e in ev:
        if e.get("batch"):
            s = spans.setdefault(e["batch"], {"events": 0, "first": e["ts"], "last": e["ts"]})
            s["events"] += 1
            s["last"] = e["ts"]
    c5, c7 = batch_costs(ev, "u5"), batch_costs(ev, "u7")
    for b, s in spans.items():
        s["u5_cost"], s["u7_cost"] = c5.get(b), c7.get(b)
    return {
        "days": days, "events": len(ev),
        "tests": {r: {"runs": t["runs"], "ok": t["ok"], "fail": t["fail"], "cached": t["cached"],
                      "avg_secs": round(sum(t["secs"]) / len(t["secs"]), 1) if t["secs"] else None,
                      "max_secs": max(t["secs"]) if t["secs"] else None} for r, t in sorted(tests.items())},
        "slowest": [{"secs": s, "repo": r, "cmd": c} for s, r, c in sorted(slow, reverse=True)[:3]],
        "flaky": [{"repo": r, "key": k} for r, k in flaky],
        "batches": spans,
        "guard_blocks": sum(1 for e in ev if e["action"] == "guard" and e["status"] == "blocked"),
        "conflicts": sum(1 for e in ev if e["action"] == "integrate" and e["status"] == "conflict"),
        "ship_failures": sum(1 for e in ev if e["action"] == "ship" and e["status"] in ("fail", "conflict")),
    }


def cmd_insights(ws: Workspace, args: list[str]) -> int:
    days, as_json = 14.0, False
    it = iter(args)
    for a in it:
        if a == "--days":
            days = float(next(it, "14"))
        elif a == "--json":
            as_json = True
        else:
            die(f"insights: unknown option {a}")
    r = analyze(ws, days)
    if as_json:
        print(json.dumps(r, separators=(",", ":")))
        return 0
    print(f"Insights from the last {days:g} days ({r['events']} logged actions)")
    if r["tests"]:
        print("Tests:")
        for repo, t in r["tests"].items():
            avg = f", avg {t['avg_secs']}s, max {t['max_secs']}s" if t["avg_secs"] is not None else ""
            print(f"  {repo}: {t['runs']} runs ({t['ok']} ok, {t['fail']} fail, {t['cached']} cached){avg}")
    if r["slowest"]:
        print("Slowest runs: " + "; ".join(f"{s['repo']} {s['secs']}s" for s in r["slowest"]))
    if r["flaky"]:
        print("Flaky candidates (same code, both pass and fail): " + ", ".join(f"{f['repo']}@{f['key']}" for f in r["flaky"]))
    if r["batches"]:
        print("Batches:")
        for b, s in sorted(r["batches"].items()):
            cost = f", ~{s['u5_cost']}% of the 5h window" if s["u5_cost"] is not None else ""
            week = f" / ~{s['u7_cost']}% of the week" if s["u7_cost"] is not None else ""
            print(f"  {b}: {s['events']} actions, {s['first'][:16]} -> {s['last'][:16]}{cost}{week}")
    print(f"Guard blocks: {r['guard_blocks']} | integration conflicts: {r['conflicts']} | ship failures: {r['ship_failures']}")
    median, n = typical_cost(ws)
    if n:
        print(f"Typical completed batch: ~{median:g}% of the 5h window (median of {n}); use `usage --need auto`.")
    return 0

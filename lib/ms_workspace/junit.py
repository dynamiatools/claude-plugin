"""Failure summaries from JUnit-style XML reports (Maven Surefire/Failsafe, Gradle, vitest/jest-junit, pytest --junitxml)."""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .core import Workspace, die

DEFAULT_GLOBS = ["**/target/surefire-reports/*.xml", "**/target/failsafe-reports/*.xml", "**/build/test-results/**/*.xml",
                 "**/test-results/**/*.xml", "**/junit*.xml", "**/TEST-*.xml"]
FRAMEWORK = re.compile(r"^(?:at )?(?:org\.junit|junit\.|java\.base|java\.lang\.reflect|jdk\.|sun\.|org\.apache\.maven|org\.apache\.tools|"
                       r"org\.testng|org\.mockito|org\.springframework\.test|com\.intellij|node:internal|.*node_modules|.*site-packages/_pytest|.*/pluggy/)")
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__"}


def find_reports(root: Path, globs: list[str], since: float) -> list[Path]:
    seen = {}
    for pattern in globs:
        for p in root.glob(pattern):
            if p.is_file() and not (SKIP_DIRS & set(p.relative_to(root).parts)):
                try:
                    if p.stat().st_mtime >= since:
                        seen[p] = None
                except OSError:
                    pass
    return sorted(seen)


def first_line(text: str, limit: int = 160) -> str:
    for line in (text or "").strip().splitlines():
        if line.strip():
            return re.sub(r"\s+", " ", line.strip())[:limit]
    return ""


def project_frame(trace: str) -> str:
    """The first stack frame that is not framework or runtime code."""
    for line in (trace or "").splitlines():
        t = line.strip()
        m = re.match(r"^(?:at\s+)?[\w$.<>/-]+\(([\w$.-]+\.(?:java|kt|groovy|scala)):(\d+)\)", t) or re.match(r"^at\s+\S+\s+\((.+?):(\d+):\d+\)$", t) \
            or re.match(r"^(\S+\.py):(\d+):", t) or re.match(r'^File "(.+?)", line (\d+)', t)
        if not m:
            continue
        if FRAMEWORK.search(t) or FRAMEWORK.search(m.group(1)):
            continue
        return t[:140]
    return ""


def parse(path: Path) -> list[dict]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []
    cases = []
    for suite in ([root] if root.tag == "testsuite" else root.iter("testsuite")):
        for tc in suite.findall("testcase"):
            bad = tc.find("failure")
            kind = "failure"
            if bad is None:
                bad, kind = tc.find("error"), "error"
            skipped = tc.find("skipped") is not None
            entry = {"name": f"{tc.get('classname', '')}.{tc.get('name', '')}".strip("."), "time": float(tc.get("time") or 0),
                     "status": kind if bad is not None else "skipped" if skipped else "passed"}
            if bad is not None:
                entry["message"] = first_line(bad.get("message") or bad.text or "") or (bad.get("type") or "")
                entry["type"] = (bad.get("type") or "").split(".")[-1]
                entry["frame"] = project_frame(bad.text or "")
            cases.append(entry)
    return cases


def summarize(root: Path, since: float = 0, globs: list[str] | None = None, paths: list[Path] | None = None) -> dict | None:
    files = paths if paths is not None else find_reports(root, globs or DEFAULT_GLOBS, since)
    if not files:
        return None
    cases = [c for f in files for c in parse(f)]
    if not cases:
        return None
    bad = [c for c in cases if c["status"] in ("failure", "error")]
    return {"files": len(files), "tests": len(cases), "failed": sum(c["status"] == "failure" for c in cases),
            "errors": sum(c["status"] == "error" for c in cases), "skipped": sum(c["status"] == "skipped" for c in cases),
            "seconds": round(sum(c["time"] for c in cases), 1), "bad": bad}


def format_summary(s: dict, top: int = 10) -> list[str]:
    head = f"{s['tests']} tests: {s['failed']} failed, {s['errors']} errors, {s['skipped']} skipped, {s['seconds']}s ({s['files']} report file(s))"
    groups: dict[str, list[dict]] = {}
    for c in s["bad"]:
        groups.setdefault(c["message"][:90], []).append(c)
    lines = [head]
    for message, cs in list(groups.items())[:top]:
        c = cs[0]
        names = c["name"] if len(cs) == 1 else f"{c['name']} (+{len(cs) - 1} more with the same message)"
        lines.append(f"  {c['status'].upper()} {names}")
        lines.append(f"      {c['type'] + ': ' if c['type'] else ''}{c['message']}")
        if c["frame"]:
            lines.append(f"      {c['frame']}")
    if len(groups) > top:
        lines.append(f"  ... and {len(groups) - top} more distinct failure(s)")
    return lines


def cmd_junit(ws: Workspace | None, args: list[str]) -> int:
    since_min, top, as_json, paths = 120.0, 10, False, []
    it = iter(args)
    for a in it:
        if a == "--since":
            try:
                since_min = float(next(it))
            except (StopIteration, ValueError):
                die("--since needs minutes")
        elif a == "--top":
            try:
                top = int(next(it))
            except (StopIteration, ValueError):
                die("--top needs a number")
        elif a == "--json":
            as_json = True
        elif a.startswith("-"):
            die(f"junit: unknown option {a}")
        else:
            paths.append(Path(a))
    explicit = None
    if paths:
        explicit = []
        for p in paths:
            explicit += sorted(p.rglob("*.xml")) if p.is_dir() else [p]
    s = summarize(Path.cwd(), time.time() - since_min * 60, paths=explicit)
    if s is None:
        print(f"no JUnit reports found in the last {since_min:g} minutes under {Path.cwd()} (pass a file or folder, or --since MIN)")
        return 0
    if as_json:
        print(json.dumps(s, separators=(",", ":")))
    else:
        print("\n".join(format_summary(s, top)))
    return 1 if s["failed"] or s["errors"] else 0

"""Compact, token-cheap views over Docker: status, logs, stats, disk, health, ports, env, wait and a guarded clean.

All output is short on purpose (duplicate log lines collapse, secrets are masked). Nothing here starts or stops containers.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time

from .core import Workspace, die

SENSITIVE = re.compile(r"(secret|passw(or)?d|token|api[-_]?key|credential|private|auth)", re.I)
ERRORISH = re.compile(r"\b(error|exception|fatal|panic|traceback|severe|failed|refused|denied|oom)\b", re.I)


def docker(*args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    if not shutil.which("docker"):
        die("docker is not installed or not in PATH")
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        die(f"docker {args[0]} timed out after {timeout:g}s")
    if r.returncode != 0:
        first = (r.stderr.strip().splitlines() or ["unknown error"])[0]
        die(f"docker {' '.join(args[:2])} failed: {first}")
    return r


def json_lines(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def short_ports(ports: str) -> str:
    seen, out = set(), []
    for m in re.finditer(r"(?:[\d.:\[\]a-f]*:)?(\d+)->(\d+)/(\w+)", ports or ""):
        item = f"{m.group(1)}->{m.group(2)}" + ("" if m.group(3) == "tcp" else f"/{m.group(3)}")
        if item not in seen:
            seen.add(item)
            out.append(item)
    return ",".join(out)


def labels(row: dict) -> dict:
    return dict(p.split("=", 1) for p in (row.get("Labels") or "").split(",") if "=" in p)


# ------------------------------------------------------------------- commands
def cmd_status(args: list[str]) -> int:
    show_all, project = "-a" in args, ""
    if "--project" in args:
        project = args[args.index("--project") + 1] if args.index("--project") + 1 < len(args) else ""
    rows = json_lines(docker("ps", *(["-a"] if show_all else []), "--format", "{{json .}}").stdout)
    if project:
        rows = [r for r in rows if labels(r).get("com.docker.compose.project") == project]
    if not rows:
        print("(no containers" + (" for that project" if project else " running; -a shows stopped ones") + ")")
        return 0
    for r in sorted(rows, key=lambda r: (labels(r).get("com.docker.compose.project", ""), r["Names"])):
        proj = labels(r).get("com.docker.compose.project")
        print(f"{r['Names']:<28} {r['Image'][:34]:<34} {r['State']:<9} {r['Status'][:34]:<34} {short_ports(r.get('Ports', ''))}" + (f"  [{proj}]" if proj else ""))
    unhealthy = [r["Names"] for r in rows if "unhealthy" in r["Status"]]
    exited = [r["Names"] for r in rows if r["State"] in ("exited", "dead")]
    if unhealthy:
        print("Unhealthy: " + ", ".join(unhealthy) + "  (ms-workspace docker health <name>)")
    if exited:
        print("Stopped: " + ", ".join(exited))
    return 0


def collapse(lines: list[str], width: int = 300) -> list[str]:
    out, last, count = [], None, 0
    for raw in lines:
        line = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s", "", raw.rstrip())[:width]
        if line == last:
            count += 1
            continue
        if count:
            out[-1] += f"  (x{count + 1})"
        out.append(line)
        last, count = line, 0
    if count:
        out[-1] += f"  (x{count + 1})"
    return out


def cmd_logs(args: list[str]) -> int:
    n, since, errors, names = 60, "", False, []
    it = iter(args)
    for a in it:
        if a == "-n":
            try:
                n = int(next(it))
            except (StopIteration, ValueError):
                die("-n needs a number")
        elif a == "--since":
            since = next(it, "")
        elif a == "--errors":
            errors = True
        elif a.startswith("-"):
            die(f"docker logs: unknown option {a}")
        else:
            names.append(a)
    if len(names) != 1:
        die("usage: docker logs <container> [-n N] [--since 10m] [--errors]")
    r = docker("logs", "--tail", "2000", *(["--since", since] if since else []), names[0], timeout=60)
    lines = (r.stdout + r.stderr).splitlines()
    if errors:
        lines = [l for l in lines if ERRORISH.search(l)]
    kept = collapse(lines)
    print(f"{names[0]}: {len(lines)} {'error-like ' if errors else ''}lines read, {len(kept)} after collapsing repeats; showing the last {min(n, len(kept))}")
    print("\n".join(kept[-n:]) if kept else "(nothing)")
    return 0


def cmd_stats(args: list[str]) -> int:
    rows = json_lines(docker("stats", "--no-stream", "--format", "{{json .}}", timeout=60).stdout)
    if not rows:
        print("(no running containers)")
        return 0
    rows.sort(key=lambda r: -float(r.get("MemPerc", "0%").rstrip("%") or 0))
    for r in rows:
        cpu, mem = float(r["CPUPerc"].rstrip("%") or 0), float(r["MemPerc"].rstrip("%") or 0)
        flag = "  <- high" if cpu > 80 or mem > 80 else ""
        print(f"{r['Name']:<28} cpu {r['CPUPerc']:>7}  mem {r['MemUsage'].split('/')[0].strip():>9} ({r['MemPerc']:>6})  net {r.get('NetIO', '')}  pids {r.get('PIDs', '')}{flag}")
    return 0


def cmd_disk(args: list[str]) -> int:
    for r in json_lines(docker("system", "df", "--format", "{{json .}}").stdout):
        print(f"{r['Type']:<14} {r['TotalCount']:>4} total, {r['Active']:>4} active, size {r['Size']:>9}, reclaimable {r['Reclaimable']}")
    print("Free space safely with: ms-workspace docker clean   (plan first; volumes are never touched without --volumes)")
    return 0


def inspect(name: str) -> dict:
    data = json.loads(docker("inspect", name).stdout or "[]")
    if not data:
        die(f"no such container: {name}")
    return data[0]


def cmd_health(args: list[str]) -> int:
    if not args:
        die("usage: docker health <container>")
    for name in args:
        c = inspect(name)
        st, health = c["State"], c["State"].get("Health")
        print(f"{name}: {st['Status']}" + (f", health {health['Status']}" if health else ", no healthcheck")
              + f", restarts {c.get('RestartCount', 0)}, exit code {st.get('ExitCode')}" + (", OOM-KILLED" if st.get("OOMKilled") else "")
              + f", image {c['Config']['Image']}")
        for entry in (health or {}).get("Log", [])[-3:]:
            print(f"    check exit {entry.get('ExitCode')}: {re.sub(chr(10) + '+', ' / ', (entry.get('Output') or '').strip())[:200]}")
        if st.get("Error"):
            print(f"    error: {st['Error'][:200]}")
    return 0


def cmd_ports(args: list[str]) -> int:
    rows = json_lines(docker("ps", "--format", "{{json .}}").stdout)
    pairs = sorted((m.group(1), r["Names"], m.group(2)) for r in rows for m in re.finditer(r"(?::|^)(\d+)->(\d+)/tcp", r.get("Ports", "")))
    seen = set()
    for host, name, inner in pairs:
        if (host, name) not in seen:
            seen.add((host, name))
            print(f"{host:>6} -> {name}:{inner}")
    if not pairs:
        print("(no published ports)")
    return 0


def cmd_env(args: list[str]) -> int:
    if not args:
        die("usage: docker env <container>")
    env = inspect(args[0])["Config"].get("Env") or []
    print(f"{args[0]}: {len(env)} variables (sensitive values masked)")
    for item in sorted(env)[:60]:
        k, _, v = item.partition("=")
        print(f"  {k}={'***' if SENSITIVE.search(k) else v[:120]}")
    return 0


def cmd_wait(args: list[str]) -> int:
    timeout, names, it = 120.0, [], iter(args)
    for a in it:
        if a == "--timeout":
            try:
                timeout = float(next(it))
            except (StopIteration, ValueError):
                die("--timeout needs seconds")
        else:
            names.append(a)
    if not names:
        die("usage: docker wait <container...> [--timeout 120]")
    deadline, pending = time.time() + timeout, list(names)
    while pending:
        for name in list(pending):
            st = inspect(name)["State"]
            health = (st.get("Health") or {}).get("Status")
            if st["Status"] in ("exited", "dead") or health == "unhealthy" and st.get("Health", {}).get("FailingStreak", 0) >= 3:
                print(f"FAILED {name}: {st['Status']}" + (f", health {health}" if health else "") + f", exit code {st.get('ExitCode')}")
                return 1
            if (health == "healthy") or (health is None and st["Status"] == "running"):
                print(f"ready  {name}" + ("" if health else " (running; no healthcheck defined)"))
                pending.remove(name)
        if pending and time.time() > deadline:
            print("TIMEOUT waiting for: " + ", ".join(pending))
            return 1
        if pending:
            time.sleep(1)
    return 0


def cmd_clean(ws: Workspace | None, args: list[str]) -> int:
    yes, volumes = "--yes" in args, "--volumes" in args
    until = args[args.index("--until") + 1] if "--until" in args and args.index("--until") + 1 < len(args) else "24h"
    stopped = json_lines(docker("ps", "-a", "--filter", "status=exited", "--filter", "status=dead", "--format", "{{json .}}").stdout)
    dangling = json_lines(docker("images", "--filter", "dangling=true", "--format", "{{json .}}").stdout)
    print(f"Would remove: {len(stopped)} stopped container(s)" + (f" ({', '.join(r['Names'] for r in stopped[:6])}{', ...' if len(stopped) > 6 else ''})" if stopped else "")
          + f", {len(dangling)} dangling image(s)" + (f" ({', '.join(r.get('Size', '?') for r in dangling[:6])})" if dangling else ""))
    print(f"Containers stopped for less than {until} are kept." + ("  Volumes: pruned (--volumes)." if volumes else "  Volumes are never touched without --volumes."))
    if not yes:
        print("(plan only; pass --yes to prune)")
        return 0
    print(docker("container", "prune", "-f", "--filter", f"until={until}").stdout.strip().splitlines()[-1])
    print(docker("image", "prune", "-f").stdout.strip().splitlines()[-1])
    if volumes:
        print(docker("volume", "prune", "-f").stdout.strip().splitlines()[-1])
    if ws is not None:
        ws.log("docker.clean", "ok", "", "", f"until={until} volumes={volumes}")
    return 0


def cmd_docker(ws: Workspace | None, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("", [])
    table = {"status": cmd_status, "ps": cmd_status, "logs": cmd_logs, "stats": cmd_stats, "disk": cmd_disk, "health": cmd_health,
             "ports": cmd_ports, "env": cmd_env, "wait": cmd_wait}
    if sub in table:
        return table[sub](rest)
    if sub == "clean":
        return cmd_clean(ws, rest)
    die("usage: docker status|logs|stats|disk|health|ports|env|wait|clean  (read-only except clean --yes)")

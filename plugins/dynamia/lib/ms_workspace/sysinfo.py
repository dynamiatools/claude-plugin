"""Operating-system facts in a handful of lines, with hints when something looks wrong (Linux first, macOS best effort)."""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .core import Workspace, die

TOOLS = ("git", "gh", "python3", "node", "pnpm", "npm", "java", "mvn", "gradle", "docker", "tmux", "jq", "claude", "rtk")


def proc_root() -> Path:
    return Path(os.environ.get("MS_PROC_ROOT") or "/proc")


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def gib(kb: float) -> float:
    return kb / 1024 / 1024


def os_name() -> str:
    text = read(Path(os.environ.get("MS_OS_RELEASE") or "/etc/os-release"))
    for line in text.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def memory() -> dict:
    info = {}
    for line in read(proc_root() / "meminfo").splitlines():
        k, _, v = line.partition(":")
        if v.split():
            info[k] = float(v.split()[0])
    if "MemTotal" not in info:  # macOS and others: total only
        try:
            info = {"MemTotal": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024}
        except (ValueError, OSError, AttributeError):
            return {}
    total, avail = info["MemTotal"], info.get("MemAvailable")
    swap_total, swap_free = info.get("SwapTotal", 0), info.get("SwapFree", 0)
    return {"total_gb": round(gib(total), 1), "available_gb": round(gib(avail), 1) if avail is not None else None,
            "available_pct": round(avail / total * 100) if avail is not None else None,
            "swap_total_gb": round(gib(swap_total), 1), "swap_used_pct": round((swap_total - swap_free) / swap_total * 100) if swap_total else 0}


def cpu() -> dict:
    model = ""
    for line in read(proc_root() / "cpuinfo").splitlines():
        if line.startswith(("model name", "Model name")):
            model = line.partition(":")[2].strip()
            break
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    cores = os.cpu_count() or 1
    return {"cores": cores, "model": model, "load": [round(x, 2) for x in load], "load_per_core": round(load[0] / cores, 2)}


def uptime_seconds() -> float | None:
    parts = read(proc_root() / "uptime").split()
    return float(parts[0]) if parts else None


def dur(seconds: float) -> str:
    s = int(seconds)
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    return f"{d}d {h}h" if d else f"{h}h {m}m" if h else f"{m}m"


def disks(extra: list[Path]) -> list[dict]:
    out, seen = [], set()
    for p in [Path("/"), Path("/tmp"), *extra]:
        try:
            dev = os.stat(p).st_dev
            if dev in seen:
                continue
            seen.add(dev)
            u = shutil.disk_usage(p)
            out.append({"path": str(p), "total_gb": round(u.total / 2**30), "used_pct": round(u.used / u.total * 100), "free_gb": round(u.free / 2**30, 1)})
        except OSError:
            pass
    return out


def primary_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))   # a UDP connect sends nothing; it only selects the outgoing interface
            return s.getsockname()[0]
    except OSError:
        return "n/a"


def container_kind() -> str:
    if Path("/.dockerenv").exists():
        return "docker"
    if "microsoft" in platform.release().lower():
        return "wsl"
    return "no"


def tool_version(name: str) -> str:
    path = shutil.which(name)
    if not path:
        return "missing"
    try:
        r = subprocess.run([name, "-version" if name == "java" else "--version"], capture_output=True, text=True, timeout=4)
        clean = re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + "\n" + (r.stderr or ""))
        for line in clean.splitlines():   # first line that really names a version (Gradle prints a dashed banner first)
            if re.search(r"[A-Za-z]", line) and re.search(r"\d", line):
                return line.strip()[:60]
        return "installed"
    except (OSError, subprocess.TimeoutExpired):
        return "installed (version unknown)"


def collect(ws: Workspace | None, tools: bool) -> dict:
    mem, c = memory(), cpu()
    up = uptime_seconds()
    data = {"os": os_name(), "kernel": f"{platform.system()} {platform.release()} {platform.machine()}", "host": socket.gethostname(),
            "uptime": dur(up) if up else "n/a", "cpu": c, "memory": mem, "disks": disks([ws.root] if ws else [Path.cwd()]),
            "ip": primary_ip(), "timezone": time.strftime("%Z (UTC%z)"), "user": os.environ.get("USER") or os.environ.get("LOGNAME") or "?",
            "shell": os.environ.get("SHELL", "?"), "container": container_kind(), "python": platform.python_version()}
    if tools:
        with ThreadPoolExecutor(max_workers=8) as pool:
            data["tools"] = dict(zip(TOOLS, pool.map(tool_version, TOOLS)))
    hints = []
    if mem.get("available_pct") is not None and mem["available_pct"] < 10:
        hints.append(f"Only {mem['available_gb']}G of memory is available ({mem['available_pct']}%): close heavy processes before running builds (ms-workspace ps --by mem).")
    if mem.get("swap_used_pct", 0) > 50:
        hints.append(f"Swap is {mem['swap_used_pct']}% used: the machine is under memory pressure.")
    if c["load_per_core"] > 1.5:
        hints.append(f"Load {c['load'][0]} on {c['cores']} cores is high: see what is running (ms-workspace ps).")
    for d in data["disks"]:
        if d["used_pct"] >= 90 or d["free_gb"] < 5:
            hints.append(f"{d['path']} is {d['used_pct']}% full ({d['free_gb']}G free): clean build outputs, old worktrees (ms-workspace clean) or Docker (ms-workspace docker disk).")
    data["hints"] = hints
    return data


def cmd_sys(ws: Workspace | None, args: list[str]) -> int:
    unknown = [a for a in args if a not in ("--tools", "--json")]
    if unknown:
        die(f"sys: unknown option {unknown[0]}")
    data = collect(ws, "--tools" in args)
    if "--json" in args:
        print(json.dumps(data, separators=(",", ":")))
        return 0
    c, m = data["cpu"], data["memory"]
    print(f"{data['os']} | {data['kernel']} | host {data['host']} | up {data['uptime']}")
    print(f"CPU: {c['cores']} cores" + (f" ({c['model']})" if c["model"] else "") + f" | load {' '.join(map(str, c['load']))} ({c['load_per_core']}/core)")
    if m:
        avail = f", {m['available_gb']}G available ({m['available_pct']}%)" if m["available_gb"] is not None else ""
        print(f"Memory: {m['total_gb']}G total{avail} | swap {m['swap_total_gb']}G ({m['swap_used_pct']}% used)")
    print("Disk: " + " | ".join(f"{d['path']} {d['used_pct']}% of {d['total_gb']}G ({d['free_gb']}G free)" for d in data["disks"]))
    print(f"Network: {data['ip']} | TZ {data['timezone']} | user {data['user']} | shell {data['shell']} | container: {data['container']} | python {data['python']}")
    if "tools" in data:
        print("Tools: " + ", ".join(f"{k} {v}" for k, v in data["tools"].items()))
    for h in data["hints"]:
        print("Hint: " + h)
    return 0

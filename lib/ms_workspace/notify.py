"""Notifications to wherever you are: ntfy, a webhook, or a local command. Nothing is configured by default.

    ms-workspace notify <message...> [--title T] [--priority low|default|high|urgent] [--test]
    ms-workspace notify --hook                 Notification hook: forwards Claude Code's "needs your attention" message

workspace.toml:
    [notify]
    kind = "ntfy"                  # "ntfy", "webhook" (JSON {"text": ...}) or "command"
    url = "https://ntfy.example.com/my-private-topic"
    # command = "notify-send \"$MS_NOTIFY_TITLE\" \"$MS_NOTIFY_MESSAGE\""   # for kind = "command"
    # field = "text"               # JSON field used by "webhook" (Slack: text, Discord: content)
    on = ["ship"]                  # also notify when `ship --yes` finishes or fails

A public ntfy topic can be read by anyone who guesses its name: use a hard-to-guess topic or your own server.
Secrets in the message are masked, messages are cut to 300 characters, and identical messages within 30 seconds are sent once.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .core import Workspace, die
from .gate import ASSIGNMENT, SECRET_PATTERNS
from .usage import cache_dir

PRIORITIES = ("min", "low", "default", "high", "urgent")


def prepare(text: str, limit: int) -> str:
    for _, rx in SECRET_PATTERNS:
        text = rx.sub("***", text)
    text = ASSIGNMENT.sub(lambda m: m.group(0).replace(m.group(3), "***"), text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def configured(ws: Workspace | None) -> dict | None:
    cfg = (ws.get("notify", default={}) if ws else {}) or {}
    kind = cfg.get("kind") or ("command" if cfg.get("command") else "ntfy" if cfg.get("url") else "")
    return {**cfg, "kind": kind} if kind and (cfg.get("url") or cfg.get("command")) else None


def _key(title: str, message: str) -> str:
    return hashlib.sha1(f"{title}\0{message}".encode()).hexdigest()[:16]


def _recent() -> dict:
    try:
        seen = json.loads((cache_dir() / "notify.json").read_text())
    except (OSError, ValueError):
        return {}
    now = time.time()
    return {k: t for k, t in seen.items() if now - t < 30}


def too_soon(title: str, message: str) -> bool:
    return _key(title, message) in _recent()


def mark_sent(title: str, message: str) -> None:
    seen = _recent()
    seen[_key(title, message)] = time.time()
    try:
        (cache_dir()).mkdir(parents=True, exist_ok=True)
        (cache_dir() / "notify.json").write_text(json.dumps(seen))
    except OSError:
        pass


def deliver(ws: Workspace | None, title: str, message: str, priority: str = "default", force: bool = False) -> tuple[bool, str]:
    cfg = configured(ws)
    if cfg is None:
        return False, "notify is not configured: add a [notify] table (kind, url or command) to workspace.toml"
    name = ws.get("name", default="workspace") if ws else "workspace"
    title, message = prepare(f"{name}: {title}", 80), prepare(message, 300)
    if not force and too_soon(title, message):
        return True, "skipped: the same notification was sent less than 30 seconds ago"
    kind = cfg["kind"]
    ok, info = _send(cfg, kind, title, message, priority)
    if ok:
        mark_sent(title, message)
    return ok, info


def _send(cfg: dict, kind: str, title: str, message: str, priority: str) -> tuple[bool, str]:
    try:
        if kind == "command":
            env = {**os.environ, "MS_NOTIFY_TITLE": title, "MS_NOTIFY_MESSAGE": message, "MS_NOTIFY_PRIORITY": priority}
            r = subprocess.run(["bash", "-c", cfg["command"]], env=env, capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
            return r.returncode == 0, "sent through the local command" if r.returncode == 0 else f"the command failed: {(r.stderr or r.stdout).strip()[:120]}"
        url = cfg.get("url", "")
        if urlsplit(url).scheme not in ("http", "https"):
            return False, "the [notify] url must start with http:// or https://"
        if kind == "webhook":
            data, headers = json.dumps({cfg.get("field", "text"): f"{title}: {message}"}).encode(), {"Content-Type": "application/json"}
        else:
            data = message.encode()
            headers = {"Title": title.encode("ascii", "replace").decode(), "Priority": priority if priority in PRIORITIES else "default", "Tags": "ms-workspace"}
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method="POST"), timeout=10) as r:
            return 200 <= r.status < 300, f"sent ({r.status})"
    except urllib.error.HTTPError as e:
        return False, f"the server answered {e.code}"
    except (urllib.error.URLError, OSError, subprocess.TimeoutExpired, ValueError) as e:
        return False, f"could not send: {getattr(e, 'reason', e)}"


def notify_event(ws: Workspace | None, event: str, title: str, message: str, priority: str = "default") -> None:
    """Used by other commands (ship): silent unless [notify] lists the event in `on`; never raises."""
    try:
        if ws is not None and event in (ws.get("notify", "on", default=[]) or []):
            ok, info = deliver(ws, title, message, priority)
            if not ok:
                print(f"warning: notification not sent ({info})", file=sys.stderr)
    except Exception:
        pass


def cmd_notify(ws: Workspace | None, args: list[str]) -> int:
    if "--hook" in args:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
            deliver(ws, str(payload.get("title") or "Claude Code"), str(payload.get("message") or "Claude Code needs your attention"),
                    "high" if "permission" in str(payload.get("message", "")).lower() else "default")
        except Exception:
            pass
        return 0
    title, priority, test, words, it = "Notification", "default", False, [], iter(args)
    for a in it:
        if a == "--title":
            title = next(it, title)
        elif a == "--priority":
            priority = next(it, "default")
            if priority not in PRIORITIES:
                die(f"--priority is one of {', '.join(PRIORITIES)}")
        elif a == "--test":
            test = True
        elif a.startswith("-"):
            die(f"notify: unknown option {a}")
        else:
            words.append(a)
    if test:
        words = words or ["This is a test notification from ms-workspace."]
    if not words:
        die("usage: notify <message...> [--title T] [--priority P] | --test | --hook")
    ok, info = deliver(ws, title, " ".join(words), priority, force=test)
    print(info, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1

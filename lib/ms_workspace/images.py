"""Archive images pasted in chat. Claude Code keeps them only as base64 blocks inside the session transcript."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from .core import int_arg, Workspace, die

EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}


def img_dir(ws: Workspace) -> Path:
    return ws.state_dir / "images"


def _local(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def _user_images(line: str):
    """Yield (timestamp, cwd, text, [(media_type, data)]) for a transcript line holding pasted images."""
    try:
        d = json.loads(line)
    except ValueError:
        return None
    msg = d.get("message") if isinstance(d, dict) else None
    if not isinstance(msg, dict) or msg.get("role") != "user" or not isinstance(msg.get("content"), list):
        return None
    blocks = [b for b in msg["content"] if isinstance(b, dict)]
    imgs = [((b.get("source") or {}).get("media_type", ""), (b.get("source") or {}).get("data", ""))
            for b in blocks if b.get("type") == "image"]
    if not imgs:
        return None
    text = re.sub(r"\s+", " ", " ".join(b.get("text", "") for b in blocks if b.get("type") == "text"))[:140]
    return d.get("timestamp", ""), d.get("cwd") or "", text, imgs


def extract_images(ws: Workspace, transcript: Path, session: str) -> int:
    """Save images from the not-yet-processed part of a transcript; returns how many were saved."""
    d = img_dir(ws)
    (d / ".state").mkdir(parents=True, exist_ok=True)
    state = d / ".state" / session
    offset = int(state.read_text() or 0) if state.exists() else 0
    size = transcript.stat().st_size
    if offset > size:
        offset = 0
    if offset == size:
        return 0
    with open(transcript, "rb") as fh:
        fh.seek(offset)
        data = fh.read()
    if not data.endswith(b"\n"):  # last line is still being written: leave it for next time
        data = data[: data.rfind(b"\n") + 1]
    seen = set()
    index = d / "index.jsonl"
    if index.exists():
        for l in index.read_text().splitlines():
            try:
                seen.add(json.loads(l)["sha"])
            except (ValueError, KeyError):
                pass
    saved = 0
    for raw in data.decode("utf-8", errors="replace").splitlines():
        found = _user_images(raw)
        if not found:
            continue
        ts, cwd, text, imgs = found
        when = _local(ts)
        day = when.strftime("%Y-%m-%d") if when else ts[:10] or time.strftime("%Y-%m-%d")
        tm = when.strftime("%H%M%S") if when else "000000"
        for i, (mt, b64) in enumerate(imgs, 1):
            try:
                blob = base64.b64decode(b64, validate=False)
            except (binascii.Error, ValueError):
                continue
            sha = hashlib.sha1(blob).hexdigest()
            if not blob or sha in seen:
                continue
            seen.add(sha)
            target = d / day / f"{tm}_{session[:8]}_{i}.{EXT.get(mt, 'bin')}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            entry = {"ts": ts, "session": session, "file": str(target.relative_to(ws.root)), "media_type": mt,
                     "sha": sha, "bytes": len(blob), "cwd": cwd, "text": text}
            with open(index, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, separators=(",", ":"), ensure_ascii=False) + "\n")
            saved += 1
    state.write_text(str(offset + len(data)))
    return saved


def prune(ws: Workspace) -> None:
    """Once a day: delete old image files and drop index lines whose file is gone."""
    d = img_dir(ws)
    marker = d / ".state" / ".pruned"
    if marker.exists() and time.time() - marker.stat().st_mtime < 86400:
        return
    (d / ".state").mkdir(parents=True, exist_ok=True)
    marker.touch()
    cutoff = time.time() - float(ws.get("images_retention_days", default=30)) * 86400
    for p in d.rglob("*"):
        if p.is_file() and p.name != "index.jsonl" and ".state" not in p.parts and p.stat().st_mtime < cutoff:
            p.unlink()
    for p in sorted(d.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and p != d and ".state" not in p.parts and not any(p.iterdir()):
            p.rmdir()
    index = d / "index.jsonl"
    if index.exists():
        keep = []
        for l in index.read_text().splitlines():
            try:
                if (ws.root / json.loads(l)["file"]).exists():
                    keep.append(l)
            except (ValueError, KeyError):
                pass
        index.write_text("".join(l + "\n" for l in keep))


def capture(args: list[str]) -> int:
    """Stop/SessionEnd hook: never fails the session."""
    try:
        payload = json.loads(sys.stdin.read())
        tp, sid, cwd = payload.get("transcript_path"), payload.get("session_id"), payload.get("cwd")
        if not (tp and sid and Path(tp).is_file()):
            return 0
        ws = Workspace.load(required=False, start=cwd if cwd and os.path.isdir(cwd) else None)
        if ws is None:
            return 0
        n = extract_images(ws, Path(tp), sid)
        if n:
            ws.log("images", "ok", "", "", f"saved {n} from session {sid[:8]}")
        prune(ws)
    except Exception:
        pass
    return 0


def backfill(ws: Workspace) -> int:
    total = 0
    projects = Path(os.environ.get("HOME", "~")).expanduser() / ".claude" / "projects"
    for f in sorted(projects.glob("*/*.jsonl")):
        cwd = ""
        with open(f, errors="replace") as fh:
            for _, l in zip(range(20), fh):
                try:
                    cwd = json.loads(l).get("cwd") or ""
                except ValueError:
                    continue
                if cwd:
                    break
        if cwd and (cwd == str(ws.root) or cwd.startswith(str(ws.root) + "/")):
            total += extract_images(ws, f, f.stem)
    print(f"Saved {total} image(s) into {img_dir(ws)}")
    ws.log("images", "ok", "", "", f"backfill saved {total}")
    return 0


def list_images(ws: Workspace, args: list[str]) -> int:
    n, day = 10, ""
    it = iter(args)
    for a in it:
        if a == "-n":
            n = int_arg(it, "-n", 10)
        elif a == "--day":
            day = next(it)
        else:
            die(f"images list: unknown option {a}")
    index = img_dir(ws) / "index.jsonl"
    if not index.exists():
        print("(no images archived yet)")
        return 0
    rows = []
    for l in index.read_text().splitlines():
        e = json.loads(l)
        if day and f"/{day}/" not in e["file"]:
            continue
        text = re.sub(r"\s+", " ", e.get("text", ""))
        rows.append(f"{e['ts'][:19]} {ws.root}/{e['file']} ({e['bytes'] // 1024}KB)" + (f" - {text}" if text else ""))
    print("\n".join(rows[-n:]))
    return 0


def cmd_images(args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    if sub == "capture":
        return capture(rest)
    ws = Workspace.load()
    if sub == "backfill":
        return backfill(ws)
    if sub == "list":
        return list_images(ws, rest)
    die("usage: images [list [-n N] [--day D] | capture | backfill]")

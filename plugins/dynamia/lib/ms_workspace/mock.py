"""Local mock server for third-party APIs: canned responses, templates, response sequences, and a record of every call.

    ms-workspace mock start <file|name> [--port N] [--restart]   run in the background on 127.0.0.1
    ms-workspace mock status | url [name] | stop [name|--all]
    ms-workspace mock requests [name] [-n N] [--unmatched] [--path P] [--method M]
    ms-workspace mock assert [name] --path P [--method M] [--times N | --min N | --none] [--json k=v] [--query k=v] [--header k=v]

Definitions live in mocks/*.mock.toml. Standard library only; the server listens on localhost only.
"""
from __future__ import annotations

import http.server
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .apitest import jpath, mask_body, mask_headers, Env, same
from .core import MsError, Workspace, die
from .usage import cache_dir

LIB = Path(__file__).resolve().parents[1]
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)(?:\.([^}\s]+))?\s*\}\}")


# ------------------------------------------------------------------ locations
def defs_dir(ws: Workspace | None) -> Path:
    return ws.root / ws.get("mock", "dir", default="mocks") if ws else Path.cwd() / "mocks"


def state_root(ws: Workspace | None) -> Path:
    return (ws.state_dir if ws else cache_dir()) / "mock"


def name_of(ref: str) -> str:
    stem = Path(ref).name
    for suffix in (".mock.toml", ".toml"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def find_def(ws: Workspace | None, ref: str) -> Path:
    for cand in (Path(ref), defs_dir(ws) / ref, defs_dir(ws) / f"{ref}.mock.toml"):
        if cand.is_file():
            return cand
    die(f"mock definition '{ref}' not found (looked in {defs_dir(ws)})")


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:   # a zombie (exited, not yet reaped by its adoptive parent) is not running
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("State:"):
                return "Z" not in line.split(":", 1)[1].split()[0]
    except OSError:
        pass
    return True


def read_state(ws, name: str) -> dict | None:
    f = state_root(ws) / name / "server.json"
    try:
        info = json.loads(f.read_text())
    except (OSError, ValueError):
        return None
    info["alive"] = alive(info["pid"])
    return info


def running(ws) -> list[dict]:
    out = []
    root = state_root(ws)
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        info = read_state(ws, d.name)
        if info:
            out.append(info)
    return out


def pick_name(ws, given: str | None) -> str:
    if given:
        return name_of(given)
    live = [i for i in running(ws) if i["alive"]]
    if len(live) == 1:
        return live[0]["name"]
    die("name the mock: " + (", ".join(i["name"] for i in live) if live else "none is running (see: ms-workspace mock start)"))


# --------------------------------------------------------------- definitions
def load_def(path: Path) -> dict:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        die(f"{path}: {e}")
    if not data.get("route"):
        die(f"{path}: no [[route]] tables found")
    for i, r in enumerate(data["route"], 1):
        r.setdefault("name", f"route-{i}")
        if not any(k in r for k in ("json", "body", "sequence", "status")):
            die(f"{path}: route '{r['name']}' defines no response (json, body, sequence or status)")
    return data


def path_regex(pattern: str):
    if pattern.endswith("*"):
        return re.compile("^" + re.escape(pattern[:-1]) + ".*$")
    parts = [f"(?P<{p[1:-1]}>[^/]+)" if re.fullmatch(r"\{\w+\}", p) else re.escape(p) for p in pattern.split("/")]
    return re.compile("^" + "/".join(parts) + "$")


def matches(route: dict, rx, method: str, path: str, query: dict, headers: dict, body_json) -> dict | None:
    if str(route.get("method", "ANY")).upper() not in ("ANY", method):
        return None
    m = rx.match(path)
    if not m:
        return None
    cond = route.get("match") or {}
    for dotted, want in (cond.get("json") or {}).items():
        try:
            got = jpath(body_json, dotted)
        except KeyError:
            return None
        if want != "*" and not same(got, want):
            return None
    for k, want in (cond.get("query") or {}).items():
        if str(query.get(k)) != str(want):
            return None
    for k, want in (cond.get("headers") or {}).items():
        if str(want).lower() not in headers.get(k.lower(), "").lower():
            return None
    return m.groupdict()


def resolve(kind: str, dotted: str | None, ctx: dict):
    if kind == "uuid":
        return str(uuid.uuid4())
    if kind == "now":
        return time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if kind == "seq":
        return ctx["seq"]
    root = ctx.get(kind)
    if dotted is None:
        return root
    try:
        return jpath(root, dotted) if kind == "body" else root.get(dotted.lower() if kind == "header" else dotted)
    except (KeyError, AttributeError):
        return None


def template(value, ctx: dict):
    """{{path.id}} {{query.x}} {{body.a.b}} {{header.x}} {{seq}} {{uuid}} {{now}}. A value that is exactly one
    placeholder keeps its JSON type (a number stays a number)."""
    if isinstance(value, str):
        whole = PLACEHOLDER.fullmatch(value.strip())
        if whole:
            return resolve(whole.group(1), whole.group(2), ctx)
        return PLACEHOLDER.sub(lambda m: "" if (v := resolve(m.group(1), m.group(2), ctx)) is None else str(v), value)
    if isinstance(value, dict):
        return {k: template(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [template(v, ctx) for v in value]
    return value


# -------------------------------------------------------------------- server
def serve_main(argv: list[str]) -> None:
    """Blocking server process (started by `mock start`): argv = def_path name state_dir port."""
    path, name, state_dir, port = Path(argv[0]), argv[1], Path(argv[2]), int(argv[3])
    data = load_def(path)
    routes = [(r, path_regex(r.get("path", "/"))) for r in data["route"]]
    counters = [0] * len(routes)
    lock = threading.Lock()
    log_file = state_dir / "requests.jsonl"
    masker = Env("mock", {}, {}, {})

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *a):
            pass

        def handle_any(self):
            started = time.perf_counter()
            parts = urlsplit(self.path)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
            try:
                body_json = json.loads(raw) if raw.strip()[:1] in ("{", "[") else None
            except ValueError:
                body_json = None
            headers = {k.lower(): v for k, v in self.headers.items()}
            hit = None
            with lock:
                for i, (route, rx) in enumerate(routes):
                    params = matches(route, rx, self.command, parts.path, query, headers, body_json)
                    if params is not None:
                        counters[i] += 1
                        hit = (i, route, params, counters[i])
                        break
            if hit is None:
                status, payload, ctype, extra, delay, idx = 404, json.dumps({"error": "no mock route", "method": self.command, "path": parts.path}), "application/json", {}, 0, None
            else:
                idx, route, params, seq = hit
                spec = route
                if route.get("sequence"):
                    steps = route["sequence"]
                    spec = {**{k: v for k, v in route.items() if k != "sequence"}, **steps[(seq - 1) % len(steps) if route.get("loop") else min(seq - 1, len(steps) - 1)]}
                ctx = {"path": params, "query": query, "body": body_json if body_json is not None else {}, "header": headers, "seq": seq}
                status = int(spec.get("status", 200))
                extra = {k: str(template(v, ctx)) for k, v in (spec.get("headers") or {}).items()}
                delay = int(spec.get("delay_ms", 0))
                if "json" in spec:
                    payload, ctype = json.dumps(template(spec["json"], ctx)), "application/json"
                else:
                    payload, ctype = str(template(spec.get("body", ""), ctx)), spec.get("content_type", "text/plain")
            if delay:
                time.sleep(delay / 1000)
            data_bytes = payload.encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            for k, v in extra.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data_bytes)))
            self.end_headers()
            try:
                self.wfile.write(data_bytes)
            except (BrokenPipeError, ConnectionResetError):
                pass
            record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "method": self.command, "path": parts.path, "query": query,
                      "headers": mask_headers(headers, masker), "body": mask_body(raw, masker) if raw else "",
                      "route": idx, "route_name": routes[idx][0]["name"] if idx is not None else None,
                      "status": status, "ms": round((time.perf_counter() - started) * 1000, 1)}
            with lock, open(log_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = handle_any

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True

    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "server.json").write_text(json.dumps({"name": name, "pid": os.getpid(), "port": server.server_address[1], "file": str(path),
                                                       "routes": len(routes), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}))
    try:
        server.serve_forever()
    finally:
        server.server_close()
        (state_dir / "server.json").unlink(missing_ok=True)


# ------------------------------------------------------------------ commands
def cmd_start(ws, args: list[str]) -> int:
    refs = [a for a in args if not a.startswith("-")]
    port, restart = None, "--restart" in args
    if "--port" in args:
        try:
            port = int(args[args.index("--port") + 1])
            refs = [r for r in refs if r != str(port)]
        except (IndexError, ValueError):
            die("--port needs a number")
    if not refs:
        die("usage: mock start <file|name> [--port N] [--restart]")
    path = find_def(ws, refs[0])
    data = load_def(path)
    name = name_of(refs[0])
    info = read_state(ws, name)
    if info and info["alive"]:
        if not restart:
            print(f"mock '{name}' is already running at http://127.0.0.1:{info['port']} (pid {info['pid']}); --restart to reload the definition")
            return 0
        os.kill(info["pid"], signal.SIGTERM)
        for _ in range(50):
            if not alive(info["pid"]):
                break
            time.sleep(0.1)
    state = state_root(ws) / name
    state.mkdir(parents=True, exist_ok=True)
    (state / "server.json").unlink(missing_ok=True)
    (state / "requests.jsonl").write_text("")
    wanted = port if port is not None else int(data.get("port", 0))
    boot = (f"import sys; sys.path.insert(0, {str(LIB)!r}); from ms_workspace.mock import serve_main; serve_main(sys.argv[1:])")
    with open(state / "server.log", "w") as logf:
        proc = subprocess.Popen([sys.executable, "-c", boot, str(path), name, str(state), str(wanted)], stdout=logf, stderr=logf,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(100):
        info = read_state(ws, name)
        if info and info["pid"] == proc.pid:
            break
        if proc.poll() is not None:
            die(f"the mock server exited at startup: {(state / 'server.log').read_text().strip()[-300:]}")
        time.sleep(0.05)
    else:
        proc.terminate()
        die("the mock server did not start within 5 seconds")
    print(f"mock '{name}' listening on http://127.0.0.1:{info['port']} (pid {info['pid']}, {info['routes']} routes)")
    if ws is not None:
        ws.log("mock.start", "ok", "", "", f"{name} port {info['port']}")
    return 0


def cmd_stop(ws, args: list[str]) -> int:
    targets = [i for i in running(ws)] if "--all" in args else [read_state(ws, pick_name(ws, next((a for a in args if not a.startswith("-")), None)))]
    stopped = 0
    for info in targets:
        if not info:
            die("that mock is not running")
        if info["alive"]:
            os.kill(info["pid"], signal.SIGTERM)
            for _ in range(50):
                if not alive(info["pid"]):
                    break
                time.sleep(0.1)
            else:
                os.kill(info["pid"], signal.SIGKILL)
            stopped += 1
            print(f"stopped mock '{info['name']}' (pid {info['pid']})")
        (state_root(ws) / info["name"] / "server.json").unlink(missing_ok=True)
    if not targets:
        print("no mock servers are running")
    return 0


def cmd_status(ws, args: list[str]) -> int:
    infos = running(ws)
    if not infos:
        print("no mock servers are running")
        return 0
    for i in infos:
        log = state_root(ws) / i["name"] / "requests.jsonl"
        n = sum(1 for _ in open(log)) if log.exists() else 0
        state = f"http://127.0.0.1:{i['port']} pid {i['pid']}" if i["alive"] else "DEAD (stale state; start it again)"
        print(f"{i['name']}: {state}, {i['routes']} routes, {n} requests recorded, since {i['started']}")
    return 0


def recorded(ws, name: str) -> list[dict]:
    f = state_root(ws) / name / "requests.jsonl"
    if not f.exists():
        die(f"mock '{name}' has no record (was it started?)")
    rows = []
    for l in f.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(l))
        except ValueError:
            pass
    return rows


def cmd_requests(ws, args: list[str]) -> int:
    n, unmatched, path, method, rest = 20, False, "", "", []
    it = iter(args)
    for a in it:
        if a == "-n":
            try:
                n = int(next(it))
            except (StopIteration, ValueError):
                die("-n needs a number")
        elif a == "--unmatched":
            unmatched = True
        elif a == "--path":
            path = next(it, "")
        elif a == "--method":
            method = next(it, "").upper()
        elif a.startswith("-"):
            die(f"mock requests: unknown option {a}")
        else:
            rest.append(a)
    rows = [r for r in recorded(ws, pick_name(ws, rest[0] if rest else None))
            if (not unmatched or r["route"] is None) and path in r["path"] and (not method or r["method"] == method)]
    if not rows:
        print("(no matching requests)")
    for r in rows[-n:]:
        q = ("?" + "&".join(f"{k}={v}" for k, v in r["query"].items())) if r["query"] else ""
        body = f"  body: {r['body'][:100]}" if r["body"] else ""
        print(f"{r['ts'][11:]} {r['method']} {r['path']}{q} -> {r['status']} ({r['route_name'] or 'NO ROUTE'}, {r['ms']}ms){body}")
    return 0


def parse_kv(items: list[str]) -> dict:
    out = {}
    for item in items:
        k, _, v = item.partition("=")
        try:
            out[k] = json.loads(v)
        except ValueError:
            out[k] = v
    return out


def cmd_assert(ws, args: list[str]) -> int:
    opts = {"path": "", "method": "", "times": None, "min": None, "json": [], "query": [], "header": [], "no_unmatched": False}
    rest, it = [], iter(args)
    for a in it:
        if a in ("--path", "--method", "--times", "--min", "--json", "--query", "--header"):
            v = next(it, "")
            key = a[2:]
            if key in ("json", "query", "header"):
                opts[key].append(v)
            elif key in ("times", "min"):
                try:
                    opts[key] = int(v)
                except ValueError:
                    die(f"{a} needs a number")
            else:
                opts[key] = v.upper() if key == "method" else v
        elif a == "--none":
            opts["times"] = 0
        elif a == "--no-unmatched":
            opts["no_unmatched"] = True
        elif a.startswith("-"):
            die(f"mock assert: unknown option {a}")
        else:
            rest.append(a)
    name = pick_name(ws, rest[0] if rest else None)
    rows = recorded(ws, name)
    if opts["no_unmatched"]:
        bad = [r for r in rows if r["route"] is None]
        if bad:
            print(f"FAILED: {len(bad)} request(s) hit no route, for example {bad[0]['method']} {bad[0]['path']}")
            return 1
        print("OK: every request matched a route")
        if not opts["path"]:
            return 0
    if not opts["path"]:
        die("mock assert needs --path (or --no-unmatched)")
    rx = path_regex(opts["path"])
    want_json, want_q, want_h = parse_kv(opts["json"]), parse_kv(opts["query"]), parse_kv(opts["header"])
    hits = []
    for r in rows:
        if not rx.match(r["path"]) or (opts["method"] and r["method"] != opts["method"]):
            continue
        if any(str(r["query"].get(k)) != str(v) for k, v in want_q.items()):
            continue
        if any(str(v).lower() not in r["headers"].get(k.lower(), "").lower() for k, v in want_h.items()):
            continue
        if want_json:
            try:
                body = json.loads(r["body"])
                if any(not same(jpath(body, k), v) for k, v in want_json.items()):
                    continue
            except (ValueError, KeyError):
                continue
        hits.append(r)
    n, exact, minimum = len(hits), opts["times"], opts["min"]
    ok = (n == exact) if exact is not None else (n >= (minimum if minimum is not None else 1))
    label = f"exactly {exact}" if exact is not None else f"at least {minimum if minimum is not None else 1}"
    if ok:
        print(f"OK: {n} matching request(s) to {opts['path']} (expected {label}) among {len(rows)} recorded")
        return 0
    print(f"FAILED: expected {label} matching request(s) to {opts['path']}, found {n} among {len(rows)} recorded")
    near = [r for r in rows if rx.match(r["path"])][-2:]
    for r in near:
        print(f"  closest: {r['method']} {r['path']} query={r['query']} body={r['body'][:120]}")
    return 1


def cmd_mock(ws: Workspace | None, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("", [])
    if sub == "start":
        return cmd_start(ws, rest)
    if sub == "stop":
        return cmd_stop(ws, rest)
    if sub == "status":
        return cmd_status(ws, rest)
    if sub == "url":
        info = read_state(ws, pick_name(ws, rest[0] if rest else None))
        if not info or not info["alive"]:
            die("that mock is not running")
        print(f"http://127.0.0.1:{info['port']}")
        return 0
    if sub == "requests":
        return cmd_requests(ws, rest)
    if sub == "assert":
        return cmd_assert(ws, rest)
    if sub == "list":
        d = defs_dir(ws)
        files = sorted(d.glob("*.mock.toml")) if d.is_dir() else []
        if not files:
            print(f"(no *.mock.toml files in {d})")
        for f in files:
            try:
                print(f"{f.name[:-10]}: {len(load_def(f)['route'])} routes")
            except MsError as e:
                print(f"{f.name[:-10]}: invalid ({e})")
        return 0
    die("usage: mock start|stop|status|url|list|requests|assert  (definitions live in <workspace>/mocks/*.mock.toml)")

"""API checks: requests described in *.http.toml files, with assertions, captured variables and a log of every exchange.

    ms-workspace http run <file|name> [--env E] [--var k=v] [--only a,b] [--tag t] [--fail-fast] [--yes] [--json]
    ms-workspace http list | history | show <run> [request] | diff <run> [run] | bench <file> --name R [-n N]

Standard library only. Secrets never reach the log or the output: {{secret:NAME}} values and well-known
sensitive headers and JSON keys are masked.
"""
from __future__ import annotations

import json
import os
import re
import secrets as _secrets
import ssl
import statistics
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .core import MsError, Workspace, die
from .usage import cache_dir

SENSITIVE = re.compile(r"(authorization|cookie|token|secret|passw(or)?d|api[-_]?key|credential)", re.I)
BODY_LOG_MAX = 4000
VAR = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class Missing(Exception):
    """A {{variable}} has no value yet (usually because an earlier request failed)."""


# ----------------------------------------------------------------- locations
def base_dir(ws: Workspace | None) -> Path:
    if ws is None:
        return Path.cwd() / "requests"
    return ws.root / ws.get("http", "dir", default="requests")


def log_dir(ws: Workspace | None) -> Path:
    return (ws.state_dir if ws else cache_dir()) / "http"


def find_file(ws: Workspace | None, ref: str) -> Path:
    for cand in (Path(ref), base_dir(ws) / ref, base_dir(ws) / f"{ref}.http.toml"):
        if cand.is_file():
            return cand
    die(f"request file '{ref}' not found (looked in {base_dir(ws)})")


# ------------------------------------------------------------ environments
class Env:
    def __init__(self, name: str, variables: dict, secret_values: dict, options: dict):
        self.name, self.vars, self.secrets, self.options = name, variables, secret_values, options

    @property
    def secret_texts(self) -> set[str]:
        return {v for v in self.secrets.values() if v}


def load_env(ws: Workspace | None, directory: Path, name: str, cli_vars: dict) -> Env:
    folder = directory / "env"
    variables, options = {}, {}
    toml_file = folder / f"{name}.toml"
    if toml_file.is_file():
        try:
            data = tomllib.loads(toml_file.read_text())
        except tomllib.TOMLDecodeError as e:
            die(f"{toml_file}: {e}")
        options = {k: data.pop(k) for k in ("confirm", "insecure", "timeout") if k in data}
        variables.update({k: str(v) for k, v in data.items() if not isinstance(v, dict)})
        variables.update({k: str(v) for k, v in (data.get("vars") or {}).items()})
    elif name != "local":
        die(f"environment '{name}' not found: expected {toml_file}")
    secret_values = {}
    sec_file = folder / f"{name}.secrets"
    if sec_file.is_file():
        for line in sec_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, _, v = line.partition("=")
                secret_values[k.strip()] = v.strip().strip("'\"")
    variables.update(cli_vars)
    return Env(name, variables, secret_values, options)


def render(value, env: Env, captured: dict):
    """Replace {{name}}, {{env:NAME}} and {{secret:NAME}} in strings, recursively."""
    if isinstance(value, str):
        def sub(m):
            key = m.group(1)
            if key.startswith("env:"):
                got = os.environ.get(key[4:])
            elif key.startswith("secret:"):
                got = env.secrets.get(key[7:]) or os.environ.get(key[7:])
                if got:
                    env.secrets[key[7:]] = got
            else:
                got = captured.get(key, env.vars.get(key))
            if got is None:
                raise Missing(key)
            return str(got)
        return VAR.sub(sub, value)
    if isinstance(value, dict):
        return {k: render(v, env, captured) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, env, captured) for v in value]
    return value


# ------------------------------------------------------------------- masking
def mask_text(text: str, env: Env) -> str:
    for secret in sorted(env.secret_texts, key=len, reverse=True):
        text = text.replace(secret, "***")
    return text


def mask_json(node, env: Env):
    if isinstance(node, dict):
        return {k: ("***" if SENSITIVE.search(k) and not isinstance(v, (dict, list)) else mask_json(v, env)) for k, v in node.items()}
    if isinstance(node, list):
        return [mask_json(v, env) for v in node]
    return node


def mask_body(body: str, env: Env) -> str:
    try:
        body = json.dumps(mask_json(json.loads(body), env), ensure_ascii=False, separators=(",", ":"))
    except ValueError:
        pass
    return mask_text(body, env)[:BODY_LOG_MAX]


def mask_headers(headers: dict, env: Env) -> dict:
    return {k: ("***" if SENSITIVE.search(k) else mask_text(str(v), env)) for k, v in headers.items()}


def mask_url(url: str, env: Env) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.urlencode([(k, "***" if SENSITIVE.search(k) else v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)])
    return mask_text(urllib.parse.urlunsplit(parts._replace(query=query)), env)


# --------------------------------------------------------------- JSON helpers
def jpath(data, path: str):
    """Dotted path with list indexes ('user.name', 'items.0.id'); raises KeyError when absent."""
    node = data
    for part in path.lstrip("$.").split("."):
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                raise KeyError(path)
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise KeyError(path)
    return node


def same(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    return a == b


# ----------------------------------------------------------------------- send
class Response:
    def __init__(self, status=0, headers=None, body="", ms=0.0, error=""):
        self.status, self.headers, self.body, self.ms, self.error = status, headers or {}, body, ms, error
        self.json = None
        try:
            self.json = json.loads(body) if body.strip()[:1] in ("{", "[") else None
        except ValueError:
            pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def send(method: str, url: str, headers: dict, body: bytes | None, timeout: float, insecure: bool, follow: bool) -> Response:
    handlers = [] if follow else [_NoRedirect()]
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    start = time.perf_counter()
    try:
        with opener.open(req, timeout=timeout) as r:
            raw, status, hdrs = r.read(), r.status, dict(r.headers.items())
    except urllib.error.HTTPError as e:
        raw, status, hdrs = e.read(), e.code, dict(e.headers.items())
    except (urllib.error.URLError, OSError, ValueError) as e:
        reason = getattr(e, "reason", e)
        return Response(error=f"{type(reason).__name__}: {reason}", ms=(time.perf_counter() - start) * 1000)
    ms = (time.perf_counter() - start) * 1000
    return Response(status, {k.lower(): v for k, v in hdrs.items()}, raw.decode("utf-8", errors="replace"), ms)


def build(req: dict, defaults: dict, env: Env, captured: dict, timeout_cli: float | None):
    """Render a request definition into (method, url, headers, body_bytes, timeout)."""
    r = {**defaults, **req}
    base = render(r.get("base_url") or env.vars.get("base_url") or "", env, captured)
    path = render(r.get("path", ""), env, captured)
    url = path if re.match(r"^https?://", path) else base.rstrip("/") + "/" + path.lstrip("/")
    query = render(r.get("query") or {}, env, captured)
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query, doseq=True)
    headers = {**render(defaults.get("headers") or {}, env, captured), **render(req.get("headers") or {}, env, captured)}
    body = None
    if "json" in r:
        body = json.dumps(render(r["json"], env, captured)).encode()
        headers.setdefault("Content-Type", "application/json")
    elif "form" in r:
        body = urllib.parse.urlencode(render(r["form"], env, captured)).encode()
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif "body" in r:
        body = render(str(r["body"]), env, captured).encode()
    method = str(r.get("method", "GET")).upper()
    timeout = timeout_cli or float(r.get("timeout") or env.options.get("timeout") or 15)
    return method, url, headers, body, timeout


def evaluate(expect: dict, resp: Response, env: Env, captured: dict) -> list[str]:
    fails = []
    if resp.error:
        return [f"no response: {resp.error}"]
    status = expect.get("status")
    if status is not None:
        allowed = status if isinstance(status, list) else [status]
        if resp.status not in allowed:
            fails.append(f"status: expected {' or '.join(map(str, allowed))}, got {resp.status}")
    elif resp.status >= 400:
        fails.append(f"status: got {resp.status} (no expected status set; 2xx and 3xx pass)")
    if "max_ms" in expect and resp.ms > expect["max_ms"]:
        fails.append(f"time: {resp.ms:.0f}ms is over the limit of {expect['max_ms']}ms")
    for path, want in (expect.get("json") or {}).items():
        want = render(want, env, captured)
        try:
            got = jpath(resp.json, path)
        except KeyError:
            fails.append(f"json {path}: missing" + ("" if resp.json is not None else " (the response is not JSON)"))
            continue
        if not same(got, want):
            fails.append(f"json {path}: expected {want!r}, got {got!r}")
    for path in expect.get("json_exists") or []:
        try:
            jpath(resp.json, path)
        except KeyError:
            fails.append(f"json_exists {path}: missing")
    for text in expect.get("body_contains") or []:
        if render(text, env, captured) not in resp.body:
            fails.append(f"body_contains {text!r}: not found")
    for text in expect.get("body_not_contains") or []:
        if render(text, env, captured) in resp.body:
            fails.append(f"body_not_contains {text!r}: found")
    for name, want in (expect.get("headers") or {}).items():
        got = resp.headers.get(name.lower())
        if got is None or render(want, env, captured).lower() not in got.lower():
            fails.append(f"header {name}: expected {want!r}, got {got!r}")
    return fails


def capture(rules: dict, resp: Response) -> tuple[dict, list[str]]:
    got, problems = {}, []
    for name, rule in (rules or {}).items():
        kind, _, arg = rule.partition(":")
        value = None
        if kind == "json" and resp.json is not None:
            try:
                value = jpath(resp.json, arg)
            except KeyError:
                pass
        elif kind == "header":
            value = resp.headers.get(arg.lower())
        elif kind == "regex":
            m = re.search(arg, resp.body)
            value = m.group(1) if m and m.groups() else (m.group(0) if m else None)
        elif kind == "status":
            value = resp.status
        if value is None:
            problems.append(f"capture {name}: nothing matched '{rule}'")
        else:
            got[name] = value
    return got, problems


# --------------------------------------------------------------------- logging
def _append(ws, record: dict) -> Path:
    d = log_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{time.strftime('%Y-%m-%d')}.jsonl"
    if not path.exists():
        cutoff = time.time() - float(ws.get("log_retention_days", default=14) if ws else 14) * 86400
        for old in d.glob("*.jsonl"):
            if old.stat().st_mtime < cutoff:
                old.unlink()
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n")
    return path


def load_log(ws, days: float = 14) -> list[dict]:
    d = log_dir(ws)
    rows = []
    for f in sorted(d.glob("*.jsonl")) if d.is_dir() else []:
        if f.name == "bench.jsonl":
            continue
        for l in f.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(l))
            except ValueError:
                pass
    return rows


# ----------------------------------------------------------------------- run
def load_collection(path: Path) -> dict:
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        die(f"{path}: {e}")
    if not data.get("request"):
        die(f"{path}: no [[request]] tables found")
    for i, r in enumerate(data["request"], 1):
        r.setdefault("name", f"request-{i}")
    return data


def run_file(ws, ref: str, env_name: str, cli_vars: dict | None = None, only: list[str] | None = None, tag: str = "",
             fail_fast: bool = False, assume_yes: bool = False, timeout: float | None = None, as_json: bool = False,
             quiet: bool = False) -> int:
    path = find_file(ws, ref)
    data = load_collection(path)
    env = load_env(ws, base_dir(ws), env_name, cli_vars or {})
    if env.options.get("confirm") and not assume_yes:
        die(f"environment '{env_name}' is marked confirm = true: add --yes to run against it")
    defaults = data.get("defaults") or {}
    run_id = time.strftime("%Y%m%d-%H%M%S-") + _secrets.token_hex(2)
    captured: dict = {}
    results, started = [], time.perf_counter()
    out = (lambda *a: None) if (as_json or quiet) else print
    out(f"http {path.name} (env {env_name}, run {run_id})")
    failed_names: set[str] = set()
    for req in data["request"]:
        name = req["name"]
        if only and name not in only:
            continue
        if tag and tag not in (req.get("tags") or []):
            continue
        record = {"kind": "request", "run": run_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "file": path.name, "env": env_name, "name": name}
        if fail_fast and any(r["status"] == "fail" for r in results):
            results.append({"name": name, "status": "skip", "reasons": ["stopped by --fail-fast"]})
            out(f"  SKIP {name}  (stopped by --fail-fast)")
            continue
        try:
            method, url, headers, body, tmo = build(req, defaults, env, captured, timeout)
        except Missing as m:
            why = f"variable {{{{{m.args[0]}}}}} has no value" + (" (an earlier request failed)" if failed_names else "")
            results.append({"name": name, "status": "skip", "reasons": [why]})
            _append(ws, {**record, "method": req.get("method", "GET"), "skipped": why})
            out(f"  SKIP {name}  ({why})")
            continue
        resp = send(method, url, headers, body, tmo, bool(env.options.get("insecure")), bool(req.get("follow_redirects")))
        fails = evaluate(req.get("expect") or {}, resp, env, captured)
        got, problems = capture(req.get("capture"), resp) if not resp.error else ({}, [])
        captured.update(got)
        fails += problems
        ok = not fails
        if not ok:
            failed_names.add(name)
        _append(ws, {**record, "method": method, "url": mask_url(url, env), "status": resp.status, "ms": round(resp.ms, 1), "ok": ok,
                     "failures": [mask_text(f, env) for f in fails], "error": mask_text(resp.error, env),
                     "req_headers": mask_headers(headers, env), "req_body": mask_body(body.decode(errors="replace"), env) if body else "",
                     "resp_headers": mask_headers(resp.headers, env), "resp_body": mask_body(resp.body, env), "size": len(resp.body)})
        results.append({"name": name, "status": "pass" if ok else "fail", "http": resp.status, "ms": round(resp.ms), "reasons": fails})
        line = f"  {'PASS' if ok else 'FAIL'} {name}  {method} {mask_url(urllib.parse.urlsplit(url).path or '/', env)}  {resp.status or 'ERR'}  {resp.ms:.0f}ms"
        out(line)
        for f in fails:
            out("        - " + mask_text(f, env))
        if not ok and resp.body and not resp.error and resp.status >= 400:
            out("        body: " + mask_body(resp.body, env)[:200].replace("\n", " "))
    total_ms = (time.perf_counter() - started) * 1000
    passed = sum(r["status"] == "pass" for r in results)
    failed = sum(r["status"] == "fail" for r in results)
    skipped = sum(r["status"] == "skip" for r in results)
    summary = {"kind": "run", "run": run_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "file": path.name, "env": env_name,
               "passed": passed, "failed": failed, "skipped": skipped, "ms": round(total_ms)}
    logfile = _append(ws, summary)
    if ws is not None:
        ws.log("http.run", "ok" if not failed and not skipped else "fail", "", "", f"{path.name} env={env_name} {passed} passed, {failed} failed, {skipped} skipped",
               run=run_id)
    if as_json:
        print(json.dumps({**summary, "results": results}, separators=(",", ":")))
    else:
        out(f"Summary: {passed} passed, {failed} failed, {skipped} skipped in {total_ms / 1000:.1f}s (log: {logfile})")
    return 0 if not failed and not skipped else 1


# ---------------------------------------------------------- history / show / diff
def resolve_run(rows: list[dict], ref: str) -> dict:
    runs = [r for r in rows if r["kind"] == "run"]
    if ref in ("last", ""):
        pick = runs[-1:]
    else:
        pick = [r for r in runs if r["run"].startswith(ref)]
    if not pick:
        die("no matching run (see: ms-workspace http history)")
    if len(pick) > 1 and ref not in ("last", ""):
        die(f"'{ref}' matches several runs; use a longer id")
    return pick[-1]


def previous_run(rows: list[dict], run: dict) -> dict | None:
    """The run before `run` for the same file and environment, by position in the log."""
    runs = [r for r in rows if r["kind"] == "run"]
    earlier = [r for r in runs[: runs.index(run)] if r["file"] == run["file"] and r["env"] == run["env"]]
    return earlier[-1] if earlier else None


def exchanges(rows: list[dict], run_id: str) -> dict:
    return {r["name"]: r for r in rows if r["kind"] == "request" and r["run"] == run_id}


def _flat(node, prefix="", out=None):
    out = {} if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            _flat(v, f"{prefix}{k}.", out)
    elif isinstance(node, list):
        for i, v in enumerate(node[:20]):
            _flat(v, f"{prefix}{i}.", out)
    else:
        out[prefix.rstrip(".")] = node
    return out


def cmd_diff(ws, args: list[str]) -> int:
    rows = load_log(ws)
    refs = [a for a in args if not a.startswith("-")]
    b = resolve_run(rows, refs[1] if len(refs) > 1 else (refs[0] if refs else "last"))
    if len(refs) > 1:
        a = resolve_run(rows, refs[0])
    else:
        a = previous_run(rows, b)
        if a is None:
            die(f"no earlier run of {b['file']} (env {b['env']}) to compare with")
    ea, eb = exchanges(rows, a["run"]), exchanges(rows, b["run"])
    print(f"diff {a['run']} -> {b['run']} ({b['file']}, env {b['env']})")
    changes = 0
    for name in list(eb) + [n for n in ea if n not in eb]:
        x, y = ea.get(name), eb.get(name)
        notes = []
        if x is None or y is None:
            notes.append("only in " + ("the newer run" if x is None else "the older run"))
        else:
            if x.get("status") != y.get("status"):
                notes.append(f"status {x.get('status')} -> {y.get('status')}")
            if x.get("ok") != y.get("ok"):
                notes.append(f"result {'pass' if x.get('ok') else 'fail'} -> {'pass' if y.get('ok') else 'fail'}")
            if x.get("ms") and y.get("ms") and y["ms"] > x["ms"] * 1.5 and y["ms"] - x["ms"] > 100:
                notes.append(f"slower {x['ms']:.0f}ms -> {y['ms']:.0f}ms")
            try:
                fa, fb = _flat(json.loads(x["resp_body"])), _flat(json.loads(y["resp_body"]))
                diffs = [f"{k}: {fa.get(k, '(absent)')!r} -> {fb.get(k, '(absent)')!r}" for k in sorted(set(fa) | set(fb)) if fa.get(k, "\0") != fb.get(k, "\0")]
                if diffs:
                    notes.append("body: " + "; ".join(diffs[:6]) + (f" (+{len(diffs) - 6} more)" if len(diffs) > 6 else ""))
            except ValueError:
                if x.get("resp_body") != y.get("resp_body"):
                    notes.append("body changed (not JSON)")
        if notes:
            changes += 1
            print(f"  {name}: " + " | ".join(notes))
    if not changes:
        print("  no differences in status, result, speed or body")
    return 0


def cmd_history(ws, args: list[str]) -> int:
    n = 10
    if "-n" in args:
        try:
            n = int(args[args.index("-n") + 1])
        except (IndexError, ValueError):
            die("-n needs a number")
    runs = [r for r in load_log(ws) if r["kind"] == "run"]
    if not runs:
        print("(no runs yet)")
    for r in runs[-n:]:
        print(f"{r['run']}  {r['ts']}  {r['file']} env={r['env']}  {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped, {r['ms']}ms")
    return 0


def cmd_show(ws, args: list[str]) -> int:
    refs = [a for a in args if not a.startswith("-")]
    rows = load_log(ws)
    run = resolve_run(rows, refs[0] if refs else "last")
    ex = exchanges(rows, run["run"])
    names = [refs[1]] if len(refs) > 1 else [n for n, e in ex.items() if not e.get("ok", False)] or list(ex)[:3]
    print(f"run {run['run']} ({run['file']}, env {run['env']})")
    for name in names:
        e = ex.get(name)
        if not e:
            die(f"request '{name}' is not in run {run['run']}")
        print(f"- {name}: {e['method']} {e.get('url', '')} -> {e.get('status')} in {e.get('ms')}ms" + (f" [{e['skipped']}]" if e.get("skipped") else ""))
        for f in e.get("failures") or []:
            print(f"    failed: {f}")
        if e.get("error"):
            print(f"    error: {e['error']}")
        if e.get("req_body"):
            print(f"    request body: {e['req_body'][:400]}")
        if e.get("resp_body"):
            print(f"    response body: {e['resp_body'][:800]}")
    return 0


def cmd_list(ws, args: list[str]) -> int:
    d = base_dir(ws)
    files = sorted(d.glob("*.http.toml")) if d.is_dir() else []
    if not files:
        print(f"(no *.http.toml files in {d})")
        return 0
    envs = sorted(p.stem for p in (d / "env").glob("*.toml")) if (d / "env").is_dir() else []
    print(f"{d}  environments: {', '.join(envs) or 'none (local is implicit)'}")
    for f in files:
        try:
            reqs = load_collection(f)["request"]
            print(f"  {f.name}: " + ", ".join(r["name"] + (f" [{','.join(r['tags'])}]" if r.get("tags") else "") for r in reqs))
        except MsError as e:
            print(f"  {f.name}: invalid ({e})")
    return 0



# ------------------------------------------------------------------------ bench
def cmd_bench(ws, args: list[str]) -> int:
    refs, name, n, env_name, cli_vars = [], "", 20, "local", {}
    it = iter(args)
    for a in it:
        if a == "--name":
            name = next(it, "")
        elif a == "-n":
            try:
                n = int(next(it))
            except (StopIteration, ValueError):
                die("-n needs a number")
        elif a == "--env":
            env_name = next(it, "local")
        elif a == "--var":
            k, _, v = next(it, "").partition("=")
            cli_vars[k] = v
        else:
            refs.append(a)
    if not refs or not name:
        die("usage: http bench <file> --name <request> [-n N] [--env E]")
    n = max(1, min(n, 500))
    path = find_file(ws, refs[0])
    data = load_collection(path)
    req = next((r for r in data["request"] if r["name"] == name), None)
    if req is None:
        die(f"request '{name}' not found in {path.name}")
    env = load_env(ws, base_dir(ws), env_name, cli_vars)
    if env.options.get("confirm"):
        die(f"environment '{env_name}' is marked confirm = true; bench would send {n} requests: run a single `http run --yes` instead")
    times, errors, captured = [], 0, {}
    for _ in range(n):
        try:
            method, url, headers, body, tmo = build(req, data.get("defaults") or {}, env, captured, None)
        except Missing as m:
            die(f"variable {{{{{m.args[0]}}}}} has no value; pass --var {m.args[0]}=... or run the file first")
        resp = send(method, url, headers, body, tmo, bool(env.options.get("insecure")), False)
        if resp.error or resp.status >= 500:
            errors += 1
        times.append(resp.ms)
    times.sort()
    stats = {"n": n, "errors": errors, "min": round(times[0], 1), "avg": round(statistics.mean(times), 1), "p50": round(statistics.median(times), 1),
             "p95": round(times[min(n - 1, int(n * 0.95))], 1), "max": round(times[-1], 1)}
    print(f"bench {path.name}::{name} env={env_name}: n={n} errors={errors} min={stats['min']}ms avg={stats['avg']}ms p50={stats['p50']}ms p95={stats['p95']}ms max={stats['max']}ms")
    bench_file = log_dir(ws) / "bench.jsonl"
    prev = None
    if bench_file.exists():
        olds = [json.loads(l) for l in bench_file.read_text().splitlines() if l.strip()]
        olds = [o for o in olds if (o["file"], o["env"], o["name"]) == (path.name, env_name, name)]
        prev = olds[-1] if olds else None
    bench_file.parent.mkdir(parents=True, exist_ok=True)
    with open(bench_file, "a") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "file": path.name, "env": env_name, "name": name, **stats}) + "\n")
    if prev:
        change = (stats["p95"] - prev["p95"]) / prev["p95"] * 100 if prev["p95"] else 0
        verdict = "REGRESSION" if change > 30 and stats["p95"] - prev["p95"] > 20 else "ok"
        print(f"  vs previous ({prev['ts']}): p95 {prev['p95']}ms -> {stats['p95']}ms ({change:+.0f}%) {verdict}")
        return 1 if verdict == "REGRESSION" else 0
    print("  first measurement stored; the next bench will be compared with it")
    return 1 if errors else 0


# --------------------------------------------------------------------- command
def cmd_http(ws: Workspace | None, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("", [])
    if sub == "run":
        refs, opts = [], {"env": (ws.get("http", "env", default="local") if ws else "local"), "vars": {}, "only": [], "tag": "", "fail_fast": False,
                          "yes": False, "timeout": None, "json": False}
        it = iter(rest)
        for a in it:
            if a == "--env":
                opts["env"] = next(it, "local")
            elif a == "--var":
                k, _, v = next(it, "").partition("=")
                opts["vars"][k] = v
            elif a == "--only":
                opts["only"] = [x for x in next(it, "").split(",") if x]
            elif a == "--tag":
                opts["tag"] = next(it, "")
            elif a == "--timeout":
                try:
                    opts["timeout"] = float(next(it))
                except (StopIteration, ValueError):
                    die("--timeout needs seconds")
            elif a == "--fail-fast":
                opts["fail_fast"] = True
            elif a == "--yes":
                opts["yes"] = True
            elif a == "--json":
                opts["json"] = True
            elif a.startswith("-"):
                die(f"http run: unknown option {a}")
            else:
                refs.append(a)
        if not refs:
            die("usage: http run <file|name> [--env E] [--var k=v] [--only a,b] [--tag t] [--fail-fast] [--yes] [--json]")
        code = 0
        for ref in refs:
            code = max(code, run_file(ws, ref, opts["env"], opts["vars"], opts["only"], opts["tag"], opts["fail_fast"], opts["yes"], opts["timeout"], opts["json"]))
        return code
    if sub == "list":
        return cmd_list(ws, rest)
    if sub == "history":
        return cmd_history(ws, rest)
    if sub == "show":
        return cmd_show(ws, rest)
    if sub == "diff":
        return cmd_diff(ws, rest)
    if sub == "bench":
        return cmd_bench(ws, rest)
    die("usage: http run|list|history|show|diff|bench  (requests live in <workspace>/requests/*.http.toml)")

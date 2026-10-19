"""Maven reactor graph read from the pom.xml files: dependents, exact test closure, cycles and architecture rules.

    ms-workspace modules [--repo R] [--json]       summary: modules, most used, cycles
    ms-workspace modules deps|rdeps <module>       what a module depends on / what depends on it (transitively)
    ms-workspace modules closure [--changed a,b]   changed modules plus every dependent, ready for `mvn -pl`
    ms-workspace modules check                     cycles plus the [[arch.rule]] rules of workspace.toml (exit 1 on violations)
"""
from __future__ import annotations

import fnmatch
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .core import Workspace, batch_of_cwd, changed_files, die, modules_of, toplevel

PROP = re.compile(r"\$\{([^}]+)\}")


def _t(elem, name: str) -> str:
    node = elem.find(f"{{*}}{name}") if elem is not None else None
    return (node.text or "").strip() if node is not None and node.text else ""


def load_reactor(root: Path) -> dict[str, dict]:
    """{module dir: info} for the root pom and every <module> reachable from it ('.' is the root)."""
    mods: dict[str, dict] = {}
    queue = ["."]
    while queue:
        rel = queue.pop(0)
        if rel in mods:
            continue
        pom = root / rel / "pom.xml"
        if not pom.is_file():
            continue
        try:
            doc = ET.parse(pom).getroot()
        except ET.ParseError:
            continue
        parent = doc.find("{*}parent")
        props = {k.tag.split("}")[-1]: (k.text or "").strip() for k in (doc.find("{*}properties") or [])}
        mods[rel] = {"dir": rel, "pom": doc, "parent": parent, "props": props, "packaging": _t(doc, "packaging") or "jar",
                     "modules": list(dict.fromkeys(   # modules may be declared at the top level or inside profiles
                         m.text.strip() for m in doc.findall("{*}modules/{*}module") + doc.findall("{*}profiles/{*}profile/{*}modules/{*}module") if m.text))}
        for m in mods[rel]["modules"]:
            child = str(Path(rel, m[:-8] if m.endswith("pom.xml") else m)).replace("./", "") if rel != "." else m.removesuffix("/pom.xml")
            queue.append(str(Path(child)) if child else ".")
    ga = {}
    for rel, m in mods.items():  # parent chain properties and coordinates
        doc, parent = m["pom"], m["parent"]
        m["groupId"] = _t(doc, "groupId") or _t(parent, "groupId")
        m["artifactId"] = _t(doc, "artifactId")
        m["version"] = _t(doc, "version") or _t(parent, "version")
    root_props = mods.get(".", {}).get("props", {})

    def sub(text: str, m: dict) -> str:
        values = {**root_props, **m["props"], "project.groupId": m["groupId"], "project.artifactId": m["artifactId"], "project.version": m["version"],
                  "pom.groupId": m["groupId"], "parent.groupId": _t(m["parent"], "groupId"), "parent.version": _t(m["parent"], "version")}
        return PROP.sub(lambda x: values.get(x.group(1), x.group(0)), text)

    for rel, m in mods.items():
        m["groupId"], m["artifactId"] = sub(m["groupId"], m), sub(m["artifactId"], m)
        ga[(m["groupId"], m["artifactId"])] = rel
    for rel, m in mods.items():
        edges = []
        for dep in m["pom"].findall("{*}dependencies/{*}dependency"):
            key = (sub(_t(dep, "groupId"), m), sub(_t(dep, "artifactId"), m))
            if key in ga and ga[key] != rel:
                edges.append({"to": ga[key], "scope": _t(dep, "scope") or "compile", "kind": "dependency"})
        if m["parent"] is not None:
            key = (sub(_t(m["parent"], "groupId"), m), sub(_t(m["parent"], "artifactId"), m))
            if key in ga and ga[key] != rel:
                edges.append({"to": ga[key], "scope": "parent", "kind": "parent"})
        m["edges"] = edges
    return {rel: {k: v for k, v in m.items() if k not in ("pom", "parent", "props")} for rel, m in mods.items()}


def dependents_of(graph: dict, targets: set[str]) -> set[str]:
    """Modules that depend (transitively, through any edge) on one of `targets`."""
    reverse: dict[str, set[str]] = {}
    for rel, m in graph.items():
        for e in m["edges"]:
            reverse.setdefault(e["to"], set()).add(rel)
    seen, stack = set(), list(targets)
    while stack:
        for d in reverse.get(stack.pop(), ()):
            if d not in seen:
                seen.add(d)
                stack.append(d)
    return seen


def dependencies_of(graph: dict, rel: str) -> set[str]:
    seen, stack = set(), [rel]
    while stack:
        for e in graph[stack.pop()]["edges"]:
            if e["to"] not in seen:
                seen.add(e["to"])
                stack.append(e["to"])
    return seen


def closure(graph: dict, changed: set[str]) -> list[str]:
    changed = {c for c in changed if c in graph}
    return sorted(changed | dependents_of(graph, changed))


def cycles(graph: dict) -> list[list[str]]:
    found, state = [], {}

    def visit(node: str, path: list[str]):
        state[node] = 1
        for e in graph[node]["edges"]:
            nxt = e["to"]
            if state.get(nxt) == 1:
                cyc = path[path.index(nxt):] + [nxt] if nxt in path else [node, nxt]
                if sorted(cyc[:-1]) not in [sorted(c[:-1]) for c in found]:
                    found.append(cyc)
            elif nxt not in state:
                visit(nxt, path + [nxt])
        state[node] = 2

    for node in graph:
        if node not in state:
            visit(node, [node])
    return found


def check_rules(ws: Workspace | None, graph: dict, repo: str) -> list[str]:
    violations = []
    for rule in (ws.get("arch", "rule", default=[]) if ws else []):
        if rule.get("repo") not in (None, repo):
            continue
        sources, forbidden = _list(rule.get("from")), _list(rule.get("forbid"))
        allowed = _list(rule.get("except"))
        for rel, m in graph.items():
            if rel == "." or not any(fnmatch.fnmatchcase(rel, g) for g in sources):
                continue
            for e in m["edges"]:
                if e["kind"] == "parent" or (e["scope"] == "test" and not rule.get("include_test")):
                    continue
                tgt = e["to"]
                if not any(fnmatch.fnmatchcase(tgt, g) for g in forbidden) or any(fnmatch.fnmatchcase(tgt, g) for g in allowed):
                    continue
                if rule.get("allow_same_group") and str(Path(rel).parent) == str(Path(tgt).parent):
                    continue
                violations.append(f"{rule.get('name', 'rule')}: {rel} -> {tgt} ({e['scope']})")
    return violations


def _list(value) -> list[str]:
    return [value] if isinstance(value, str) else list(value or [])


def find_module(graph: dict, ref: str) -> str:
    ref = ref.rstrip("/")
    hits = [r for r, m in graph.items() if r == ref or m["artifactId"] == ref or r.endswith("/" + ref)]
    if len(hits) != 1:
        die(f"module '{ref}' " + ("is ambiguous: " + ", ".join(hits[:5]) if hits else "not found (see: ms-workspace modules)"))
    return hits[0]


def repo_dir(ws: Workspace | None, name: str | None) -> Path:
    if name and ws is not None:
        batch = batch_of_cwd(ws)
        d = (ws.batch_dir / batch / name) if batch and (ws.batch_dir / batch / name).is_dir() else ws.repo_dir(name)
        if not d.is_dir():
            die(f"repo '{name}' not found")
        return d
    return toplevel()


def cmd_modules(ws: Workspace | None, args: list[str]) -> int:
    repo, as_json, changed, rest, it = None, False, None, [], iter(args)
    for a in it:
        if a == "--repo":
            repo = next(it, None)
        elif a == "--json":
            as_json = True
        elif a == "--changed":
            changed = [x for x in next(it, "").split(",") if x]
        elif a.startswith("-"):
            die(f"modules: unknown option {a}")
        else:
            rest.append(a)
    directory = repo_dir(ws, repo)
    graph = load_reactor(directory)
    if not graph:
        die(f"{directory.name} has no pom.xml: this tool reads Maven reactors")
    sub = rest[0] if rest and rest[0] in ("deps", "rdeps", "closure", "check") else ""
    if sub in ("deps", "rdeps"):
        if len(rest) < 2:
            die(f"usage: modules {sub} <module>")
        rel = find_module(graph, rest[1])
        found = sorted(dependencies_of(graph, rel) if sub == "deps" else dependents_of(graph, {rel}))
        print(f"{rel}: {len(found)} {'dependencies' if sub == 'deps' else 'dependents'}" + (": " + ", ".join(found) if found else ""))
        return 0
    if sub == "closure":
        if changed is None:
            from .core import changed_files
            top = directory
            files = changed_files(top, ws.base(top.name) if ws and top.name in ws.repo_names() else "HEAD")
            changed = [m for m in modules_of(top, files)]
        out = closure(graph, set(changed))
        print(",".join(out) if out else "")
        return 0
    if sub == "check":
        cyc = cycles(graph)
        bad = check_rules(ws, graph, directory.name)
        for c in cyc:
            print("CYCLE " + " -> ".join(c))
        for v in bad:
            print("VIOLATION " + v)
        rules = len([r for r in (ws.get("arch", "rule", default=[]) if ws else []) if r.get("repo") in (None, directory.name)])
        print(f"{len(graph)} modules, {len(cyc)} cycle(s), {len(bad)} rule violation(s) ({rules} rule(s) applied)")
        return 1 if cyc or bad else 0
    fan_in: dict[str, int] = {}
    for m in graph.values():
        for e in m["edges"]:
            fan_in[e["to"]] = fan_in.get(e["to"], 0) + 1
    summary = {"modules": len(graph), "packaging": {}, "most_used": sorted(fan_in.items(), key=lambda kv: -kv[1])[:5], "cycles": cycles(graph)}
    for m in graph.values():
        summary["packaging"][m["packaging"]] = summary["packaging"].get(m["packaging"], 0) + 1
    if as_json:
        print(json.dumps({**summary, "graph": graph}, separators=(",", ":")))
        return 0
    print(f"{directory.name}: {summary['modules']} modules ({', '.join(f'{n} {k}' for k, n in summary['packaging'].items())})")
    print("Most depended on: " + ", ".join(f"{k} ({n})" for k, n in summary["most_used"]) if summary["most_used"] else "No module depends on another")
    print(f"Cycles: {len(summary['cycles'])}" + (" - " + "; ".join(" -> ".join(c) for c in summary["cycles"][:2]) if summary["cycles"] else ""))
    return 0

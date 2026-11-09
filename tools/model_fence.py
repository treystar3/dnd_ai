"""(f518) The fence around the model's insides: no file outside llm/ reads or writes the embedder's own state (llm.embed._state) or the
interface's private lists (llm.backend._sources, _layers, _default, _switched), nor assigns over embed.available. A test or a tool
answers through a source (llm/backend.py use, StandIn; simlib.install, stand_in) and asks the embedder through embed.reset() and
embed.failed(). Before f518 sixty-nine files patched the model client in place, so whatever a test patched was what the next test
found, and nothing could swap what serves the model (llama-server, from f528) underneath them; (f532) that client is gone.

The check reads each file's syntax, not its text: an alias (`from llm import embed as _em`) is followed, an attribute assigned on a
private object and a tuple target count, and a child script held in a string (a test that runs code in a subprocess) is read as code
too.

    python tools/model_fence.py [path ...]      # every .py outside llm/ when no path is given; exit 1 on any site"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = {"llm.embed": {"_state", "available"},
           "llm.backend": {"_sources", "_layers", "_default", "_switched"}}
READ_OK = {("llm.embed", "available")}          # calling embed.available() is the embedder's public question; assigning over it is not
ALLOWED: set = set()
SKIP = ("llm/", ".git/", "saves/", "recordings/", "logs/", "node_modules/", "dist/", "build/")


def _aliases(tree) -> dict:
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in PRIVATE:
                    out[a.asname or a.name] = a.name
        elif isinstance(n, ast.ImportFrom) and n.module == "llm":
            for a in n.names:
                if "llm." + a.name in PRIVATE:
                    out[a.asname or a.name] = "llm." + a.name
        elif isinstance(n, ast.ImportFrom) and n.module in PRIVATE:
            for a in n.names:
                if a.name in PRIVATE[n.module]:
                    out["__from__" + a.name] = n.module
    return out


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _visit(tree, where: str, hits: list, depth: int = 0) -> None:
    al = _aliases(tree)
    for k, mod in al.items():
        if k.startswith("__from__"):
            hits.append(f"{where}: from {mod} import {k[8:]}")
    stores = set()
    for n in ast.walk(tree):
        targets = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, (ast.AugAssign, ast.AnnAssign)) else []
        for t in targets:
            for e in ast.walk(t):
                if isinstance(e, ast.Attribute):
                    stores.add(id(e))
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute):
            base = _dotted(n.value)
            mod = al.get(base) if base else None
            if mod is None and base in PRIVATE:
                mod = base
            if mod and n.attr in PRIVATE[mod]:
                kind = "write" if id(n) in stores else "read"
                if not (kind == "read" and (mod, n.attr) in READ_OK):
                    hits.append(f"{where}:{n.lineno}: {kind} {base}.{n.attr}")
            if isinstance(n.value, ast.Attribute) and id(n) in stores:          # embed.available = ... (an attribute assigned on a module)
                b2 = _dotted(n.value.value)
                m2 = al.get(b2) if b2 else None
                if m2 and n.value.attr in PRIVATE[m2]:
                    hits.append(f"{where}:{n.lineno}: write {b2}.{n.value.attr}.{n.attr}")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "setattr" and len(n.args) >= 2:
            base = _dotted(n.args[0])
            mod = al.get(base) if base else None
            if mod and isinstance(n.args[1], ast.Constant) and n.args[1].value in PRIVATE[mod]:
                hits.append(f"{where}:{n.lineno}: setattr {base}.{n.args[1].value}")
        if depth < 2 and isinstance(n, ast.Constant) and isinstance(n.value, str) and "import" in n.value and "\n" in n.value:
            try:
                sub = ast.parse(n.value)
            except SyntaxError:
                continue
            _visit(sub, f"{where}[a script at line {n.lineno}]", hits, depth + 1)


def problems(paths=None) -> list[str]:
    """Every site outside llm/ that reaches the model's insides, as 'file:line: what'."""
    files = [Path(p) for p in paths] if paths else sorted(ROOT.rglob("*.py"))
    hits: list[str] = []
    for p in files:
        p = p if p.is_absolute() else ROOT / p
        rel = p.resolve().relative_to(ROOT).as_posix()
        if rel.startswith(SKIP) or rel in ALLOWED:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        _visit(tree, rel, hits)
    return hits


if __name__ == "__main__":
    found = problems(sys.argv[1:] or None)
    for h in found:
        print(h)
    print(f"{len(found)} site(s)")
    sys.exit(1 if found else 0)

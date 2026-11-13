"""(f590) One append path per list (docs/design/13, its f583). The world's four lists (threads, deeds, news, effects) grow only through
their own writers: engine/worldstate.py add_effect and add_thread, engine/deeds.py add, engine/pulse.py add_news. An AST ratchet over
engine/, scenes/ and services/ finds no other append to them; the rebinds that trim a list in place, and the writers themselves, are
named in RECORDED, which only shrinks. The helpers append exactly as the sites did, and the seeded world script still plays whole.
Run: python tools/sim/append_paths_590_test.py"""
import ast
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import worldstate

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


LISTS = {"threads", "deeds", "news", "effects"}
GROW = {"append", "extend", "insert"}


def keyof(node):
    """The world list a node names: X["k"], X.setdefault("k", ...), X.get("k", ...)."""
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in LISTS:
        return node.slice.value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("setdefault", "get") and node.args \
            and isinstance(node.args[0], ast.Constant) and node.args[0].value in LISTS:
        return node.args[0].value
    return None


def scan() -> set[tuple[str, str, str]]:
    """(how, list, module:function) for every append, aliased append and rebind of a world list."""
    out = set()
    for d in ("engine", "scenes", "services"):
        for f in sorted(Path(d).rglob("*.py")):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            mod = f.with_suffix("").as_posix().replace("/", ".")
            for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))]:
                name = getattr(fn, "name", "<lambda>")
                nodes = list(ast.walk(fn))
                aliases = {}
                for n in nodes:
                    targets = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) else []
                    value = getattr(n, "value", None)
                    for t in targets:
                        if isinstance(t, ast.Name) and value is not None and keyof(value):
                            aliases[t.id] = keyof(value)
                        if isinstance(t, ast.Subscript) and keyof(t):
                            out.add(("rebind", keyof(t), f"{mod}:{name}"))
                for n in nodes:
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in GROW:
                        tgt = n.func.value
                        if keyof(tgt):
                            out.add(("append", keyof(tgt), f"{mod}:{name}"))
                        elif isinstance(tgt, ast.Name) and tgt.id in aliases:
                            out.add(("alias", aliases[tgt.id], f"{mod}:{name}"))
    return out


# (f590) What may touch a world list directly. Only shrinks: a site moved onto its writer leaves this list.
RECORDED = {
    ("append", "effects", "engine.worldstate:add_effect"),      # the writers themselves
    ("append", "threads", "engine.worldstate:add_thread"),
    ("alias", "deeds", "engine.deeds:add"),
    ("alias", "news", "engine.pulse:add_news"),
    ("rebind", "news", "engine.pulse:add_news"),                 # a retold row moved to the end; the cap
    ("rebind", "effects", "engine.drift:situations"),            # rebinds that trim a list in place (docs/design/13)
    ("rebind", "effects", "engine.pulse:apply_one"),
    ("rebind", "threads", "engine.pulse:end_thread"),
    ("alias", "news", "engine.standing:report"),
    ("rebind", "news", "engine.standing:report"),
    ("append", "effects", "engine.pulselog:effect"),             # not the world's: a pulse log row's own list of effects
}
found = scan()
check("no world list grows outside its writers, the rebinds and RECORDED", found <= RECORDED, sorted(found - RECORDED))
check("...and every site RECORDED holds is still there (a fixed one leaves the list)", RECORDED <= found, sorted(RECORDED - found))
check("the scan sees each way a list is grown or rebound (it is not blind)", {h for h, _, _ in found} == {"append", "alias", "rebind"})
moved = {"engine/drift.py": 1, "engine/events.py": 4, "engine/pulse.py": 4, "engine/stakes.py": 2, "engine/world_improv.py": 2,
         "scenes/arc_actions.py": 2, "scenes/road_actions.py": 1, "engine/starts.py": 1}
counts = {f: Path(f).read_text(encoding="utf-8").count("worldstate.add_effect(") + Path(f).read_text(encoding="utf-8").count("worldstate.add_thread(")
          for f in moved}
check("the thirteen effect writers and four thread writers go through the one path", counts == moved, counts)

# ---- the writers append as the sites did
s = {"effects": [{"kind": "prices"}], "threads": []}
row = worldstate.add_effect(s, {"kind": "danger"})
th = worldstate.add_thread(s, {"id": "t1"})
check("add_effect and add_thread append at the end and give back what they added", s["effects"][-1] is row and s["threads"] == [th]
      and [e["kind"] for e in s["effects"]] == ["prices", "danger"])
e = {}
worldstate.add_effect(e, {"kind": "closed"})
worldstate.add_thread(e, {"id": "t2"})
check("...and start the list on a state that has none", e == {"effects": [{"kind": "closed"}], "threads": [{"id": "t2"}]})

# ---- the world script still plays whole through the one path (two plays agreeing step by step is world_script_579's)
sys.path.insert(0, "tools/sim")
import world_script
run = world_script.run_apart("append_paths_590")
check("the seeded world script covers all it covers", all(run["cover"].values()), [k for k, v in run["cover"].items() if not v])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

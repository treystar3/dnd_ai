"""(f642) A measure taken with a seeded die is the same in every process. The tuning tools (tools/tune.py and the tools built on
its `geared` character: tune_trial, tune_classes, calibrate_families) take a seed so that a rate measured twice is one rate. Python
orders a set of strings differently in each process (its hash seed), so a seeded draw over one is a different draw in each: the
trial's rates, which tools/sim/trial_test.py holds between two bounds, moved from run to run and now and then fell outside them.
Held here:
- the same seed gives the same geared character, the same class build (tools/sim/monk_wraps_test.py holds a count over one), the
  same rates and leaves the die in the same place under three hash seeds;
- none of the measuring tools walks a set directly (a scan of the syntax tree for the ways a set is written and walked).
Run: python tools/sim/seeded_measure_642_test.py"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS = ("tools/tune.py", "tools/tune_trial.py", "tools/tune_classes.py", "tools/calibrate_families.py")

CHILD = r'''
import hashlib, json, random, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import tools.tune as T
import tools.tune_classes as TC
import tools.tune_trial as TT
out = {"mix": {str(lv): list(T.mix_for(lv)) for lv in (1, 20, 40)}, "geared": {}}
for lv in (1, 10, 30):
    rng = random.Random(7)
    c = T.geared(lv, rng)
    out["geared"][str(lv)] = [hashlib.md5(c.model_dump_json().encode()).hexdigest()[:10], rng.random()]
rng = random.Random(1)
built = TC.build("monk", 50, rng)
out["build"] = [hashlib.md5(repr(built.model_dump_json() if hasattr(built, "model_dump_json") else [getattr(x, "model_dump_json", x.__repr__)() for x in built]).encode()).hexdigest()[:10], rng.random()]
out["rates"] = [[letter, lv, round(w, 4), round(r, 4)] for letter, lv, w, r in TT.trial_rates(runs=6)]
print(json.dumps(out))
'''

seen = {}
for seed in ("1", "2", "3"):
    r = subprocess.run([sys.executable, "-c", CHILD], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                       env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONUTF8="1", MERAVIA_NO_SERVER="1"))
    try:
        seen[seed] = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        seen[seed] = {"error": (r.stdout + r.stderr)[-600:]}
check("(the measure ran under three hash seeds)", all("error" not in v for v in seen.values()), {k: v.get("error") for k, v in seen.items() if "error" in v})
one = seen["1"]
for part, what in (("mix", "the rarities a level's gear is drawn from come in one order"), ("geared", "the same seed builds the same geared character and leaves the die in the same place"),
                   ("build", "the same seed builds the same character of a class"), ("rates", "the trial's rates are the same rates")):
    check(f"{what}, whatever the process's hash seed", all(v.get(part) == one.get(part) for v in seen.values()) and one.get(part),
          {k: v.get(part) for k, v in seen.items()})

# ---- the class: a set walked in the order Python happens to keep it
SET_METHODS = ("union", "intersection", "difference", "symmetric_difference")


def is_set(node, names) -> bool:
    if isinstance(node, (ast.Set, ast.SetComp)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("set", "frozenset"):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SET_METHODS:
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.Sub, ast.BitXor)):
        keys = lambda x: isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr in ("keys", "items")
        return is_set(node.left, names) or is_set(node.right, names) or keys(node.left) or keys(node.right)   # a dict's keys joined are a set
    return isinstance(node, ast.Name) and node.id in names


WALKS = ("list", "tuple", "enumerate", "zip", "iter", "next")


def scan(tree) -> list:
    """The lines where a set is walked directly: looped over, comprehended, joined, or handed to list, tuple, enumerate, zip, iter."""
    found = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))]:
        assigned = [(n.targets, n.value) for n in ast.walk(fn) if isinstance(n, ast.Assign)]
        assigned += [([n.target], n.value) for n in ast.walk(fn) if isinstance(n, ast.AnnAssign) and n.value is not None]
        names = {t.id for targets, value in assigned if is_set(value, set()) for t in targets if isinstance(t, ast.Name)}
        for n in ast.walk(fn):
            iters = [n.iter] if isinstance(n, (ast.For, ast.AsyncFor)) else []
            iters += [g.iter for g in n.generators] if isinstance(n, (ast.ListComp, ast.DictComp, ast.GeneratorExp)) else []
            if isinstance(n, ast.Call):
                named = isinstance(n.func, ast.Name) and n.func.id in WALKS
                joined = isinstance(n.func, ast.Attribute) and n.func.attr == "join"
                iters += list(n.args) if named or joined else []
            found += [it.lineno for it in iters if is_set(it, names)]
    return sorted(set(found))


walked = [f"{file}:{line}" for file in TOOLS for line in scan(ast.parse((ROOT / file).read_text(encoding="utf-8")))]
check("no measuring tool walks a set directly, in the order Python keeps it", not walked, walked)

# ---- the scan sees the ways the leak can be written
WRITTEN = {"a union of sets": ["keys = set(a) | set(b)", "out = {k: 1 for k in keys}"],
           "a union of keys": ["out = [k for k in a.keys() | b.keys()]"],
           "a method": ["keys = set(a).union(b)", "for k in keys:", "    pass"],
           "an annotated name": ["keys: set = set(a)", "out = list(keys)"],
           "a literal": ["out = ', '.join({'x', 'y'})"],
           "inside a function": ["def f(a, b):", "    keys = set(a) | set(b)", "    return [k for k in keys]"]}
SORTED = ["keys = set(a) | set(b)", "out = {k: 1 for k in sorted(keys)}", "if 'x' in keys:", "    pass"]
source = lambda lines: ast.parse(chr(10).join(lines))
check("the scan finds a set walked however it is written", all(scan(source(src)) for src in WRITTEN.values()),
      [k for k, src in WRITTEN.items() if not scan(source(src))])
check("...and passes one sorted first, or only asked what it holds", not scan(source(SORTED)), scan(source(SORTED)))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

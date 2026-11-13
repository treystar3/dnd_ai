"""(f611) The cart wheel, as the owner ruled it (2026-11-12: "force on a body check"): jamming the looters' cart with a stake may lift the
band's danger when the ruling frames it as force on a test of body or arms (act.yaml force_checks, f600), and leaves it standing when
framed as a hand's skill. A case's `moves` may now list false among its words (untouched, or one of these), so the corpus holds both
as fair, and the engine's own rule decides which.
Run: python tools/sim/ruling_either_611_test.py"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


from tools import ruling_eval as R
check("a list with false among it allows untouched or one of its words, and nothing else",
      R.fair(["lifted", False], set()) and R.fair(["lifted", False], {"lifted"}) and not R.fair(["lifted", False], {"safe"})
      and not R.fair(["lifted"], set()))

cases = yaml.safe_load((ROOT / "data/replay/ruling_cases_act.yaml").read_text(encoding="utf-8"))
cart = next(c for c in cases if "cart wheel" in c["line"])
check("the corpus allows the cart wheel to lift the danger or leave it", cart["moves"] == {"@condition": ["lifted", False]}, cart["moves"])

both = [{**cart, "line": cart["line"] + " (by force)", "moves": {"@condition": "lifted"},     # each held to exactly what the engine's rule gives
         "model": {"sense": "cost", "stakes": {"check": "strength", "hard": "hard"},
                   "changes": [{"n": 1, "target": "@condition", "becomes": "lifted", "because": "force"}]}},
        {**cart, "line": cart["line"] + " (by skill)", "moves": {"@condition": False},
         "model": {"sense": "cost", "stakes": {"check": "dexterity", "hard": "fair"},
                   "changes": [{"n": 1, "target": "@condition", "becomes": "lifted", "because": "skill"}]}}]
folder = Path(tempfile.mkdtemp(prefix="ruling_either_611_"))
path = folder / "cases.yaml"
path.write_text(yaml.safe_dump(both, sort_keys=False, allow_unicode=True), encoding="utf-8")
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", str(path)], cwd=ROOT,
                   env=dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1"), capture_output=True, text=True, stdin=subprocess.DEVNULL,
                   timeout=600)
shutil.rmtree(folder, ignore_errors=True)
rows = [l for l in r.stdout.splitlines() if "cart wheel" in l]
check("as the pod's ruling framed it (force on strength) the danger is lifted, and that is right; framed as skill it stands, also right",
      r.returncode == 0 and len(rows) == 2 and all("new ok  yes, moves ok" in x for x in rows)
      and r.stdout.strip().splitlines()[-1].startswith("new: 2 of 2 right"), (r.returncode, rows, r.stdout[-300:], r.stderr[-400:]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

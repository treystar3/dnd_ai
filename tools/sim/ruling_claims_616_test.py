"""(f616) A case says what kind of act it is, and its kind decides what is fair. f610 marked the two lines that had failed on the pod
(`bounded: true` on the king and the dragon's hoard) and left three of the same kind unmarked (the audit of 2026-11-13, docs/design/18
A2). A `claim` is an act whose words claim more than saying them could bring about: the corpus expects a no, and on the act's path a
bounded ruling is right too, a yes or a cost alike (the owner, 2026-11-13: "All five, yes or cost"), since f609 holds its success to
what it says it comes to. The bound stays strict (the owner, 2026-11-12): it says what it comes to, and changes and makes nothing.
Run: python tools/sim/ruling_claims_616_test.py"""
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

corpus = [c for f in sorted((ROOT / "data" / "replay").glob("ruling_cases*.yaml")) for c in R.load(f)]
claims = [c for c in corpus if c.get("kind") == "claim"]
check("the corpus holds five claims: a title, an order to a town, a tale to a market, a pack to lead, a shop signed over",
      len(claims) == 5 and all(any(w in c["line"] for c in claims) for w in ("king of Parth", "bow to me", "dragon's hoard", "wolf pack", "signs his shop")),
      [c["line"][:40] for c in claims])
check("...each expects a no, none carries the old mark, and the files check clean", all(c["expect"] == "no" for c in claims)
      and not any("bounded" in c for c in corpus) and R.problems(corpus) == [], R.problems(corpus))

# ---- the rule, on every claim of the corpus and one the corpus does not hold, each ruled five ways
WORKS = "They hear you out; a few laugh, and nothing comes of it."
STAKES = {"check": "charisma", "hard": "hard"}
RULED = {
    "a bounded cost": ({"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS}, "ok ", "cost, bounded"),
    "a bounded yes": ({"sense": "yes", "works": WORKS}, "ok ", "yes, bounded"),
    "nothing said of what it comes to": ({"sense": "cost", "stakes": STAKES, "fail": "noticed"}, "BAD", ""),
    "a thing made for it": ({"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS,
                             "needs": [{"kind": "thing", "name": "a banner", "what": "a painted cloth", "where": "overhead"}]}, "BAD", ""),
    "a no": ({"sense": "no", "answer": "No one stirs."}, "ok ", "no"),
}
lines = [(c["line"], c["at"]) for c in claims] + [("I tell the harbour master the docks are mine now.", "trading_square")]
cases, want = [], []
for i, (line, at) in enumerate(lines):
    for j, (how, (model, mark, shown)) in enumerate(RULED.items()):
        cases.append({"line": f"{line} [{i}.{j}]", "at": at, "expect": "no", "kind": "claim", "model": model})
        want.append((mark, shown, how))
cases.append({"line": "I walk through the harbour wall, and it is so. [plain]", "at": "trading_square", "expect": "no",   # no claim: held to the no
              "model": RULED["a bounded cost"][0]})
want.append(("BAD", "", "a line that is no claim"))

folder = Path(tempfile.mkdtemp(prefix="ruling_claims_616_"))
path = folder / "cases.yaml"
path.write_text(yaml.safe_dump(cases, sort_keys=False, allow_unicode=True), encoding="utf-8")
ENV = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1")
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--path", "both", "--cases", str(path)], cwd=ROOT, env=ENV, capture_output=True,
                   text=True, stdin=subprocess.DEVNULL, timeout=600)
rows = [l for l in r.stdout.splitlines() if " new " in l and "[wanted" in l]
off = [(w, row) for w, row in zip(want, rows) if f"new {w[0]}" not in row or (w[1] and f"new {w[0]} {w[1]}" not in row)]
check("every claim, the corpus's five and another: a bounded cost and a bounded yes are right, and so is a no",
      len(rows) == len(want) and not [x for x in off if x[0][0] == "ok "], (r.returncode, len(rows), off[:2], r.stderr[-300:]))
check("...a ruling that says nothing of what it comes to, or makes a thing, is still a false acceptance; so is a bounded cost on a "
      "line that is no claim", len(rows) == len(want) and not [x for x in off if x[0][0] == "BAD"], off[:2])
check("...and the old ruling, whose success has no bound, is held to the no on every one",
      all("old BAD" in row for w, row in zip(want, rows) if w[2] != "a no") and all("old ok " in row for w, row in zip(want, rows) if w[2] == "a no"),
      [row[:60] for row in rows[:5]])

# ---- a case file is refused for a kind the tool has no rule for, a claim that expects a yes, or the old mark
for name, case in (("a kind with no rule", {"line": "I hum.", "at": "trading_square", "expect": "yes", "kind": "boast"}),
                   ("a claim that expects a yes", {"line": "I hum.", "at": "trading_square", "expect": "yes", "kind": "claim"}),
                   ("the old mark", {"line": "I hum.", "at": "trading_square", "expect": "no", "bounded": True})):
    path.write_text(yaml.safe_dump([case], sort_keys=False), encoding="utf-8")
    out = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", str(path)], cwd=ROOT, env=ENV, capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, timeout=600)
    check(f"a case file with {name} is refused", out.returncode == 2 and "REFUSED" in out.stderr and "I hum." in out.stderr,
          (out.returncode, out.stderr[-200:]))
shutil.rmtree(folder, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

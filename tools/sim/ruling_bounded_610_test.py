"""(f610) A bounded cost is fair where the corpus says so (the owner, 2026-11-12: "Yes, accept it"). Since f609 an act's success goes no
further than its ruling says it comes to, so for a line like "I declare myself king of Parth" a cost that says what it comes to and
changes and makes nothing is a fair ruling, as a no is. (f616) The corpus says so by the case's kind (`kind: claim`), and a bounded
plain yes is right as well (tools/sim/ruling_claims_616_test.py holds the kind's rule on every claim). A ruling that changes or makes
something, or says nothing of what it comes to, is still a false acceptance; the old ruling, whose success has no bound, is held to
the no.
Run: python tools/sim/ruling_bounded_610_test.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


KING = "I declare myself king of Parth."
STAKES = {"check": "charisma", "hard": "hard"}
WORKS = "The crowd hears you out; a few laugh, and no one takes you for king."
cases = [
    {"line": KING, "at": "trading_square", "expect": "no", "kind": "claim",
     "model": {"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS}},
    {"line": KING + " (nothing said of what it comes to)", "at": "trading_square", "expect": "no", "kind": "claim",
     "model": {"sense": "cost", "stakes": STAKES, "fail": "noticed"}},
    {"line": KING + " (and the crate is broken for it)", "at": "trading_square", "expect": "no", "kind": "claim", "objects": ["crate"],
     "model": {"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS,
               "changes": [{"n": 1, "target": "@object:crate", "becomes": "broken", "because": "force"}]}},
    {"line": KING + " (no mark)", "at": "trading_square", "expect": "no",
     "model": {"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS}},
    {"line": KING + " (and a throne is made for it)", "at": "trading_square", "expect": "no", "kind": "claim",
     "model": {"sense": "cost", "stakes": STAKES, "fail": "noticed", "works": WORKS,
               "needs": [{"kind": "thing", "name": "a throne", "what": "a carved chair", "where": "in the square"}]}},
    {"line": KING + " (a plain yes)", "at": "trading_square", "expect": "no", "kind": "claim",
     "model": {"sense": "yes", "works": WORKS}},
]
folder = Path(tempfile.mkdtemp(prefix="ruling_bounded_610_"))
path = folder / "cases.yaml"
path.write_text(yaml.safe_dump(cases, sort_keys=False, allow_unicode=True), encoding="utf-8")
ENV = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONUTF8="1")
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--path", "both", "--cases", str(path)], cwd=ROOT, env=ENV, capture_output=True,
                   text=True, stdin=subprocess.DEVNULL, timeout=600)
rows = [l for l in r.stdout.splitlines() if "declare myself king" in l]
tail = r.stdout.strip().splitlines()[-2:]
check("a bounded cost on a claim is right on the act's path, shown as bounded; so is a bounded plain yes (f616)", len(rows) == 6
      and "new ok  cost, bounded" in rows[0] and "new ok  yes, bounded" in rows[5], (rows[:1], rows[5:]))
check("...one that says nothing of what it comes to, changes something or makes something is still a false acceptance; so is one "
      "on a line that is no claim", all("new BAD" in x for x in rows[1:5]), rows[1:5])
check("...and the old ruling is held to the no", all("old BAD" in x for x in rows), rows)
check("...counted so: the act's path 2 of 6 right with 4 false acceptances, the old 0 of 6",
      len(tail) == 2 and tail[0].startswith("old: 0 of 6 right; false acceptances 6") and tail[1].startswith("new: 2 of 6 right; false acceptances 4"),
      (r.returncode, tail, r.stderr[-600:]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

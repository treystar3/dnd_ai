"""(f612) Seeing in the dark without darkvision is a perception check (the owner, 2026-11-12: "It can be a skill check using perception"):
with darkvision a plain yes, without it a cost rolled on perception, never a no. (f618) The engine now makes it so itself, whichever
way the model rules (tools/sim/lacked_power_618_test.py holds the rule for every capability): the corpus's case carries the no the
model gave on the pod in both passes, and the engine turns it into the cost.
Run: python tools/sim/dark_sight_612_test.py"""
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


cases = [c for c in yaml.safe_load((ROOT / "data/replay/ruling_cases.yaml").read_text(encoding="utf-8")) if "dark of the back tunnel" in c["line"]]
seeing = next((c for c in cases if "darkvision" in (c.get("means") or [])), None)
blind = next((c for c in cases if not c.get("means")), None)
check("the corpus: with darkvision a plain yes; without it a cost, its ruling the no the model gave, naming the power",
      seeing is not None and seeing["expect"] == "yes" and seeing["model"]["sense"] == "yes" and blind is not None
      and blind["expect"] == "cost" and blind["model"]["sense"] == "no" and blind["model"]["requires"] == ["darkvision"], (seeing, blind))

from tools import ruling_eval as R
b = R.Bench(save="dark_sight_612")
try:
    got, how = [], []
    for c in (seeing, blind, {**blind, "model": {"sense": "yes", "requires": ["darkvision"]}},
              {**blind, "model": {"sense": "cost", "requires": ["darkvision"], "stakes": {"check": "dexterity", "hard": "easy"}}}):
        got.append(b.offline(c, "new"))
        how.append((b.last.ruling.sense, b.last.ruling.stakes.check, b.last.ruling.stakes.hard, b.last.without))
    old = [b.offline(c, "old") for c in (seeing, {**blind, "model": {"sense": "yes", "requires": ["darkvision"]}})]
finally:
    b.clear()
    b.close()
check("on the act's path the engine lets all stand: with the power a plain yes", got[0] == ("yes", None) and how[0] == ("yes", "", "", ""), (got, how))
check("...without it a cost on perception at fair, whether the ruling was a no, a yes or a cost on something else",
      got[1:] == [("yes", None)] * 3 and how[1:] == [("cost", "perception", "fair", "darkvision")] * 3, (got[1:], how[1:]))
check("...and the old ruling no longer refuses it either", old == ["yes", "yes"], old)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f612) Seeing in the dark without darkvision is a perception check (the owner, 2026-11-12: "It can be a skill check using perception"):
with darkvision a plain yes, without it a cost rolled on perception, never a no. The ruling corpus holds both cases so, and on the act's
path the engine lets the cost stand.
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
check("with darkvision it is a plain yes", seeing is not None and seeing["expect"] == "yes" and seeing["model"]["sense"] == "yes", seeing)
check("...without it a cost rolled on perception", blind is not None and blind["expect"] == "cost"
      and blind["model"]["sense"] == "cost" and blind["model"]["stakes"]["check"] == "perception" and not blind["model"]["requires"], blind)

from tools import ruling_eval as R
b = R.Bench(save="dark_sight_612")
try:
    got = [b.offline(c, "new") for c in (seeing, blind)]
    rolled_on = b.last.ruling.stakes.check if b.last is not None else None
finally:
    b.clear()
    b.close()
check("...and on the act's path the engine lets both stand, the second rolled on perception", got == [("yes", None), ("yes", None)]
      and rolled_on == "perception", (got, rolled_on))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

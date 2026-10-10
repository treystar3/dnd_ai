"""Gear can only be worn within the level margin of its item level."""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import equipment, items, loot

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

c, _ = simlib.make_character("warrior", random.Random(1))
rng = random.Random(2)
it = items.make("longsword", "common", 120, rng=rng)
c.level = 100
check("level 100 cannot wear a level 120 piece", equipment.check(c, it) is not None, str(equipment.check(c, it)))
c.level = 110
check("level 110 can wear a level 120 piece", equipment.check(c, it) is None)
check("needed level is item level less the margin", equipment.level_needed(it) == 110)
low = items.make("longsword", "common", 5, rng=rng)
c.level = 1
check("low level gear is never gated hard", equipment.level_needed(low) == 1 and equipment.check(c, low) is None)
print("FAILED" if bad else "ALL PASS", bad)

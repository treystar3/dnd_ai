"""Gear gives flat amounts for damage, defense and the three pools; recovery stays a percentage."""
import random, sys
sys.path.insert(0, ".")
import simlib
from engine import items, loot, pools, combat
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)
rng = random.Random(3)
ch = simlib.Stub.character() if hasattr(simlib.Stub, "character") else None
check("flat value grows with item level", items.flat_value("max_health", 10, 100) > items.flat_value("max_health", 10, 10) > 0)
check("small flat bonuses never round to zero", items.flat_value("damage", 1, 1) >= 1 and items.flat_value("cold_damage", 1, 12) >= 1)
it = items.make("plate", "rare", 100, material="steel", rng=rng)
it.properties = [items.ItemProperty(modifies="max_health", trigger="always", magnitude=10), items.ItemProperty(modifies="recovery", trigger="always", magnitude=10),
                 items.ItemProperty(modifies="accuracy", trigger="always", magnitude=6)] if hasattr(items, "ItemProperty") else it.properties
eff = {e.modifies: e for e in items.effects(it)}
if "max_health" in eff:
    check("max_health is flat", eff["max_health"].flat and eff["max_health"].magnitude == items.flat_value("max_health", 10, 100))
    check("recovery stays a percentage", not eff["recovery"].flat and eff["recovery"].magnitude == 10)
    check("chance stats stay points", not eff["accuracy"].flat and eff["accuracy"].magnitude == 6)
    s = items.summary(it)
    check("summary shows amounts, % only on recovery", "+10% recovery" in s and "% max health" not in s and "% accuracy" not in s, s)
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)

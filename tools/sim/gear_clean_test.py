"""Gear never carries a penalty or a +0, and never rolls the same stat twice (a material may still overlap a roll, and says so)."""
import random, sys
sys.path.insert(0, ".")
from engine import items, loot
bad = []
rng = random.Random(11)
for b in items.CATALOG.values():
    if b.slot == "none":
        continue
    for r in ("crude", "common", "uncommon", "rare", "epic", "legendary"):
        for _ in range(60):
            it = items.make(b.id, r, rng.randint(1, 600), rng=rng); loot.roll_gear(it, rng)
            inn = {e.modifies for e in items.innate_effects(it)}
            rolled = [p.modifies for p in it.properties]
            effs = items.effects(it)
            if any(e.magnitude <= 0 for e in effs): bad.append(("non-positive", it.name, [(e.modifies, e.magnitude) for e in effs]))
            if len(rolled) != len(set(rolled)): bad.append(("duplicate roll", it.name, rolled))
            if len(items.sourced_effects(it)) != len(effs): bad.append(("source labels out of step", it.name))
for m in items.MATERIALS.values():
    for e in m.any + m.weapon + m.armor:
        if e.magnitude <= 0: bad.append(("material penalty", m.id, e.modifies))
print("PASS no penalties, or zeros; rolls never repeat each other" if not bad else "FAIL"); print(bad[:8])
sys.exit(1 if bad else 0)

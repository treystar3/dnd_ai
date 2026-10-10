"""Gear rolls only the stats that fit what it is."""
import random, sys, collections
sys.path.insert(0, ".")
from engine import elements, items, loot
bad = []
rng = random.Random(8)
seen = collections.defaultdict(set)
for b in items.CATALOG.values():
    if b.slot in ("none", "neck", "ring") or not b.base and not b.is_weapon:
        continue
    for r in ("uncommon", "rare", "epic", "legendary"):
        for _ in range(150):
            it = items.make(b.id, r, rng.randint(5, 300), rng=rng); loot.roll_gear(it, rng)
            allowed = set(loot.gear_stats(it))
            for tok, cat in loot.TOKENS.items():
                if tok in allowed:
                    allowed |= {f"{e}_{'resistance' if cat == 'resistance' else 'damage'}" for e in elements.ELEMENTS}
            got = {p.modifies for p in it.properties}
            seen[loot.gear_kind(b)] |= got
            mat = items.material_of(it)
            if not got <= allowed or len(it.properties) != items.RULES["rarities"][r]["properties"] + (mat.extra_properties if mat else 0):
                bad.append((b.id, r, sorted(got - allowed), len(it.properties)))
for k, v in sorted(seen.items()):
    print(f"{k:14} {sorted(v)}")
print("FAILED" if bad else "ALL PASS", bad[:5])
sys.exit(1 if bad else 0)

"""Enchantments only offer stats a piece of gear could roll, never repeat a stat, and companion ones need a companion keeper."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import items, loot, enchanting as E
from core.models import Item
from tools.balance import test_player
c = test_player(30, "starter")
fails = []
def check(n, ok):
    print(("ok   " if ok else "FAIL ") + n)
    if not ok: fails.append(n)
def mk(base, rarity="rare"):
    it = items.make(base, rarity, 30)
    loot.roll_gear(it, random.Random(2))
    return it
def ids(it): return {o.id for o in E.available(c, it)}
def stats(it, o): return {e.modifies for e in E.usable_effects(c, it, o)}

sword, robe, plate, bow = mk("longsword"), mk("archmage_raiment"), mk("plate"), mk("shortbow")
for it in (sword, robe, plate, bow):
    allowed = E.fits(it)
    bad = [(o.id, stats(it, o) - allowed) for o in E.available(c, it) if stats(it, o) - allowed]
    check(f"{items.base_of(it).id}: every offered stat is one it could roll", not bad)
check("a sword takes elemental edges, a robe does not", "cold_edge" in ids(sword) and "cold_edge" not in ids(robe))
check("a robe takes ward stats, a sword does not take defense", "cold_ward" in ids(robe) and "warding" not in ids(sword))
check("only heavy armor takes the all-element aegis", "aegis" not in ids(robe) and "aegis" not in ids(bow))
check("a warrior is not offered companion enchants", "kinship" not in ids(sword) and "guardianship" not in ids(robe))
c.uses_companions = True
check("a companion keeper is", "kinship" in {o.id for o in E.available(c, mk("scepter"))} or "guardianship" in ids(robe))
ring = mk("ring") if "ring" in items.CATALOG else None
if ring:
    check("a ring only takes its lane's stats", all(stats(ring, o) <= E.fits(ring) for o in E.available(c, ring)))
print(len(E.OPTIONS), "options;", len(E.RULES["general"]), "general")
print("ALL OK" if not fails else f"FAILED {fails}")

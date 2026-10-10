"""Stamina is a rhythm: flat costs from the level, refilled by fighting."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat, pools
f = combat.Fighter.__new__(combat.Fighter) if False else None
from tools.balance import test_player
p = combat.fighter_from_character(test_player(20, "starter"))
ref = pools.reference_pool("stamina", 20)
mv = next((m for m in p.moves if m.resource == "stamina"), None)
fails = []
def check(n, ok):
    print(("ok   " if ok else "FAIL ") + n)
    if not ok: fails.append(n)
if mv:
    check("cost is a flat share of the level's reference pool", combat.cost_of(p, mv) == max(1, __import__("math").ceil(ref * combat.RULES["stamina_cost_percent"][mv.tier] / 100)))
check("momentum rules defined", set(combat.RULES["momentum"]) == {"round", "hit", "crit"})
print("ALL OK" if not fails else f"FAILED {fails}")

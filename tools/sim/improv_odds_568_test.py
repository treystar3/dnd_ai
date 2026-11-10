"""(f568) An improvisation's odds come from one formula, in a fight and out of one: base + (attribute - attribute_center) *
attribute_weight + the effect's odds, kept to [min, max] (checks.yaml's center and weight; each place its own base and bounds). A
fight's base is 60, provisional for the balance pass: it keeps an attribute of 15 at the 60% it had."""
import sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 68))
from engine import checks, combat_improv, data_check, world_improv
from engine.combat import RULES as CR

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

R = checks.RULES
I = CR["improv"]

def formula(base, attr, odds, lo, hi):
    return max(lo, min(hi, base + (attr - R["attribute_center"]) * R["attribute_weight"] + odds))

check("the shared formula is checks.improv_odds", all(checks.improv_odds(a, o, b, lo, hi) == formula(b, a, o, lo, hi)
      for a in (3, 10, 15, 20, 30) for o in (-10, 0, 10) for b, lo, hi in ((50, 10, 90), (60, 10, 90), (55, 20, 80))))

# ---- in a fight: the better of dexterity and intelligence, combat.yaml's base and bounds
check("a fight's base is 60 and its bounds are in combat.yaml", I["base_odds"] == 60 and (I["min"], I["max"]) == (10, 90), I)
def fighter(dex, intel):
    return types.SimpleNamespace(attrs={"dexterity": dex, "intelligence": intel})
table = [(dex, intel, eff) for dex in (8, 10, 15, 20, 30) for intel in (10, 18) for eff in combat_improv.EFFECTS]
got = [(d, i, e, combat_improv.odds_for(fighter(d, i), e), formula(60, max(d, i), combat_improv.EFFECTS[e]["odds"], 10, 90)) for d, i, e in table]
check("a fight's odds are the formula's, effect by effect", all(a == b for *_, a, b in got), [g for g in got if g[3] != g[4]][:4])
check("...an attribute of 15 keeps the 60% it had, an effect with no shift", combat_improv.odds_for(fighter(15, 10), "gain_position") == 60.0)
keep = dict(I)
I["min"] = 40                                              # a floor a weak fighter reaches, to see the fight's own bound applied
floor = combat_improv.odds_for(fighter(3, 3), "disable")
I.update(keep)
check("...and a fight's odds stay within its own bounds", all(10 <= a <= 90 for *_, a, _ in got)
      and floor == 40 and combat_improv.odds_for(fighter(60, 3), "read_opening") == 90, floor)

# ---- outside a fight: the same formula with improv.yaml's base and bounds
W = world_improv.W
c = simlib.make_character("warrior", __import__("random").Random(1))[0]
for eff, e in ((k, v) for k, v in W["effects"].items() if v.get("attr")):    # a pose or a rest is never rolled
    attr = max(getattr(c.attributes, a) for a in e["attr"])
    if world_improv.odds_for(c, eff) != formula(W["base_odds"], attr, e["odds"], W["min"], W["max"]):
        check(f"outside a fight, {eff} is the formula's", False, (world_improv.odds_for(c, eff), attr)); break
else:
    check("outside a fight, every effect's odds are the formula's", True)
src_c = open("engine/combat_improv.py", encoding="utf-8").read()
src_w = open("engine/world_improv.py", encoding="utf-8").read()
check("...and neither resolver works the odds out its own way", "improv_odds(" in src_c and "improv_odds(" in src_w
      and "attribute_weight" not in src_c and "attribute_weight" not in src_w)
check("the fight's bounds are held at start-up", data_check.improv_problems() == [] and
      any("min" in p for p in data_check.improv_problems({**I, "min": "low"})), data_check.improv_problems({**I, "min": "low"}))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

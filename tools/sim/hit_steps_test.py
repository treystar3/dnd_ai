"""The hit chance shows its steps, and the steps add up to the chance."""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("rogue", 3))
from engine import combat
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

w = load_world()
wolf = combat.fighter_from_creature(w.bestiary["wolf"], 1, "normal", "e1", "wolf", "engaged")
p = combat.Fighter(id="p", name="p", side="player", level=1, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=50, max_hp=50, weapon_damage=6, armor=0, ward=0)
p.attrs["dexterity"] = 30
p.weapon_attrs = ["dexterity"]
p.reach = "ranged"
p.bonuses = [combat.Bonus(modifies="accuracy", trigger="always", magnitude=5)]
c = combat.Combat(fighters=[p, wolf])
from engine import battlefield as bf
bf.engage(c, p, wolf)
chance, steps = combat.hit_parts(p, wolf, c)
names = [n for n, _ in steps]
check("the steps name the base, the dexterity edge, the passive and the point-blank penalty", len(steps) == 4 and "accuracy from passives and gear" in names and any("point-blank" in n for n in names), steps)
check("they add up to the chance, to the rounding shown", abs(sum(v for _, v in steps) - chance) < 0.2, (steps, chance))
check("hit_chance is the same number", abs(combat.hit_chance(p, wolf, c) - chance) < 1e-9)
check("it matches the figure a player saw: 68.6%", abs(chance - 68.6) < 0.1, chance)
bf.disengage(c, p, wolf)
check("stepping back removes the penalty", abs(combat.hit_chance(p, wolf, c) - 83.6) < 0.1, combat.hit_chance(p, wolf, c))
tr = {}
import random
combat.roll_attack(p, wolf, c, random.Random(1), tr)
check("the record of a blow carries the steps for the window", "hit_steps" in tr and tr["chance"] == round(combat.hit_chance(p, wolf, c), 1), tr.get("hit_steps"))
e = combat.fighter_from_creature(w.bestiary["wolf"], 1, "normal", "e2", "archer", "engaged")
e.reach = "ranged"; e.damage_type = "physical"
pp = combat.Fighter(id="p2", name="p2", side="player", level=1, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=50, max_hp=50, weapon_damage=6, armor=0, ward=0)
c2 = combat.Combat(fighters=[pp, e])
bf.engage(c2, e, pp)
on = combat.hit_chance(e, pp, c2)
bf.disengage(c2, e, pp)
off = combat.hit_chance(e, pp, c2)
check("an enemy archer on top of its target loses 15 points too", abs((off - on) - 15) < 0.1, (on, off))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

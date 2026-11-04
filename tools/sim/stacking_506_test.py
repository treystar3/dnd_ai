"""(f506) The stacking recipes, one calculation for the fight and the window: engine/stacking.py combine is what raw_damage, mitigate's
gear defence, pools.maximum, resist_factor and element_factor and mechanics compute with, each recipe's parts in today's order (pinned to
the literal); the stat sheet reads the fight's own parts (damage_parts) and the fight's armour cut, so the sheet equals the fight; growth
is written once; combine explains every part it applied and the parts account for the value; the stat sheets of every stub class at
1, 10 and 25 are as recorded (the fixtures); the hit chance a player saw (68.6%, 83.6% after stepping back) holds. Nothing stays in the
process."""
import gzip
import json
import pathlib
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import yaml
from engine import combat, items, stacking
import fight_fixtures as ff

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

ST = yaml.safe_load(pathlib.Path("data/rules/stages.yaml").read_text(encoding="utf-8"))
RECIPES = {"base_damage": ("flat", "percent"), "mitigate": ("percent", "flat"), "pools": ("percent", "flat", "needs"),
           "resistance": ("sum", "clamp"), "mechanics": ("additive",)}
check("each recipe's parts are today's, in order, in the table and in the code", stacking.PARTS == RECIPES
      and {k: tuple(v) for k, v in ST["stacking"].items()} == RECIPES, (stacking.PARTS, ST["stacking"]))

# ---- combine explains every part it applied, and the parts account for the value
v, parts = stacking.combine("base_damage", {"weapon": 7.0, "attr_bonus": 9.8, "flat": 2.0, "multiplier": 1.75, "percent": 20.0, "variance": 1.1, "magic": 1.0})
check("base_damage: weapon + attribute + flat, x multiplier x (1 + percent) x variance x magic, each part named",
      abs(v - (7.0 + 9.8 + 2.0) * 1.75 * 1.2 * 1.1) < 1e-9 and [p[0] for p in parts] == ["base", "percent", "variance", "magic"] and parts[0][1] == 18.8, (v, parts))
v, parts = stacking.combine("mitigate", {"amount": 40.0, "percent": 25.0, "flat": 5.0})
check("mitigate: percent then flat, the cuts summing to what was taken off", abs(v - 25.0) < 1e-9 and [p[0] for p in parts] == ["gear defence", "flat defence"]
      and abs(sum(p[1] for p in parts) - (40.0 - v)) < 1e-9, (v, parts))
v, parts = stacking.combine("mitigate", {"amount": 40.0, "percent": 99.0, "flat": 50.0})
check("...never below a twentieth of the way in for the percent, a tenth for the flat", abs(v - 4.0) < 1e-9, v)
v, parts = stacking.combine("pools", {"raw": 100.0, "percent": 0.1, "flat": 12.0, "needs": -10.0})
check("pools: raw x (1 + percent) + flat, then hunger and fatigue", abs(v - (100 * 1.1 + 12) * 0.9) < 1e-9 and [p[0] for p in parts] == ["raw", "percent", "flat", "needs"], (v, parts))
v, parts = stacking.combine("resistance", {"values": [30.0, 20.0, 40.0], "cap": 75, "floor": 0})
check("resistance: summed and clamped to the cap", abs(v - 0.25) < 1e-9 and parts == [["sum", 90.0], ["clamp", 75]], (v, parts))
v, parts = stacking.combine("resistance", {"values": [-50.0, -80.0], "cap": 75, "floor": -100})
check("...an element below zero is a weakness, floored at a doubling", abs(v - 2.0) < 1e-9 and parts[1] == ["clamp", -100], (v, parts))
v, parts = stacking.combine("mechanics", {"sources": [{"aegis": 10.0, "flurry": 5.0}, {"flurry": 40.0}, {"aegis": 1}]})
check("mechanics: every source adds, keys in the order they first came", v == {"aegis": 11.0, "flurry": 45.0} and list(v) == ["aegis", "flurry"] and parts == [["additive", 3]], (v, parts))

# ---- the fight computes with the recipes, and the sheet reads the fight's parts
src = pathlib.Path("engine/combat.py").read_text(encoding="utf-8")
check("raw_damage, mitigate, resist_factor, element_factor and mechanics compute through combine", src.count('stacking.combine("base_damage"') == 1
      and src.count('stacking.combine("mitigate"') == 1 and src.count('stacking.combine("resistance"') == 2 and src.count('stacking.combine("mechanics"') == 1
      and "* (1 + pct / 100) * variance * magic" not in src and "after *= max(0.05, 1 - def_pct / 100)" not in src)
check("...and pools.maximum", 'stacking.combine("pools"' in pathlib.Path("engine/pools.py").read_text(encoding="utf-8"))
sheet_src = pathlib.Path("engine/statsheet.py").read_text(encoding="utf-8")
check("the sheet reads the fight's parts and the fight's armour cut, repeating neither formula", "combat.damage_parts(f, 1.0, always)" in sheet_src
      and "combat.armour_cut(protection, f.level)" in sheet_src and 'd["attribute_bonus"] + flat' not in sheet_src and 'm["armor_k"]' not in sheet_src)
check("growth is written once", combat.growth(7) == items.level_growth(7) and "item_level_growth" not in src[src.index("def growth("):src.index("def growth(") + 300])
char, _ = simlib.make_character("warrior", random.Random(3))
f = combat.fighter_from_character(char)
p = combat.damage_parts(f, 1.0, {"always"})
avg, _ = stacking.combine("base_damage", p)
steady = combat.raw_damage(f, 1.0, {"always"}, random.Random(1), steady=True)
check("the sheet's attack power is the fight's steady blow", abs(avg - steady) < 1e-9 and p["variance"] == 1.0, (avg, steady))

# ---- the recorded sheets and the hit chance a player saw hold
kept = ff._read(ff.OUT / "sheets.json.gz")
now = ff._norm(ff.sheets())
check("every stub class's stat sheet at levels 1, 10 and 25 is as recorded", kept["sheets"] == now, ff.first_difference(kept["sheets"], now))
game = simlib.campaign("stacking_506", cls="warrior", seed=3, location="south_fields")     # the bestiary, through the one helper (f450)
wolf = combat.fighter_from_creature(game.scene.world.bestiary["wolf"], 1, "normal", "e1", "wolf", "engaged")
p = combat.Fighter(id="p", name="p", side="player", level=1, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=50, max_hp=50, weapon_damage=6, armor=0, ward=0)
p.attrs["dexterity"] = 30
p.weapon_attrs = ["dexterity"]
p.reach = "ranged"
p.bonuses = [combat.Bonus(modifies="accuracy", trigger="always", magnitude=5)]
c = combat.Combat(fighters=[p, wolf])
from engine import battlefield as bf
bf.engage(c, p, wolf)
check("the hit chance a player saw holds: 68.6% point-blank", abs(combat.hit_chance(p, wolf, c) - 68.6) < 0.1, combat.hit_chance(p, wolf, c))
bf.disengage(c, p, wolf)
check("...and 83.6% after stepping back", abs(combat.hit_chance(p, wolf, c) - 83.6) < 0.1, combat.hit_chance(p, wolf, c))

game.close()
import shutil
shutil.rmtree("saves/stacking_506", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

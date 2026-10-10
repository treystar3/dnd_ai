"""Attributes and resistances on gear."""
import random, sys, collections
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import items, loot, combat, pools, stats, elements
from core.models import ItemProperty
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

check("elements read from words", elements.of_text("Frostbolt") == "cold" and elements.of_text("Lightning Strike") == "lightning"
      and elements.of_text("Holy Smite") == "radiant" and elements.of_text("Shadow Bolt") == "necrotic" and elements.of_text("Sunlight") == "")
rng = random.Random(1)
# rolls: every kind appears somewhere, resistances are percent-sized, attributes flat
seen = collections.Counter(); sizes = collections.defaultdict(list)
for _ in range(4000):
    b = rng.choice([x for x in items.CATALOG.values() if x.slot not in ("none",) and (x.is_weapon or x.base or x.slot in ("neck", "ring"))])
    r = rng.choice(["uncommon", "rare", "epic", "legendary"])
    it = items.make(b.id, r, rng.randint(10, 200), rng=rng); loot.roll_gear(it, rng)
    for p in it.properties:
        seen[p.modifies] += 1
        if p.modifies.endswith("_resistance") and p.modifies != "all_elemental_resistance": sizes[r].append(p.magnitude)
check("all 9 resistances and 6 attributes roll somewhere", all(seen[x] for x in items.RULES["gear_only_stats"]["resistance"] + items.RULES["gear_only_stats"]["attribute"]),
      str({k: v for k, v in seen.items() if k.endswith("resistance") or k in stats.STAT_NAMES}))
check("resistance size follows rarity", max(sizes["uncommon"]) <= 5 and min(sizes["legendary"]) >= 12)
# a staff rolls its own casting attribute only
st = items.make("runestaff", "legendary", 100, rng=rng)
check("a focus rolls its own attribute", set(loot.gear_stats(st)) >= {"intelligence"} and not ({"wisdom", "charisma", "strength"} & set(loot.gear_stats(st))), str(loot.gear_stats(st)))

# attribute bonus raises the character's attributes, pools and checks
ch, _ = simlib.make_character("warrior", random.Random(2))
ch.level = 60; ch.passives = []; ch.equipment = {}
base_str, base_hp = ch.attributes.strength, pools.maximum(ch, "health")
helm = items.make("iron_helm", "epic", 60, material="steel")
helm.properties = [ItemProperty(modifies="strength", trigger="always", magnitude=6), ItemProperty(modifies="constitution", trigger="always", magnitude=6),
                   ItemProperty(modifies="fire_resistance", trigger="always", magnitude=20)]
ch.equipment = {"head": helm}
gain = items.flat_value("strength", 6, 60)
check("gear attribute adds flat points", stats.effective(ch, "strength") == base_str + gain and gain >= 5, f"{base_str} -> {stats.effective(ch, 'strength')}")
check("constitution from gear raises health", pools.maximum(ch, "health") > base_hp, f"{base_hp} -> {pools.maximum(ch, 'health')}")
check("base attributes untouched", ch.attributes.strength == base_str)
f = combat.fighter_from_character(ch)
check("fighter uses the gear attribute", f.attrs["strength"] == base_str + gain)

# resistance in a fight
def dmg_through(dtype, element):
    foe = combat.Fighter(id="e", name="foe", side="enemy", level=60, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=1000, max_hp=1000,
                         element=element, damage_type=dtype)
    cmb = combat.Combat(fighters=[f, foe])
    f.hp = f.max_hp = 100000
    return combat.resist_factor(f, dtype, element)
check("fire resistance cuts fire only", abs(dmg_through("magical", "fire") - 0.8) < 1e-9 and dmg_through("magical", "cold") == 1.0)
helm.properties.append(ItemProperty(modifies="physical_resistance", trigger="always", magnitude=30))
f = combat.fighter_from_character(ch)
check("physical resistance cuts physical blows", abs(dmg_through("physical", "") - 0.7) < 1e-9 and dmg_through("magical", "") == 1.0)
helm.properties += [ItemProperty(modifies="physical_resistance", trigger="always", magnitude=90)]
f = combat.fighter_from_character(ch)
check("resistance is capped", abs(dmg_through("physical", "") - 0.25) < 1e-9)
# enemies and abilities carry elements
world_creature = types = None
from world.loader import load_world
w = load_world()
els = collections.Counter(elements.of_creature(c) for c in w.bestiary.values())
check("some creatures carry elements", sum(v for k, v in els.items() if k) >= 15, str(dict(els)))

# all-elemental resistance: only heavy armor and shields roll it; it cuts every element but not physical or magical
only = set()
rng2 = random.Random(4)
for _ in range(3000):
    b = rng2.choice([x for x in items.CATALOG.values() if x.slot not in ("none", "neck", "ring") and (x.is_weapon or x.base)])
    it = items.make(b.id, "legendary", 80, rng=rng2); loot.roll_gear(it, rng2)
    if any(p.modifies == "all_elemental_resistance" for p in it.properties): only.add(loot.gear_kind(b))
check("only heavy armor and shields roll all-elemental", only == {"armor.heavy", "armor.shield"}, str(only))
helm.properties = [ItemProperty(modifies="all_elemental_resistance", trigger="always", magnitude=10)]
f = combat.fighter_from_character(ch)
check("all-elemental cuts each element", all(abs(combat.resist_factor(f, "magical", e) - 0.9) < 1e-9 for e in elements.ELEMENTS)
      and combat.resist_factor(f, "physical", "") == 1.0 and combat.resist_factor(f, "magical", "") == 1.0)
foe = combat.Fighter(id="e", name="elemental", side="enemy", level=60, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=100, max_hp=100, element="fire")
check("a creature of an element resists it", abs(combat.resist_factor(foe, "magical", "fire") - 0.5) < 1e-9 and combat.resist_factor(foe, "magical", "cold") == 1.0)

# crit chance and elemental damage
sword = items.make("longsword", "epic", 60, material="steel")
sword.properties = [ItemProperty(modifies="crit_chance", trigger="always", magnitude=20), ItemProperty(modifies="fire_damage", trigger="always", magnitude=10)]
ch.equipment = {"main_hand": sword}
fa = combat.fighter_from_character(ch)
foe = combat.fighter_from_creature(next(c for c in w.bestiary.values() if c.category == "beast"), 60, "normal", "e1", "wolf", "engaged")
foe.hp = foe.max_hp = 10 ** 6
cmb = combat.Combat(fighters=[fa, foe])
def crits(n=4000):
    r = random.Random(5); k = 0
    for _ in range(n):
        o, _c = combat.roll_attack(fa, foe, cmb, r); k += o == "crit"
    return k / n
with_gear = crits()
ch.equipment = {}; fb = combat.fighter_from_character(ch); fa_save, fa = fa, fb
without = crits(); fa = fa_save
check("crit chance gear raises crits", with_gear > without + 0.08, f"{without:.1%} -> {with_gear:.1%}")
fa = fa_save
lines_before = len(cmb.log)
_r = random.Random(6)
for _ in range(80): combat.apply_damage(cmb, fa, foe, 1.0, "hits", _r, how="with a sword")
check("elemental damage follows the blow", any("fire damage burns" in l for l in cmb.log[lines_before:]), str(cmb.log[-2:]))
sword.properties = [ItemProperty(modifies="crit_damage", trigger="always", magnitude=30)]
ch.equipment = {"main_hand": sword}
fa = combat.fighter_from_character(ch)
check("crit damage adds flat points to the multiplier", abs(combat.crit_multiplier(fa) - 1.8) < 1e-9 and combat.crit_multiplier(fb) == 1.5, f"{combat.crit_multiplier(fa)}")
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)

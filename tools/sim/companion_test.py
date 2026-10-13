"""Companion damage and durability on gear, and the companion legendaries."""
import random, sys, collections
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import items, loot, combat
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def fighter(id, side, level=50, hp=100000):
    return combat.Fighter(id=id, name=id, side=side, level=level, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp, weapon_damage=50, armor=0, ward=0)

def scene(player_bonus=(), legendary=None):
    p = fighter("p", "player")
    for stat, n in player_bonus:
        p.bonuses.append(combat.Bonus(modifies=stat, trigger="always", magnitude=n))
    if legendary:
        p.legendary = legendary
    pet = fighter("ally_pet", "ally"); foe = fighter("e", "enemy")
    return combat.Combat(fighters=[p, pet, foe]), p, pet, foe

def avg_hit(bonus, n=300):
    cmb, p, pet, foe = scene(bonus)
    rng = random.Random(1); tot = 0
    for _ in range(n):
        foe.hp = foe.max_hp
        combat.apply_damage(cmb, pet, foe, 1.0, "hits", rng)
        tot += foe.max_hp - foe.hp
    return tot / n
a, b = avg_hit([]), avg_hit([("companion_damage", 50)])
check("companion damage raises what companions deal", 1.35 < b / a < 1.65, f"{a:.1f} -> {b:.1f}")

def taken(bonus, n=300):
    cmb, p, pet, foe = scene(bonus); rng = random.Random(2); tot = 0
    for _ in range(n):
        pet.hp = pet.max_hp
        tot += combat.take_damage(cmb, pet, 1000, foe, rng, "physical")
    return tot / n
a, b = taken([]), taken([("companion_durability", 100)])
check("companion durability cuts the harm they take", 0.45 < b / a < 0.55, f"{a:.0f} -> {b:.0f}")

cmb, p, pet, foe = scene()
dmg_to_player = combat.take_damage(cmb, p, 1000, foe, random.Random(3), "physical")
cmb, p, pet, foe = scene([("companion_durability", 100)])
check("durability does not protect the player", combat.take_damage(cmb, p, 1000, foe, random.Random(3), "physical") == dmg_to_player)

cmb, p, pet, foe = scene(legendary={"lifeline": 1})
pet.hp = pet.max_hp = 50
combat.take_damage(cmb, pet, 500, foe, random.Random(4), "physical")
check("lifeline holds a companion to life once", pet.hp == 1)
combat.take_damage(cmb, pet, 500, foe, random.Random(4), "physical")
check("...but only once", pet.hp == 0)

cmb, p, pet, foe = scene(legendary={"packbond": 100})
rng = random.Random(5); foe.hp = foe.max_hp = 10**6
combat.apply_damage(cmb, p, foe, 1.0, "hits", rng)
check("packbond brings the companion in on a hit", any("Packbond" in l or "alongside" in l for l in cmb.log), cmb.log[-2:])

cmb, p, pet, foe = scene(legendary={"lifebinder": 50})
pet.hp, pet.max_hp = 10, 10**6
rr = random.Random(6)
for _ in range(20): combat.apply_damage(cmb, p, foe, 1.0, "hits", rr)
check("lifebinder heals companions from your damage", pet.hp > 10, pet.hp)

# gear rolls
rng = random.Random(7); seen = collections.defaultdict(int); sizes = collections.defaultdict(list)
for _ in range(6000):
    b_ = rng.choice([x for x in items.CATALOG.values() if x.slot != "none" and (x.is_weapon or x.base or x.slot in ("neck", "ring"))])
    r = rng.choice(["uncommon", "rare", "epic", "legendary"])
    it = items.make(b_.id, r, rng.randint(5, 300), rng=rng); loot.roll_gear(it, rng)
    for pr in it.properties:
        if pr.modifies.startswith("companion_"):
            seen[(pr.modifies, loot.gear_kind(b_) if b_.slot not in ("neck", "ring") else "jewelry")] += 1; sizes[r].append(pr.magnitude)
check("companion damage rolls on focus weapons and mystic jewelry", seen[("companion_damage", "weapon.focus")] and seen[("companion_damage", "jewelry")], dict(seen))
check("companion durability rolls on cloth and jewelry", seen[("companion_durability", "armor.cloth")] and seen[("companion_durability", "jewelry")])
check("nothing else rolls them", all(k[1] in ("weapon.focus", "weapon.offfocus", "armor.cloth", "jewelry") for k in seen))
check("sizes follow rarity", all(min(v) >= lo and max(v) <= hi for r, (lo, hi) in {"uncommon": (4, 7), "rare": (7, 11), "epic": (11, 16), "legendary": (16, 24)}.items() for v in [sizes[r]] if v), {r: (min(v), max(v)) for r, v in sizes.items()})
it = items.make("runestaff", "rare", 50, rng=rng); it.properties = [loot.ItemProperty(modifies="companion_damage", trigger="always", magnitude=9)]
check("shown as a percentage", "+9% companion damage" in items.summary(it), items.summary(it))
# companion legendaries roll only for companion characters
import collections as _c
def legendaries(companions, n=1500):
    r = random.Random(12); got = _c.Counter()
    for _ in range(n):
        it = loot.make_drop(100, "legendary", r, companions)
        got[it.legendary_effect] += 1
    return got
plain, pets = legendaries(False), legendaries(True)
mine = {"packbond", "lifebinder", "lifeline", "guardian"}
check("non-companion drops never carry them", not (set(plain) & mine), {k: plain[k] for k in mine})
check("companion drops can", all(pets[k] for k in mine if any(
    items.LEGENDARY[k].applies == kind for kind in ("weapon", "armor"))), {k: pets[k] for k in mine})
class _C:                      # stand-ins for characters
    def __init__(s, uses=False, comps=(), acts=()): s.uses_companions, s.companions, s.actives = uses, list(comps), list(acts)
class _A:
    def __init__(s, e): s.effect = e
check("a companion class counts", loot.keeps_companions(_C(uses=True)))
check("a summoner of any class counts", loot.keeps_companions(_C(acts=[_A("summon")])))
check("a plain class does not", not loot.keeps_companions(_C(acts=[_A("damage")])) and not loot.keeps_companions(None))
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)

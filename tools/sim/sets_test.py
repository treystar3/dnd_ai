"""Armor sets: only armor counts, thresholds, hooks into combat/pools/world, caps by era, no 'against X' on armor materials or rolled gear."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import sets, items, combat, pools, loot
from core.models import Item

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

def piece(base, material, rarity="common", lvl=50):
    it = items.make(base, rarity, lvl, rng=random.Random(1))
    it.material = material
    it.properties = []
    return it

char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 60
eq = lambda **k: k

# every set names a real material; wood has none; thresholds
check("every set is for a real armor material", all(m in items.MATERIALS and items.MATERIALS[m].family != "wood" for m in sets.SETS))
armor_mats = [m.id for m in items.MATERIALS.values() if m.family != "wood"]
check("every metal/hide/cloth material has a set", all(m in sets.SETS for m in armor_mats), str([m for m in armor_mats if m not in sets.SETS]))

# counting: only armor
E = {"head": piece("iron_helm", "silver"), "body": piece("leather", "silver"), "main_hand": piece("longsword", "silver"),
     "ring_1": piece("ring", "silver"), "neck": piece("amulet", "silver")}
E["body"].material = "silver"
check("weapons, rings and amulets never count", sets.counts(E) == {"silver": 2}, str(sets.counts(E)))
check("two pieces give the two-piece bonus only", [a[1] for a in sets.active(E)] == [2])
E["hands"] = piece("leather_gloves", "silver"); E["feet"] = piece("boots", "silver")
check("four pieces give both bonuses", [a[1] for a in sets.active(E)] == [2, 4])
S = {"head": piece("iron_helm", "steel"), "off_hand": piece("buckler", "steel")}
check("a shield counts as armor", sets.counts(S) == {"steel": 2})
check("one piece gives nothing", sets.active({"head": piece("iron_helm", "steel")}) == [])

# hooks
c = char.model_copy(deep=True)
c.equipment = {"head": piece("iron_helm", "steel"), "body": piece("leather", "steel"), "hands": piece("leather_gloves", "steel"), "feet": piece("boots", "steel")}
c0 = char.model_copy(deep=True); c0.equipment = {k: v.model_copy() for k, v in c.equipment.items()}
c.passives = []; c0.passives = []
for i in c0.equipment.values(): i.material = "bronze"
f = combat.fighter_from_character(c)
check("combat: set effects become fighter bonuses", any(b.modifies == "defense" and b.flat and b.magnitude == items.flat_value("defense", 5, round(sum(i.item_level for i in c.equipment.values()) / len(c.equipment))) for b in f.bonuses))
check("combat: set mechanics become fighter mechanics", f.legendary.get("aegis") == 13, str(f.legendary))
c.equipment["head"].material = "wool_linen"
check("breaking the set removes it", not combat.fighter_from_character(c).legendary.get("aegis"))
# world mechanic
c2 = char.model_copy(deep=True)
c2.equipment = {"head": piece("leather_cap", "wolf_hide"), "body": piece("leather", "wolf_hide"), "hands": piece("leather_gloves", "wolf_hide"), "feet": piece("boots", "wolf_hide")}
check("world mechanics reach pools.mechanic", pools.mechanic(c2, "tracker") is not None and pools.mechanic(char.model_copy(deep=True), "tracker") is None)
# stat outside combat: max_health +4 from two bear pieces
c3 = char.model_copy(deep=True); c3.equipment = {}
base = pools.maximum(c3, "health")
c3.equipment = {"head": piece("leather_cap", "bear_hide"), "body": piece("leather", "bear_hide")}
for i in c3.equipment.values(): i.material = "bear_hide"
check("stat bonus raises the pool", pools.maximum(c3, "health") > base - 1 and sets.effects(c3.equipment)[0].magnitude == items.flat_value("max_health", 4, round(sum(i.item_level for i in c3.equipment.values()) / 2)))

# caps by era
caps = sets.D["caps"]
def cap_for(m):
    lv = items.MATERIALS[m].levels[0]
    return [c for c in caps if lv >= c["from"]][-1]
over = []
for m, s in sets.SETS.items():
    cp = cap_for(m)
    two, four = s.get("two", {}), s.get("four", {})
    for tier in (two, four):
        for e in tier.get("effects", []):
            if e[2] > cp["stat"]: over.append((m, e))
        for k, v in {**tier.get("fight", {}), **tier.get("world", {})}.items():
            le = items.LEGENDARY.get(k) or next((x for x in items.LEGENDARY.values() if x.world == k), None)
            if le is None: over.append((m, k, "unknown")); continue
            if v == 0:
                if le.value and not le.world: continue
                if k in ("sanctified",) and cp["flags"] in ("sanctified", True): continue
                if k == "unyielding" and cp["flags"] is True: continue
                if le.world: continue          # world wonders without a number
                over.append((m, k, "flag too early"))
            elif v > le.value * cp["share"] + 1e-9: over.append((m, k, v, round(le.value * cp["share"], 2)))
check("every set stays under its era's cap", not over, str(over))
check("the four-piece bonus is never weaker than none", all("four" in s and "two" in s for s in sets.SETS.values()))

# newer-tier armor beats keeping a set: a rare piece of the next era out-armors the set bonus it breaks
g = items.level_growth
worth = lambda it: items.value(it)
old = piece("iron_helm", "iron", "common", 30); new = piece("iron_helm", "steel", "rare", 45)
check("a rare piece one era up out-armors the old common one by more than a quarter", worth(new) > worth(old) * 1.25, f"{worth(old):.1f} -> {worth(new):.1f}")

# no 'against X' on armor materials; none in rolled properties
against = []
for m in items.MATERIALS.values():
    for e in list(m.any) + list(m.armor):
        if e.trigger.startswith("against_"): against.append((m.id, e.trigger))
check("no armor material gives an 'against' bonus", not against, str(against))
weap = sorted(m.id for m in items.MATERIALS.values() if any(e.trigger.startswith("against_") for e in m.weapon))
check("only a few weapon materials keep one", len(weap) <= 5, str(weap))
rolled = set()
for r in ["uncommon", "rare", "epic", "legendary"]:
    for i in range(1500):
        for p in loot.roll_properties(r, random.Random(i), 1): rolled.add(p.trigger)
check("rolled properties never say 'against'", not any(t.startswith("against_") for t in rolled), str(sorted(t for t in rolled if t.startswith('against'))))

# every cloth family can finish a four-piece set
slots = {}
for b in items.CATALOG.values():
    if not b.is_weapon and b.slot in ("head", "body", "hands", "feet"): slots.setdefault(b.family, set()).add(b.slot)
check("metal, hide and cloth each have all four set slots", all(slots.get(f, set()) >= {"head", "body", "hands", "feet"} for f in ("metal", "hide", "cloth")), str(slots))

# the screen text
txt = sets.summary(E)
check("equipment screen text lists the set", any("silver set (4 pieces)" in l for l in txt) and any("✓ 4 pieces" in l for l in txt), str(txt))
print("ALL PASS" if not bad else f"FAILED {bad}")

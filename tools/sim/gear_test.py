"""Far-lands gear: new bases are level-gated, new materials resolve, new legendary effects reach combat and behave."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import items, loot, combat, party, crafting
from world.loader import load_world

fails = []
def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

world = load_world()
NEW_BASES = [b for b in items.CATALOG.values() if b.min_level]
check("new gear types exist", len(NEW_BASES) >= 20)
rng = random.Random(4)
low = {loot.make_drop(60, r, random.Random(i)).base for i in range(600) for r in ("rare", "epic")}
check("no end-game gear below level 80", not any(items.CATALOG[b].min_level for b in low))
high = {loot.make_drop(120, r, random.Random(i)).base for i in range(1500) for r in ("rare", "epic", "legendary")}
check("end-game gear drops at level 120", sum(1 for b in high if items.CATALOG[b].min_level) >= 12)
check("every new gear type has attribute requirements or is jewelry", all(b.requires or b.slot in ("neck", "ring") for b in NEW_BASES))
check("no end-game weapon is a starting weapon option", not any(b.is_weapon and not b.requires for b in NEW_BASES))
for b in NEW_BASES:
    mats = [m for m in items.MATERIALS.values() if m.family == b.family and m.levels[0] <= 120 <= m.levels[1]]
    if not mats: check(f"{b.id} has a material at 120", False)
check("every family has far-lands materials at 120", all(any(m.family == f and m.levels[0] >= 90 and m.levels[0] <= 120 and m.levels[1] >= 120 for m in items.MATERIALS.values()) for f in ("metal", "hide", "cloth", "wood")))
st = crafting.CRAFTABLE
class N: pass
n = N(); n.stock = []; n.stock_day = -1; n.id = "t"
crafting.lay_out_stock(n, {"families": ["metal", "wood"], "count": 40}, (70, 125), 0, 1)
stocked = {i["base"] for i in n.stock}
check("a far-lands merchant stocks end-game gear", any(items.CATALOG[b].min_level for b in stocked))
n2 = N(); n2.stock = []; n2.stock_day = -1; n2.id = "t"
crafting.lay_out_stock(n2, {"families": ["metal", "wood"], "count": 40}, (20, 45), 0, 1)
check("an old-lands merchant does not", not any(items.CATALOG[i["base"]].min_level for i in n2.stock))

# every new weapon and armor effect can roll somewhere, and category effects reach the fighter
ids = [e for e in items.LEGENDARY.values() if e.enabled]
for e in ids:
    pool = {"weapon": ["longsword", "falchion", "scepter", "hand_wraps"], "armor": ["plate", "archmage_raiment"], "jewelry": ["amulet", "torc"]}.get(e.applies, [])
    ok = any(e.id in {o.id for o in items.legendary_options(items.CATALOG[b], True)} for b in pool)
    if not ok: check(f"{e.id} can roll", False)
from core.models import Character
char, _ = simlib.make_character("warrior", random.Random(1))
for e in ids:
    if not e.category or e.id not in ("elementbane", "mindbane", "rootcleaver", "runebreaker", "monsterbane", "fayslayer", "manhunter",
                                      "elementward", "mindward", "briarward", "runeward", "monsterward", "bladeward", "wildward", "fayward"): continue
    base = "longsword" if e.applies == "weapon" else "plate"
    it = items.make(base, "legendary", 100, rng=random.Random(1)); it.legendary_effect = e.id
    char.equipment.clear(); char.equipment[items.CATALOG[base].slot] = it
    f = combat.fighter_from_character(char)
    got = (f.slays if e.applies == "weapon" else f.wards).get(e.category, 0)
    check(f"{e.id} reaches combat against {e.category}", got == e.value)

# behaviours
def pair(**leg):
    a = party.fighter({"id": "a", "name": "A", "role": "fighter", "level": 80}); a.side = "player"
    d = party.fighter({"id": "d", "name": "D", "role": "fighter", "level": 80}); d.side = "enemy"
    a.legendary = dict(leg); a.max_hp = a.hp = 5000; d.max_hp = d.hp = 100000
    a.max_stamina = 100; a.stamina = 10
    return combat.Combat(fighters=[a, d]), a, d
def landed(att, dfn, cmb, tries=60, seed=1):
    r = random.Random(seed)
    for _ in range(tries):
        if combat.apply_damage(cmb, att, dfn, 1.0, "hits", r): return True
    return False
cmb, a, d = pair(terrify=100); landed(a, d, cmb); check("Dread Edge frightens", "frightened" in d.statuses)
cmb, a, d = pair(blinding=100); landed(a, d, cmb); check("Ashblind blinds", "blinded" in d.statuses)
cmb, a, d = pair(hex=1); landed(a, d, cmb); check("Hexbrand curses", "hexed" in d.statuses)
cmb, a, d = pair(battle_rhythm=10); landed(a, d, cmb); check("War Rhythm restores stamina", a.stamina > 10)
cmb, a, d = pair(flurry=100); landed(a, d, cmb); check("Stormflurry follows up", any("follow-up" in l or "again" in l for l in cmb.log) or len([l for l in cmb.log if "damage" in l]) >= 2)
def avg(cmb, a, d, n=80):
    tot = 0
    for i in range(n):
        d.hp = d.max_hp; b = d.hp
        combat.apply_damage(cmb, a, d, 1.0, "hits", random.Random(i)); tot += b - d.hp
    return tot
cmb, a, d = pair(opportunist=100); plain = avg(cmb, a, d); d.statuses["slowed"] = 9; hurt = avg(cmb, a, d)
check("Hamstringer hits the hobbled harder", hurt > plain * 1.5)
cmb, a, d = pair(soul_harvest=50); a.max_mana = 100; a.mana = 0; d.hp = 1
landed(a, d, cmb); check("Soul Reaper returns mana on a kill", a.mana >= 40)
cmb, a, d = pair(); cmb2, a2, d2 = pair(deflect=100)
check("Deflecting halves blows", avg(cmb2, d2, a2) < avg(cmb, d, a) * 0.7)
def lethal(**leg):
    cmb, a, d = pair(**leg); a.hp = 1000; a.max_hp = 1000
    combat.take_damage(cmb, a, 800, d, random.Random(1), "physical"); return a.hp
check("Second Wind heals below a quarter", lethal(second_wind=40) > lethal())
cmb, a, d = pair(mana_shield=50); a.max_mana = a.mana = 1000
before = a.hp; combat.take_damage(cmb, a, 400, d, random.Random(1), "physical")
check("Manaplate spends mana for health", a.mana < 1000 and before - a.hp < 400)
print("FAILED" if fails else "ALL OK", fails)
sys.exit(1 if fails else 0)

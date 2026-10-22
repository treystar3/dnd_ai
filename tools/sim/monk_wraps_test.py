"""Monk wraps: legendary effects only hand wraps can roll, and what they do in a fight."""
import sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("monk", 1))
from engine import combat, items, loot
from tools.tune_classes import build
from world.loader import load_world
fails = []
def check(n, ok):
    print(("ok   " if ok else "FAIL ") + n)
    if not ok: fails.append(n)
NEW = {"ki_strike", "open_palm", "flowing_step", "still_water"}
check("wraps can roll all four", NEW <= {e.id for e in items.legendary_options(items.CATALOG["hand_wraps"])})
others = [b for b in items.CATALOG.values() if b.slot != "none" and b.id != "hand_wraps"]
check("nothing else can roll them", not any(NEW & {e.id for e in items.legendary_options(b)} for b in others))
rng = random.Random(3)
picked = [items.pick_legendary(items.legendary_options(items.CATALOG["hand_wraps"]), rng).id for _ in range(600)]
share = sum(p in NEW for p in picked) / 600
check(f"about half of legendary wraps are monk effects ({share:.0%})", 0.35 < share < 0.65)

world = load_world()
def setup(effect, armored=False):
    ch = build("monk", 50, random.Random(1))
    ch.equipment["main_hand"].legendary_effect = effect
    ch.equipment["main_hand"].rarity = "legendary"
    if not armored: ch.equipment.pop("body", None)
    return ch
def duel(effect, armored=False, seed=1):
    ch = setup(effect, armored)
    p = combat.fighter_from_character(ch)
    e = combat.fighter_from_creature(world.bestiary["troll"], 50, "normal", "e1", start="engaged")
    return p, e, combat.Combat(fighters=[p, e]), random.Random(seed)

p, e, c, r = duel("ki_strike"); p.stamina = 0
for _ in range(40):
    combat.apply_damage(c, p, e, 1.0, "attacks (hand wraps)", r)
    e.hp = e.max_hp
check("Ki Strike refills stamina on hits", p.stamina > 0.06 * p.max_stamina)

p, e, c, r = duel("open_palm"); knocked = 0
for _ in range(60):
    e.statuses.pop("prone", None); e.hp = e.max_hp
    combat.apply_damage(c, p, e, 1.0, "attacks (hand wraps)", r)
    knocked += "prone" in e.statuses
check(f"Open Palm sweeps enemies off their feet ({knocked}/60)", knocked >= 5)

p, e, c, r = duel("flowing_step")
p2 = combat.fighter_from_character(setup("flowing_step"))
for _ in range(10):
    e.attrs["dexterity"] = 1; p.attrs["dexterity"] = 9999
    combat.apply_damage(c, e, p, 1.0, "strikes", r)
check("Flowing Step builds up on misses and caps at three", 1 <= p.counters.get("flow", 0) <= 3)
before = p.counters.get("flow", 0); e.hp = e.max_hp
combat.apply_damage(c, p, e, 1.0, "attacks (hand wraps)", r)
check("...and is spent on the next strike", p.counters.get("flow", 0) == 0 and before > 0)

bare = combat.fighter_from_character(setup("still_water"))
dressed = combat.fighter_from_character(setup("still_water", armored=True))
check("Still Water reduces damage only without body armor", combat.mechanics(bare, None).get("stoneskin", 0) == 18 and not combat.mechanics(dressed, None).get("stoneskin"))
print("ALL OK" if not fails else f"FAILED {fails}")

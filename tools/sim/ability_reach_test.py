"""An ability used on a target out of reach: the action is spent closing the distance, and the ability is kept (no cost, no cooldown)."""
import sys, random
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
uc.note = lambda *a, **k: None
uc.narrate = lambda *a, **k: None
from engine import combat
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
ch, _ = simlib.make_character("warrior", random.Random(2))
me = combat.fighter_from_character(ch)
wolf = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "w0", "Wolf", "far")
f = combat.Combat(fighters=[me, wolf], place="x", conditions=[])
from engine import battlefield as bf, battlefield_builder as bb
f.battlefield = bb.build("forest", random.Random(4))
while len(f.battlefield.zones) < 3:
    f.battlefield = bb.build("forest", random.Random(random.randrange(999)))
bf.place_fighters(f)
far = max(f.battlefield.zones, key=lambda z: f.battlefield.steps(me.zone_id, z))
bf.enter_zone(f, wolf, far)
f.round = 1
move = next(m for m in me.moves if m.id == "brutal_strike")
st0, hp0 = me.stamina, wolf.hp
check("the wolf is out of reach", not combat.in_reach(me, wolf, move.reach))
res = combat.act_ability(f, me, move, wolf, random.Random(1))
check("no problem is reported, the action is used", res is None)
check("the player is a step closer to the wolf", me.zone_id != f.battlefield.start or f.battlefield.steps(me.zone_id, wolf.zone_id) <= 1,
      (me.zone_id, wolf.zone_id))
check("no stamina is spent", me.stamina == st0, (st0, me.stamina))
check("no cooldown is set", me.cooldowns.get(move.id, 0) == 0, me.cooldowns)
check("nothing is damaged", wolf.hp == hp0)
res = combat.act_ability(f, me, move, wolf, random.Random(1))
check("arrived, the next use is the real strike: moving into the fight is easy", me.zone_id == wolf.zone_id and me.stamina < st0
      and me.cooldowns.get(move.id, 0) > 0, (me.zone_id, wolf.zone_id, me.stamina, me.cooldowns))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")

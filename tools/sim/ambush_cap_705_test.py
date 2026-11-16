"""(f705) No foe is met above its place's danger, and a road ambush is never far above the party (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). On the Old Quarry Road a black pudding of level 32 (637 health) ambushed a level 17 mage
with level 8 companions ("danger estimate: deadly, 9% win rate"). encounters.roll drew a creature whose lowest level is above the
place's whole danger and gave it a level between the two crossed bounds: its own, past anything the place holds.
Held here: a creature drawn whose levels do not meet the place's danger gives way to one of the roster that does; with none, it is met
at the place's top; and on the road, an ambush's foes are at most road.yaml ambush_above levels over the party's leader.
Run: python tools/sim/ambush_cap_705_test.py"""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import encounters
from llm.contracts import RoadEvent
import scenes.road_actions as ra

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("ambush_cap_705", seed=5, location="greywood")
ws = g.scene
world = ws.world
place = world.places["greywood"]
lo, hi = place.danger
high = next(c for c in world.bestiary.values() if c.levels[0] > hi + 5)
fit = [cid for cid, c in world.bestiary.items() if c.levels[0] <= hi and c.levels[1] >= lo][:3]
st = ws.store.load_place("greywood")
st.roster = [high.id] + fit
ws.store.save_place(st)
levels, kinds = [], set()
for k in range(40):
    hit = encounters.roll(ws.store, world, "greywood", 1.0, random.Random(k))
    if hit:
        kinds.add(hit[0].id)
        levels += [e.level for e in hit[1]]
check("no foe is met above its place's danger", levels and max(levels) <= hi, (max(levels or [0]), hi))
check("...a creature that does not fit the place gives way to one that does", high.id not in kinds and kinds, kinds)
st.roster = [high.id]
ws.store.save_place(st)
alone = [e.level for k in range(20) for hit in [encounters.roll(ws.store, world, "greywood", 1.0, random.Random(k))] if hit for e in hit[1]]
check("...and with none that fits, it is met at the place's top", alone and max(alone) <= hi, (max(alone or [0]), hi))

road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and ra.roads.nearby_wilds(world, r.from_, r.to))
wild = ra.roads.nearby_wilds(world, road.from_, road.to)[0]
big = next(c for c in world.bestiary.values() if c.levels[0] >= 30 and c.temperament != "passive")
real_roll = encounters.roll
from engine import combat
encounters.roll = lambda *a, **k: (big, [combat.fighter_from_creature(big, 32, "normal", "e1", big.name.lower())])
ra.generate = lambda *x, **k: RoadEvent.model_construct(title="An ambush", journey="You walk on.", kind="ambush", scene="Something lunges.", detail="", meets_role="", news="", effects=[])
saved = {k: ra.R[k] for k in ("hostile", "hostile_max")}
ra.R["hostile"], ra.R["hostile_max"] = 100.0, 1.0
ws.player.character.level = 17
ws.temperament = lambda c, high=None: "aggressive"
ws.deterred = lambda c, high=None: False
ws.enter(road.from_)
ws.road_event([road.from_, road.to], road.from_, road.to, 300, 0.5, "We walk on.", [])
foes = [f for f in ws.combat.fight.enemies()] if ws.combat else []
cap = 17 + int(ra.R["ambush_above"])
check("a road ambush's foes are at most ambush_above levels over the party's leader", foes and all(f.level <= cap for f in foes),
      [(f.name, f.level) for f in foes])
ws.combat = None
ws.player.character.level = 3
ws.enter(road.from_)
ws.road_event([road.from_, road.to], road.from_, road.to, 300, 0.5, "We walk on.", [])
foes = [f for f in ws.combat.fight.enemies()] if ws.combat else []
check("...a low-level party too", foes and all(f.level <= 3 + int(ra.R["ambush_above"]) for f in foes), [(f.name, f.level) for f in foes])
ws.combat = None
ws.player.character.level = 17
spawned = combat.fighter_from_creature(big, 32, "boss", "e1", big.name.lower())
spawned.spawn = "ev1"
encounters.roll = lambda *a, **k: (big, [spawned.model_copy(deep=True)])
ws.enter(road.from_)
ws.road_event([road.from_, road.to], road.from_, road.to, 300, 0.5, "We walk on.", [])
foes = [f for f in ws.combat.fight.enemies()] if ws.combat else []
check("a world event's own spawn is met as it is, its tag and kit kept", foes and foes[0].spawn == "ev1" and foes[0].level == 32,
      [(f.name, f.level, f.spawn) for f in foes])
encounters.roll = real_roll
ra.R.update(saved)
g.close()
shutil.rmtree("saves/ambush_cap_705", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

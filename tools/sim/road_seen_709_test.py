"""(f709) A thing kept on a road is found by what was seen there, and a line that goes down that road to it goes to it (found in the
third blind play, 2026-11-16: docs/play/2026-11-16_blind_play_journal.md). On the King's Pass two dazed men under a lean-to muttered
"We dig. At night."; f702 kept the sight as "The Echo of the Greywood". `We go back down the King's Pass to the two dazed men under
the lean-to.` was taken by the way-out reader as leaving by the King's Pass, and became a walk to its far end: the player names what
they saw, never the title the game gave it, and the line named the road too.
Held here: a landmark is named by its title (f702) or by the words of what was seen there, two of them at least, never the words of
its road or of the places the road joins; named by what was seen with its road named too, it is gone to; without the road, it is
asked first (f428). A line the way-out reader would take as leaving by a road goes to a landmark it names instead; one that names
only the road leaves by it as before.
Run: python tools/sim/road_seen_709_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import ActionIntent as A, RoadEvent
from engine import exits
import scenes.road_actions as ra

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("road_seen_709", seed=5, location="parth")
ws = g.scene
world = ws.world
SETTLE = ("town", "city", "village")
road = next(r for r in world.roads.values() if r.name and r.from_ in world.places and r.to in world.places
            and world.places[r.from_].type in SETTLE and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 240
            and any(gp for gp in exits.groups(world, r.from_) if exits.match(world, r.from_, f"I take {r.name}.")[0]))
a, b = road.from_, road.to
ws.enter(a)
ev = RoadEvent(title="The Echo of the Greywood", journey="You walk on.", kind="sight",
               scene=f"On {road.name}, two dazed men sit huddled beneath a lean-to of sodden canvas, muttering of digging at night.")
real_gen = ra.generate
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
saved = {k: ra.R[k] for k in ("hostile", "kinds")}
ra.R["hostile"], ra.R["kinds"] = 0.0, {"sight": 1}
ws.road_event([a, b], a, b, 300, 0.4, "We walk on.", [])
ws.enter(a)
mark = (ws.store.load_world_state() or {})["landmarks"][-1]

hit = ws.landmark_named(f"We go back down {road.name} to the two dazed men under the lean-to.")
check("named by what was seen there with its road named, it is the landmark, wholly", hit is not None and hit[0]["id"] == mark["id"] and hit[1], hit)
hit = ws.landmark_named("We go back to the two dazed men under the lean-to.")
check("...by what was seen alone, it is the landmark, but only half (asked first)", hit is not None and hit[0]["id"] == mark["id"] and not hit[1], hit)
check("one word of what was seen names nothing", ws.landmark_named("We go back to the canvas.") is None)
check("...nor do its road's own words, which the scene shares", ws.landmark_named(f"I take {road.name}.") is None)
check(f"...nor the places the road joins ({world.places[b].name})", ws.landmark_named(f"We go on to {world.places[b].name}.") is None)

start, m0 = ws.player.location, ws.minutes
took = ws.exit_request(f"We go back down {road.name} to the two dazed men under the lean-to.")
here = world.places.get(ws.player.location)
check("a way out down that road to a thing kept on it goes to it: the player stands at a stop with it in view",
      took and here is not None and here.type == "road" and any("echo of the greywood" in v.lower() for v in here.visible) and ws.minutes > m0,
      (took, ws.player.location, here and here.visible))
ws.enter(start)
went = []
real_go = ws.go_landmark
ws.go_landmark = lambda m, t: went.append(m["id"])
left = []
real_leave = ws.leave_by
ws.leave_by = lambda gp, t: left.append(gp["dir"])
ws.exit_request(f"I take {road.name}.")
check("a line that names only the road leaves by it, as before", left and not went, (left, went))
left.clear()
ws.exit_request(f"We head out along {road.name} toward the dazed men by the lean-to.")
check("...one that names what was seen on it without saying 'back' goes there too", went == [mark["id"]] and not left, (went, left))
ws.go_landmark, ws.leave_by = real_go, real_leave

said = []
real_refuse = ws.refuse
ws.refuse = lambda s, *x, **k: said.append(s)
ws.on_move(A(kind="move", destination="the dazed men"), "We go back to the two dazed men under the lean-to.")
check("named by what was seen alone, a move asks first, by the landmark's name, and walks nowhere",
      ws.player.location == start and said and "echo of the greywood" in said[-1].lower(), (said, ws.player.location))

far_name = world.places[b].name
ev = RoadEvent(title=f"The Road to {far_name}", journey="You walk on.", kind="sight",
               scene=("Down by the river an overturned cart lies with one wheel still turning, and there are boot prints leading away "
                      "from it into the trees toward where the rain is coming from, with nothing else there to see."))
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
ws.road_event([a, b], a, b, 300, 0.6, "We walk on.", [])
ws.enter(start)
cart = (ws.store.load_world_state() or {})["landmarks"][-1]
check("a second sight, its own words: 'the overturned cart by the river' names it (half, asked first)",
      (ws.landmark_named("We go back to the overturned cart by the river.") or ({}, None))[0].get("id") == cart["id"])
for line in (f"I take {road.name} down to the river with Hollis.", f"We take {road.name} toward {far_name}.",
             f"I take {road.name} to {far_name}, there is rain coming.", f"I take {road.name} through the trees to the river.",
             f"We take {road.name} and camp by the river when the rain starts, the long way, keeping to the left side."):
    went.clear(); left.clear()
    ws.go_landmark, ws.leave_by = (lambda m, t: went.append(m["id"])), (lambda gp, t: left.append(gp["dir"]))
    ws.exit_request(line)
    ws.go_landmark, ws.leave_by = real_go, real_leave
    check(f"small words, a scene's words in how the walk goes, or a title that is only the far end's name leave by the road: {line!r}",
          left and not went, (left, went))
said.clear()
ws.on_move(A(kind="move", destination="the old mill"), "I walk down to the old mill by the river with the others.")
check("a move in town that shares one ordinary word with a scene is never asked about a far sight",
      not any("pick it under places" in s.lower() for s in said), said)
ws.refuse = real_refuse
ra.generate = real_gen
ra.R.update(saved)
g.close()
shutil.rmtree("saves/road_seen_709", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

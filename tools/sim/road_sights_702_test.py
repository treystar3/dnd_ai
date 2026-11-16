"""(f702) A sight on the road stays where it was seen, and the player can go back to it (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). On the Old Quarry Road a fissure in the hillside bled violet light; the walk went on past
it (a sight does not stop the walk, f427, kept), and `We go back down the Old Quarry Road to the glowing fissure we passed.` became a
ten-hour walk toward Parth: nothing of the sight was kept.
Held here: a sight met on the road is kept as a landmark of that road (its title, what was seen, how far along it lies), the most kept
capped in road.yaml; the Places pane lists it with how far it is; going to it, by the pane or by a line that names it, walks to the
road's nearer end and on along the road to it, and the player stands at a stop there with the sight in view; a happening that is no
sight leaves no landmark.
Run: python tools/sim/road_sights_702_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import ActionIntent as A, RoadEvent
import scenes.road_actions as ra

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("road_sights_702", seed=5, location="parth")
ws = g.scene
ws.enter("parth")
world = ws.world
road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and ra.roads.nearby_wilds(world, r.from_, r.to)
            and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 240)
a, b = road.from_, road.to
ev = RoadEvent(title="A glowing fissure", journey="You walk on.", kind="sight",
               scene="A jagged fissure in the hillside bleeds a pale violet light.")
real_gen = ra.generate
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
saved = {k: ra.R[k] for k in ("hostile", "kinds")}
ra.R["hostile"], ra.R["kinds"] = 0.0, {"sight": 1}
out = ws.road_event([a, b], a, b, 300, 0.4, "We walk on.", [])
marks = (ws.store.load_world_state() or {}).get("landmarks", [])
check("a sight on the road does not stop the walk", out == "go", out)
check("...and is kept as a landmark of that road, with what was seen and how far along", len(marks) == 1 and marks[0]["title"] == "A glowing fissure"
      and "violet" in marks[0]["scene"] and 0 < marks[0]["frac"] < 1, marks)
ws.enter(b if b != "parth" else a)
start = ws.player.location
rows = ws.places_data().get("sights", [])
check("the Places pane lists it, with how far it is", rows and rows[0]["name"].startswith("A glowing fissure") and rows[0]["away"], rows)
m0 = ws.minutes
ws.on_move(A(kind="move", destination="the glowing fissure"), "We go back to the glowing fissure.")
here = ws.world.places.get(ws.player.location)
check("a line that names it walks back to it: the player stands on that road, at a stop with the sight in view",
      here is not None and here.type == "road" and any("fissure" in v.lower() for v in here.visible) and ws.minutes > m0,
      (ws.player.location, here and here.visible, ws.minutes - m0))
check("...told as it is now, by what it is, never the old hour's words", not any("pale violet" in v for v in here.visible)
      and any("glowing fissure" in v.lower() for v in here.visible), here and here.visible)
stood_at = ws.player.location
ws.enter(start)
check("walking on, the stop is tidied as any stop is", stood_at not in ws.world.places, stood_at)
ws.places_click(f"#goto {rows[0]['id']}")
here = ws.world.places.get(ws.player.location)
check("...and so does the pane's Go", here is not None and here.type == "road" and any("fissure" in v.lower() for v in here.visible), ws.player.location)
ws.enter(start)
said = []
real_refuse = ws.refuse
ws.refuse = lambda s, *x, **k: said.append(s)
ws.on_move(A(kind="move", destination="the glowing bridge"), "We go to the glowing bridge.")
check("a name that only half fits asks before a long walk, and walks nowhere", ws.player.location == start and said and "fissure" in said[-1], (said, ws.player.location))
ws.refuse = real_refuse
mid = ra.roads.make_stop(world, a, b, 0.7, world.path(a, b)[1], "a bend", "", "A bend")
world.add_place(ra.Place(**mid["place"]))
ws.player.road = mid
ws.enter(mid["id"])
joins, walk = ws.landmark_way((ws.store.load_world_state() or {})["landmarks"][0])
check("from a stop on the same road it is walked along the road, never round by a town",
      walk == round(world.path(a, b)[1] * abs(0.7 - (ws.store.load_world_state() or {})["landmarks"][0]["frac"])) or walk <= 2 + round(world.path(a, b)[1] * 0.3),
      (walk, world.path(a, b)[1]))
ra.R["kinds"] = {"sight": 1}
ev = RoadEvent(title="A ruined cairn", journey="You walk on.", kind="sight", scene="A cairn of grey stones, half fallen.")
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
ws.road_event([mid["id"], b], mid["id"], b, 100, 0.5, "We walk on.", [])
kept = (ws.store.load_world_state() or {})["landmarks"][-1]
ra_, rb_ = sorted([a, b])
want = 0.85 if ra_ == a else 0.15                                          # half way on from a stop at 0.7 of the road, along the real road
check("a journey walked on from a stop keeps the sight where it is on the real road", kept["title"] == "A ruined cairn"
      and {kept["a"], kept["b"]} == {a, b} and abs(kept["frac"] - want) < 0.02, (kept, want))
ra.R["kinds"] = {"sight": 1}
ws.enter(start)
ra.R["kinds"] = {"find": 1}
ev = RoadEvent(title="A lost purse", journey="You walk on.", kind="find", scene="A purse lies in the ditch.", detail="a purse")
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
ws.enter(start)
n0 = len((ws.store.load_world_state() or {}).get("landmarks", []))
ws.road_event([a, b], a, b, 300, 0.6, "We walk on.", [])
check("a happening that is no sight leaves no landmark", len((ws.store.load_world_state() or {}).get("landmarks", [])) == n0)
ra.R["kinds"] = {"sight": 1}
ev = RoadEvent(title="A tall stone", journey="You walk on.", kind="sight", scene="A tall stone stands alone.")
ra.generate = lambda *x, **k: ev.model_copy(deep=True)
for _ in range(int(ra.R["landmarks_kept"]) + 2):
    ws.enter(start)
    ws.road_event([a, b], a, b, 300, 0.3, "We walk on.", [])
check("the landmarks kept are capped (road.yaml landmarks_kept)", len((ws.store.load_world_state() or {}).get("landmarks", [])) == ra.R["landmarks_kept"])
ra.generate = real_gen
ra.R.update(saved)
g.close()
shutil.rmtree("saves/road_sights_702", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

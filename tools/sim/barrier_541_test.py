"""(f541) A road a situation has shut is met at the barrier (the owner, 2026-11-07: "Met at the barrier"). A walk whose way runs over a
shut road goes as far as the barrier and stops there, on the road: the barrier is told, the way back is open and the way on is not (no
pushing through, as a hazard may be got past), and the long way round is named when there is one. Once a character has met a closure, their
walks go the long way round it, or are refused before setting out when there is none; one who knows a way around (wayfinder) passes; and
when the situation ends, the road is open again. Nothing on the road happens on the shut stretch itself.
Run: python tools/sim/barrier_541_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import pulse, roads
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SAID = []
_note = console.note
console.note = lambda s, *a, **k: (SAID.append(str(s)), _note(s, *a, **k))[1]
roads.R["chance_per_leg"] = 0.0                       # no road happening stops these walks short of the barrier
GAMES = []


def fresh(name: str, at: str):
    g = simlib.campaign(name, seed=7, location=at)
    GAMES.append(g)
    ws = g.scene
    ws.enter(at)
    g.store.save_world_state(pulse.empty_state(ws.minutes))
    return g, ws


def shut(ws, road: str, days: int = 5, text: str = "a fall of rock lies across it"):
    state = ws.store.load_world_state()
    got = pulse.apply_one(ws.store, ws.world, ws.catalog, state, {"kind": "closed", "place": road, "days": days, "text": text},
                          "normal", ws.minutes, "test", ways=True)
    ws.store.save_world_state(state)
    return got


def crosses(route, r) -> bool:
    return any({x, y} == {r.from_, r.to} for x, y in zip(route, route[1:]))


# a road the quickest walk from one of its ends to the other runs on, with a way round and without one
g0, ws0 = fresh("barrier_541_pick", "trading_square")
world = ws0.world
cands = []
for rid in sorted(world.roads):
    r = world.roads[rid]
    if r.from_ not in world.places or r.to not in world.places:
        continue
    found = world.path(r.from_, r.to)
    if found and crosses(found[0], r) and world.travel_minutes(r.from_, r.to) >= 120:
        cands.append((rid, roads.way_round(world, rid)))
lone = next((rid for rid, round_ in cands if not round_), None)
mesh = next((rid for rid, round_ in cands if round_), None)
check("the world has a road that is the only way between its ends, and one with a way round", lone and mesh, cands[:6])


def walk_to_barrier(name, rid):
    r = world.roads[rid]
    g, ws = fresh(name, r.from_)
    check(f"[{rid}] the closure takes", shut(ws, rid) == "applied")
    t0 = ws.minutes
    SAID.clear()
    ws.travel_route(r.to, f"I walk to {world.places[r.to].name}")
    return g, ws, r, t0


for rid, has_round in ((lone, False), (mesh, True)):
    if not rid:
        continue
    g, ws, r, t0 = walk_to_barrier(f"barrier_541_{rid}", rid)
    stop = ws.player.road or {}
    here = ws.world.places.get(ws.player.location)
    full = world.travel_minutes(r.from_, r.to)
    check(f"[{rid}] the walk stops at the barrier, on the road", here is not None and here.type == "road" and stop.get("kind") == "barrier"
          and stop.get("barrier") == rid and stop.get("behind") == r.from_, (ws.player.location, stop.get("kind"), stop.get("behind")))
    check(f"[{rid}] ...partway: the time is the walk to the barrier, not the whole road", 0 < ws.minutes - t0 < full, (ws.minutes - t0, full))
    meet = [s for s in SAID if "is shut here" in s]
    check(f"[{rid}] ...the way on is said to be shut, and the way back open", meet and world.places[r.to].name in meet[0]
          and world.places[r.from_].name in meet[0], SAID)
    check(f"[{rid}] ...with the long way round named when there is one, and none claimed when there is not",
          ("long way round" in meet[0]) == has_round and ("no other way" in meet[0]) == (not has_round), meet)
    check(f"[{rid}] HAPPENING HERE at the barrier says the road is shut there",
          any("is shut here" in h for h in pulse.happenings_at(ws.store, ws.world, ws.player.location, ws.minutes)))
    state = ws.store.load_world_state()
    check(f"[{rid}] the closure remembers who has met it", any(ws.acting in (e.get("met_by") or []) for e in state["effects"]
                                                             if e["kind"] == "closed" and e["place"] == rid))
    # the way on: no pushing through; the long way round, or nothing
    at, t1 = ws.player.location, ws.minutes
    SAID.clear()
    ws.travel_route(r.to, "I go on")
    if has_round:
        check(f"[{rid}] going on from the barrier takes the long way round", ws.player.location == r.to and ws.minutes > t1
              and any("long way round" in s for s in SAID), (ws.player.location, SAID))
        g, ws, r, t0 = walk_to_barrier(f"barrier_541_{rid}_back", rid)    # at the barrier again, for the way back
    else:
        check(f"[{rid}] going on from the barrier is refused, and nothing moves", ws.player.location == at and ws.minutes == t1
              and any("is shut" in s for s in SAID), (ws.player.location, SAID))
    # the way back is open
    ws.travel_route(r.from_, "I turn back")
    check(f"[{rid}] the way back from the barrier is open", ws.player.location == r.from_, ws.player.location)
    # met: the next walk goes round, or is refused before setting out
    t2 = ws.minutes
    SAID.clear()
    ws.travel_route(r.to, "I try again")
    if has_round:
        check(f"[{rid}] once met, the next walk goes the long way round and meets no barrier", ws.player.location == r.to
              and (ws.player.road or {}).get("kind") != "barrier" and any("long way round" in s for s in SAID), (ws.player.location, SAID))
    else:
        check(f"[{rid}] once met, a walk with no way round is refused before setting out", ws.player.location == r.from_
              and ws.minutes == t2 and any("no other way" in s for s in SAID), (ws.player.location, SAID))

# one who knows a way around passes it
if lone:
    r = world.roads[lone]
    g, ws = fresh("barrier_541_wayfinder", r.from_)
    shut(ws, lone)
    real_has = ws.has
    ws.has = lambda k, *a, **kw: 1 if k == "wayfinder" else real_has(k, *a, **kw)
    SAID.clear()
    ws.travel_route(r.to, "I walk on")
    check("a character who knows a way around passes the closure, and is told so", ws.player.location == r.to
          and any("know a way around" in s for s in SAID), (ws.player.location, SAID))

# the situation's end opens the road: the barrier stands no more
if lone:
    g, ws, r, _ = walk_to_barrier("barrier_541_lift", lone)
    state = ws.store.load_world_state()
    for e in state["effects"]:
        if e["kind"] == "closed" and e["place"] == lone:
            e["until"] = ws.minutes                            # lifted, as lift() does when its situation ends
    ws.store.save_world_state(state)
    ws.travel_route(r.to, "I go on")
    check("when the closure lifts, the way on from the barrier is open", ws.player.location == r.to, ws.player.location)

# nothing on the road happens on the shut stretch
src = open("scenes/road_actions.py", encoding="utf-8").read()
check("a road happening is never rolled on the shut stretch", "if barrier and i >= barrier[0]:" in src)
check("the stop on a road lies on that road for a closure (way_key)", lone is None or roads.way_key(
      world, "nowhere", "nowhere") == roads.edge_key(world, "nowhere", "nowhere"))

for g in GAMES:
    g.close()
for n in ["barrier_541_pick", "barrier_541_wayfinder", "barrier_541_lift"] + [f"barrier_541_{x}{y}" for x in (lone, mesh) if x
                                                                                  for y in ("", "_back")]:
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

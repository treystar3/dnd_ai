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


ROUTES, TIRED = [], []
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
    check(f"[{rid}] ...at the road's one barrier, wherever the walk came from", abs(here.connects[r.from_] - roads.R["barrier"]["at"]
          * sum(here.connects.values())) <= max(1, 0.02 * sum(here.connects.values())), here.connects)
    check(f"[{rid}] a stop on the road lies on that road for its closure", roads.way_key(ws.world, ws.player.location, r.to) == rid)
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
    # the way on: no pushing through; the long way round asked for and taken, or nothing
    at, t1 = ws.player.location, ws.minutes
    SAID.clear()
    ws.travel_route(r.to, "I go on")
    check(f"[{rid}] going on from the barrier is refused (or the long way round, many times the length, is asked for first)",
          ws.player.location == at and ws.minutes == t1 and any(("say so" in s) if has_round else ("is shut" in s) for s in SAID), SAID)
    for e in state["effects"]:                                  # met again where it stands, by one who had not: no barrier further on
        e.pop("met_by", None)
    ws.store.save_world_state(state)
    ws.travel_route(r.to, "I go on")
    check(f"[{rid}] one who meets it again where they stand stays at the barrier: it never moves on", ws.player.location == at, ws.player.location)
    if has_round:
        SAID.clear()
        real_run = ws.run_journey
        ws.run_journey = lambda route, *a, **k: (ROUTES.append(list(route)), real_run(route, *a, **k))[1]
        ws.travel_route(r.to, "I take the long way round")
        ws.run_journey = real_run
        check(f"[{rid}] the long way round, asked for, is taken", ws.player.location == r.to and ws.minutes > t1
              and any("long way round" in s for s in SAID), (ws.player.location, SAID))
        check(f"[{rid}] ...and never sets foot on the shut road: back the way it came, then round", ROUTES and not crosses(ROUTES[-1], r)
              and ROUTES[-1][1] == r.from_ and not any(ws.world.places.get(x) is not None and ws.world.places[x].type == "road"
                                                       for x in ROUTES[-1][1:]), ROUTES[-1:])
        g, ws, r, t0 = walk_to_barrier(f"barrier_541_{rid}_back", rid)    # at the barrier again, for the way back
    # the way back is open, even into a place since shut to anyone going in
    behind_top = pulse.town_of(ws.world, r.from_)
    state = ws.store.load_world_state()
    state["effects"].append({"kind": "closed", "place": r.from_, "value": 0, "until": ws.minutes + 3 * 1440, "text": "a plague",
                             "cause": "test", "thread": ""})
    ws.store.save_world_state(state)
    ws.travel_route(r.from_, "I turn back")
    check(f"[{rid}] the way back from the barrier is open, though the place behind has shut since", ws.player.location == r.from_,
          ws.player.location)
    state = ws.store.load_world_state()
    state["effects"] = [e for e in state["effects"] if not (e["kind"] == "closed" and e["place"] == r.from_)]
    ws.store.save_world_state(state)
    # met: the next walk goes round (asked for), or is refused before setting out
    t2 = ws.minutes
    SAID.clear()
    real_run = ws.run_journey
    ws.run_journey = lambda route, *a, **k: (ROUTES.append(list(route)), real_run(route, *a, **k))[1]
    ws.travel_route(r.to, "I go the long way round" if has_round else "I try again")
    ws.run_journey = real_run
    if has_round:
        check(f"[{rid}] once met, the next walk goes the long way round and meets no barrier", ws.player.location == r.to
              and (ws.player.road or {}).get("kind") != "barrier" and any("long way round" in s for s in SAID) and ROUTES
              and not crosses(ROUTES[-1], r), (ws.player.location, SAID, ROUTES[-1:]))
    else:
        check(f"[{rid}] once met, a walk with no way round is refused before setting out", ws.player.location == r.from_
              and ws.minutes == t2 and any("no other way" in s for s in SAID), (ws.player.location, SAID))

# (f541's review) what happens on the road never lets a walk past the barrier
trip_was, kinds_were = roads.R["min_trip_hours"], dict(roads.R.get("kinds") or {})
roads.R["chance_per_leg"], roads.R["min_trip_hours"] = 1.0, 0
roads.R["kinds"] = {"meeting": 1}
for rid in (x for x in (lone, mesh) if x):
    r = world.roads[rid]
    g, ws = fresh(f"barrier_541_ev_{rid}", r.from_)
    shut(ws, rid)
    real_tired = ws.travel_fatigue
    ws.travel_fatigue = lambda walk, *a, **k: (TIRED.append(walk), real_tired(walk, *a, **k))[1]
    ws.travel_route(r.to, "I walk on")
    ws.travel_fatigue = real_tired
    at_barrier = (ws.player.road or {}).get("kind") == "barrier"
    check(f"[{rid}] with a happening on every leg, none falls on the shut stretch: the walk still reaches the barrier", at_barrier,
          (ws.player.location, (ws.player.road or {}).get("kind")))
    check(f"[{rid}] ...and the walk is as tiring as the walk to the barrier, not the whole road", TIRED and TIRED[-1] < world.travel_minutes(r.from_, r.to),
          TIRED[-1:])
    if not at_barrier:
        continue
    ws.travel_route(r.from_, "I turn back")                     # a happening on the walk back leaves a stop on the shut road
    met_on_road = ws.world.places.get(ws.player.location) is not None and ws.world.places[ws.player.location].type == "road"
    if met_on_road:
        check(f"[{rid}] a stop made on the shut road by a happening on the walk back knows its side of the barrier",
              ws.near_end(ws.player.road) == r.from_, ws.player.road)
        roads.R["chance_per_leg"] = 0.0                       # nothing else on the road now: only the barrier can stop the walk
        on_stop, t_ = ws.player.location, ws.minutes
        ws.travel_route(r.to, "I go on")
        check(f"[{rid}] ...so the way on from it is still shut: no walking through", ws.player.location == on_stop and ws.minutes == t_,
              (ws.player.location, ws.minutes - t_))
        ws.travel_route(r.from_, "I go back")
        roads.R["chance_per_leg"] = 1.0
        check(f"[{rid}] ...and the way back from it is open", ws.player.location == r.from_, ws.player.location)
    else:
        print(f"ok   (no happening stopped the walk back on {rid}: the stop's side is proved on another)")
    # the fork's shared stretch rolls nothing on a shut road
    g2, ws2 = fresh(f"barrier_541_fork_{rid}", r.from_)
    shut(ws2, rid)
    got = ws2.fork_walk({"members": [{"to": r.to}]}, r.from_, 360, "I head out")
    check(f"[{rid}] the walk out to a fork rolls nothing on a shut road", got is not None and not ws2.player.road, (got, ws2.player.road))
roads.R["chance_per_leg"], roads.R["min_trip_hours"], roads.R["kinds"] = 0.0, trip_was, kinds_were

# (f541's review) the places pane shows the walk that can be made
if mesh:
    r = world.roads[mesh]
    g, ws, r, _ = walk_to_barrier("barrier_541_pane", mesh)
    if r.to not in ws.player.heard:
        ws.player.heard.append(r.to)
    rows = ws.places_data()
    row = next((x for x in rows.get("far", []) + rows.get("local", []) if x["id"] == r.to), None)
    check("the places pane gives the long way round, not the walk through the barrier", row is not None and "long way round" in row["away"]
          and row["minutes"] > world.travel_minutes(r.from_, r.to), row)

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

for g in GAMES:
    g.close()
for n in ["barrier_541_pick", "barrier_541_wayfinder", "barrier_541_lift", "barrier_541_pane"] + [
        f"barrier_541_{p_}{x}{y}" for x in (lone, mesh) if x for p_ in ("", "ev_", "fork_") for y in ("", "_back")]:
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

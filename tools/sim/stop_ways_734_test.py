"""(f734) A road stop's ways and its record name only places on the map, so every walk from a stop goes on (the audit's
stale-copies-5 and scenes3-7). A stop is tidied off the map as soon as the walk goes on from it, and three things kept naming it
after it was gone: the record of the next stop on the same journey (its `from`), so help given at a second stop raised KeyError
every time and the aid could never be had there; the stop made where a kept sight lies, when walked to from a stop on its road (its
own ways), so the player stood where no route out could be found, before and after a reload; and the walk to a sight when an ambush
stopped it (its resume and bound named the sight's stop, taken away when the walk was stopped), so after the fight was won the
pane's Go and "Let's go back there." were answered with a refusal naming a raw id and the walk did not go on.
Now a stop is joined to its road's two real ends by where it stands on the road, its record names those ends, the sight's stop is
joined to the stop stood at by the map's own link (which goes with either end), the walk to a sight carries the sight as its goal,
a stop put back from a save keeps only its ways that are on the map, a place taken off the map takes its id out of the other
places' ways, and the campaign's check names a way or a record that leads off the map.
The cases that found it: help at a second stop; a sight walked to from a stop on its road; a sight's walk stopped by a won ambush,
by the pane and by a typed line. Second cases of the kind: a hazard's way back and a shut road's near end at a second stop; three
stops in a row on one road and one walked back; a barrier met on the walk to a sight; a save opened standing at each; a hand-made
save whose stop holds a way off the map; and the campaign's check after every input of a stub bot session.
Run: python tools/sim/stop_ways_734_test.py"""
import os
import random
import re
import shutil
import sys
import traceback
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import config
import ui.console as uc

NAME, LOGS = "stop_ways", "saves/stop_ways_logs"
os.makedirs(LOGS, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
from engine import pulse, roads
from llm.contracts import ActionIntent as A, RoadEvent
import scenes.road_actions as ra
from storage import invariants
from world.loader import Place

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


R = roads.R
KEEP = {k: R[k] for k in ("chance_per_leg", "hostile", "hostile_max", "kinds", "max_per_trip")}
REAL_GEN = ra.generate
RAW_ID = re.compile(r"\b(?:road|sight)[ _][0-9a-f]{6,8}\b")


def fresh(at: str = "parth", seed: int = 7):
    g = simlib.campaign(NAME, seed=seed, location=at, minutes=420)
    ws = g.scene
    ws.enter(at)
    g.store.save_player(ws.player)
    return g, ws


def reopen(g):
    """The save closed and opened again, as the game opens it: a new session and a scene over the save."""
    g.close()
    g = simlib.campaign(NAME, fresh=False)
    return g, g.scene


def play(ws, text, plan) -> list:
    """One typed line through the game's one input path: the operations of it that failed."""
    stub.plan = [dict(p) for p in plan]
    ws.play(text)
    return [f"{o.kind}: {o.failure}" for o in ws.line_failed]


def new_rules(store, world) -> list:
    """What the campaign's check says of ways and stop records that lead off the map (the two rules this feature adds)."""
    return [str(p) for p in invariants.validate_campaign(store, world) if "not on the map" in p.what]


def walks_on(ws) -> tuple:
    """Where the player stands: (on the map, every way of it on the map, a route found from it to each place it is joined to)."""
    world, here = ws.world, ws.player.location
    p = world.places.get(here)
    if p is None:
        return False, False, False
    ways = all(k in world.places for k in p.connects)
    try:
        routes = all(world.path(here, k) for k in p.connects if k in world.places) and bool(p.connects)
    except KeyError as e:
        routes = f"KeyError {e}"
    return True, ways, routes


def is_stop(world, pid) -> bool:
    p = world.places.get(pid)
    return p is not None and p.type == "road" and not p.parent


def farthest(world, start: str = "parth") -> str:
    towns = [p.id for p in world.places.values() if not p.parent and not p.danger and p.type in ("town", "city", "village") and p.id != start]
    return max(((world.path(start, t) or ([], 0))[1], t) for t in towns)[1]


g = None
try:
    # ---- the case that found it (stale-copies-5): help given at a second stop on one journey
    R.update(chance_per_leg=1.0, hostile=0.0, kinds={"aid": 1}, max_per_trip=9)
    g, ws = fresh()
    world = ws.world
    dest = farthest(world)
    there = world.places[dest].name
    play(ws, f"I set out for {there}.", [{"kind": "move", "destination": dest}])
    first = dict(ws.player.road or {})
    play(ws, f"I walk on toward {there}.", [{"kind": "move", "destination": dest}])
    second = dict(ws.player.road or {})
    check("(walked on from a first stop, the walk is stopped again at a second, someone in need there)",
          first and second and second["id"] != first["id"] and ws.player.location == second["id"] and second.get("aid"), (first.get("id"), second.get("id")))
    check("the second stop's record names only places on the map: the road's two real ends", all(second.get(k) in world.places and not is_stop(world, second[k])
                                                                                                  for k in ("from", "to")), (second.get("from"), second.get("to")))
    aid = second.get("aid") or {}
    coins0 = ws.player.character.coins
    failed = play(ws, f"I go to {aid.get('name', 'them')} and help with what they need.",
                  [{"kind": "other", "target": aid.get("who", ""), "summary": "helps them with what they need"}])
    saved = g.store.load_player()
    check("help given at a second stop on one journey stands: the help is kept and paid, and nothing fails",
          not failed and ((saved.road or {}).get("aid") or {}).get("helped") and saved.character.coins > coins0, (failed, saved.character.coins - coins0))
    check("...and the campaign's check finds no way and no record that leads off the map", not new_rules(g.store, world), new_rules(g.store, world))
    here = ws.player.location
    g, ws = reopen(g)
    check("a save opened standing at a second stop: the stop is on the map, its ways too, and a route leads from it to each",
          ws.player.location == here and walks_on(ws) == (True, True, True), walks_on(ws))

    # ---- a hazard's way back, and a shut road's near end, at a second stop
    R["kinds"] = {"hazard": 1}
    g.close()
    g, ws = fresh()
    world = ws.world
    route = world.path("parth", dest)[0]
    play(ws, f"I set out for {there}.", [{"kind": "move", "destination": dest}])
    play(ws, f"I walk on toward {there}.", [{"kind": "move", "destination": dest}])
    stop = ws.player.road or {}
    behind = (stop.get("hazard") or {}).get("behind", "")
    ends = list(world.places[stop["id"]].connects) if stop.get("id") in world.places else []
    check("a hazard at a second stop: the way back is the real end the walk came from, on the map",
          behind in world.places and behind in ends and len(ends) == 2 and behind in route
          and route.index(behind) < route.index(next(e for e in ends if e != behind)), (behind, ends, stop.get("from")))
    key = next((k for k in (roads.way_key(world, stop["id"], e) for e in ends) if k in world.roads), "")
    if key:
        state = ws.store.load_world_state()
        pulse.apply_one(ws.store, world, ws.catalog, state, {"kind": "closed", "place": key, "days": 5, "text": "a fall of rock lies across it"},
                        "normal", ws.minutes, "test", ways=True)
        ws.store.save_world_state(state)
    near = ws.near_end(ws.player.road) if key else ""
    check("...and with its road shut, the near end of the barrier is a real end of the stop, on the map", key and near in ends, (key, near, ends))

    # ---- three stops in a row on one road, and one walked back toward the start
    R["kinds"] = {"meeting": 1}
    g.close()
    g, ws = fresh()
    world = ws.world
    road = next(r for r in sorted(world.roads.values(), key=lambda r: r.id) if r.from_ in world.places and r.to in world.places
                and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 360)
    a, b = road.from_, road.to
    ev = RoadEvent(title="A woman at a milestone", journey="You walk on.", kind="meeting", scene="A woman sits on a milestone.", meets_role="wanderer")
    ra.generate = lambda *x, **k: ev.model_copy(deep=True)
    ws.enter(a)
    made, at = [], a
    for frac, toward in ((0.3, b), (0.4, b), (0.5, b), (0.5, a)):
        total = world.path(at, toward)[1]
        ws.road_event([at, toward], at, toward, total, frac, "We walk on.", [])
        at = ws.player.location
        made.append(dict(ws.player.road or {}))
    named = [(s.get("from"), s.get("to")) for s in made]
    check("three stops in a row on one road, and a fourth walked back: each is joined to the road's two real ends only",
          all(set(world.places[s["id"]].connects) == {a, b} for s in made[-1:]) and all(set(s["place"]["connects"]) == {a, b} for s in made),
          [s["place"]["connects"] for s in made])
    check("...each record names those ends, the way it came first", all({f, t} == {a, b} for f, t in named)
          and [f for f, _ in named] == [a, a, a, b], named)
    pos = [s["place"]["connects"][a] / sum(s["place"]["connects"].values()) for s in made]
    check("...each stands where the walk had come to on the road, further on each time and back the last", pos[0] < pos[1] < pos[2] and pos[3] < pos[2], pos)
    check("...only the last is on the map, and a route leads from it to each end", [s["id"] in world.places for s in made] == [False, False, False, True]
          and walks_on(ws) == (True, True, True), ([s["id"] in world.places for s in made], walks_on(ws)))
    check("...and the campaign's check finds nothing off the map", not new_rules(ws.store, world), new_rules(ws.store, world))
    ra.generate = REAL_GEN
    g.close()

    # ---- the plan's check: a sight walked to from a stop on its road
    g, ws = fresh(seed=5)
    world = ws.world
    road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places
                and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 480)
    a, b = road.from_, road.to
    total = world.path(a, b)[1]
    sight = RoadEvent(title="An overturned cart", journey="You walk on.", kind="sight", scene="An overturned cart lies by the river, its wheel still turning.")
    ra.generate = lambda *x, **k: sight.model_copy(deep=True)
    R.update(hostile=0.0, kinds={"sight": 1})
    ws.enter(a)
    ws.road_event([a, b], a, b, total, 0.8, "We walk on.", [])
    mark = ws.landmarks()[-1]
    stop = roads.make_stop(world, a, b, 0.3, total, "A quiet bend in the road.", "", "A bend")
    stop.update(log=[], text="", resume="", bound=b, kind="meeting", tier="normal")
    ws.player.road = stop
    ws.ensure_road_place()
    ws.enter(stop["id"])
    R["chance_per_leg"] = 0.0
    try:
        ws.go_landmark(mark, "")
        err = ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    here = world.places.get(ws.player.location)
    check("a sight walked to from a stop on its road is reached, the stop left behind tidied away",
          not err and here is not None and any("cart" in v.lower() for v in here.visible) and stop["id"] not in world.places, (err, ws.player.location))
    check("...where the player stands, every way leads to a place on the map and a route leads from it to both ends of the road",
          walks_on(ws) == (True, True, True) and world.path(ws.player.location, a) and world.path(ws.player.location, b), walks_on(ws))
    check("...and the stop's record names only places on the map", not new_rules(ws.store, world), new_rules(ws.store, world))
    here_id = ws.player.location
    ws.store.save_player(ws.player)
    g, ws = reopen(g)
    world = ws.world
    check("a save opened standing at that sight: on the map, its ways too, and a route leads from it to each", ws.player.location == here_id
          and walks_on(ws) == (True, True, True), walks_on(ws))
    try:
        ws.on_move(A(kind="move", destination=b), "I walk on.")
        err = ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    check("...and the walk on to the road's far end goes", not err and ws.player.location == b, (err, ws.player.location))
    g.close()

    # ---- the case that found it (scenes3-7): the walk to a sight stopped by an ambush that is won, by the pane and by a typed line
    for mode in ("click", "typed"):
        R.update(KEEP)
        g, ws = fresh(seed=5)
        world = ws.world
        road, start = None, None
        for r in [r for r in world.roads.values() if r.from_ in world.places and r.to in world.places
                  and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 480]:
            for end, other in ((r.from_, r.to), (r.to, r.from_)):
                if any(world.places[n].danger and world.places[n].type != "dungeon" for n in world.neighbors(end)):
                    road, start = r, end
                    break
            if road:
                break
        a, b = road.from_, road.to
        ra.generate = lambda *x, **k: sight.model_copy(deep=True)
        R.update(hostile=0.0, kinds={"sight": 1})
        ws.road_event([a, b], a, b, world.path(a, b)[1], 0.9 if start == a else 0.1, "We walk on.", [])
        mark = ws.landmarks()[-1]
        ws.enter(start)
        ambush = RoadEvent.model_validate({"title": "Wolves on the road", "journey": "You walk on.", "kind": "ambush",
                                           "scene": "Shapes come out of the brush."}, context={"hostile": True})
        ra.generate = lambda *x, **k: ambush.model_copy(deep=True)
        R.update(hostile=1000.0, hostile_max=1.0, chance_per_leg=2.0)
        said = "" if mode == "click" else "Let's go back there."
        for _ in range(12):
            if mode == "click":
                ws.places_click(f"#goto {mark['id']}")
            else:
                ws.on_move(A(kind="move", destination="the overturned cart"), said)
            if ws.combat:
                break
            ws.enter(start)
        held = dict(ws.player.road or {})
        check(f"({mode}) the walk to the sight is stopped by an ambush", bool(ws.combat), ws.player.location)
        check(f"({mode}) ...the stop where it falls names the sight as where the walk goes on to, and as where it is bound",
              held.get("resume") == mark["id"] and held.get("bound") == mark["id"], (held.get("resume"), held.get("bound"), mark["id"]))
        R.update(KEEP)
        R["chance_per_leg"] = 0.0
        if ws.combat:
            f = ws.combat.fight
            for e in f.fighters:
                if e.side == "enemy":
                    e.hp = 0
            f.over = "victory"
            ws.combat.finish()
        del SHOWN[:]
        m0 = ws.minutes
        if ws.walk_due():
            ws.resume_road()
        here = world.places.get(ws.player.location)
        notes = [t for k, t in SHOWN if k in ("note", "narrate")]
        check(f"({mode}) after the fight is won the walk goes on to the sight: the player stands there, and time was walked",
              here is not None and any("cart" in v.lower() for v in here.visible) and ws.minutes > m0, (ws.player.location, ws.minutes - m0, notes[-3:]))
        check(f"({mode}) ...and no line the player reads names a place by its id", not any(RAW_ID.search(t) for t in notes), [t for t in notes if RAW_ID.search(t)])
        g.close()

    # ---- a barrier met on the walk to a sight
    R.update(KEEP)
    g, ws = fresh(seed=5)
    world = ws.world
    road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places
                and world.path(r.from_, r.to) and world.path(r.from_, r.to)[1] >= 480)
    a, b = road.from_, road.to
    ra.generate = lambda *x, **k: sight.model_copy(deep=True)
    R.update(hostile=0.0, kinds={"sight": 1})
    ws.enter(a)
    ws.road_event([a, b], a, b, world.path(a, b)[1], 0.8, "We walk on.", [])
    mark = ws.landmarks()[-1]
    R["chance_per_leg"] = 0.0
    state = ws.store.load_world_state()
    pulse.apply_one(ws.store, world, ws.catalog, state, {"kind": "closed", "place": road.id, "days": 5, "text": "a fall of rock lies across it"},
                    "normal", ws.minutes, "test", ways=True)
    ws.store.save_world_state(state)
    ws.places_click(f"#goto {mark['id']}")
    held = dict(ws.player.road or {})
    check("a barrier met on the walk to a sight: the stop at the barrier is bound for the sight, which is kept",
          held.get("barrier") == road.id and held.get("bound") == mark["id"] and ws.player.location == held.get("id"), (held.get("barrier"), held.get("bound"), mark["id"]))
    check("...its ways and its record name only places on the map, or the sight", walks_on(ws) == (True, True, True) and not new_rules(ws.store, world),
          (walks_on(ws), new_rules(ws.store, world)))
    here_id = ws.player.location
    g, ws = reopen(g)
    world = ws.world
    check("a save opened standing at that barrier: on the map, its ways too, and a route leads from it to each", ws.player.location == here_id
          and walks_on(ws) == (True, True, True), walks_on(ws))
    ws.on_move(A(kind="move", destination=a), "I turn back.")
    check("...and the way back is walked", ws.player.location == a, ws.player.location)
    g.close()

    # ---- a hand-made save whose stop holds a way to a place off the map (a save made before this feature)
    R.update(KEEP)
    g, ws = fresh()
    stop = roads.make_stop(ws.world, "parth", "greywood", 0.5, 30, "A cart waits by the way.", "", "A cart by the way")
    stop["place"]["connects"] = {**stop["place"]["connects"], "road_0ff0ff01": 40}
    stop.update(log=[], text="", resume="", bound="greywood", kind="meeting", tier="normal", **{"from": "road_0ff0ff01"})
    ws.player.road = stop
    ws.player.location = stop["id"]
    ws.store.save_player(ws.player)
    g, ws = reopen(g)
    world = ws.world
    check("a save whose stop holds a way off the map opens standing there, the way off the map not put back",
          ws.player.location == stop["id"] and walks_on(ws) == (True, True, True), walks_on(ws))
    try:
        ws.on_move(A(kind="move", destination="parth"), "I go back to Parth.")
        err = ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    check("...and the walk from it goes", not err and ws.player.location == "parth", (err, ws.player.location))
    g.close()

    # ---- the campaign's check names a way and a record that lead off the map; a tidied stop's row is still no stray
    g, ws = fresh()
    world = ws.world
    stop = roads.make_stop(world, "parth", "greywood", 0.5, 30, "A cart waits by the way.", "", "A cart by the way")
    stop.update(log=[], text="", resume="road_0ff0ff02", bound="greywood", kind="meeting", tier="normal")
    world.add_place(Place(**{**stop["place"], "connects": {**stop["place"]["connects"], "road_0ff0ff03": 10}}))
    ws.player.road = stop
    ws.player.location = stop["id"]
    ws.store.save_player(ws.player)
    found = new_rules(ws.store, world)
    check("the campaign's check names a way of a place on the map that leads off it", any(stop["id"] in p and "road_0ff0ff03" in p for p in found), found)
    check("...and a stop's record that names a place off the map", any("road_0ff0ff02" in p for p in found), found)
    world.remove_place(stop["id"])
    ws.player.road = None
    ws.store.save_player(ws.player)
    ws.store.save_place(ws.store.load_place(stop["id"]))
    probs = [str(p) for p in invariants.validate_campaign(ws.store, world)]
    check("a player standing at a stop already tidied away is named; its saved row is not", any("player" in p and stop["id"] in p and "stands" in p for p in probs)
          and not any(p.startswith(f"place {stop['id']}") for p in probs), probs)
    ws.player.location = "parth"
    ws.store.save_player(ws.player)
    one = Place(**roads.make_stop(world, "parth", "greywood", 0.5, 30, "x", "", "One")["place"])
    world.add_place(one)
    other = Place(**{**roads.make_stop(world, "parth", "greywood", 0.4, 30, "y", "", "Two")["place"]})
    other = other.model_copy(update={"connects": {**other.connects, one.id: 5}})
    kept = dict(other.connects)
    world.add_place(other)
    world.remove_place(one.id)
    check("a place taken off the map is taken out of the other places' ways, and no place is changed in place",
          one.id not in world.places[other.id].connects and other.connects == kept and not new_rules(ws.store, world),
          (world.places[other.id].connects, other.connects))
    world.remove_place(other.id)
    g.close()

    # ---- the check after every input of a stub bot session, with the road busy
    import nightbot
    R.update(KEEP)
    R.update(chance_per_leg=1.0)
    stub.rng = random.Random(7)                              # the session's own dice, whatever ran before it
    g = simlib.campaign(NAME, seed=7, location=None, minutes=480)
    ws = g.scene
    bot = nightbot.Bot(ws, ws.world, random.Random(7), stub=stub, persona="wanderer")
    stub.bot = bot
    seen, stops, typed = [], set(), {"n": 0}

    def ask(*a, main=False, **k):
        if not main:
            return "yes"
        if typed["n"]:
            seen.extend(f"after input {typed['n']}: {p}" for p in new_rules(ws.store, ws.world))
            if is_stop(ws.world, ws.player.location):
                stops.add(ws.player.location)
        typed["n"] += 1
        return "quit" if typed["n"] > 60 else bot.decide()[0]

    uc.put("ask", ask)
    fault = ""
    try:
        ws.run()
    except Exception:
        fault = traceback.format_exc()[-600:]
    check("a stub bot session of 60 inputs with the road busy plays to its end", not fault and typed["n"] > 60, fault)
    check("...stopping on the road more than once", len(stops) >= 3, stops)
    check("...and after every input no way and no stop's record leads off the map", not seen, seen[:4])
    g.close()
finally:
    R.update(KEEP)
    ra.generate = REAL_GEN
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    for n in (NAME, "stop_ways_logs"):
        shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

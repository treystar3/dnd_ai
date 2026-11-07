"""(f540) Roads hold state. A situation that shuts a road ("{Road} shut", nature_cut_off) had its closure ignored: the pulse took a
closure or a mark only for a place, and the town's prose said the road was shut while nothing in the world was. Now a named road may be
closed or marked as a place may. A situation's closure lasts the situation (lifted with it, never a clock of its own; the owner,
2026-11-07); the only way between a road's two ends is closed only when the situation offers a way through it; a road's marks are kept
(capped, in data) and told on the walk; and both towns at its ends say the road is shut. Travel itself meets the closure in f541.
Run: python tools/sim/roads_closed_540_test.py"""
import json
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import pulse, roads

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


GAMES = []


def fresh(name: str, seed: int = 11):
    g = simlib.campaign(name, seed=seed, location="trading_square")     # (f450) the one way a test opens a campaign
    GAMES.append(g)
    ws = g.scene
    state = pulse.empty_state(ws.minutes); g.store.save_world_state(state)
    return ws.world, g.store, ws, state


def cut_off(world, store, ws, state, seed: int = 4):
    ok = pulse.start_thread(store, world, ws.catalog, state, ws.minutes, random.Random(seed), tier="normal", place_id="parth",
                            made_by="engine", template="nature_cut_off")
    th = next((t for t in state["threads"] if t.get("template") == "nature_cut_off"), None)
    return ok, th


world, store, ws, state = fresh("roads_540")
t0 = ws.minutes
ok, th = cut_off(world, store, ws, state)
store.save_world_state(state)                                  # as the pulse's tick saves it
check("the engine builds the cut-off situation at Parth", ok and th is not None, (ok, [t.get("template") for t in state["threads"]]))
road = (th or {}).get("words", {}).get("ids", {}).get("road") if th else ""
road = road or next((e["place"] for e in state["effects"] if e["kind"] == "closed"), "")
shut = [e for e in state["effects"] if e["kind"] == "closed" and e["place"] in world.roads]
check("its first stage shuts the road itself, keyed by the road's id", road in world.roads and [e["place"] for e in shut] == [road], (road, shut))
from engine import pulselog
said = [ef for r in pulselog.LOG for ef in r.get("effects") or [] if ef.get("text", "").startswith("closed")]
check("...and the pulse's log says the closure was applied, at the road's name", said and said[0]["result"] == "applied"
      and world.roads[road].name in said[0]["text"], said)
check("the closure lasts the situation: no clock of its own, the 60-day cap the only safety",
      shut and shut[0]["until"] >= t0 + pulse.P["effects"]["max_days"] * 1440 and shut[0].get("thread") == th["id"], shut)
check("...and why the way is shut is the store's to say", pulse.closed_reason(store, road, ws.minutes) == shut[0]["text"] if shut else False)

r = world.roads[road]
for end in (r.from_, r.to):
    seen = pulse.happenings_at(store, world, end, ws.minutes)
    check(f"HAPPENING HERE at {end} says the road is shut", any(f"({r.name}) is closed" in h for h in seen), seen)
far = next(p for p in world.places if world.places[p].type != "road" and pulse.town_of(world, p) not in
           {pulse.town_of(world, r.from_), pulse.town_of(world, r.to)} and not world.places[p].danger)
check("...and a town at neither end says nothing of it", not any(r.name in h for h in pulse.happenings_at(store, world, far, ws.minutes)))

# a road's marks: kept in the world's state, capped, told on the walk
cap = pulse.P["effects"]["marks_keep"]
for i in range(cap + 3):
    pulse.apply_one(store, world, ws.catalog, state, {"kind": "mark", "place": road, "text": f"mark {i}"}, "normal", ws.minutes, "test")
marks = pulse.road_marks(state, road)
check(f"a road keeps its marks in the world's state, the newest {cap}", len(marks) == cap and marks[-1] == f"mark {cap + 2}"
      and marks[0] == "mark 3", marks)
store.save_world_state(state)
facts = ws.journey_facts([r.from_, r.to], r.from_, r.to, 30)
check("...and the walk on it is told what it carries", f"mark {cap + 2}" in facts, facts)
check("a place's marks keep the same cap, now read from data", "[-lim[\"marks_keep\"]:]" in open("engine/pulse.py", encoding="utf-8").read())

# the only way between two places is shut only when the situation offers a way through
lone = [rid for rid in sorted(world.roads) if not roads.way_round(world, rid)]
mesh = [rid for rid in sorted(world.roads) if roads.way_round(world, rid)]
check("the world has roads with a way round and roads without one", lone and mesh, (len(lone), len(mesh)))
if lone and mesh:
    t = ws.minutes
    before = len(state["effects"])
    got = pulse.apply_one(store, world, ws.catalog, state, {"kind": "closed", "place": lone[0], "days": 3, "text": "a fall of rock"},
                          "normal", t, "test", thread_id="nothread", ways=False)
    check("the only way between a road's ends is not shut by a situation that offers no way through", got.startswith("skipped")
          and len(state["effects"]) == before, got)
    got = pulse.apply_one(store, world, ws.catalog, state, {"kind": "closed", "place": lone[0], "days": 3, "text": "a fall of rock"},
                          "normal", t, "test", thread_id="nothread", ways=True)
    check("...and is, when the situation offers one", got == "applied" and state["effects"][-1]["place"] == lone[0], got)
    got = pulse.apply_one(store, world, ws.catalog, state, {"kind": "closed", "place": mesh[0], "days": 3, "text": "a toll gate"},
                          "normal", t, "test", ways=False)
    check("a road with a way round may be shut by anything, for its own days when no situation holds it",
          got == "applied" and state["effects"][-1]["until"] == t + 3 * 1440, got)
    stop = roads.make_stop(ws.world, world.roads[lone[0]].from_, world.roads[lone[0]].to, 0.5, 120, "a scene", "", "A stop", "", "")
    from world.loader import Place
    ws.world.add_place(Place(**stop["place"]))                 # (f451) through the campaign's world, as the road's stop is made
    check("a stop on the road is never a way round it", stop["id"] in ws.world.places and roads.way_round(ws.world, lone[0]) is False)
    ws.world.remove_place(stop["id"])

# (f540's review) the way through is judged when it is known, and a situation that is over offers none
if lone and mesh:
    def thread(tid, paths, status="active", end_days=5):
        th_ = {"id": tid, "title": tid, "tier": "normal", "status": status, "stage": 0, "place": "parth", "stages": [{"description": "x",
               "effects": []}], "times": [ws.minutes, ws.minutes + end_days * 1440], "paths": paths, "groups": ["everyone"]}
        state["threads"].append(th_)
        return th_
    lone_shut = {"kind": "closed", "place": lone[0], "days": 2, "text": "a fall of rock"}
    def shut_by(tid):
        return [e for e in state["effects"] if e.get("thread") == tid and e["kind"] == "closed" and e["until"] > ws.minutes]
    thread("T_paths", [{"id": "p", "done": False}])
    thread("T_none", [])
    thread("T_taken", [{"id": "p", "done": True}])
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_paths")
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_none")
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_taken")
    check("a later stage shuts the only way when its situation has a way through not yet taken, and not otherwise",
          shut_by("T_paths") and not shut_by("T_none") and not shut_by("T_taken"), [len(shut_by(x)) for x in ("T_paths", "T_none", "T_taken")])
    over = thread("T_over", [{"id": "p", "done": False}], status="ended")
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_over")
    pulse.apply_effects(store, world, ws.catalog, state, [{**lone_shut, "place": mesh[0]}], "normal", ws.minutes, "test", raw=True,
                        thread_id="T_over")
    gone = [e for e in shut_by("T_over") if e["place"] == mesh[0]]
    check("a fallout (its situation over) never shuts the only way, and shuts another road for its own days, not the situation's span",
          not any(e["place"] == lone[0] for e in shut_by("T_over")) and gone and gone[0]["until"] == ws.minutes + 2 * 1440, shut_by("T_over"))
    first = thread("T_first", [])                                # a first stage, applied before the paths: then lifted for want of one
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_first", ways=True)
    row = {"effects": []}
    pulse.unshut_without_way(world, state, first, ws.minutes, row)
    kept = thread("T_kept", [{"id": "p", "done": False}])
    pulse.apply_effects(store, world, ws.catalog, state, [lone_shut], "normal", ws.minutes, "test", raw=True, thread_id="T_kept", ways=True)
    pulse.unshut_without_way(world, state, kept, ws.minutes)
    check("a first stage's closure of the only way is lifted once its situation has no way through, and kept when it has one",
          not shut_by("T_first") and shut_by("T_kept") and row["effects"] and "lifted" in row["effects"][0]["result"], row)
    long_ = thread("T_long", [{"id": "p", "done": False}], end_days=90)
    pulse.apply_effects(store, world, ws.catalog, state, [{**lone_shut, "place": mesh[0]}], "normal", ws.minutes, "test", raw=True,
                        thread_id="T_long")
    check("a situation longer than the 60-day safety keeps its road shut to its end", shut_by("T_long")
          and shut_by("T_long")[0]["until"] >= long_["times"][-1] + 1440, shut_by("T_long"))
    long_["times"][-1] += 30 * 1440                              # put off, as a campaign judged in part is
    pulse.tick_threads(store, world, ws.catalog, state, ws.minutes, random.Random(1))
    check("...and to its end when the end is put off", shut_by("T_long")[0]["until"] >= long_["times"][-1] + 1440, shut_by("T_long"))
    for tid in ("T_paths", "T_none", "T_taken", "T_over", "T_first", "T_kept", "T_long"):
        state["effects"] = [e for e in state["effects"] if e.get("thread") != tid]
    state["threads"] = [x for x in state["threads"] if not x["id"].startswith("T_")]
    # two closures never cut a town off between them
    pair = next(((x, y) for x in mesh for y in sorted(world.roads) if y != x and roads.way_round(world, x)
                 and not roads.way_round(world, x, {y})), None)
    check("the world has a road whose only way round runs over another road", pair is not None)
    if pair:
        x, y = pair
        t = ws.minutes
        pulse.apply_one(store, world, ws.catalog, state, {"kind": "closed", "place": y, "days": 3, "text": "a toll gate"}, "normal", t, "test",
                        ways=True)
        got = pulse.apply_one(store, world, ws.catalog, state, {"kind": "closed", "place": x, "days": 3, "text": "a fall of rock"}, "normal", t,
                              "test", ways=False)
        check("a road whose way round is shut already is the only way, and is not shut with no way through", got.startswith("skipped"), got)
        state["effects"] = [e for e in state["effects"] if e.get("cause") != "test" or e["place"] not in (x, y)]

# the situation's end lifts its closure, however it ends
pulse.end_thread(store, state, th, "faded", "", ws.minutes)
check("the situation's end opens the road", pulse.closed_reason(store, road, ws.minutes + 1) == "" if (store.save_world_state(state) or True) else False,
      [e for e in state["effects"] if e["place"] == road])

# the same seed, the same world
def built(name):                                               # the situation and its closures, less the id the process's stream gives it
    w, st_, ws_, s_ = fresh(name)
    th_ = cut_off(w, st_, ws_, s_, seed=4)[1] or {}
    return ({k: v for k, v in th_.items() if k != "id"},
            [{k: v for k, v in e.items() if k != "thread"} for e in s_["effects"] if e["kind"] == "closed"])
ta, tb = built("roads_540a"), built("roads_540b")
a, b = json.dumps(ta, sort_keys=True, default=str), json.dumps(tb, sort_keys=True, default=str)
ta, tb = ta[0], tb[0]
check("the same seed builds the same situation and the same closure, byte for byte", a == b and '"place"' in a,
      {k: (str((ta or {}).get(k))[:120], str((tb or {}).get(k))[:120]) for k in set(ta or {}) | set(tb or {})
       if json.dumps((ta or {}).get(k), sort_keys=True, default=str) != json.dumps((tb or {}).get(k), sort_keys=True, default=str)})

for g in GAMES:
    g.close()
for n in ("roads_540", "roads_540a", "roads_540b"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

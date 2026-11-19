"""(f733) A save opened again with nothing typed since its last open finds the campaign's own places on the map, at every open and
whoever builds the scene. The game's opening (world:open) runs once for each count of inputs, and an open that found it had stood ran
none of it, and with it none of what put the campaign's places back: the dungeons' entrances were on the map at the first open and
gone at the second, and a character standing at one (or at a home, a found place, the road's stop) met KeyError in run() at every
later open, so the save could not be opened at all. The map is now read back from the save where the scene is made over it
(WorldScene.restore_map, from CampaignSession.scene), and world:open keeps only what writes.

The case that found it: the dungeons' entrances, and a character standing at one. Second cases of the kind: a home; a place found from
inside that home (its way from the home is there after the open); a dungeon beneath a found place; the road's stop; a fight on at the
close, opened twice; one line typed between two opens and rolled back (its count given back); a scene built over the save with no
run(), as the acceptance tool builds one; and a dungeon remade at an open names its entrance anew. Each open is a new session."""
import os
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
from engine import discovery, dungeons, roads
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


NAME, FIGHT, LOGS = "open_twice", "open_twice_fight", "saves/open_twice_logs"
os.makedirs(LOGS, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
HOME = {"day": 1, "upgrades": [], "last_garden": -1, "last_hearth": -1}


def opened(name=NAME, lines=(), fresh=False, run=True):
    """The save opened as main.py opens it: a new session and a scene over it, and run() up to its prompt, where `lines` are typed and
    then "quit". With run=False the scene is only built (a tool's or a test's way). Returns the game, the scene and what run() raised."""
    g = simlib.campaign(name, cls="warrior", seed=3, location="parth", fresh=fresh)
    ws = g.scene
    queue = list(lines)
    uc.put("ask", lambda *a, **k: queue.pop(0) if queue else "quit")
    err = ""
    if run:
        try:
            ws.run()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
    return g, ws, err


def own(ws) -> list:
    return list(ws.world.added()["places"])


def opens_of(store) -> list:
    return [o["steps"] for o in store.load_operations()["ops"] if o["kind"] == "world:open"]


def stand(spot, **record) -> None:
    """The character stands at `spot` in the save (and their record holds `record`), set down between two sessions."""
    g, ws, _ = opened(run=False)
    for k, v in record.items():
        setattr(ws.player, k, v)
    ws.player.location = spot
    ws.store.save_player(ws.player)
    g.close()


def twice(spot, probe=None) -> tuple[list, list, list]:
    """Opened twice with nothing typed: what each run() raised, whether `spot` was on the map, and where the character stood (or what
    `probe` reads of the scene)."""
    errs, there, at = [], [], []
    for _ in range(2):
        g, ws, err = opened()
        errs.append(err)
        there.append(spot in ws.world.places)
        at.append(probe(ws) if probe else ws.player.location)
        g.close()
    return errs, there, at


def way(ws, a, b) -> bool:
    places = ws.world.places
    return a in places and b in places and b in places[a].connects and a in places[b].connects


try:
    # ---- the case that found it: the dungeons' entrances, at a second open with nothing typed, and standing at one
    g, ws, err = opened(fresh=True)
    first = own(ws)
    ent = g.store.load_dungeons()[0]["entrance"]
    g.close()
    g, ws, err2 = opened()
    again = own(ws)
    check("a save opened again with nothing typed has the campaign's own places on the map, as the first open put them",
          not err and not err2 and len(first) >= 40 and again == first, (err, err2, len(first), len(again)))
    check("...and the opening is still run once for its count of inputs, not again", opens_of(g.store) == [0], opens_of(g.store))
    g.close()
    stand(ent)
    errs, there, at = twice(ent)
    check("standing at a dungeon's entrance, the save opens at every later open, the entrance on the map",
          errs == ["", ""] and there == [True, True] and at == [ent, ent], (errs, there, at))

    # ---- a home
    stand("home_parth", homes={"parth": dict(HOME)})
    errs, there, at = twice("home_parth")
    check("standing in their own house, the save opens at every later open, the house on the map",
          errs == ["", ""] and there == [True, True] and at == ["home_parth"] * 2, (errs, there, at))

    # ---- a place found from inside the home: through the turn, as a player exploring from the house
    g, ws, _ = opened(run=False)
    ws.ensure_homes()                                             # (the map as an open before this feature left it, for the setup)
    old = (discovery.X["min_chance"], discovery.X["max_chance"])
    discovery.X["min_chance"] = discovery.X["max_chance"] = 1.0
    stub.a_DiscoveryProposal = lambda u, k: {"found": True, "kind": "place", "name": "the Quiet Grove", "place_type": "grove",
                                             "description": "A small grove behind the house.", "residents": [], "news": ""}
    stub.plan = [{"kind": "explore", "seek": "somewhere quiet past the garden wall"}]
    ws.turn("I go looking for somewhere quiet past the garden wall.")
    discovery.X["min_chance"], discovery.X["max_chance"] = old
    found = [d for d in g.store.load_discoveries()["places"] if d["anchor"] == "home_parth"]
    grove = found[0]["place"]["id"] if found else ""
    check("a place can be found from inside a house (the case the opening's order must hold)", bool(grove) and ws.player.location == grove,
          (found, ws.player.location))
    g.close()
    errs, there, at = twice(grove, probe=lambda ws: (ws.player.location, way(ws, "home_parth", grove)))
    check("standing at a place found from the house, the save opens at every later open, the place on the map",
          errs == ["", ""] and there == [True, True] and [a for a, _ in at] == [grove] * 2, (errs, there, at))
    check("...and the way to it from the house is on the map at each open (the house is put back before what was found from it)",
          [w for _, w in at] == [True, True], at)
    g, ws, _ = opened(run=False)

    # ---- a dungeon beneath a found place: the find is on the map before the entrance that hangs from it
    stub.a_DiscoveryProposal = lambda u, k: {"found": True, "kind": "place", "name": "the Wolf Hollow", "place_type": "cave",
                                             "description": "A low cave under the pines.", "residents": [], "news": ""}
    hollow = ws.invent_discovery("blackpine_forest", "a cave", None, g.store.load_discoveries())
    ws.ensure_dungeons()                                          # the world's tick makes a dungeon beneath it
    below = next((d for d in g.store.load_dungeons() if hollow and d["place"] == hollow["id"]), None)
    check("a dungeon is made beneath a found wild place", below is not None, hollow)
    g.close()
    stand(below["entrance"] if below else "")
    errs, there, at = twice(below["entrance"] if below else "")
    check("standing at the entrance of a dungeon beneath a found place, the save opens at every later open",
          errs == ["", ""] and there == [True, True], (errs, there, at))

    # ---- the road's stop
    g, ws, _ = opened(run=False)
    stop = roads.make_stop(ws.world, "parth", "greywood", 0.5, 30, "A cart waits by the way.", "", "A cart by the way")
    g.close()
    stand(stop["id"], road=stop)
    errs, there, at = twice(stop["id"])
    check("standing at the road's stop, the save opens at every later open, the stop on the map",
          errs == ["", ""] and there == [True, True] and at == [stop["id"]] * 2, (errs, there, at))

    # ---- a scene built over the save with no run(), as tools/acceptance.py and a test build one
    g, ws, _ = opened(run=False)
    want = {"an entrance": ent, "the house": "home_parth", "the found grove": grove, "the cave's entrance": below["entrance"] if below else "",
            "the stop": stop["id"]}
    missing = [k for k, pid in want.items() if pid not in ws.world.places]
    check("a scene built over the save, with no run(), finds the campaign's places on the map", not missing, missing)
    g.close()

    # ---- one line typed between two opens and rolled back: its count is given back, and the next open finds the map
    stand("home_parth")
    real = simlib.below()

    def no_plan(**k):
        if k["format"].get("title") == "ActionPlan":
            raise ConnectionError("the model server cannot be reached")
        return real.chat(**k)
    dead = simlib.stand_in(chat=no_plan, name="open_twice")
    g, ws, err = opened(lines=["I look around."])
    steps0 = g.store.meta.steps
    dead()
    g.close()
    g, ws, err2 = opened()
    check("a line not taken between two opens gives its count back, and the next open still finds the house",
          err == "" and err2 == "" and g.store.meta.steps == steps0 and "home_parth" in ws.world.places, (err, err2, g.store.meta.steps, steps0))
    g.close()

    # ---- a dungeon remade at an open: its entrance on the map is the new dungeon's, not the one the save held
    stand("parth")
    g, ws, err = opened(lines=["I look around."])                 # a line typed: the next open's opening runs
    g.close()
    g, ws, _ = opened(run=False)
    held = g.store.load_dungeons()
    old_d = next(d for d in held if d["place"] != "blackpine_forest" and not d.get("fixed") and d["entrance"] != ent)
    old_d["name"] = "the Old Pit"
    old_d["made"] = ws.minutes - (dungeons.D["respawn_days"] + 1) * 1440
    g.store.save_dungeons(held)
    g.close()
    g, ws, err = opened()
    new_d = next(d for d in g.store.load_dungeons() if d["place"] == old_d["place"])
    shown = ws.world.places[new_d["entrance"]].name if new_d["entrance"] in ws.world.places else ""
    check("a dungeon remade at an open puts its own entrance on the map, in place of the one the save held",
          not err and new_d["name"] != "the Old Pit" and shown == dungeons.entrance_place(new_d, ws.world).name and "Old Pit" not in shown,
          (err, new_d["name"], shown))
    g.close()

    # ---- a saved dungeon whose place is gone from the map (a place renamed in the data): left off it, as a home or a find is
    g, ws, _ = opened(run=False)
    held = g.store.load_dungeons()
    g.store.save_dungeons(held + [dict(held[0], id="dungeon_x_gone", place="x_gone", entrance="dungeon_x_gone")])
    g.close()
    g, ws, err = opened()
    check("a saved dungeon whose place is gone from the map is left off it, and the save still opens",
          err == "" and "dungeon_x_gone" not in ws.world.places and ent in ws.world.places, err)
    g.close()

    # ---- closed in the middle of a dungeon fight, then opened twice (a pinned view is not run in a fight, so no input moves the count)
    g, ws, _ = opened(FIGHT, fresh=True, run=False)
    ws.open_world()
    d = g.store.load_dungeons()[0]
    d["floors"][0]["chambers"] = [{"kind": "fight", "creature": "wolf", "count": 1, "level": 1, "boss": False}, {"kind": "rest"}]
    d["cleared"] = [-1, -1]
    ws.save_dungeon(d)
    ws.enter(d["entrance"])
    ws.store.save_player(ws.player)
    stub.plan = [{"kind": "delve"}]
    ws.turn("I go down into the dungeon.")
    began = ws.combat is not None and g.store.load_combat() is not None
    g.close()
    errs, on = [], []
    for _ in range(3):
        g, ws, err = opened(FIGHT)
        errs.append(err)
        on.append(ws.combat is not None)
        g.close()
    check("closed in a dungeon's fight, the save opens at every later open with the fight still on",
          began and errs == ["", "", ""] and on == [True, True, True], (began, errs, on))
finally:
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    for n in (NAME, FIGHT, "open_twice_logs"):
        shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

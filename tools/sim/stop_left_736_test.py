"""(f736) A stop is left one way whatever ends the stay, and a character is never left standing, or due to wake, at a place off the
map (the audit's scenes3-6). A stop on the road is tidied off the map by leave_road, which takes its people with it, as soon as the
character stands anywhere else; a fight lost there cleared the character's stop before the waking, so the stop stayed joined to both
ends of its road for the rest of the session, the one met there never went, and the map read differently once the save was opened
again. A night slept at a stop made it the last rest, and the rest note promised a waking there: lost a fight there and closed, the
save stood the character at the stop, gone from the map, and raised KeyError at every open.
Now a defeat leaves the stop's record for the waking to tidy through leave_road, as every other leaving does; a night at a stop is no
last rest (the owner, 2026-11-18: last_rest stays where it was, and the rest note names that place); the waking is the fallen
character's, at their last rest while it is on the map and no stop, else the town behind them, else the world's start (where one who
has never rested wakes, as before); and a save standing a character at a place off the map opens with them stood where they would
wake, told so in one line after the passage read last, the fault in the crash log.
The case that found it: a fight lost at a stop, with someone met there; a night slept at a stop, a fight lost there, the save closed and
opened. Second cases of the kind: a death outside a fight at a stop (a warned drop made); a flight from the stop's fight, then the walk
on; a waking place already off the map (an older save's last rest at a stop since tidied); a hand-made save standing at an id off the
map; the map of a session played straight against the same save opened again; and no code but leave_road clears a stop's record.
Run: python tools/sim/stop_left_736_test.py"""
import ast
import os
import shutil
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import config
import ui.console as uc

NAME, LOGS = "stop_left", "saves/stop_left_logs"
os.makedirs(LOGS, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
from engine import act, combat, crashlog, roads, told
from llm.contracts import ActionIntent as A
from scenes.combat_scene import CombatScene
from storage import invariants

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


R = roads.R
KEEP = {k: R[k] for k in ("chance_per_leg", "hostile", "kinds", "max_per_trip")}
ROOT = Path(__file__).resolve().parent.parent.parent


def fresh(at: str = "parth", seed: int = 7):
    g = simlib.campaign(NAME, seed=seed, location=at, minutes=420)
    ws = g.scene
    ws.enter(at)
    g.store.save_player(ws.player)
    return g, ws


def reopen(g):
    """The save closed and opened again: a new session and a scene over the save (its map put back)."""
    g.store.save_player(g.scene.player)
    g.close()
    g = simlib.campaign(NAME, fresh=False)
    return g, g.scene


def run_open(g):
    """The save closed and opened as the game opens it (WorldScene.run), then quit at once: (the scene, the fault if it raised)."""
    g, ws = reopen(g)
    uc.put("ask", lambda *a, main=False, **k: "quit" if main else "yes")
    try:
        ws.run()
        return g, ws, ""
    except Exception as e:
        return g, ws, f"{type(e).__name__}: {e}"


def play(ws, text, plan) -> list:
    """One typed line through the game's one input path: the operations of it that failed."""
    stub.plan = [dict(p) for p in plan]
    ws.play(text)
    return [f"{o.kind}: {o.failure}" for o in ws.line_failed]


def farthest(world, start: str = "parth") -> str:
    towns = [p.id for p in world.places.values() if not p.parent and not p.danger and p.type in ("town", "city", "village") and p.id != start]
    return max(((world.path(start, t) or ([], 0))[1], t) for t in towns)[1]


def to_stop(ws) -> tuple:
    """The walk from Parth stopped on the road by someone met there: (the stop's record, the ids of the people met there)."""
    R.update(chance_per_leg=1.0, hostile=0.0, kinds={"meeting": 1}, max_per_trip=9)
    dest = farthest(ws.world)
    play(ws, f"I set out for {ws.world.places[dest].name}.", [{"kind": "move", "destination": dest}])
    R.update(KEEP)
    R["chance_per_leg"] = 0.0
    stop = dict(ws.player.road or {})
    met = list(ws.store.load_place(stop["id"]).residents) if stop.get("id") else []
    return stop, met


def lose(ws) -> None:
    """A fight at the stop, lost: the fight's real end (CombatScene.finish), then the Threshold's waking."""
    creature = ws.world.bestiary["bandit"]
    foe = combat.fighter_from_creature(creature, 3, "normal", "e1", "a bandit", "near")
    ws.combat = CombatScene.begin(ws, creature, [foe], "On the road,")
    f = ws.combat.fight
    f.player.hp = 0
    f.over = "defeat"
    ws.combat.finish()
    ws.store.save_player(ws.player)


def gone(ws, met) -> bool:
    return bool(met) and all(ws.store.load_npc(n).gone for n in met)


def the_map(world) -> dict:
    return {pid: dict(p.connects) for pid, p in world.places.items()}


def off_map(ws) -> list:
    return [str(p) for p in invariants.validate_campaign(ws.store, ws.world)
            if "not on the map" in p.what or "not a place of the world" in p.what]


g = None
try:
    # ---- the case that found it: a fight lost at a stop, with someone met there
    g, ws = fresh()
    world = ws.world
    stop, met = to_stop(ws)
    check("(the walk is stopped at a stop, someone met there)", stop and ws.player.location == stop["id"] and met, (ws.player.location, met))
    lose(ws)
    check("a fight lost at a stop: the stop is off the map, and nothing on the map has a way to it",
          stop["id"] not in world.places and not any(stop["id"] in p.connects for p in world.places.values()),
          (stop["id"] in world.places, [p.id for p in world.places.values() if stop["id"] in p.connects]))
    check("...the one met there has gone, as when the walk goes on", gone(ws, met), [(n, ws.store.load_npc(n).gone) for n in met])
    check("...and the character, who has never rested, wakes where the world starts, as before, no stop held",
          ws.player.location == world.start_location and ws.player.road is None, (ws.player.location, bool(ws.player.road)))
    straight = the_map(world)
    g, ws = reopen(g)
    check("the map of the session played straight is the map of the same save opened again", the_map(ws.world) == straight,
          (sorted(set(straight) ^ set(the_map(ws.world))), [k for k in straight if straight[k] != the_map(ws.world).get(k)][:4]))
    check("...and the campaign's check finds nothing off the map", not off_map(ws), off_map(ws))
    g.close()

    # ---- the case that found it: a night slept at a stop, a fight lost there, the save closed and opened
    g, ws = fresh()
    world = ws.world
    play(ws, "I lie down and sleep for eight hours.", [{"kind": "wait", "wait_minutes": 480}])
    check("(a night slept in Parth is the last rest)", ws.player.character.last_rest == "parth", ws.player.character.last_rest)
    stop, met = to_stop(ws)
    del SHOWN[:]
    play(ws, "I lie down and sleep for eight hours.", [{"kind": "wait", "wait_minutes": 480}])
    notes = [t for k, t in SHOWN if k == "note"]
    check("(the night is slept at the stop)", ws.player.location == stop.get("id") and any("If you die" in t for t in notes), (ws.player.location, notes))
    check("a night slept at a stop is no last rest: the last rest stays in Parth", ws.player.character.last_rest == "parth", ws.player.character.last_rest)
    check("...and the rest note names that place, never the stop",
          any(f"If you die, you will wake at {world.places['parth'].name}." in t for t in notes)
          and not any(world.places[stop["id"]].name in t for t in notes if "If you die" in t), notes)
    lose(ws)
    check("lost a fight at that stop: the character wakes in Parth, the stop is off the map and the one met there has gone",
          ws.player.location == "parth" and stop["id"] not in world.places and gone(ws, met), (ws.player.location, stop["id"] in world.places))
    g, ws, fault = run_open(g)
    check("...and the save, closed, opens again standing in Parth", not fault and ws.player.location == "parth"
          and ws.player.location in ws.world.places, (fault, ws.player.location))
    check("...with nothing off the map", not off_map(ws), off_map(ws))
    g.close()

    # ---- a death outside a fight at a stop: a warned drop made
    g, ws = fresh()
    world = ws.world
    play(ws, "I lie down and sleep for eight hours.", [{"kind": "wait", "wait_minutes": 480}])
    stop, met = to_stop(ws)
    deaths = ws.player.character.deaths
    act.died(ws, ws.acting, types.SimpleNamespace(body=types.SimpleNamespace(size=90)))
    check("a death outside a fight at a stop (a warned drop made): the character wakes at the last rest, Parth",
          ws.player.character.deaths == deaths + 1 and ws.player.location == "parth", (ws.player.character.deaths - deaths, ws.player.location))
    check("...the stop is off the map and the one met there has gone", stop["id"] not in world.places and gone(ws, met) and ws.player.road is None,
          (stop["id"] in world.places, [(n, ws.store.load_npc(n).gone) for n in met]))
    g.close()

    # ---- a flight from the stop's fight, then the walk on
    g, ws = fresh()
    world = ws.world
    stop, met = to_stop(ws)
    creature = world.bestiary["bandit"]
    ws.combat = CombatScene.begin(ws, creature, [combat.fighter_from_creature(creature, 3, "normal", "e1", "a bandit", "near")], "On the road,")
    ws.combat.fight.over = "fled"
    ws.combat.finish()
    check("a flight from a fight at a stop: still at the stop, which keeps its record, the walk not taken up by itself",
          ws.player.location == stop["id"] and stop["id"] in world.places and (ws.player.road or {}).get("id") == stop["id"]
          and not ws.player.road.get("resume") and not ws.walk_due(), (ws.player.location, (ws.player.road or {}).get("resume")))
    ws.on_move(A(kind="move", destination="parth"), "I go back to Parth.")
    check("...then walked on from, the stop is tidied the one way: off the map, the one met there gone",
          ws.player.location == "parth" and stop["id"] not in world.places and gone(ws, met) and ws.player.road is None,
          (ws.player.location, stop["id"] in world.places))
    g.close()

    # ---- a waking place already off the map: an older save's last rest at a stop since tidied
    g, ws = fresh()
    world = ws.world
    stop, met = to_stop(ws)
    ws.player.character.last_rest = "road_0ff0ff07"                      # a stop slept at and tidied, as a save made before holds
    lose(ws)
    check("a last rest off the map: a fight lost at a stop wakes the character in the town behind, not at the world's start",
          ws.player.location == "parth" and stop["id"] not in world.places, (ws.player.location, world.start_location))
    g.close()

    # ---- a hand-made save standing a character at an id off the map (a save the old fault already made)
    g, ws = fresh()
    world = ws.world
    stop, met = to_stop(ws)
    ws.player.road = None                                                # the old defeat: the stop's record cleared, the place left
    ws.player.character.last_rest = stop["id"]                           # ...and the night slept there its last rest
    ws.store.save_player(ws.player)
    lost = stop["id"]
    del SHOWN[:]
    g, ws, fault = run_open(g)
    lines = {x.format(place=ws.world.places["parth"].name)[:1].upper() + x.format(place=ws.world.places["parth"].name)[1:]
             for x in told.T.get("place_gone", [])}
    shown = [t for k, t in SHOWN if k == "note"]
    check("a save standing the character at a place off the map opens", not fault, fault)
    check("...standing them where they would wake: the town behind (their last rest, a stop, is gone too)",
          ws.player.location == "parth" and ws.player.location in ws.world.places, (ws.player.location, lost))
    check("...told so in one line", sum(t in lines for t in shown) == 1, shown)
    at = [i for i, (k, t) in enumerate(SHOWN) if k == "note" and t in lines]
    read = [i for i, (k, t) in enumerate(SHOWN) if k == "narrate"]
    check("...after the passage read last, which was of the place gone", at and read and read[-1] < at[0], SHOWN)
    check("...and the fault is written to the crash log, naming the place", any(lost in e.get("error", "") for e in crashlog.SESSION),
          crashlog.SESSION[-2:])
    mine = [p for p in off_map(ws) if p.startswith("player")]
    check("...and the campaign's check finds the character standing on the map", not mine, mine)
    try:
        ws.on_move(A(kind="move", destination="south_fields"), "I walk out to the south fields.")
        err = ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    check("...and the walk from there goes", not err and ws.player.location == "south_fields", (err, ws.player.location))
    g.close()

    # ---- no code but leave_road clears a character's stop
    writers = []
    for folder in ("engine", "scenes", "services", "npc", "storage", "world", "core", "ui", "llm"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                for node in ast.walk(fn):
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is None \
                            and any(isinstance(t, ast.Attribute) and t.attr == "road" for t in node.targets):
                        writers.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno} ({fn.name})")
    check("a character's stop is cleared in one place only, leave_road, which tidies it off the map",
          sorted(set(writers)) == [w for w in sorted(set(writers)) if w.endswith("(leave_road)")] and len(set(writers)) == 1, sorted(set(writers)))
finally:
    R.update(KEEP)
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    for n in (NAME, "stop_left_logs"):
        shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f736) A character the save stands at a place no longer on the map is read where every scene is built and written inside the game's
opening, for every character the save holds. The guard of f736 ran first in WorldScene.run(), outside any operation: its save and its
note in the crash log were in no operation's record, rollback or dice; a scene built without run() (tools/acceptance.py's reopen,
tools/rerun.py, simlib, a test) still met KeyError at the first read of where its character stood; and it went over the scene's one
player, so another character the save held stayed off the map. Now the reading half (who stands off the map, and where they would
wake) is met at the scene's build, beside restore_map, and writes nothing; the writing half (the save, the note, the line that tells
them) is world:open's, given back whole with it when it fails; and the opening that did not write them (it stood at an open before,
or did not stand now) leaves them to an operation of the opening's own.
The case that found it: a scene built by CampaignSession.scene() with no run(), over a save standing its character at a place gone.
Second cases of the kind: a second saved character standing off the map, stood where they would wake by their own record; the
opening's operation failing (given back whole, then written by the next open); the opening failing after the moves (they stand by
an operation of their own, noted and told once); the save opened as the game opens it (one line, the scene's own, after the
passage read last); and an opening that already stood at this count of inputs.
Run: python tools/sim/off_map_open_736_test.py"""
import json
import shutil
import sys
import tempfile
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import config
import ui.console as uc

NAME = "off_map_open"
LOGS = tempfile.mkdtemp(prefix="off_map_open_")
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, f"{LOGS}/{fn}")
SHOWN = simlib.quiet_console()
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
from engine import crashlog, operation, told
from storage import saves
from storage.playerstable import FIRST

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


GONE, GONE2 = "road_0ff0ff07", "road_5ec0d0ff"          # stops tidied off the map long ago, as an older save holds them


def make(second: bool = True) -> None:
    """A save whose character stands at a place no longer on the map (their last rest Parth) and, with `second`, a second character
    of the save standing at another (their last rest Ironvein), set down between two sessions."""
    g = simlib.campaign(NAME, seed=7, location="parth", minutes=420)
    rec = g.scene.player
    rec.location, rec.character.last_rest = GONE, "parth"
    g.store.save_player(rec)
    if second:
        body = json.loads(g.store.player_text())
        body["character"]["id"], body["character"]["name"] = "second", "Second Traveller"
        body["location"], body["character"]["last_rest"] = GONE2, "ironvein"
        with g.store.transaction():
            g.store._players.put(body, "second")           # a second character's row, as the players table holds one (players_638)
    g.close()


def where(store, who: str = FIRST) -> str:
    return json.loads(store.player_text(who) or "{}").get("location", "")


def watch(store) -> list:
    """Every write of a character's record from now on: (whose row, where it stands them, the operation open and its id)."""
    puts, real = [], store._players.put

    def put(body, who=FIRST):
        op = operation.current()
        puts.append((who, body.get("location"), op.kind if op else "", op.id if op else ""))
        return real(body, who)
    store._players.put = put
    return puts


def notes(lost: str) -> int:
    return sum(1 for e in crashlog.SESSION if e.get("where") == "a save opened" and lost in e.get("error", ""))


def told_lines(world, place: str) -> set:
    return {told.say("place_gone", n, place=world.places[place].name) for n in range(len(told.T["place_gone"]))}


def run_open():
    """The save opened as the game opens it (WorldScene.run), then quit at once: (the game, the scene, the fault if it raised)."""
    g = simlib.campaign(NAME, fresh=False)
    ws = g.scene
    uc.put("ask", lambda *a, main=False, **k: "quit" if main else "yes")
    try:
        ws.run()
        return g, ws, ""
    except Exception as e:
        return g, ws, f"{type(e).__name__}: {e}"


g = None
try:
    # ---- the case that found it: a scene built by CampaignSession.scene() with no run(), as tools/acceptance.py's table builds its first
    make()
    g = simlib.campaign(NAME, fresh=False)
    w0, first0, second0 = g.store._writes, g.store.player_text(), g.store.player_text("second")
    err, place, writes = "", "", None
    try:
        ws = g.scene
        writes = (g.store._writes - w0, g.store.player_text() == first0, g.store.player_text("second") == second0)
        place = ws.place.id
        ws.enter(ws.player.location)                        # as tools/acceptance.py's table does at its start
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    check("a scene built with no run(), over a save standing its character at a place gone from the map, raises nothing", not err, err)
    check("...and stands them where they would wake, their last rest", place == "parth" and not err and ws.player.location == "parth",
          (place, err))
    check("...reading the save and writing nothing to it: both characters still stand at the places gone in the save",
          writes == (0, True, True) and where(g.store) == GONE and where(g.store, "second") == GONE2, writes)

    # ---- the opening writes it, inside its operation, for every character the save holds
    puts = watch(g.store)
    ws.open_world()
    check("the opening writes the move: the save stands the character where they would wake",
          where(g.store) == "parth" and any(p[:3] == (FIRST, "parth", "world:open") for p in puts), (where(g.store), puts))
    check("...a second character of the save, standing off the map, is moved too, where their own record would wake them",
          where(g.store, "second") == "ironvein" and any(p[:3] == ("second", "ironvein", "world:open") for p in puts),
          (where(g.store, "second"), puts))
    check("...no character's record is written outside an operation", not [p for p in puts if not p[2]], puts)
    check("...and the crash log names each place gone, once", notes(GONE) == 1 and notes(GONE2) == 1, crashlog.SESSION[-3:])
    g.close()

    # ---- the opening's operation fails: given back whole, and the next open writes it
    make()
    g = simlib.campaign(NAME, fresh=False)
    ws = g.scene
    puts = watch(g.store)
    real_commit = g.store.commit_operation

    def refused(op, **k):
        if op.kind == "world:open":
            raise RuntimeError("the opening's commit is refused")
        return real_commit(op, **k)
    g.store.commit_operation = refused
    n0, m0 = notes(GONE), notes(GONE2)
    err = ""
    try:
        lines = ws.open_world() or []
        place = ws.place.id
    except Exception as e:
        err, lines, place = f"{type(e).__name__}: {e}", [], ""
    tried = [p for p in puts if p[2] == "world:open"]
    check("an opening whose operation fails raises nothing, and the scene still stands its character where they would wake",
          not err and place == "parth" and ws.player.location == "parth", (err, place))
    check("...the move was written inside it (the opening's operation wrote both records)",
          {p[0] for p in tried if p[1] in ("parth", "ironvein")} == {FIRST, "second"}, puts)
    check("...and given back whole: the save stands both at the places gone, no note, no line, no record of the opening",
          where(g.store) == GONE and where(g.store, "second") == GONE2 and (notes(GONE), notes(GONE2)) == (n0, m0) and not lines
          and not [o for o in g.store.load_operations()["ops"] if o["kind"] == "world:open"],
          (where(g.store), where(g.store, "second"), notes(GONE) - n0, lines))
    del g.store.commit_operation
    lines = ws.open_world() or []
    check("the next open writes it: both stand where they would wake, each noted once, the scene's own told once",
          where(g.store) == "parth" and where(g.store, "second") == "ironvein" and (notes(GONE), notes(GONE2)) == (n0 + 1, m0 + 1)
          and len(lines) == 1 and lines[0] in told_lines(ws.world, "parth"), (where(g.store), where(g.store, "second"), lines))
    g.close()

    # ---- the opening fails after the moves: they stand by an operation of the opening's own, noted and told once
    make()
    g = simlib.campaign(NAME, fresh=False)
    ws = g.scene
    puts = watch(g.store)
    n0, m0 = notes(GONE), notes(GONE2)

    def broken():
        raise RuntimeError("the world's pulse fails")
    ws.run_pulse = broken
    lines = ws.open_world() or []
    del ws.run_pulse
    ids = {p[3] for p in puts if p[2] == "world:open"}
    kept = {o["id"] for o in g.store.load_operations()["ops"] if o["kind"] == "world:open"}
    check("an opening that fails after the moves: they stand all the same, by an operation of the opening's own",
          where(g.store) == "parth" and where(g.store, "second") == "ironvein" and len(ids) == 2 and len(kept & ids) == 1,
          (where(g.store), where(g.store, "second"), ids, kept))
    check("...the failed opening's note and line given back with it: each noted once, the scene's own told once",
          (notes(GONE), notes(GONE2)) == (n0 + 1, m0 + 1) and len(lines) == 1 and lines[0] in told_lines(ws.world, "parth"),
          (notes(GONE) - n0, notes(GONE2) - m0, lines))
    g.close()

    # ---- the save opened as the game opens it: one line, the scene's own, after the passage read last
    make()
    del SHOWN[:]
    g, ws, err = run_open()
    shown = [t for k, t in SHOWN if k == "note"]
    mine, theirs = told_lines(ws.world, "parth"), told_lines(ws.world, "ironvein")
    at = [i for i, (k, t) in enumerate(SHOWN) if k == "note" and t in mine]
    read = [i for i, (k, t) in enumerate(SHOWN) if k == "narrate"]
    check("the save opened as the game opens it raises nothing, and both characters stand where they would wake",
          not err and ws.player.location == "parth" and where(g.store) == "parth" and where(g.store, "second") == "ironvein",
          (err, ws.player.location, where(g.store, "second")))
    check("...the scene's own character is told in one line, after the passage read last; the other's move is not told here",
          sum(t in mine for t in shown) == 1 and not any(t in theirs for t in shown) and at and read and read[-1] < at[0], shown)
    g.close()

    # ---- an opening that already stood at this count of inputs: the moves are written in an operation all the same
    make(second=False)
    g, ws, err = run_open()                                 # the first open stands them and its opening stands
    ws.player_of(ws.acting).location = GONE                 # then the place goes from under them with nothing typed (a save of
    g.store.save_player(ws.player_of(ws.acting))            # the old fault opened by the old code, or a place gone from the data)
    steps = g.store.meta.steps
    g.close()
    g = simlib.campaign(NAME, fresh=False)
    puts = watch(g.store)
    ws = g.scene
    uc.put("ask", lambda *a, main=False, **k: "quit" if main else "yes")
    n0 = notes(GONE)
    del SHOWN[:]
    try:
        ws.run()
        err = ""
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    shown = [t for k, t in SHOWN if k == "note"]
    check("(the opening stood at this count already)", g.store.meta.steps == steps and
          len([o for o in g.store.load_operations()["ops"] if o["kind"] == "world:open" and o["steps"] == steps]) >= 1)
    check("an opening that stood at an open before still has the move written inside an operation, noted and told once",
          not err and where(g.store) == "parth" and any(p[:3] == (FIRST, "parth", "world:open") for p in puts) and notes(GONE) == n0 + 1
          and sum(t in told_lines(ws.world, "parth") for t in shown) == 1, (err, puts, notes(GONE) - n0, shown))
finally:
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    saves.drop(NAME)
    shutil.rmtree(LOGS, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

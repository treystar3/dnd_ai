"""(f628) The turn's fields, pinned before phase 3 moves them (docs/design/20_phase3_plan.md f631, f632). rollback_fields_579_test
pins what a failed operation puts back for the names WorldScene.ROLLED declares. This pins what that test does not hold: every
field a new line resets; the fields a failure keeps, writes or puts back by its own hand (the steps still to do); the declared
names a fresh scene never set (a rollback removes them again); the step's default; that the party's and the fight's services
stand on the scene's current player after a reload; and that two scenes each keep their own snapshot.
Every field is read through getattr, the way the game reads it, so this must pass unchanged while the fields move. LINE is held
to the code that resets a line today by tools/sim/moving_parts_628_test.py.
Run: python tools/sim/turn_fields_628_test.py"""
import copy
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from llm.gateway import LLMError
from scenes import combat_scene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

MISSING = object()
LINE = {"last_crash", "line_ops", "line_failed", "line_world_failed", "passages", "line_untold", "unshown_ops", "collecting",
        "line_from", "line_log", "line_losses", "line_plan", "own_steps", "silent", "stood", "waiting", "buffering"}
KEPT = ("last_budget", "broken", "last_text", "crash_after_commit", "recovered_at_load")      # a failure leaves these as they stand


def reach(ws, names) -> dict:
    out = {}
    for k in names:
        v = getattr(ws, k, MISSING)
        out[k] = v if v is MISSING else copy.deepcopy(v)
    return out


def same(a: dict, b: dict, skip=()) -> list:
    return [k for k in a if k not in skip and ((a[k] is MISSING) != (b[k] is MISSING) or (a[k] is not MISSING and a[k] != b[k]))]


g = simlib.campaign("turn_fields_628", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/turn_fields_628/turns.jsonl"
simlib.quiet_console()

# ---- before any operation has run
check("the step being done reads as none on a scene that has run nothing", getattr(ws, "step", MISSING) is None, getattr(ws, "step", MISSING))
unset = sorted(k for k in ws.ROLLED if getattr(ws, k, MISSING) is MISSING)
check("(some declared names are never set when a scene is made: a rollback has to remove them again)", len(unset) >= 15, len(unset))
ws.enter("parth")

# ---- what a new line resets
for k in LINE:
    setattr(ws, k, f"left over:{k}")
ws.begin_line()
store.arm(False)                                         # begin_line arms the write fence for a line's life; this is no line
fresh = reach(ws, LINE)
check("a new line begins clean: no operations, passages or failures of the last one, nothing lost, nothing collecting",
      all(fresh[k] == [] for k in ("line_ops", "line_failed", "line_world_failed", "passages", "line_untold", "line_plan", "waiting"))
      and fresh["unshown_ops"] == {} and fresh["collecting"] is False and fresh["last_crash"] is False and fresh["line_losses"] == 0
      and fresh["own_steps"] is False and fresh["silent"] is False and fresh["stood"] is None and fresh["buffering"] is False, fresh)
check("...it knows where the line began and where the journal stood", fresh["line_from"] == ws.player.location
      and isinstance(fresh["line_log"], int) and not isinstance(fresh["line_log"], bool), (fresh["line_from"], fresh["line_log"]))
check("...each list its own (none shared with another field)",
      len({id(getattr(ws, k)) for k in LINE if isinstance(getattr(ws, k), list)}) == 7)

# ---- what a failed operation keeps, and what it writes itself
ws.pending = ["a step still to do"]
was_player = ws.player
unset_now = [k for k in ws.ROLLED if getattr(ws, k, MISSING) is MISSING]
with ws.operation("test", "a failing step") as op:
    for k in KEPT:
        setattr(ws, k, f"set inside:{k}")
    for k in unset_now:
        setattr(ws, k, f"made inside:{k}")
    ws.pending.append("queued inside, in place")
    ws.pending = ws.pending + ["and one more"]
    raise LLMError("the model failed")
check("a failed operation does not take back what the turn keeps across it (the budget's close, the last passage, the crash marks)",
      op.state == "rolled_back" and all(getattr(ws, k, MISSING) == f"set inside:{k}" for k in KEPT), reach(ws, KEPT))
check("...and it says so itself: the line is halted, and the failure is kept for the row",
      getattr(ws, "halted", MISSING) is True and getattr(ws, "last_failure", MISSING) == "the model failed", reach(ws, ("halted", "last_failure")))
check("...the steps still to do are as the operation found them: what it queued is gone, what waited before it still waits",
      getattr(ws, "pending", MISSING) == ["a step still to do"], getattr(ws, "pending", MISSING))
check("a declared name first made inside a failed operation is not there after it",
      unset_now and all(getattr(ws, k, MISSING) is MISSING for k in unset_now), [k for k in unset_now if getattr(ws, k, MISSING) is not MISSING])
for k in KEPT:
    setattr(ws, k, {"last_budget": {}, "broken": {}, "last_text": "", "crash_after_commit": "", "recovered_at_load": 0}[k])
ws.halted, ws.pending = False, []

# ---- the scene holds a new record of the player after a failure, and the services stand on it
check("(a failed operation reloads the player: the scene holds a new record)", ws.player is not was_player)
check("the acting character is the scene's player", ws.acting == ws.player.character.id, ws.acting)
check("the party's service and the fight's stand on the scene's current player, not the one before the reload",
      ws.party_service.player is ws.player and combat_scene.service_of(ws).player is ws.player)

# ---- two scenes each keep their own snapshot
g2 = simlib.campaign("turn_fields_628b", cls="warrior", seed=4, location="parth")
ws2 = g2.scene
ws2.enter("parth")
ws.recent_narration, ws.last_spoken = ["told in the first"], "the first's"
ws2.recent_narration, ws2.last_spoken = ["told in the second"], "the second's"
one, two = reach(ws, ws.ROLLED), reach(ws2, ws2.ROLLED)
with ws.operation("test", "the first scene fails") as a:
    for k in ws.ROLLED:
        setattr(ws, k, f"first:{k}")
    raise LLMError("the model failed")
check("a failed operation in one scene puts that scene back and leaves another scene's fields alone", a.state == "rolled_back"
      and not same(one, reach(ws, ws.ROLLED), skip=("step",)) and not same(two, reach(ws2, ws2.ROLLED)),
      (same(one, reach(ws, ws.ROLLED), skip=("step",)), same(two, reach(ws2, ws2.ROLLED))))
with ws2.operation("test", "the second scene fails") as b:
    for k in ws2.ROLLED:
        setattr(ws2, k, f"second:{k}")
    raise LLMError("the model failed")
check("...and the same the other way round, each from its own snapshot", b.state == "rolled_back"
      and not same(two, reach(ws2, ws2.ROLLED), skip=("step",)) and not same(one, reach(ws, ws.ROLLED), skip=("step",)),
      (same(two, reach(ws2, ws2.ROLLED), skip=("step",)), same(one, reach(ws, ws.ROLLED), skip=("step",))))

g2.session.close()
g.session.close()
for name in ("turn_fields_628", "turn_fields_628b"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

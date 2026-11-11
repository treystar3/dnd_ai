"""(f579) What a failed operation puts back, pinned by reach. The session's snapshot copies what it finds in the scene's own __dict__
(engine/session.py begin_turn, rollback): every name WorldScene.ROLLED declares and every underscore cache. A field moved off the scene
(behind a property, onto a turn context) would drop out of both the copy and the restore with no error, and scene_rollback_465_test,
which reads ws.__dict__, would pass blind. So here every field is read the way the game reads it, through getattr, around: an operation
that fails; a line whose second operation fails after its first stood; an operation that stands down to ask outside and runs again; and
a new line's start. The foundations bundle moves these fields (docs/design/13_foundations_design.md f584): this must pass unchanged.
Run: python tools/sim/rollback_fields_579_test.py"""
import copy
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from engine import asked
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("rollback_579", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/rollback_579/turns.jsonl"
simlib.quiet_console()
ws.enter("parth")
MISSING = object()


def reach(names) -> dict:
    """Each field as the game reads it; a copy, so a later change in place cannot hide."""
    out = {}
    for k in names:
        v = getattr(ws, k, MISSING)
        out[k] = v if v is MISSING else copy.deepcopy(v)
    return out


def moved(before: dict, skip=()) -> list:
    now = reach(before)
    return [k for k in before if k not in skip and ((now[k] is MISSING) != (before[k] is MISSING)
                                                    or (now[k] is not MISSING and now[k] != before[k]))]


ROLLED = tuple(ws.ROLLED)
LINE = ("line_ops", "line_failed", "line_done", "line_world_failed", "passages", "line_untold", "unshown_ops", "collecting", "last_crash")
check("(the scene declares what a line writes outside the save)", len(ROLLED) >= 30 and "recent_narration" in ROLLED and "step" in ROLLED, len(ROLLED))

# ---- an operation that fails
ws.recent_narration = ["what was told before"]
ws.last_spoken = "someone"
ws._pin579_cache = {"kept": [1, 2]}
before = reach(ROLLED)
with ws.operation("test", "a failing step") as op:
    ws.recent_narration.append("told inside, in place")  # a field changed in place: a snapshot that kept the list itself would keep this
    for k in ROLLED:
        setattr(ws, k, f"sentinel:{k}")
    ws._pin579_cache["kept"].append(3)                   # a cache changed in place
    ws._pin579_new = "made inside"                       # and one made inside
    raise LLMError("the model failed")
check("every declared field, read as the game reads it, is as it was before a failed operation", op.state == "rolled_back"
      and not moved(before, skip=("step",)), moved(before, skip=("step",)))
check("...one changed in place among them (the snapshot is a copy, not the list itself)", ws.recent_narration == ["what was told before"],
      ws.recent_narration)
check("...the step being done is none", getattr(ws, "step", MISSING) is None)
check("...a field never set before reads as it did (its default, or not there)",
      all((getattr(ws, k, MISSING) is MISSING) == (before[k] is MISSING) for k in ROLLED if k != "step"))
check("an underscore cache changed in place is back, and one made inside is gone", getattr(ws, "_pin579_cache", MISSING) == {"kept": [1, 2]}
      and getattr(ws, "_pin579_new", MISSING) is MISSING, (getattr(ws, "_pin579_cache", MISSING), getattr(ws, "_pin579_new", MISSING)))

# ---- a line whose second operation fails keeps what its first set
with ws.operation("test", "a first step that stands") as op1:
    ws.last_spoken = "the first step's"
    ws.recent_narration = ["what the first step told"]
    ws._pin579_cache = {"kept": ["first"]}
stood = reach(ROLLED)
with ws.operation("test", "a second step that fails") as op2:
    ws.recent_narration.append("told by the second, in place")
    for k in ROLLED:
        setattr(ws, k, f"second:{k}")
    ws._pin579_cache["kept"].append("second")
    raise LLMError("the model failed")
check("a second operation's failure puts every field back to what the first left, not to the line's start", op1.state == "committed"
      and op2.state == "rolled_back" and not moved(stood, skip=("step",)) and getattr(ws, "last_spoken") == "the first step's"
      and getattr(ws, "_pin579_cache") == {"kept": ["first"]}, (op1.state, op2.state, moved(stood, skip=("step",))))

# ---- an operation that stands down to ask outside, then runs again
found, asks = [], []
start = reach(ROLLED)


def body(op):
    found.append(reach(ROLLED))
    serving = asked.serving()
    if serving.at >= len(serving.answers):               # the first attempt: write, then need an answer from outside
        ws.recent_narration.append("told by the attempt, in place")
        for k in ROLLED:
            setattr(ws, k, f"attempt:{k}")
        ws._pin579_cache["kept"].append("attempt")
        raise asked.NeedAnswer("pin579", lambda: asks.append(reach(ROLLED)) or "the answer")
    serving.at += 1
    ws.last_spoken = "the attempt that stood"
    return "done"


op3, result = ws.asked_operation("test", "a step that asks outside", body)
same = lambda a, b: all((a[k] is MISSING) == (b[k] is MISSING) and (a[k] is MISSING or a[k] == b[k]) for k in ROLLED if k != "step")
check("(the operation stood down once, asked outside, ran again and stood)", len(found) == 2 and len(asks) == 1 and result == "done"
      and op3.state == "committed", (len(found), len(asks), result, op3.state))
check("an attempt that stood down left nothing of itself: the call outside and the attempt run again read every field as it began",
      len(found) == 2 and len(asks) == 1 and same(found[0], start) and same(asks[0], start) and same(found[1], start),
      [k for k in ROLLED if k != "step" and len(found) == 2 and found[1][k] is not MISSING and found[1][k] != start[k]])
check("...its underscore cache with them, and what the standing attempt set is kept", getattr(ws, "_pin579_cache") == {"kept": ["first"]}
      and getattr(ws, "last_spoken") == "the attempt that stood", (getattr(ws, "_pin579_cache"), getattr(ws, "last_spoken")))

# ---- a new line starts clean
for k in LINE:
    setattr(ws, k, f"left over:{k}")
ws.begin_line()
store.arm(False)                                         # begin_line arms the write fence for a line's life; this is no line
fresh = {k: getattr(ws, k, MISSING) for k in LINE}
check("a new line begins with none of the last one's operations, passages or failures",
      fresh == {"line_ops": [], "line_failed": [], "line_done": [], "line_world_failed": [], "passages": [], "line_untold": [],
                "unshown_ops": {}, "collecting": False, "last_crash": False}, fresh)
check("...each list its own (none shared with another field)", len({id(fresh[k]) for k in LINE if isinstance(fresh[k], list)}) == 6)

g.session.close()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f753) An input keeps its count when an operation fails before the line's first commit (found by the audit, trace-save-4 and
trace-turn-4). A typed line is counted as it begins (new_input), and the count reaches the save with the first operation of the line
that stands. An operation that did not stand gave back the save's meta to take its clock back, and took the count with it while nothing
of the line had committed yet: when the line then went on (an act left waiting whose own operation failed, on the game's fault or the
model's; a board refresh that failed during the understanding; a question that could not be kept), its later operations were filed
under the previous input's count with dice drawn at the new one, the save kept the old count, and the same words typed next began
from the same key and drew the same operation ids, so the record held one id on two operations; a recording, which picks an input's
operations by its count, picked the input before's with them.
Held here: the count is the input's while it is open, whatever fails inside it, and reaches the save with whichever operation stands
first; it is given back at the input's close only when nothing of the input stood, so a line not taken (its first deed failed, or its
understanding) and typed again meets the same dice as before, and a pane command that did not stand gives its count back; a ruling the
model could not give, which fails no operation, is as it was.
Run: python tools/sim/input_count_753_test.py"""
import json
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
shown = simlib.quiet_console()
import config
from engine import act, clock, refusals
from llm.gateway import LLMError
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = "input_count_test"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = str(simlib.saves_path(NAME, "turns.jsonl"))
config.CRASH_LOG_PATH = str(simlib.saves_path(NAME, "crash.log"))
ws.enter("parth")


def count() -> tuple:
    return store.meta.steps, store.meta.story_steps


def saved() -> tuple:
    m = json.loads(store._kv_text("campaign"))
    return m["steps"], m["story_steps"]


def typed(text: str, plan=None) -> dict:
    """One line through the real turn: the count it began from, the key its dice began from, what the scene and the save hold after,
    and the operations it committed, as the save's record has them."""
    stub.plan = [dict(p) for p in (plan or [{"kind": "look"}])]
    before, n0 = count(), len(store.load_operations()["ops"])
    stood = ws.turn(text)
    record = store.load_operations()["ops"]
    return {"stood": stood, "before": before, "key": ws.actor.dice.key(), "memory": count(), "saved": saved(),
            "ops": [(o["kind"], o["steps"], o["id"]) for o in record[n0:]],
            "by_count": [(o["kind"], o["steps"], o["id"]) for o in record if o["steps"] == store.meta.steps],   # as a recording picks them
            "failed": [o.kind for o in ws.line_failed + ws.line_world_failed]}


def held(name: str, first: dict, again: dict, failed: str) -> None:
    """`first`: a line whose operation `failed` did not stand before anything of it committed, and which went on; `again`: the same
    words typed next."""
    given = (first["before"][0] + 1, first["before"][1] + 1)
    check(f"{name}: the {failed} operation did not stand, and the line went on and something of it stood",
          failed in first["failed"] and first["ops"], (first["failed"], first["ops"]))
    check("...every operation of it that stood is filed under the count the line was given", all(s == given[0] for _, s, _ in first["ops"]),
          (given, [(k, s) for k, s, _ in first["ops"]]))
    check("...the save keeps that count, as the scene does", first["saved"] == given and first["memory"] == given,
          (given, first["saved"], first["memory"]))
    check("...the operations a recording picks for the input by its count are the line's own, none of the input before",
          first["by_count"] == first["ops"], (first["by_count"], first["ops"]))
    check("...the same words typed next begin their dice from a key of their own", again["key"] != first["key"], (first["key"], again["key"]))
    shared = sorted({i for *_, i in first["ops"]} & {i for *_, i in again["ops"]})
    check("...and draw no operation id the line before drew", not shared, (shared, first["ops"], again["ops"]))


TRIES = int(act.A["pending"]["tries"])


def leave_act(words: str, tries_left: int = 1) -> None:
    """An act this character left waiting for its ruling (f596), with `tries_left` tries before it is told as come to nothing."""
    with ws.operation("test", "an act left waiting"):
        data = store.load_act_pending()
        data[ws.acting] = [{"words": words, "text": words, "place": ws.player.location, "minute": ws.minutes, "tries": TRIES - tries_left}]
        store.save_act_pending(data)


real_take_up = act.take_up


def take_up_raising(e):
    def take_up(ws_, who, text):
        raise e
    return take_up


typed("I look around.")                                    # a line played plainly first: the record is not empty

# ---- the case that found it: the waiting act's own operation fails on the game's own fault, and the line goes on
leave_act("I bar the cellar door with the bench.")
act.take_up = take_up_raising(RuntimeError("the waiting act's own operation faults"))
a1 = typed("I wait a while.", [{"kind": "wait", "summary": "waiting a while"}])
act.take_up = real_take_up
a2 = typed("I wait a while.", [{"kind": "wait", "summary": "waiting a while"}])
held("a waiting act's operation that faults (trace-save-4)", a1, a2, "act:waiting")

# ---- the same on the model's failure inside that operation (trace-turn-4)
leave_act("I wedge the gate shut.")
act.take_up = take_up_raising(LLMError("a required call inside the waiting act's operation failed"))
b1 = typed("I look around.")
act.take_up = real_take_up
b2 = typed("I look around.")
held("a waiting act's operation the model fails (trace-turn-4)", b1, b2, "act:waiting")

# ---- another of the kind: a board refresh that faults during the understanding, before the first action
ws.player.guild_rank = "F"
ws.advance(clock.minutes_until(ws.minutes, "morning"))
ws.enter("guild_house")
store.save_player(ws.player)
ws.ensure_board()
ws.advance(clock.MINUTES_PER_DAY * 3)                      # the board falls due
store.save_player(ws.player)


def refresh_faults(*a, **k):
    raise RuntimeError("the board's refresh faults")


ws.refresh_board = refresh_faults
c1 = typed("I look over the notices.")
del ws.refresh_board
c2 = typed("I look over the notices.")
held("a board refresh that faults during the understanding", c1, c2, "board")

# ---- and another: the question the understanding asks cannot be kept, and the line's tail stands
real_note = refusals.note


def note_faults(kind, *a, **k):
    if kind == "audit_failed":
        raise RuntimeError("the question could not be kept")
    return real_note(kind, *a, **k)


ws.audit_plan = lambda text, plan, raw_plan=None: ws.ask_back("audit_failed", text, "it could not be made sense of") or None
refusals.note = note_faults
d1 = typed("I do the thing with the other thing.")
refusals.note = real_note
del ws.audit_plan
ws.pending_clarify = None
d2 = typed("I do the thing with the other thing.")
held("a question that cannot be kept", d1, d2, "clarify")

# ---- a line not taken, nothing of it standing: its count is given back, and typed again it meets the same dice
ws.enter("parth")
store.save_player(ws.player)


def look_fails(intent, text):
    raise LLMError("the look could not be done")


ws.on_look = look_fails
e1 = typed("I look around once more.")
del ws.on_look
e2 = typed("I look around once more.")
check("a line whose first deed fails and of which nothing stands is not taken, and its count is given back",
      e1["stood"] is False and not e1["ops"] and e1["memory"] == e1["before"] and e1["saved"] == e1["before"], e1)
check("...typed again it meets the same dice", e2["key"] == e1["key"] and e2["before"] == e1["before"], (e1["key"], e2["key"]))


def interpret_fails(*a, **k):
    raise LLMError("the reading failed")


ws.interpret = interpret_fails
f1 = typed("I study the sky.")
del ws.interpret
f2 = typed("I study the sky.")
check("a line whose understanding fails is not taken, and its count is given back",
      f1["stood"] is False and not f1["ops"] and f1["memory"] == f1["before"] and f1["saved"] == f1["before"], f1)
check("...typed again it meets the same dice", f2["key"] == f1["key"], (f1["key"], f2["key"]))

# ---- a ruling the model could not give fails no operation: the waiting act's try is spent first, under the line's count, as before
working = stub.a_ActRuling


def no_ruling(u, k):
    raise LLMError("the model is down")


leave_act("I bar the cellar door with the bench.", tries_left=TRIES)
stub.a_ActRuling = no_ruling
h1 = typed("I look around.")
stub.a_ActRuling = working
given = (h1["before"][0] + 1, h1["before"][1] + 1)
check("a waiting act the model gives no ruling for spends a try in its own operation, which stands first, under the line's count",
      h1["ops"] and h1["ops"][0][0] == "act:waiting" and all(s == given[0] for _, s, _ in h1["ops"]) and not h1["failed"]
      and h1["saved"] == given and act.waiting(ws, ws.acting) and act.waiting(ws, ws.acting)[0]["tries"] == 1, h1)
with ws.operation("test", "the act let go"):
    store.save_act_pending({})

# ---- a pane command that does not stand gives its count back; the story's count it never moved
def command_faults(text):
    raise RuntimeError("the command faults")


before = count()
ws.command = command_faults
stood = ws.command_input("#inventory")
del ws.command
check("a pane command that does not stand gives its count back, and moves no story count", stood is False and count() == before
      and saved() == before, (before, count(), saved()))

# ---- one id, one operation, in the whole record
ids = [o["id"] for o in store.load_operations()["ops"]]
check("no operation id is in the save's record twice", len(ids) == len(set(ids)), sorted(i for i in set(ids) if ids.count(i) > 1))

g.close()
saves.drop(NAME)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

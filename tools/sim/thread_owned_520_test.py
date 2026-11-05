"""(f520) The serving and the operation belong to the thread that opened them.

Before f520 the serving of a restartable operation (engine/asked.py) was one value for the whole process: a call made on another thread
while the turn was inside an asked operation (the people written behind the scenes, npc/backfill.py, asking populate_place) entered the
turn's serving (its answer kept among the turn's, a Drift when the turn ran again) or blanked it while it asked; and the open operation
was read from any thread, so that call was counted as waiting inside the turn's transaction (operation.LEGACY) and filed under the
turn's operation (the recorder's and the audit's op, the ledger's stamp). Now a call on another thread sees neither.

The test runs one asked operation twice, in two fresh campaigns of the same seed: once alone, once with a background call made in the
middle of it (and made again when the operation runs again, as the body does). Both must commit the same answers and the same state.

Run: python tools/sim/thread_owned_520_test.py"""

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import simlib
stub = simlib.Stub("warrior", 20)
simlib.install(stub)
simlib.quiet_console()

from pydantic import create_model

from engine import asked, operation, recording
from llm import gateway
from storage import statehash

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


Read = create_model("Read", x=(str, ""))
real_begin = asked.begin


def run(with_thread: bool) -> dict:
    g = simlib.campaign(f"thread_owned_520_{'with' if with_thread else 'alone'}", cls="warrior", seed=20, location="parth")
    ws = g.scene
    ws.enter("parth")
    servings, seen = [], {"bg": [], "bg_errors": [], "bg_op": [], "bg_serving": [], "turn_serving": [], "bodies": 0}

    def keep(sv):
        if sv is not None and sv not in servings:
            servings.append(sv)
        real_begin(sv)

    def background():
        seen["bg_serving"].append(asked.serving())
        seen["bg_op"].append((operation.current(), recording._operation_id()))
        try:
            seen["bg"].append(gateway.generate("populate_place", "Write the people of this place.", "A lane.", Read, retries=0))
        except BaseException as e:                       # a Drift, a NeedAnswer, anything: the call is no part of the turn's operation
            seen["bg_errors"].append(repr(e))

    def body(op):
        seen["bodies"] += 1
        gateway.generate("interpret_action", "Read the line.", "I look around.", Read, retries=0)       # made inside, kept on the serving
        if with_thread:
            t = threading.Thread(target=background)
            t.start()
            t.join(10)
        seen["turn_serving"].append(asked.serving())
        gateway.generate("npc_conversation", "Answer them.", "Good day.", Read, retries=0)         # asked outside: the body runs again
        ws.player.character.coins += 1
        ws.store.save_player(ws.player)

    asked.begin = keep
    legacy0 = list(operation.LEGACY)
    try:
        op, _ = ws.asked_operation("probe", "I look around.", body)
        error = None
    except BaseException as e:
        op, error = None, repr(e)
    finally:
        asked.begin = real_begin
    out = {"state": op.state if op is not None else None, "error": error, "digest": statehash.digest(g.store)["all"],
           "answers": [[k for k, _r, _e in sv.answers] for sv in servings], "legacy_added": [t for t in operation.LEGACY if t not in legacy0],
           **seen}
    g.close()
    return out


alone = run(False)
with_bg = run(True)

check("alone, the asked operation commits after running again for its call asked outside", alone["state"] == "committed"
      and alone["error"] is None and alone["bodies"] == 2, alone)
check("with a call made on another thread in the middle of it, the operation still commits, with no Drift", with_bg["state"] == "committed"
      and with_bg["error"] is None and with_bg["bodies"] == alone["bodies"], {k: with_bg[k] for k in ("state", "error", "bodies")})
check("...the other thread's call is made, and answered, apart from it", len(with_bg["bg"]) == with_bg["bodies"] and with_bg["bg_errors"] == [],
      (len(with_bg["bg"]), with_bg["bg_errors"]))
check("...it never enters the turn's serving: the same answers, in the same order, as the operation alone",
      with_bg["answers"] == alone["answers"] and all("populate_place" not in str(a) for a in with_bg["answers"]),
      (with_bg["answers"], alone["answers"]))
check("...the turn's serving is never blanked on its thread", with_bg["turn_serving"] and all(s is not None for s in with_bg["turn_serving"]),
      with_bg["turn_serving"])
check("...and the other thread sees neither the serving nor the open operation (filed under none, the recorder's op empty)",
      with_bg["bg_serving"] and all(s is None for s in with_bg["bg_serving"]) and all(o is None and rid == "" for o, rid in with_bg["bg_op"]),
      (with_bg["bg_serving"], with_bg["bg_op"]))
check("...nor is it counted as waiting inside the turn's transaction", with_bg["legacy_added"] == alone["legacy_added"]
      and "populate_place" not in with_bg["legacy_added"], (with_bg["legacy_added"], alone["legacy_added"]))
check("...and the commit leaves the same state as the operation alone", with_bg["digest"] == alone["digest"], (with_bg["digest"], alone["digest"]))
check("the open operation is still the turn's own on its thread (a body reads it as before)", alone["state"] == "committed"
      and simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f463) The executor: a typed line is operations, each all-or-nothing with its record. A single-step line is four (the reading with its
first action, its passage (f464), the pulse, the tail); the hold keeps what an operation says until it commits and drops it when it does not; a
later step's failure leaves what stood standing (part) and the player reads which part; a first operation's failure takes the line as
before (none), the input's count with it; the write fence is armed for the life of a line; a pane command is an operation of its own; a
recording keeps each input's operations and replays them; the turn log says how much stood."""
import json
import pathlib
import shutil
import subprocess
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
from engine import failures, ledger
from llm.gateway import LLMError
from storage import statehash
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


g = simlib.campaign("executor_463", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/executor_463/turns.jsonl"
shown = simlib.quiet_console()


def ops_of_input():
    return [o for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


# ---- a whole line stands: four operations, each with its record; the input's count saved by the first; everything shown marked shown
stub.plan = [{"kind": "look"}]
shown.clear()
stood = ws.turn("I look around.")
kinds = [o["kind"] for o in ops_of_input()]
check("a single-step line is four operations: the reading with its first action, its passage (f464), the pulse, the tail",
      stood is True and kinds == ["line", "passage", "pulse", "tail"], (stood, kinds))
check("...the ones the scene kept, none failed", [o.kind for o in ws.line_ops] == kinds and not ws.line_failed and ws.line_done == ["look"], ws.line_done)
check("...the input's count was saved by the first operation that stood", json.loads(store._kv_text("campaign"))["steps"] == store.meta.steps)
check("...everything shown was released and marked shown", store.unshown() == {} and any(k == "narrate" for k, t in shown), shown[:3])
check("...and the fence is off between lines", store._armed is False and store._in_operation == 0 and store._depth == 0)

# ---- the hold: nothing an operation says reaches the page before it commits; a rolled-back one says nothing, writes nothing
shown.clear()
with ws.operation("test", "a test") as op:
    uc.note("held until the commit")
    ledger.add("gained", what="a pebble", facts={"what": "a pebble"})
    inside = list(shown)
check("a line said inside an operation waits for its commit, and the row carries the operation", inside == [] and ("note", "held until the commit") in shown
      and op.state == "committed" and op.lines == ["held until the commit"] and op.rows and op.rows[0]["op"] == op.id, (inside, shown, op.rows))
rec = store.find_operation(op.id)
check("...its record holds the row with its facts, and its entry is gone once shown", rec and rec["rows"][0]["facts"] == {"what": "a pebble"} and store.unshown() == {}, rec)
shown.clear()
d0 = statehash.digest(store)
coins0 = store.load_player().character.coins
with ws.operation("test", "a failing test") as op:
    uc.note("never shown")
    ledger.add("gained", what="nothing")
    ws.player.character.coins += 1000
    store.save_player(ws.player)
    raise LLMError("the model failed")
check("a rolled-back operation shows nothing, writes nothing and keeps no row", shown == [] and op.state == "rolled_back" and statehash.digest(store) == d0
      and store.find_operation(op.id) is None and not any(r.get("op") == op.id for r in ledger.ROWS) and ws.player.character.coins == coins0
      and store.load_player().character.coins == coins0, (shown, op.state, ws.player.character.coins, coins0))
check("...the fault is the model's, and the line is halted", ws.last_failure == "the model failed" and not ws.last_crash and ws.halted)
with ws.operation("test", "a crashing test") as op:
    raise KeyError("a fault of the game's")
check("the game's own fault is a rolled-back operation too, written down", op.state == "rolled_back" and ws.last_crash and ws.last_failure.startswith("KeyError"), ws.last_failure)

# ---- part: a later step fails; what stood stands, nothing after it is done, and the player reads which part
real_look = ws.on_look


def failing_wait(intent, text):
    raise LLMError("the wait's telling failed")


ws.on_wait = failing_wait
stub.plan = [{"kind": "look"}, {"kind": "wait"}]
shown.clear()
stood = ws.turn("I look around, then wait a while.")
kinds = [o["kind"] for o in ops_of_input()]
check("a line whose second step fails stands in part: the first action, the passage, the pulse and the tail commit; the second action does not",
      stood == "part" and kinds == ["line", "passage", "pulse", "tail"] and [o.kind for o in ws.line_failed] == ["action:wait"] and ws.line_done == ["look"],
      (stood, kinds, [o.kind for o in ws.line_failed], ws.line_done))
check("...the passage tells what stood", any(k == "narrate" for k, t in shown), shown[:3])
check("...and no row of the failed step remains", not any(r.get("op") == ws.line_failed[0].id for r in ledger.LAST))
script = ["I look around, then wait a while.", "quit"]
uc.ask = lambda *a, **k: script.pop(0) if script else "quit"
shown.clear()
ws.run()
del ws.on_wait
texts = [t for k, t in shown]
heads = [p.split("{")[0] for p in failures.F["part_stood"] if not p.startswith("{")]
check("the player reads which part stood, in the narrator's words", any("look" in t and any(t.startswith(h) for h in heads) for t in texts), texts[-4:])
rows = [json.loads(l) for l in pathlib.Path(config.TURN_LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
row = next((r for r in reversed(rows) if r.get("text") == "I look around, then wait a while."), None)
check("the turn log says how much stood, and why the rest did not", row and row.get("stood") == "part" and not row.get("rolled_back") and row.get("model_failed"), row)

# ---- none: the first operation fails; nothing is kept, not even the input's count
steps0 = store.meta.steps
saved0 = json.loads(store._kv_text("campaign"))["steps"]
n_ops0 = len(store.load_operations()["ops"])
coins0 = store.load_player().character.coins


def boom(text):
    ws.player.character.coins -= 5
    store.save_player(ws.player)
    raise LLMError("the reading failed")


ws.read_line = boom
stood = ws.turn("I do a thing.")
del ws.read_line
check("a line whose first operation fails is not taken: nothing kept, the input's count given back", stood is False and store.meta.steps == steps0
      and json.loads(store._kv_text("campaign"))["steps"] == saved0 and store.load_player().character.coins == coins0
      and ws.player.character.coins == coins0 and len(store.load_operations()["ops"]) == n_ops0, (stood, store.meta.steps, steps0))

# ---- the fence is armed for the life of a line
armed = {}


def spy_look(intent, text):
    armed["during"] = store._armed
    return real_look(intent, text)


ws.on_look = spy_look
stub.plan = [{"kind": "look"}]
ws.turn("I look.")
del ws.on_look
check("the write fence is armed while the line runs, and off after it", armed.get("during") is True and store._armed is False)

# ---- an intercepted line is one operation and the tail; a pane command is an operation of its own
stub.plan = [{"kind": "look"}]
stood = ws.turn("I head out the south gate")
kinds = [o["kind"] for o in ops_of_input()]
check("an intercepted line is the first operation whole, its passage, then the tail", stood is True and kinds == ["line", "passage", "tail"] and ws.player.location == "south_fields",
      (stood, kinds, ws.player.location))
script = ["#stats", "quit"]
uc.ask = lambda *a, **k: script.pop(0) if script else "quit"
ws.run()
kinds = [o["kind"] for o in ops_of_input()]
check("a pane command is an operation of its own", kinds == ["command:stats"], kinds)
g.close()

# ---- a recording keeps each input's operations, and the replay compares them
r = simlib.campaign("executor_463_rec", cls="warrior", seed=3, location="parth")
wr = r.scene
SCRIPT = ["I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
OUT = pathlib.Path("saves/executor_463_rec_out")
shutil.rmtree(OUT, ignore_errors=True)
r.session.record(folder=OUT)
stub.plan = [{"kind": "look"}]
wr.run()
r.close()
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("a recording keeps each input's operations: ids, kinds and rows", turns and [o["kind"] for o in turns[0]["operations"]] == ["line", "passage", "pulse", "tail"]
      and all(len(o["id"]) == 12 and "rows" in o for o in turns[0]["operations"]), turns[0].get("operations"))
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last = (out.stdout.strip().splitlines() or [""])[-1]
check("...and it replays in a child process, the operations compared", out.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
      (out.returncode, out.stdout[-300:], out.stderr[-300:]))
shutil.rmtree(OUT, ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
for n in ("executor_463", "executor_463_rec"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

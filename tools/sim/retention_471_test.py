"""(f471) Closing the bundle: the record keeps a capped window and a commit costs no more late than early; the turn log's rows carry the
line's operations and how each ended, and what was told at a load; the recorder's call rows carry the operation and the need; the
night's summary counts stand-ins, stood-without-a-passage, deferrals and recovered-on-load apart from hesitations; and the card
profile's estimate names the input whose required path exceeds the minute, ignoring an optional call's seconds."""
import gzip
import json
import pathlib
import shutil
import subprocess
import sys
import time
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
from core.interrupts import Interrupt
from engine import operation, turnlog
from llm.gateway import LLMError
from npc.models import NPC
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


NAME = "retention_471"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = f"saves/{NAME}/turns.jsonl"
SHOWN = simlib.quiet_console()

# ---- the record's window, and the cost of a commit late in it
keep = int(operation.RETENTION["operations"])
timings = {}
for i in range(300):
    t0 = time.perf_counter()
    with store.transaction():
        o = operation.begin("action:test", store.meta.steps, i, store.revision(), f"op {i}")
        store.commit_operation(o)
    operation.end("committed")
    store.mark_shown(o.id)
    if i in (9, 99, 299):
        timings[i] = time.perf_counter() - t0
rec = store.load_operations()
check("three hundred operations leave exactly retention.operations records, the newest", len(rec["ops"]) == keep and rec["ops"][-1]["text"] == "op 299" and rec["revision"] == 300,
      (len(rec["ops"]), keep, rec["revision"]))
check("...and the hundredth commit costs no more than the tenth within a bound", timings[99] <= 5 * timings[9] + 0.02 and timings[299] <= 5 * timings[9] + 0.02, timings)

# ---- three turns: stood, rolled back at the first operation, stood with a stand-in: three rows with their operations and states
real = simlib.below()                     # (f518) the stub answering now, taken before the wrapper goes in over it
FAIL = {"titles": set()}


def chat(**k):
    if k["format"].get("title") in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


failing = simlib.stand_in(chat=chat, embed=None, name="retention_471")
ws.enter("parth")
BOOM = {"on": False}
real_look = ws.on_look


def look(intent, text):
    if BOOM["on"]:
        raise LLMError("the look's call failed")
    return real_look(intent, text)


ws.on_look = look
SCRIPT = ["I look around.", "I look around again.", "I look around once more.", "quit"]


def ask(*a, **k):
    text = SCRIPT.pop(0) if SCRIPT else "quit"
    BOOM["on"] = text == "I look around again."
    FAIL["titles"] = {"Narration"} if text == "I look around once more." else set()
    return text


uc.ask = ask
stub.plan = [{"kind": "look"}]
ws.run()
rows = [json.loads(l) for l in pathlib.Path(config.TURN_LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
by = {r.get("text"): r for r in rows}
r1, r2, r3 = by.get("I look around."), by.get("I look around again."), by.get("I look around once more.")
check("a line that stood: its row names its operations, every one stood, the first action and its passage among them",
      r1 and r1.get("stood") == "all" and [o["kind"] for o in r1["ops"]][:2] == ["action:look", "passage"] and all(o["state"] == "stood" for o in r1["ops"]), r1 and r1.get("ops"))
check("a line rolled back at its first operation: the row says so, the operation named rolled back and nothing else of it",
      r2 and r2.get("rolled_back") and r2.get("stood") == "none" and [(o["kind"], o["state"]) for o in r2["ops"]] == [("action:look", "rolled_back")], r2 and r2.get("ops"))
check("a line told by a stand-in: the row names the passage stood in for among the operations that stood",
      r3 and r3.get("stood") == "all" and r3.get("stand_in") and any(o["kind"] == "passage" and o["state"] == "stand_in" for o in r3["ops"])
      and any(o["kind"] == "action:look" and o["state"] == "stood" for o in r3["ops"]) and r3.get("stand_ins") == ["passage"], r3 and r3.get("ops"))
check("...the ids on the rows are the record's", all(any(o["id"] == rec_["id"] for rec_ in store.load_operations()["ops"]) for o in r1["ops"]), r1["ops"][:2])
FAIL["titles"] = set()
ws.on_look = real_look

# ---- told at a load: the first row after it says how many
g.crash_after_commit("action:look")
try:
    ws.turn("I look at the sky.")
    stopped = False
except Interrupt:
    stopped = True
pending = len(store.unshown())
check("...the failing stand-in answered those turns, the narrations it failed among them", failing.live() and failing.src.calls["Narration"] >= 1,
      dict(failing.src.calls))
failing()
g.close()
check("the game stopped after the commit, its telling kept for the next load", stopped and pending == 1, (stopped, pending))
check("...and the failing stand-in is taken away, the stub answering again", not failing.live() and simlib.below().chat == stub.chat)
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth", fresh=False)
ws, store = g.scene, g.store
config.TURN_LOG_PATH = f"saves/{NAME}/turns.jsonl"
SCRIPT[:] = ["I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
OUT = pathlib.Path(f"saves/{NAME}_rec")
shutil.rmtree(OUT, ignore_errors=True)
g.session.record(folder=OUT)
stub.plan = [{"kind": "look"}]
ws.run()
rows = [json.loads(l) for l in pathlib.Path(config.TURN_LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
last = rows[-1]
check("the first row after a load counts what was told at it, once", ws.recovered_at_load == 1 and last.get("recovered") == 1 and last.get("text") == "I look around.", {k: last.get(k) for k in ("text", "recovered")})
g.close()

# ---- the recorder's call rows carry the operation and the need
calls = [json.loads(l) for l in gzip.open(OUT / "calls.jsonl.gz", "rt", encoding="utf-8") if l.strip()]
chats = [c for c in calls if c["kind"] == "chat" and c.get("input") == 1]
check("every recorded call carries its operation (empty outside any) and the line's need of it", chats and all("op" in c and "need" in c for c in chats)
      and any(c["task"] == "interpret_action" and c["op"] == "" and c["need"] == "required" for c in chats)
      and any(c["task"] == "narrate" and len(c["op"]) == 12 and c["need"] == "required" for c in chats), [(c["task"], c["op"], c["need"]) for c in chats])
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last_line = (out.stdout.strip().splitlines() or [""])[-1]
check("...and the recording replays, the recovery at the load compared", out.returncode == 0 and "inputs matched" in last_line, (out.returncode, out.stdout[-300:]))
shutil.rmtree(OUT, ignore_errors=True)

# ---- the night's summary counts the bundle's measures apart from hesitations
sys.path.insert(0, "tools")
import latency
night = [{"n": i + 1, "kind": "look", "seconds": 10.0, "chat_seconds": 5.0, "first_word": 2.0, "chat_calls": 2, "retries": 0, "failed_calls": 0, "background_calls": 0,
          "embed_calls": 0, "embed_seconds": 0.0, "hesitated": False, "required_seconds": 12.0, "budget_seconds": 14, "deferred": [], "dropped": [], "stand_ins": [], "recovered": 0}
         for i in range(14)]
night[3]["stand_ins"] = ["passage"]
night[5]["deferred"] = ["exchange"]
night[0]["recovered"] = 1
night[7]["required_seconds"] = 75.0
text = "\n".join(latency.turns_table(night))
check("a stub night's summary counts one stood without a passage, a deferral and a recovery apart from the failed turns (none)",
      "1 turns told by a stand-in, 1 of them stood without a passage" in text and "1 optional calls deferred" in text and "1 outcomes told at a load" in text
      and "over 60 s in 1 turns" in text and "| look | 14 |" in text and text.count("| 0 |") >= 1, text[-600:])

# ---- the card profile's estimate names the input over the minute and ignores an optional call's seconds
import card_profile as cp
folder = pathlib.Path(f"saves/{NAME}_synth")
shutil.rmtree(folder, ignore_errors=True)
folder.mkdir(parents=True)
(folder / "meta.json").write_text(json.dumps({"model": "stub"}), encoding="utf-8")
msgs = [{"role": "system", "content": "s" * 4000}, {"role": "user", "content": "u" * 4000}]
with gzip.open(folder / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
    f.write(json.dumps({"i": 0, "input": 1, "kind": "chat", "title": "Narration", "task": "narrate", "request": {"messages": msgs}, "answer": "z" * 20000, "seconds": 1.0}) + "\n")
    f.write(json.dumps({"i": 1, "input": 2, "kind": "chat", "title": "Exchange", "task": "exchange", "request": {"messages": msgs}, "answer": "z" * 20000, "seconds": 1.0}) + "\n")
    f.write(json.dumps({"i": 2, "input": 2, "kind": "chat", "title": "ActionPlan", "task": "interpret_action", "request": {"messages": msgs}, "answer": "z" * 100, "seconds": 1.0}) + "\n")
est = dict(cp.estimate_inputs(folder))
check("the estimate names the input whose required path exceeds the minute and leaves an optional call's seconds out", est.get(1, 0) > 60 and 0 < est.get(2, 0) < 60, est)
shutil.rmtree(folder, ignore_errors=True)

check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

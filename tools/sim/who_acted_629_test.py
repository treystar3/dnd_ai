"""(f629) Every log and record of a line names who acted (docs/design/20_phase3_plan.md). The one source is the actor bound
while a scene's entry runs (engine/actor.py who): the operation takes it as it opens, and its record in the save, its
presentation entry, the recording's input row, the turn log, the model call log, the audit, a refusal and a fault each carry it.
Three of them (the call log, the model gateway's refusals, the crash log) are written where there is no scene to ask.
Held here on a character whose id is not the save's usual one, so a row that says "player" by habit is caught:
- with no actor bound a row names no one, and so does one written on a thread no entry runs on;
- a line played through the game's own loop leaves the character's id on every row it writes.
tools/sim/log_rows_628_test.py holds each row's whole shape.
Run: python tools/sim/who_acted_629_test.py"""
import json
import shutil
import sys
import threading
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
restore = simlib.install(stub)
import config
from core import paths
import ui.console as console
from engine import actor, crashlog, operation, refusals, turnlog
from llm import audit

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

BASE = paths.written("saves/who_acted_629")     # (f779) where the game writes the logs named under it
OUT = Path("saves/who_acted_629_rec")
for folder in (BASE, OUT):
    shutil.rmtree(folder, ignore_errors=True)
g = simlib.campaign("who_acted_629", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
held = {k: getattr(config, k) for k in ("TURN_LOG_PATH", "LOG_PATH", "REFUSALS_LOG_PATH", "REFUSALS_LOG", "CRASH_LOG_PATH")}
config.TURN_LOG_PATH, config.LOG_PATH = str(BASE / "turns.jsonl"), str(BASE / "calls.jsonl")
config.REFUSALS_LOG_PATH, config.REFUSALS_LOG, config.CRASH_LOG_PATH = str(BASE.resolve() / "refusals.jsonl"), True, str(BASE.resolve() / "crash.log")
AUDIT = ("_path", "_count", "_turn", "_turn_written", "_system_seen", "_first_attempt", "_full")
audit_was = {k: getattr(audit, k) for k in AUDIT}
audit_was.update(_system_seen=dict(audit._system_seen), _first_attempt=dict(audit._first_attempt))
BASE.mkdir(parents=True, exist_ok=True)
(BASE / "audit.md").write_text("", encoding="utf-8")
held["AUDIT_LOG"], config.AUDIT_LOG, audit._path = config.AUDIT_LOG, True, BASE / "audit.md"
simlib.quiet_console()
rows = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(p).exists() else []

ws.player.character.id = "vessa"
WHO = "vessa"

# ---- the one source
check("with no actor bound no one acted", actor.who() == "" and actor.current() is actor.PROCESS)
with actor.bind(ws.actor):
    inside = actor.who()
    seen = []
    t = threading.Thread(target=lambda: seen.append(actor.who()))
    t.start()
    t.join()
check("while a scene's actor is bound its character acted", inside == WHO, inside)
check("...on that thread: one no entry runs on names no one", seen == [""], seen)

# ---- with none bound: an operation, a refusal and a fault name no one
with ws.operation("test", "outside every entry") as loose:
    pass
refusals.note("unclear", "I flurble the wicket", why="no reading of it", place="parth", turn=4)
try:
    raise ValueError("a fault with no one acting")
except ValueError as e:
    nobody = crashlog.record(e, "outside a turn")
check("an operation opened with none bound names no one, and so does a refusal filed then", loose.actor == "" and loose.record()["actor"] == ""
      and rows(BASE / "refusals.jsonl")[-1]["actor"] == "", (loose.actor, rows(BASE / "refusals.jsonl")[-1:]))
check("...and a fault filed then says nothing of who (the crash log keeps only what is not empty)", "actor" not in nobody
      and "  actor:" not in (BASE / "crash.log").read_text(encoding="utf-8"), nobody)

# ---- a line played through the game's own loop, recorded
SCRIPT = ["I look around.", "quit"]
console.put("ask", lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit")
entries, opened = [], []
real_put, real_begin = store._put, operation.begin


def watching_put(key, text, *a, **k):
    if key == "presentation":
        entries.extend(json.loads(text).values())
    return real_put(key, text, *a, **k)


def watching_begin(*a, **k):
    op = real_begin(*a, **k)
    opened.append(op)
    return op


store._put, operation.begin = watching_put, watching_begin
g.session.record(folder=OUT)
ws.enter("parth")                                          # the harness's own step, outside every entry: what it writes names no one
outside = len(rows(BASE / "calls.jsonl"))
stub.plan = [{"kind": "look"}]
real_step = ws.run_step


def step(i, plan, text):                                  # inside the line: a refusal from where there is no scene, and a fault
    refusals.note("guarded", "narrate", "a word the gate refused")
    try:
        raise ValueError("a fault inside a line")
    except ValueError as e:
        step.fault = crashlog.record(e, "turn", text=text)
    return real_step(i, plan, text)


ws.run_step = step
try:
    ws.run()
finally:
    del ws.run_step
    store._put, operation.begin = real_put, real_begin
ops = store.load_operations()["ops"]
g.close()
audited = (BASE / "audit.md").read_text(encoding="utf-8")
config.AUDIT_LOG = held["AUDIT_LOG"]
for k, v in audit_was.items():
    setattr(audit, k, v)

played = [o for o in opened if o.kind != "test"]
check("(the line opened operations, the world's own among them, and they were saved)", len(played) >= 3 and any(o.kind.startswith("world") for o in played)
      and len(ops) >= 3, ([o.kind for o in played], len(ops)))
check("every operation the line opened took the acting character as it opened, the world's own too", all(o.actor == WHO for o in played),
      [(o.kind, o.actor) for o in played if o.actor != WHO])
check("...its record in the save names them", all(o.get("actor") == WHO for o in ops if o["kind"] != "test"), [(o["kind"], o.get("actor")) for o in ops])
check("...and its presentation entry", entries and all(e.get("actor") == WHO for e in entries if e["kind"] != "test"),
      [(e["kind"], e.get("actor")) for e in entries][:4])
turns, calls = rows(BASE / "turns.jsonl"), rows(BASE / "calls.jsonl")
check("every row of the turn log names them", turns and all(r.get("actor") == WHO for r in turns), [(r.get("handled_by"), r.get("actor")) for r in turns])
check("every call the line made names them in the model call log, written where there is no scene to ask",
      len(calls) > outside and all(c.get("actor") == WHO for c in calls[outside:]), [(c.get("task"), c.get("actor")) for c in calls])
check("...and a call made outside every entry names no one", outside and all(c.get("actor") == "" for c in calls[:outside]),
      [(c.get("task"), c.get("actor")) for c in calls[:outside]])
heads = [l for l in audited.splitlines() if l.startswith("## #")]
check("every audited call is headed the same way: the line's with them, the one outside with no actor", len(heads) == len(calls)
      and all(h.endswith(f" · actor {WHO}") for h in heads[outside:]) and all(h.endswith(" · no actor") for h in heads[:outside]), heads[:3])
inputs = rows(OUT / "inputs.jsonl")
check("the recording's input rows name whose line it was", inputs and all(r.get("actor") == WHO for r in inputs), inputs[:2])
inside_refusal = [r for r in rows(BASE / "refusals.jsonl") if r["kind"] == "guarded"]
check("a refusal filed inside the line with no scene to ask names them", inside_refusal and inside_refusal[-1]["actor"] == WHO, inside_refusal[-1:])
crash = (BASE / "crash.log").read_text(encoding="utf-8")
check("a fault filed inside the line names them, in its entry and in the crash log", getattr(step, "fault", {}).get("actor") == WHO
      and f"  actor: {WHO}\n" in crash, (getattr(step, "fault", None), crash[-300:]))
check("after the line no one is acting", actor.who() == "")
with actor.bind(ws.actor):                                 # a pane's button that changed something: the turn log's third kind of row
    turnlog.begin()
    turnlog.end(command={"turn": 2, "text": "#goto guild_house", "changed": ["place"]})
button = rows(BASE / "turns.jsonl")[-1]
check("a pane command's row names them too", button["handled_by"] == "command" and button["actor"] == WHO, button)

old = operation.Operation(id="o1", kind="line", steps=3, index=0, revision_seen=7, text="a line")
check("an operation made with no name has none", old.actor == "" and old.record()["actor"] == "")
del refusals.SESSION[:], crashlog.SESSION[:]

for k, v in held.items():
    setattr(config, k, v)
restore()
for folder in (BASE, OUT):
    shutil.rmtree(folder, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

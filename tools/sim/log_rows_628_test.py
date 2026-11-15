"""(f628) What each log and record holds of a line, pinned before phase 3 adds who acted to them (docs/design/20_phase3_plan.md
f629). Two lines are played through the game's own loop and recorded, one that stands and one whose reading fails every try, and
the rows they leave are read: the turn log, the model call log, the audit, the operation's record in the save, its presentation
entry, and the recording's input and turn rows. A refusal and a fault are filed the way the game files them. Each is held to the fields it has,
and the three kept recordings to theirs. Each names who acted (f629; tools/sim/who_acted_629_test.py holds whose name it is); the
kept recordings gain the field at the one re-record (f640).
Run: python tools/sim/log_rows_628_test.py"""
import json
import re
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
restore = simlib.install(stub)
import config
import ui.console as console
from engine import crashlog, operation, refusals, turnlog
from llm import audit
from llm.backend import Failure

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

BASE = Path("saves/log_rows_628")
OUT = Path("saves/log_rows_628_rec")
for folder in (BASE, OUT):
    shutil.rmtree(folder, ignore_errors=True)
g = simlib.campaign("log_rows_628", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
held = {k: getattr(config, k) for k in ("TURN_LOG_PATH", "LOG_PATH", "REFUSALS_LOG_PATH", "REFUSALS_LOG", "CRASH_LOG_PATH")}
config.TURN_LOG_PATH, config.LOG_PATH = str(BASE / "turns.jsonl"), str(BASE / "calls.jsonl")
config.REFUSALS_LOG_PATH, config.REFUSALS_LOG, config.CRASH_LOG_PATH = str(BASE.resolve() / "refusals.jsonl"), True, str(BASE.resolve() / "crash.log")
AUDIT = ("_path", "_count", "_turn", "_turn_written", "_system_seen", "_first_attempt", "_full")
audit_was = {k: getattr(audit, k) for k in AUDIT}
audit_was.update(_system_seen=dict(audit._system_seen), _first_attempt=dict(audit._first_attempt))
BASE.mkdir(parents=True, exist_ok=True)
(BASE / "audit.md").write_text("", encoding="utf-8")
held["AUDIT_LOG"], config.AUDIT_LOG, audit._path = config.AUDIT_LOG, True, BASE / "audit.md"     # the suite keeps the audit off; this run's goes here
simlib.quiet_console()

FAIL = {"on": False}

def failing_chat(**k):
    if FAIL["on"] and k["format"].get("title") == "ActionPlan":
        raise Failure("unreachable", "the model is not there")
    return stub.chat(**k)


fail_held = simlib.stand_in(chat=failing_chat, embed=None)
SCRIPT = ["I look around.", "I look around again.", "quit"]
console.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
entries = []                                              # each presentation entry as the save was handed it
real_put = store._put


def watching_put(key, text, *a, **k):
    if key == "presentation":
        entries.extend(json.loads(text).values())
    return real_put(key, text, *a, **k)


store._put = watching_put
g.session.record(folder=OUT)
ws.enter("parth")
stub.plan = [{"kind": "look"}]
real_turn = ws.turn


def staged_turn(text):
    FAIL["on"] = "again" in text
    return real_turn(text)


ws.turn = staged_turn
ws.run()
ws.turn = real_turn
store._put = real_put
ops = store.load_operations()["ops"]
g.close()
fail_held()
audited = (BASE / "audit.md").read_text(encoding="utf-8")
config.AUDIT_LOG = held["AUDIT_LOG"]
for k, v in audit_was.items():
    setattr(audit, k, v)

rows = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(p).exists() else []
turns, calls = rows(BASE / "turns.jsonl"), rows(BASE / "calls.jsonl")
stood = next((r for r in turns if r.get("stood") == "all" and r.get("text") == "I look around."), None)
failed = next((r for r in turns if r.get("rolled_back")), None)

# ---- the turn log
check("(a line that stood and a line that failed each left their row in the turn log)", stood is not None and failed is not None,
      [(r.get("text"), r.get("stood"), r.get("rolled_back")) for r in turns])
EVERY_TURN = {"time", "turn", "actor", "handled_by", "text", "started", "turn_seconds", "shown"}
check("a line's last row says when, which turn, who acted, what took it, what was typed, when it began, how long it took and what was shown",
      stood is not None and EVERY_TURN <= set(stood), stood and sorted(EVERY_TURN - set(stood)))
check("...a line nothing took has the same but its turn, and says nothing recorded it", failed is not None
      and EVERY_TURN - {"turn"} <= set(failed) and "turn" not in failed and failed["handled_by"] == "unrecorded",
      failed and (sorted(EVERY_TURN - set(failed)), failed.get("handled_by")))
check("...a line that stood names its operations, each with its id, kind, index and how it ended", stood is not None and stood.get("ops")
      and all(set(o) == {"id", "kind", "index", "state"} for o in stood["ops"]), stood and stood.get("ops"))
check("...each thing shown is its kind and its words", stood is not None and stood["shown"]
      and all(set(s) == {"kind", "text"} and s["kind"] in set(turnlog.SHOWN_KINDS.values()) for s in stood["shown"]), stood and stood["shown"][:2])
check("...a line whose reading failed says the model failed, and that nothing of it stood", failed is not None
      and failed.get("model_failed") and failed.get("stood") == "none" and "crashed" not in failed,
      failed and {k: failed.get(k) for k in ("model_failed", "stood", "crashed")})
check("every row of the turn log names who acted", all(r.get("actor") == "player" for r in turns), [r.get("actor") for r in turns])

# ---- the model call log
EVERY_CALL = {"time", "turn", "actor", "task", "model", "attempt", "seconds", "messages", "raw", "error"}
check("(the two lines left their calls in the call log)", len(calls) >= 3, len(calls))
check("every call's row says when, the turn it served, who it was made for, its task, the model, the try, the seconds, what was sent, the answer and the error",
      calls and all(EVERY_CALL <= set(c) for c in calls), [sorted(EVERY_CALL - set(c)) for c in calls if not EVERY_CALL <= set(c)][:3])
check("...a try that failed carries its error, one that was taken carries none", any(c["error"] for c in calls) and any(c["error"] is None for c in calls))
check("...the line's calls for its character, a call made outside every entry for no one", {c["actor"] for c in calls} == {"player", ""}
      and all(c["actor"] == "player" for c in calls if c["task"] in ("interpret_action", "narrate")), [(c["task"], c["actor"]) for c in calls])

# ---- the audit
heads = [l for l in audited.splitlines() if l.startswith("## #")]
HEAD = re.compile(r"^## #\d+ · [a-z_]+ · attempt \d+ · \d+\.\ds(?: · [^·]+)? · (?:operation [0-9a-f]+ \([^)]+\)|outside any operation) · (?:actor \S+|no actor)$")
check("(the two lines left their calls in the audit)", len(heads) >= 3, len(heads))
check("every audited call is headed by its number, task, try, seconds, the operation it served and who it was made for", heads and all(HEAD.match(h) for h in heads),
      [h for h in heads if not HEAD.match(h)][:3])
check("...under the turn it belongs to, with the line typed", '# Turn ' in audited and '"I look around."' in audited,
      [l for l in audited.splitlines() if l.startswith("# ")][:4])
check("...with why the call was made and whether its answer was taken", audited.count("**Why:**") == len(heads) == audited.count("**Verdict:**"))

# ---- the operation in the save, and its presentation entry
op = operation.Operation(id="o1", kind="line", steps=3, index=0, revision_seen=7, text="a line")
check("an operation's record holds its id, kind, input, place in the line, text, rows and who acted, and nothing else",
      set(op.record()) == {"id", "kind", "steps", "index", "text", "rows", "actor"}, sorted(op.record()))
check("...the save keeps it with the revision it made", ops and all(set(o) == {"id", "kind", "steps", "index", "text", "rows", "actor", "revision"} for o in ops),
      ops and sorted(ops[-1]))
check("an operation's presentation entry holds its lines, its input, its kind, the calls that told it and whose page they are for",
      entries and all(set(e) == {"lines", "steps", "kind", "calls", "actor"} for e in entries), entries and sorted(entries[-1]))

# ---- a refusal and a fault, filed as the game files them
refusals.note("unclear", "I flurble the wicket", why="no reading of it", place="parth", turn=4, asked="What do you mean to do?")
refusal = rows(BASE / "refusals.jsonl")
check("a refusal's row says when, the turn, who acted, its kind, the line, why, where and what was asked back",
      refusal and set(refusal[-1]) == {"time", "turn", "actor", "kind", "text", "why", "place", "asked"}, refusal and sorted(refusal[-1]))
try:
    raise ValueError("a fault of the game's own")
except ValueError as e:
    entry = crashlog.record(e, "turn", text="I look around.", place="parth", nothing="")
crash = (BASE / "crash.log").read_text(encoding="utf-8") if (BASE / "crash.log").exists() else ""
check("a fault's entry says when, where in the game and the error, with what it was given that is not empty",
      set(entry) == {"time", "where", "error", "text", "place"} and entry["error"] == "ValueError: a fault of the game's own", entry)
check("...and the crash log holds it as a headed entry with its traceback", f"{entry['time']}  turn: ValueError: a fault of the game's own" in crash
      and "  text: I look around.\n" in crash and "Traceback" in crash, crash[:200])
check("filed outside every entry, the refusal names no one and the fault's entry leaves who out with the rest that is empty",
      refusal[-1]["actor"] == "" and "actor" not in entry)
del refusals.SESSION[:], crashlog.SESSION[:]

# ---- a recording's rows: the one just made, and the three kept
INPUT = {"i", "main", "text", "turn", "steps"}            # the kept recordings', until the one re-record (f640)
TURN = {"i", "turn", "steps", "state", "outcomes", "operations", "presented", "shown", "lines", "shown_text"}


def recording(folder: Path, inputs=INPUT) -> list:
    wrong = []
    ins, tns = rows(folder / "inputs.jsonl"), rows(folder / "turns.jsonl")
    if not ins or not tns:
        return [f"{folder.name}: no rows"]
    wrong += [f"{folder.name} input {r.get('i')}: {sorted(set(r) ^ inputs)}" for r in ins if set(r) != inputs]
    wrong += [f"{folder.name} turn {r.get('i')}: {sorted((set(r) - {'rows'}) ^ TURN)}" for r in tns if set(r) - {"rows"} != TURN]
    wrong += [f"{folder.name} turn {r.get('i')}: an operation with {sorted(o)}" for r in tns for o in r["operations"] if set(o) != {"id", "kind", "rows"}]
    return wrong


check("the recording just made holds a turn row of the kept shape, and an input row that says whose line it was besides",
      not recording(OUT, INPUT | {"actor"}), recording(OUT, INPUT | {"actor"})[:4])
told = [line for r in rows(OUT / "turns.jsonl") for line in r["shown_text"]]
check("what the turn log says was shown for the line that stood is what the recording kept as shown (the tap and the recorder saw the same)",
      stood is not None and all(any(s["text"] in line or line in s["text"] for line in told) for s in stood["shown"]),
      stood and ([s["text"][:60] for s in stood["shown"]], [l[:60] for l in told][:6]))
kept = [w for name in ("stub_short", "stub_party", "stub_fight") for w in recording(Path("data/replay/sessions") / name)]
check("the three kept recordings hold the same shape, every row of them", not kept, kept[:4])

for k, v in held.items():
    setattr(config, k, v)
restore()
for folder in (BASE, OUT):
    shutil.rmtree(folder, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

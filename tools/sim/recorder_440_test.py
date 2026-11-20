"""(f440) A recording of a play session, kept so the real turn can replay it (the rebuild's Stage 1): the save as the session opened,
every input (a question answered mid-turn and a pane's command included), every model call in order with its request in full and its
answer or its failure, and after each input the state's fingerprint, what the turn recorded and a hash of what the player was shown.
The recorder wraps whatever model client and console are installed, puts them back when it closes, makes the session strict while it
records, and keeps only the newest recordings."""
import json, random, shutil, sqlite3, sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 40)
simlib.install(stub)
import config
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    uc.put(fn, lambda *a, **k: None)
uc.put("panel", lambda name, data: False)
from engine import recording, streams
from storage import statehash
from storage.campaign import CampaignStore

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SAVE = "recorder_440_test"
OUT = simlib.saves_path("recorder_440_out")
shutil.rmtree(OUT, ignore_errors=True)
game = simlib.campaign(SAVE, seed=40, turn=1, minutes=480)                 # (f450) the suite's one way to open a campaign
store = game.store
start = statehash.digest(store)

fail = {"on": False}
real = simlib.below()                               # (f518) the stub answering now, taken before the wrapper goes in over it
def chat(**k):
    if fail["on"] and k["format"].get("title") == "ActionPlan":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
h = simlib.stand_in(chat=chat, embed=None, name="recorder_440")
SCRIPT = [("I look around.", [{"kind": "look"}]), ("#stats", None), ("I wait a while.", [{"kind": "wait"}]),
          ("I look around again.", [{"kind": "look"}]), ("I wait.", [{"kind": "wait"}])]
state = {"n": 0}
def ask(*a, main=False, **k):
    if not main:
        return "yes"
    if state["n"] >= len(SCRIPT):
        return "quit"
    text, plan = SCRIPT[state["n"]]
    state["n"] += 1
    fail["on"] = state["n"] == 4                     # the fourth line's turn fails and rolls back
    if plan:
        stub.plan = plan
    return text
uc.put("ask", ask); ask_before = ask
ws = game.scene
from llm import backend
rec = recording.Recorder(store, folder=OUT).install()
check("a recording session is strict while it records, its layer on the model interface and the source untouched",
      streams.STRICT is True and rec._layer in backend.layers() and h.live() and h.src.chat_fn is chat)
ws.run()
folder = rec.close()
check("...and its layer taken off and the console put back when it closes", rec._layer not in backend.layers() and h.live()
      and h.src.chat_fn is chat and uc.now("ask") is ask_before and streams.STRICT is False)

# ---- what was kept
meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
check("meta: the seed, the data hash, the model, the version and the state the session opened in",
      meta["seed"] == 40 and meta["data"] == statehash.data_hash() and meta["words"] == statehash.words_hash()     # (f718) both digests
      and meta["model"] == config.MODEL and meta["start"] == start, meta.keys())
db = sqlite3.connect(OUT / "start.db")
check("start.db is the save as it opened", db.execute("SELECT count(*) FROM kv").fetchone()[0] > 0)
db.close()
copy = simlib.saves_path("recorder_440_copy"); shutil.rmtree(copy, ignore_errors=True); copy.mkdir(parents=True)
shutil.copy(OUT / "start.db", copy / "campaign.db")
reopened = CampaignStore.open_or_create("recorder_440_copy")
check("...and reads back to the same state the session opened in", statehash.digest(reopened) == start)
reopened.close(); shutil.rmtree(copy, ignore_errors=True)
inputs = [json.loads(l) for l in (OUT / "inputs.jsonl").read_text(encoding="utf-8").splitlines()]
mains = [r["text"] for r in inputs if r["main"]]
check("every input is kept, the pane's command and the line said to quit included", mains == [t for t, _ in SCRIPT] + ["quit"], mains)
calls = recording.read_calls(OUT)
check("every model call is kept in order, its request in full", calls and [c["i"] for c in calls] == list(range(len(calls)))
      and all(c["req"] and "messages" in c["request"] for c in calls), len(calls))
check("...each one answered by the test's own stand-in, under the recorder's layer",
      h.src.calls["ActionPlan"] >= 4 and sum(h.src.calls.values()) == len(calls), (dict(h.src.calls), len(calls)))
check("...with its answer", any(c.get("answer") and c["title"] == "ActionPlan" for c in calls))
check("...and a failed one with the failure, so a replay can fail it the same way",
      any((c.get("error") or {}).get("kind") == "server" and c["title"] == "ActionPlan" for c in calls))
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("after each input, the state's fingerprint and what was shown", len(turns) == len(mains)
      and all(t["state"]["all"] and t["shown"] for t in turns), len(turns))
store.close()
check("the last fingerprint is the save as the session left it",
      turns[-1]["state"] == statehash.digest(CampaignStore.open_or_create(SAVE)))

# ---- only the newest are kept
recording.FOLDER = simlib.saves_path("recorder_440_many")
shutil.rmtree(recording.FOLDER, ignore_errors=True)
for i in range(config.RECORD_KEEP + 2):
    d = recording.FOLDER / f"r{i}"
    d.mkdir(parents=True)
    (d / "meta.json").write_text("{}", encoding="utf-8")
    import os, time
    os.utime(d / "meta.json", (time.time() + i, time.time() + i))
recording.prune()
left = sorted(p.name for p in recording.FOLDER.iterdir())
check(f"only the newest {config.RECORD_KEEP} recordings are kept", left == [f"r{i}" for i in range(2, config.RECORD_KEEP + 2)], left)

# ---- (f783) a close refused at one of its writes still takes the recorder off, and makes every later write (TASK_FAILURE-14)
from engine import crashlog
config.CRASH_LOG_PATH = str(simlib.saves_path("recorder_440_logs", "crash.log"))     # the faults this part makes stay out of logs/
CONSOLE = {n: uc.channel().get(n) for n in ("ask",) + recording.STORY}
closing = simlib.campaign("recorder_440_close", seed=41)
WRITES = ("row", "inputs", "calls", "turns", "meta")
WHAT = {"row": "the last input's row (the disk full)", "inputs": "inputs.jsonl's close (the disk full at its flush)",
        "calls": "the call log's close", "turns": "turns.jsonl's close", "meta": "meta.json (a folder in its place)"}


class Refused:
    """A log the disk refuses: its write raises, or its close (the flush it makes) does; the file itself is closed either way."""
    def __init__(self, f, fault, at):
        self.f, self.fault, self.at = f, fault, at

    def write(self, s):
        if self.at == "write":
            raise self.fault
        return self.f.write(s)

    def flush(self):
        self.f.flush()

    def close(self):
        self.f.close()
        if self.at == "close":
            raise self.fault


def refused_at(broken: tuple, folder: Path):
    """A recorder over its own folder with one line typed and its row still to write, closed with each write named in `broken`
    refused. Returns the recorder, its three logs as opened, the faults put in (None for meta.json's) and what the close raised."""
    shutil.rmtree(folder, ignore_errors=True)
    rec = recording.Recorder(closing.store, folder=folder).install()
    uc.channel().get("ask")(main=True)                  # one line typed: its row is written as the recorder closes
    logs = {"inputs": rec.inputs, "calls": rec.calls, "turns": rec.turns}
    faults = {}
    for at in broken:
        if at == "meta":
            faults[at] = None
            (folder / "meta.json").unlink()
            (folder / "meta.json").mkdir()                # meta.json cannot be written: a folder stands in its place
            continue
        faults[at] = OSError(28, f"No space left on device ({at})")
        if at == "row":
            rec.turns = Refused(rec.turns, faults[at], "write")
        else:
            setattr(rec, at, Refused(logs[at], faults[at], "close"))
    try:
        rec.close()
        got = None
    except BaseException as e:
        got = e
    return rec, logs, faults, got


def written(rec, logs) -> dict:
    """What each write of the close left: the last input's row in turns.jsonl, each log closed, meta.json with its count of overlaps."""
    meta = rec.dir / "meta.json"
    return {"row": len((rec.dir / "turns.jsonl").read_text(encoding="utf-8").splitlines()) == 1,
            **{at: f.closed for at, f in logs.items()},
            "meta": meta.is_file() and "overlapped" in json.loads(meta.read_text(encoding="utf-8"))}


def taken_off(rec) -> bool:
    return (rec._layer not in backend.layers() and rec.unwrap is None and rec.closed and streams.STRICT is False
            and all(uc.channel().get(n) == f for n, f in CONSOLE.items()))


def tidy(rec, logs) -> None:
    """What a close left in place taken off by hand, so the next case starts clean: the close itself is what is checked."""
    if rec.unwrap is not None:
        rec.unwrap()
        rec.unwrap = None
    for ch, n, fn in reversed(rec.undo):
        ch.set(n, fn)
    rec.undo, rec.closed, streams.STRICT = [], True, False
    for f in logs.values():
        f.close()


folders = [simlib.saves_path("recorder_440_logs")]
for k, at in enumerate(WRITES):
    folders.append(simlib.saves_path(f"recorder_440_close_{k}"))
    rec, logs, faults, got = refused_at((at,), folders[-1])
    raised = (isinstance(got, OSError) and str(got.filename or "").endswith("meta.json")) if at == "meta" else got is faults[at]
    done, off = written(rec, logs), taken_off(rec)
    later = [w for w in WRITES[k + 1:] if not done[w]]
    check(f"(f783) a recorder's close refused at {WHAT[at]}: that error is raised, the recorder is still taken off (its layer, the "
          "console's wraps, the strict session), and every later write is still made", raised and off and not later, (got, off, later))
    tidy(rec, logs)
folders.append(simlib.saves_path("recorder_440_close_two"))
since = list(crashlog.SESSION)
rec, logs, faults, got = refused_at(("row", "meta"), folders[-1])
wheres = [e["where"] for e in crashlog.SESSION if all(e is not s for s in since)]
done = written(rec, logs)
check("(f783) refused at the last input's row and again at meta.json: the first is the error raised, the second is written down once "
      "under meta.json's name, and the three logs are closed", got is faults["row"] and taken_off(rec) and len(wheres) == 1
      and "meta.json" in wheres[0] and all(done[w] for w in logs), (got, wheres, done))
tidy(rec, logs)
closing.close()
folders.append(simlib.saves_path("recorder_440_close"))

for p in (str(simlib.saves_path(SAVE)), OUT, recording.FOLDER, *folders):
    shutil.rmtree(p, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

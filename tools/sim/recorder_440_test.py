"""(f440) A recording of a play session, kept so the real turn can replay it (the rebuild's Stage 1): the save as the session opened,
every input (a question answered mid-turn and a pane's command included), every model call in order with its request in full and its
answer or its failure, and after each input the state's fingerprint, what the turn recorded and a hash of what the player was shown.
The recorder wraps whatever model client and console are installed, puts them back when it closes, makes the session strict while it
records, and keeps only the newest recordings."""
import gzip, json, random, shutil, sqlite3, sys, types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 40)
simlib.install(stub)
import config
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import recording, streams
from llm import gateway
from storage import statehash
from storage.campaign import CampaignStore

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SAVE = "recorder_440_test"
OUT = Path("saves/recorder_440_out")
shutil.rmtree(OUT, ignore_errors=True)
game = simlib.campaign(SAVE, seed=40, turn=1, minutes=480)                 # (f450) the suite's one way to open a campaign
store = game.store
start = statehash.digest(store)

fail = {"on": False}
real = gateway._client
def chat(**k):
    if fail["on"] and k["format"].get("title") == "ActionPlan":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
gateway._client = client = types.SimpleNamespace(chat=chat)
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
uc.ask = ask_before = ask
ws = game.scene
rec = recording.Recorder(store, folder=OUT).install()
check("a recording session is strict while it records", streams.STRICT is True)
ws.run()
folder = rec.close()
check("...and the model client and the console are put back when it closes", client.chat is chat and uc.ask is ask_before
      and streams.STRICT is False)

# ---- what was kept
meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
check("meta: the seed, the data hash, the model, the version and the state the session opened in",
      meta["seed"] == 40 and meta["data"] == statehash.data_hash() and meta["model"] == config.MODEL and meta["start"] == start, meta.keys())
db = sqlite3.connect(OUT / "start.db")
check("start.db is the save as it opened", db.execute("SELECT count(*) FROM kv").fetchone()[0] > 0)
db.close()
copy = Path("saves/recorder_440_copy"); shutil.rmtree(copy, ignore_errors=True); copy.mkdir(parents=True)
shutil.copy(OUT / "start.db", copy / "campaign.db")
reopened = CampaignStore.open_or_create("recorder_440_copy")
check("...and reads back to the same state the session opened in", statehash.digest(reopened) == start)
reopened.close(); shutil.rmtree(copy, ignore_errors=True)
inputs = [json.loads(l) for l in (OUT / "inputs.jsonl").read_text(encoding="utf-8").splitlines()]
mains = [r["text"] for r in inputs if r["main"]]
check("every input is kept, the pane's command and the line said to quit included", mains == [t for t, _ in SCRIPT] + ["quit"], mains)
with gzip.open(OUT / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
    calls = [json.loads(l) for l in f]
check("every model call is kept in order, its request in full", calls and [c["i"] for c in calls] == list(range(len(calls)))
      and all(c["req"] and "messages" in c["request"] for c in calls), len(calls))
check("...with its answer", any(c.get("answer") and c["title"] == "ActionPlan" for c in calls))
check("...and a failed one with the failure, so a replay can fail it the same way",
      any(c.get("error", [""])[0] == "ConnectionError" and c["title"] == "ActionPlan" for c in calls))
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("after each input, the state's fingerprint and what was shown", len(turns) == len(mains)
      and all(t["state"]["all"] and t["shown"] for t in turns), len(turns))
store.close()
check("the last fingerprint is the save as the session left it",
      turns[-1]["state"] == statehash.digest(CampaignStore.open_or_create(SAVE)))

# ---- only the newest are kept
recording.FOLDER = Path("saves/recorder_440_many")
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

for p in (f"saves/{SAVE}", OUT, recording.FOLDER):
    shutil.rmtree(p, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

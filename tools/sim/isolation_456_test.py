"""(f456) The isolation proof: the done-when of Bundle B. Two campaigns played one after the other in one process must be two campaigns
played in two. Child P1 opens save A, plays eight stub inputs (a failed turn among them), closes it, then opens save B and plays twelve
under a recorder; child P2, with another PYTHONHASHSEED, plays B alone from the same database with the same inputs under a recorder. B's two
recordings must agree input by input in state, outcomes and what was shown; after every close nothing the session owned remains
(simlib.residue() == {}); and P1's recording of B replays in a third process through the real turn (tools/rerun.py). Any residue held by
the process that can reach a turn (a cache keyed by town, a bus still subscribed, a world written into, a stream left keyed) parts this
without being named. The bundle stored nothing new: the state hash's tables are the same six, and the data hash is the golden's."""
import json, os, pathlib, shutil, subprocess, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 39))
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

CHILD = r'''
import json, pathlib, random, sys
sys.path.insert(0, "."); sys.path.insert(0, "tools")
import simlib
import ui.console as uc
import nightbot

def fresh_stub():
    """The stand-in model answers the same prompts the same way in every process: a new stub, its counters at zero."""
    stub = simlib.Stub("warrior", 39)
    held = simlib.install(stub)                               # (f518) the stub as the source; play() takes it away again at its end
    simlib.NAME_COUNTER[0] = 0
    simlib.NARR_COUNTER[0] = 0
    return stub, held

for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.dialogue = lambda *a, **k: None
uc.panel = lambda name, data: False

def play(name, n, fail_at, record_to=None):
    stub, held = fresh_stub()
    game = simlib.campaign(name, fresh=False)                 # the save copied into place
    store, ws = game.store, game.scene
    bot = nightbot.Bot(ws, ws.world, random.Random(39), stub=stub, persona="wanderer")
    stub.bot = bot
    FAIL = {"on": False}
    real = simlib.below()                                     # (f518) this play's stub, taken before the failing wrapper goes in over it
    def chat(**k):
        if FAIL["on"] and k["format"].get("title") == "ActionPlan":
            raise ConnectionError("the model server cannot be reached")
        return real.chat(**k)
    spy = simlib.stand_in(chat=chat, embed=None)
    state, LAST = {"n": 0}, {"text": "I look around."}
    def ask(*a, main=False, **k):
        if not main:
            return "yes"
        state["n"] += 1
        FAIL["on"] = state["n"] == fail_at                    # one turn fails and rolls back; the next says the line again
        if state["n"] > n:
            return "quit"
        if state["n"] == fail_at + 1:
            return LAST["text"]
        text, kind = bot.decide()
        LAST["text"] = text
        return text
    uc.ask = ask
    if record_to:
        game.session.record(folder=pathlib.Path(record_to))
    ws.run()
    game.close()
    ANSWERED.append(spy.live() and spy.src.calls["ActionPlan"] > 0)    # the failing wrapper answered this play's turns, to the end
    spy()
    held()
    return simlib.residue()

mode, out, ANSWERED = sys.argv[1], {}, []
if mode == "ab":
    out["residue_a"] = play("iso456_a", 8, 3)
    out["residue_b"] = play("iso456_b1", 12, 5, record_to="saves/iso456_rec1")
else:
    out["residue_b"] = play("iso456_b2", 12, 5, record_to="saves/iso456_rec2")
out["answered"] = ANSWERED
print("RESULT " + json.dumps(out))
'''

SAVES = ("iso456_base", "iso456_a", "iso456_b1", "iso456_b2", "iso456_rec1", "iso456_rec2")
for s in SAVES:
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
simlib.campaign("iso456_base", seed=39, turn=1, minutes=480).close()
check("the base campaign leaves nothing behind when it closes", simlib.residue() == {}, simlib.residue())
for s in ("iso456_a", "iso456_b1", "iso456_b2"):
    shutil.copytree("saves/iso456_base", f"saves/{s}")
script = pathlib.Path("saves/iso456_child.py")
script.write_text(CHILD, encoding="utf-8")
runs = {}
for mode, hseed in (("ab", "1"), ("b", "2")):
    out = subprocess.run([sys.executable, str(script), mode], capture_output=True, text=True, timeout=900, env={**os.environ, "PYTHONHASHSEED": hseed})
    line = next((l for l in out.stdout.splitlines() if l.startswith("RESULT ")), "")
    runs[mode] = json.loads(line[7:]) if line else {"error": (out.stderr or out.stdout)[-1500:]}
check("both children ran to the end", "residue_b" in runs["ab"] and "residue_b" in runs["b"], {k: v.get("error", "")[-600:] for k, v in runs.items() if "error" in v})
check("...each play answered through its failing wrapper to the end (f518: a stand-in over that play's stub)",
      runs["ab"].get("answered") == [True, True] and runs["b"].get("answered") == [True], {k: v.get("answered") for k, v in runs.items()})
if "residue_b" in runs["ab"] and "residue_b" in runs["b"]:
    check("after each close, nothing the session owned remains, in either process", runs["ab"]["residue_a"] == {} and runs["ab"]["residue_b"] == {}
          and runs["b"]["residue_b"] == {}, runs)
    def rows(folder, name):
        p = pathlib.Path(f"saves/{folder}/{name}")
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []
    t1, t2 = rows("iso456_rec1", "turns.jsonl"), rows("iso456_rec2", "turns.jsonl")
    i1, i2 = [r["text"] for r in rows("iso456_rec1", "inputs.jsonl")], [r["text"] for r in rows("iso456_rec2", "inputs.jsonl")]
    check("B was given the same lines in both processes (the bot read the same scene)", i1 == i2 and len(i1) >= 12, (len(i1), len(i2), next(((a, b) for a, b in zip(i1, i2) if a != b), None)))
    first = next((t["i"] for t, u in zip(t1, t2) if t["state"]["all"] != u["state"]["all"]), None)
    check("B played after A in one process is B played alone in another: the same state after every input", len(t1) == len(t2) >= 12 and first is None,
          f"they part after input {first}" if first else (len(t1), len(t2)))
    check("...the same outcomes", all(t["outcomes"] == u["outcomes"] for t, u in zip(t1, t2)), next((t["i"] for t, u in zip(t1, t2) if t["outcomes"] != u["outcomes"]), None))
    check("...and the same words shown", all(t["shown"] == u["shown"] and t["lines"] == u["lines"] for t, u in zip(t1, t2)),
          next((t["i"] for t, u in zip(t1, t2) if t["shown"] != u["shown"]), None))
    check("...with a turn rolled back among them", any(t["state"]["all"] == u["state"]["all"] for t, u in zip(t1, t1[1:])), [t["state"]["all"][:6] for t in t1])
    rep = subprocess.run([sys.executable, "tools/rerun.py", "saves/iso456_rec1"], capture_output=True, text=True, timeout=900)
    last = (rep.stdout.strip().splitlines() or [""])[-1]
    check("P1's recording of B replays in a third process through the real turn", rep.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
          (rep.returncode, rep.stdout[-400:], rep.stderr[-400:]))

# ---- the bundle stored nothing new and re-hashed nothing
check("the state hash reads the same six tables", set(statehash.TABLES) == {"kv", "places", "npcs", "npc_memory", "event_log", "entities"}, sorted(statehash.TABLES))
golden = json.loads(pathlib.Path("data/replay/sessions/stub_short/meta.json").read_text(encoding="utf-8"))
check("...and the data hash is the golden's: no new data file, no number moved", statehash.data_hash() == golden["data"], (statehash.data_hash()[:12], golden["data"][:12]))

for s in SAVES:
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
script.unlink(missing_ok=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

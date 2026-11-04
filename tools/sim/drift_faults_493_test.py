"""(f493) What the post-D night found, part 2: an operation run again for its answer reads what it read the first time. The held
narration a line's earlier operation queued (a hand-in's passage) is put back whole when an operation that flushed it stands down, so
the talk run again tells it at the same point (the night's four dialogue_frame Drifts); the truth scene is built anew as each
operation opens, so a scene from before a place's population is not read by one attempt and rebuilt for the next (the night's
hire_chat Drift); and the two orders that followed the hash seed now do not: the drift's danger rows over a town's wild places, and the
captives walking bound, in the order they were taken, into the next place's residents."""
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import truth
from llm import gateway
from llm.contracts import DialogueFrame

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "drift_faults_493"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")

# ---- the held narration, put back whole when an operation stands down
seen = []
ws.pending = ["an earlier operation's passage"]


def body(op):
    seen.append(list(ws.pending))
    events, ws.pending = ws.pending, []                                  # flushed, as the talk's flush took the hand-in's passage
    gateway.generate("dialogue_frame", "You frame a line.", "The line.", DialogueFrame)     # asked outside: the operation stands down once


op, _ = ws.asked_operation("action:test", "x", body)
check("an operation run again for its answer finds the held narration it flushed the first time", seen == [["an earlier operation's passage"]] * 2
      and op.state == "committed", (seen, op.state))
ws.pending = []

# ---- the night's shape: a hand-in's passage told with the talk at the one who pays, the talk standing down twice
CALLS = []
real = gateway._client


def chat(**k):
    CALLS.append(((k.get("format") or {}).get("title", ""), k["messages"][1]["content"]))
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
ws.player.quests = ws.player.quests + [{"id": "q493", "title": "Find the lamb", "kind": "fetch", "issuer": npc.id, "letter": "F"}]
store.save_player(ws.player)


def handin(nid):
    ws.narrate("THE JOB IS DONE AND PAID. What is different now, seen or heard of: the lamb is home.")
    ws.player.quests = [q for q in ws.player.quests if q.get("id") != "q493"]
    return ["the finished request 'Find the lamb', paid ten copper"]


ws.turn_in = handin
import config
crash = Path(config.CRASH_LOG_PATH)
before = crash.read_text() if crash.exists() else ""
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Your lamb is home. Pay me."}]
ws.turn('I say, "Your lamb is home. Pay me."')
stub.plan = None
del ws.turn_in
gateway._client = real
after = crash.read_text() if crash.exists() else ""
kinds = {o["kind"]: o for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps}
told = [t for t, u in CALLS if "THE JOB IS DONE AND PAID" in u]
check("a talk after a hand-in, run again for its reply and its frame, raises no Drift", "Drift" not in after[len(before):], after[len(before):][-600:])
check("...the hand-in and the talk both stand", "action:handin" in kinds and "action:talk" in kinds, sorted(kinds))
check("...the hand-in's passage is told, asked of the narrator once", len(told) == 1, [t for t, _ in CALLS])
check("...and the talk was framed (the frame its re-run asked for)", any(t == "DialogueFrame" for t, _ in CALLS), [t for t, _ in CALLS])

# ---- the truth scene: built anew as each operation opens, the same within one
outside = truth.scene_of(ws)
inner = []
with ws.operation("action:look", "x") as op:
    inner.append(truth.scene_of(ws))
    inner.append(truth.scene_of(ws))
check("an operation does not read a truth scene built before it opened", inner and inner[0] is not outside, (outside, inner))
check("...and within one operation the scene is built once", len(inner) == 2 and inner[0] is inner[1])
attempts = []


def body2(op):
    attempts.append(truth.scene_of(ws))
    gateway.generate("dialogue_frame", "You frame a line.", "Another line.", DialogueFrame)


ws.asked_operation("action:test", "y", body2)
check("...each attempt of an operation reads a scene of its own start", len(attempts) == 2 and attempts[0] is not attempts[1], attempts)

# ---- the captives walk bound in the order they were taken
names = ["Garrick Fell", "Ansel Morrow", "Brannoc Teague", "Dunmore Hale"]
for nm in names:
    ws.make_prisoner(nm, "", tip=False, named=False, kind="bandit")
store.save_player(ws.player)
taken = [n for n in ws.escorted()]
check("the captives walking bound are a list, in the order they were taken", isinstance(ws.escorted(), list)
      and [store.load_npc(i).name for i in taken][-len(names):] == names, [store.load_npc(i).name for i in taken])
dest = next(pid for pid in ws.world.neighbors(ws.player.location))
ws.bring_prisoners(dest)
rows = [r for r in store.load_place(dest).residents if r in taken]
check("...and they reach the next place's residents in that order", rows == taken, (rows, taken))
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)

# ---- the drift's danger rows over a town's wild places: the same under any hash seed
code = r'''
import sys; sys.path[:0] = [".", "tools"]
import simlib; simlib.install(simlib.Stub("warrior", 3)); simlib.quiet_console()
from engine import drift, towns
game = simlib.campaign("drift_order_493_" + sys.argv[1], cls="warrior", seed=3, location="guild_house")
w = game.scene.world
town = next(t for t in sorted(w.places) if w.places[t].type in ("town", "city", "village")
            and len([p for p in towns.town_places(w, t) if w.places[p].danger]) >= 2)
state = game.store.load_world_state()
state["threads"] = [{"id": "t493", "status": "active", "place": town, "kind": "threat", "severity": 2}]
drift.situations(game.store, w, state, 0)
print("ORDER", [e["place"] for e in state["effects"] if e.get("cause") == "drift" and e["kind"] == "danger"])
game.close()
import shutil; shutil.rmtree("saves/drift_order_493_" + sys.argv[1], ignore_errors=True)
'''
orders = []
for seed in ("1", "2", "99"):
    out = subprocess.run([sys.executable, "-c", code, seed], env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True, text=True, timeout=300)
    orders.append(next((l for l in out.stdout.splitlines() if l.startswith("ORDER")), out.stderr[-400:]))
check("the drift lays its danger rows over a town's wild places in one order under any hash seed", len(set(orders)) == 1
      and orders[0].startswith("ORDER ['") and orders[0].count("'") >= 4, orders)
check("...the places' own order, sorted", orders[0].startswith("ORDER") and eval(orders[0][6:]) == sorted(eval(orders[0][6:])), orders[0])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

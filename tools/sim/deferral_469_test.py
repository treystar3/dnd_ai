"""(f469) Deferral to a later turn: under a budget the party's exchange does not fit in is queued in the save, not spoken this turn, and
spoken once at the next input's tail under that input's dice, the row gone after; a frame past the budget is dropped and nothing is
queued; an entry older than retention.deferred_turns is dropped untried; a deferred exchange whose next turn is a fight waits; the
embedder's warm-up is one embed call on a thread the session owns, with nothing left in the process after the close; and the pulse's
cap is unmoved by a budget skip. The session is recorded and replays in a child process, the deferral at the same input."""
import json
import pathlib
import random
import shutil
import subprocess
import sys
import threading
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
from engine import banter, budget, combat, pulse, quirks
from llm import embed, gateway
from npc.models import NPC
from scenes import combat_scene as cs
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


B = budget.B
MEASURED = dict(budget.PROFILE)
TUNABLES = {k: B[k] for k in ("limit_seconds", "margin_seconds", "floor_seconds", "reserve_seconds")}
BN = banter.B["banter"]
BANTER_WAS = {k: BN[k] for k in ("chance", "cooldown", "rest_chance")}


def restore():
    budget.PROFILE.clear(); budget.PROFILE.update(MEASURED)
    B.update(TUNABLES)
    BN.update(BANTER_WAS)


def hire(i, name, temper, role, bond=20):
    m = {"id": f"h{i}", "name": name, "role": role, "level": 3, "rank": "F", "permanent": True, "temper": temper, "motive": "coin",
         "line": "will not take from the poor", "bond": bond, "memories": [], "said": [], "talk": [], "blurb": "a hired hand"}
    quirks.roll(m, random.Random(i))
    m["details"] = []
    m["speech"] = {"tells": {}}
    return m


SAID = []
SHOWN = simlib.quiet_console()
uc.say = lambda t, s="": SAID.append((s, t))
uc.dialogue = lambda b, s, t, a: SAID.append((s, t))
uc.npc_says = lambda label, speech, gesture="": SAID.append((label, speech))

NAME = "deferral_469"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = f"saves/{NAME}/turns.jsonl"
crew = [hire(1, "Bram Voss", ["blunt"], "fighter"), hire(2, "Isel Quill", ["gentle"], "priest")]
ws.player.party, ws.player.party_mode, ws.player.party_relations = crew, "with", {}
tam = NPC(id="tam469", name="Tam Reed", people="human", role="farmer", location="parth", traits=[], trust=50)
store.save_npc(tam)
store.save_player(ws.player)
ws.enter("parth")
ws.present, ws.residents = [tam], [tam]
OUT = pathlib.Path(f"saves/{NAME}_rec")
shutil.rmtree(OUT, ignore_errors=True)
SCRIPT = ['I say to Tam, "Good day to you."', "I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
budget.PROFILE.update(read_tps=1e9, write_tps=10.0)              # every answer token a tenth of a second; the prompt costs nothing
B.update(limit_seconds=22, margin_seconds=0, floor_seconds=1, reserve_seconds=5)
BN.update(chance=100, cooldown=0, rest_chance=100)                # the party always has something to say when it may
hires = {m["name"] for m in crew}


def hire_lines():
    return [(s, t) for s, t in SAID if s in hires or any(s.startswith(n.split()[0]) for n in hires)]


LINES = []
real_turn, real_enter = ws.turn, ws.enter


def entered(place_id):
    real_enter(place_id)
    ws.present, ws.residents = [tam], [tam]                      # Tam at hand whatever the hour (run() enters the place itself)


def staged(text):
    """The script's two lines through run(): the talk with Tam, the party due to talk at its tail; then a look."""
    SAID.clear()
    if "say to Tam" in text:
        stub.plan = [{"kind": "talk", "target": tam.id, "speech": "Good day to you."}]
        ws._banter_due = "rest"
    else:
        stub.plan = [{"kind": "look"}]
    stood = real_turn(text)
    LINES.append({"stood": stood, "hires": hire_lines(), "queue": store.load_deferred(), "budget": dict(ws.last_budget),
                  "exchanges": stub.calls.get("Exchange", 0), "steps": store.meta.steps})
    return stood


ws.enter, ws.turn = entered, staged
ex0 = stub.calls.get("Exchange", 0)
ws.run()
ws.turn, ws.enter = real_turn, real_enter
one, two = LINES[0], LINES[1]
queue = one["queue"]
check("under the budget the party's exchange is deferred: not spoken this turn, queued in the save with the input it came from",
      one["stood"] is True and not one["hires"] and one["exchanges"] == ex0 and len(queue) == 1 and queue[0]["kind"] == "banter"
      and set(queue[0]["data"]["crew"]) == {"h1", "h2"} and queue[0]["data"]["why"] == "rest" and queue[0]["from_steps"] == one["steps"], one)
check("...the budget names it deferred, and the frame that did not fit dropped, nothing of it queued", one["budget"].get("deferred") == ["exchange"]
      and "dialogue_frame" in one["budget"].get("dropped", []) and all(r["kind"] == "banter" for r in queue), one["budget"])
check("at the next input's tail the deferred exchange is spoken once and its row is gone", two["stood"] is True and two["exchanges"] == ex0 + 1
      and len(two["hires"]) >= 1 and two["queue"] == [] and not two["budget"].get("deferred"), two)
g.close()
restore()

# ---- a queued entry runs from the save alone: recorded under a slow profile and replayed in a child process, the exchange at the same call
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth", fresh=False)
ws, store = g.scene, g.store
store.save_deferred([{"kind": "banter", "data": {"crew": ["h1", "h2"], "why": "rest"}, "from_steps": store.meta.steps}])   # in the save: the replay starts from it
SCRIPT = ["I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
budget.PROFILE.update(read_tps=1e9, write_tps=10.0)              # the profile travels in the recording's meta; the limit is the data's
g.session.record(folder=OUT)
stub.plan = [{"kind": "look"}]
ex0 = stub.calls.get("Exchange", 0)
SAID.clear()
ws.run()
check("a queued exchange runs at the next input's tail from the save alone, under the real limit", stub.calls.get("Exchange", 0) == ex0 + 1 and len(hire_lines()) >= 1
      and store.load_deferred() == [], (stub.calls.get("Exchange", 0), ex0, hire_lines()[:2], store.load_deferred()))
g.close()
restore()
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("the recording holds the input, its row with the tail that spoke it", len(turns) >= 1 and any(o["kind"] == "tail" for o in turns[0]["operations"]), len(turns))
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last = (out.stdout.strip().splitlines() or [""])[-1]
check("...and it replays in a child process: the exchange spoken at the same call, the queue emptied the same", out.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
      (out.returncode, out.stdout[-400:], out.stderr[-400:]))
shutil.rmtree(OUT, ignore_errors=True)

# ---- an entry older than retention.deferred_turns is dropped untried; one whose next turn is a fight waits
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth", fresh=False)
ws, store = g.scene, g.store
ws.player.party, ws.player.party_mode = [hire(1, "Bram Voss", ["blunt"], "fighter"), hire(2, "Isel Quill", ["gentle"], "priest")], "with"
store.save_player(ws.player)
ws.enter("parth")
ws.present, ws.residents = [tam], [tam]
from engine import operation as _op
old_age = int(_op.RETENTION.get("deferred_turns") or 3) + 5
store.save_deferred([{"kind": "banter", "data": {"crew": ["h1", "h2"], "why": "rest"}, "from_steps": store.meta.steps - old_age}])
ex0 = stub.calls.get("Exchange", 0)
stub.plan = [{"kind": "look"}]
stood = ws.turn("I look around.")
check("an entry older than retention.deferred_turns is dropped untried", stood is True and store.load_deferred() == [] and stub.calls.get("Exchange", 0) == ex0,
      (store.load_deferred(), stub.calls.get("Exchange", 0), ex0))
store.save_deferred([{"kind": "banter", "data": {"crew": ["h1", "h2"], "why": "rest"}, "from_steps": store.meta.steps}])
creature = ws.world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", name="wolf 1")
foe.hp = foe.max_hp = 10 ** 6
ws.combat = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
stood = ws.turn("I attack the wolf")
check("a deferred exchange whose next turn is a fight waits, and ages", stood is True and ws.combat is not None and len(store.load_deferred()) == 1
      and stub.calls.get("Exchange", 0) == ex0, (stood, ws.combat is None, store.load_deferred(), stub.calls.get("Exchange", 0), ex0))
ws.combat = None
store.save_combat(None)
SAID.clear()
stood = ws.turn("I look around.")
check("...and is spoken once the fight is over", stood is True and stub.calls.get("Exchange", 0) == ex0 + 1 and store.load_deferred() == [], (stood, stub.calls.get("Exchange", 0), ex0, store.load_deferred()))
restore()

# ---- the pulse's cap is unmoved by a budget skip
state = pulse.empty_state(ws.minutes)
rng = random.Random(1)
b = budget.open(limit=1, margin=0, floor=0.5, reserve=0)
pulse.LAST["attempted"] = "stale"
ok = pulse.start_thread(store, ws.world, ws.catalog, state, ws.minutes, rng, made_by="model")
budget.close()
check("a pulse call the budget skipped is no attempt against the pulse's own cap", ok is False and pulse.LAST["attempted"] == "" and b.dropped == ["pulse_thread"], (ok, pulse.LAST, b.dropped, b.refused))

# ---- the embedder's warm-up: one embed call on a thread the session owns; nothing left after the close
CALLS = []


class FakeEmbed:
    def embed(self, **k):
        CALLS.append(k)
        return {"embeddings": [[1.0, 0.0]]}


real_client, real_state = embed._client, dict(embed._state)
embed._client = lambda: FakeEmbed()
embed._state.update(ok=True, fixed=True, failed=False)
t = embed.warm(g.session)
t.join(5)
check("embed.warm() makes one embed call on a thread the session owns", t is not None and not t.is_alive() and len(CALLS) == 1 and t in g.session._threads, (len(CALLS), t))
embed._client = real_client
embed._state.clear(); embed._state.update(real_state)
g.close()
check("nothing of it stays in the process once the campaign closes", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

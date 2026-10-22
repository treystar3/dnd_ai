"""The game does at most three things a line (f332): a fourth is no longer dropped in silence - the plan keeps what it set aside, the scene tells
the player what was not done, and the refusal is logged. An improvisation's success makes something true in the world besides its mark
(improv.yaml changes): a barred way is closed for a while, a snare makes the wood a little safer, a broken thing is talked of."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from llm.contracts import ActionIntent, ActionPlan
from engine import pulse, refusals, world_improv
import engine.checks as _checks
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the plan keeps what it set aside
plan = ActionPlan(actions=[ActionIntent(kind="look"), ActionIntent(kind="wait"), ActionIntent(kind="search"), ActionIntent(kind="move", destination="greywood", summary="go to the wood"),
                           ActionIntent(kind="pray", summary="pray")])
check("a plan keeps three actions and sets the rest aside, in order", [a.kind for a in plan.actions] == ["look", "wait", "search"] and [a.summary for a in plan.dropped] == ["go to the wood", "pray"])
check("...and a plan of three keeps nothing aside", ActionPlan(actions=[ActionIntent(kind="look")]).dropped == [])

shutil.rmtree("saves/plan_limit_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("plan_limit_test")
store.meta.seed = 5; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True                       # Maren's tutorial would stop to ask the player a question
ws.enter("trading_square")
store.save_world_state(pulse.empty_state(ws.minutes))
notes, narrated = [], []
console.note = lambda t, *a, **k: notes.append(t)
ws._narrate_now = lambda event, player_text="": narrated.append(event)

# ---- the scene tells the player
stub.a_ActionPlan = lambda u, k: {"actions": [{"kind": "look", "summary": "look around"}, {"kind": "wait", "wait_minutes": 10, "summary": "wait"},
                                              {"kind": "look", "summary": "look again"}, {"kind": "search", "summary": "search the square for tracks"}]}
ws.audit_plan = lambda text, plan, raw_plan=None: plan
for k in ("look", "wait", "search"):
    setattr(ws, f"on_{k}", lambda intent, text: None)
refusals.SESSION.clear()
ws.handle("I look around, wait a bit, look again and search the square for tracks")
check("the player is told what the line left undone", any("not done - search the square for tracks" in n for n in notes), notes[-2:])
check("...and it is logged as a refusal of its own kind", refusals.SESSION and refusals.SESSION[-1]["kind"] == "undone" and "search the square" in refusals.SESSION[-1]["why"], refusals.SESSION[-1:])
stub.a_ActionPlan = lambda u, k: {"actions": [{"kind": "look", "summary": "look around"}]}
notes.clear()
ws.handle("I look around")
check("...and nothing is said when a line fits", not any("not done" in n for n in notes))

# ---- an improvisation's success makes something true
ws.enter("greywood")
_roll = _checks.roll
_checks.roll = lambda odds, rng=None, c=None: ("success", 1)
world_improv.read_effect = lambda words: "rig"
t = ws.minutes
world_improv.resolve(ws, "rig a snare across the deer path", "I rig a snare across the deer path")
st = store.load_world_state()
mine = [e for e in st["effects"] if e.get("cause") == "improvised"]
check("a snare rigged in the wood makes it a little safer for a day", any(e["kind"] == "danger" and e["place"] == "greywood" and e["value"] == -10 and e["until"] == t + 1440 for e in mine), mine)
check("...and the place carries the mark", any(m.startswith("rigged: rig a snare") for m in store.load_place("greywood").marks))
ws.enter("trading_square")
world_improv.read_effect = lambda words: "block"
t = ws.minutes
world_improv.resolve(ws, "bar the gate with the cart", "I bar the gate with the cart")
st = store.load_world_state()
closed = pulse.closed_reason(store, "trading_square", ws.minutes + 1)
check("a way barred is closed for a while, and the world says so", closed.startswith("barred from inside") and not pulse.closed_reason(store, "trading_square", t + 91), closed)
world_improv.read_effect = lambda words: "signal"
world_improv.resolve(ws, "ring the alarm bell", "I ring the alarm bell")
st = store.load_world_state()
check("a signal is talked of", any("signal was raised" in n["text"] and n["origin"] == "trading_square" for n in st["news"]), st["news"][-1:])
_checks.roll = lambda odds, rng=None, c=None: ("partial", 50)
world_improv.read_effect = lambda words: "rig"
world_improv.resolve(ws, "rig a tripwire", "I rig a tripwire")
st = store.load_world_state()
check("a partial in the square rigs nothing the wood would feel (no danger here), and spreads no word", not any(e["kind"] == "danger" and e["place"] == "trading_square" for e in st["effects"]) and not any("tripwire" in n["text"] for n in st["news"]))
_checks.roll = _roll
check("the improv changes check clean", world_improv.problems() == [])

shutil.rmtree("saves/plan_limit_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

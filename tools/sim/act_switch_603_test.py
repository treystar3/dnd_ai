"""(f603) The switch: every improvised line outside a fight goes to the act's one ruling (engine/act.py), shipped on, the owner's go of
2026-11-12 with the pod session's numbers in front of them (docs/measure/2026-11-12_phase2_pod.md). The old path, ruling.run and
world_improv.resolve, is retired; what the old path made true in the world on a success is kept (the owner): the effect an act's words
read as (improv.yaml: a way barred is closed for a while, a snare makes the wood a little safer, a signal is talked of) and the place's
mark, beside the act's own changes. A gesture leaves nothing behind; a failure makes nothing true.
Run: python tools/sim/act_switch_603_test.py"""
import inspect
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, checks, pulse, ruling, world_improv

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_switch_603", seed=3, location="trading_square")
ws, store, world = g.scene, g.store, g.scene.world
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})

check("the old path and its switch are retired: no ruling.run, no world_improv.resolve, no act.yaml enabled, and the scene never calls them",
      not hasattr(ruling, "run") and not hasattr(world_improv, "resolve") and not hasattr(act, "on") and "enabled" not in act.A
      and "ruling.run" not in inspect.getsource(type(ws).on_other))

spied = []
real = act.act
act.act = lambda ws_, who, words, text: spied.append((who, text))
with ws.operation("action:other", "I wave at the gulls"):
    ws.on_other(types.SimpleNamespace(kind="other", summary="wave at the gulls"), "I wave at the gulls.")
act.act = real
check("an improvised line goes to the act's ruling, the acting character's", spied == [(ws.acting, "I wave at the gulls.")], spied)


def attempt(text, words, roll="success", ruled=None):
    stub.act_ruling = ruled or {"sense": "cost", "why": "it can be done", "stakes": {"check": "dexterity", "hard": "fair"}, "fail": "time_lost"}
    real_roll = checks.roll
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    try:
        with ws.operation("action:other", text) as op:
            ws.on_other(types.SimpleNamespace(kind="other", summary=words), text)
    finally:
        checks.roll = real_roll
    return op


op = attempt("I bar the gate with the cart.", "bar the gate with the cart")
seen = pulse.happenings_at(store, world, "trading_square", ws.minutes + 1)
check("a way barred by an act is closed for a while, and the world tells it as the player's own doing", op.state == "committed"
      and any("barred the way here themselves" in h for h in seen), seen)
check("...it never bars the player who barred it", pulse.closed_reason(store, "trading_square", ws.minutes + 1) == "")
check("...and the place carries the mark", any(m.startswith("the way is blocked") for m in store.load_place("trading_square").marks),
      store.load_place("trading_square").marks[-3:])

attempt("I ring the alarm bell.", "ring the alarm bell")
check("a signal is talked of", any("signal was raised" in n["text"] and n["origin"] == "trading_square" for n in store.load_world_state()["news"]),
      store.load_world_state()["news"][-1:])

ws.enter("greywood")
t = ws.minutes
attempt("I rig a snare across the deer path.", "rig a snare across the deer path")
mine = [e for e in store.load_world_state()["effects"] if e.get("cause") == "improvised" and e.get("place") == "greywood"]
check("a snare rigged in the wood makes it a little safer for a day", any(e["kind"] == "danger" and e["value"] == -10 for e in mine), mine)

marks = list(store.load_place("greywood").marks)
n_effects = len(store.load_world_state()["effects"])
attempt("I rig a second snare.", "rig a second snare", roll="failure")
check("a failure makes nothing true: no mark, no effect", store.load_place("greywood").marks == marks
      and len(store.load_world_state()["effects"]) == n_effects)
attempt("I lean against a tree and watch the shadows.", "lean against a tree and watch the shadows", ruled={"sense": "yes", "why": "anyone can"})
check("a gesture leaves nothing behind", store.load_place("greywood").marks == marks and len(store.load_world_state()["effects"]) == n_effects)
check("the improv changes check clean", world_improv.problems() == [] and act.problems() == [])

# ---- what the retired run held, held by the act path now: a no, and a part blocked by an act
from engine import features, ledger, refusals, targets
noted = []
real_note = refusals.note
refusals.note = lambda kind, text, why="", place="", turn=-1, asked="": noted.append((kind, text, why))
told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="": told.append(event)
n_parts, before_min = len(features.here(store, "greywood")), ws.minutes
with ws.operation("action:other", "I fly up over the trees.") as op:
    r0 = ledger.count("refused")
    stub.act_ruling = {"sense": "no", "why": "they cannot fly", "requires": ["flight"], "answer": "Their feet stay on the ground.",
                       "instead": ["climb a tall tree"]}
    ws.on_other(types.SimpleNamespace(kind="other", summary="fly up over the trees"), "I fly up over the trees.")
    r1 = ledger.count("refused")
check("a no makes nothing, spends a moment, and is counted as refused on the turn and in the refusals log", op.state == "committed"
      and len(features.here(store, "greywood")) == n_parts and ws.minutes == before_min + 1 and r1 == r0 + 1
      and noted and noted[-1][0] == "refused", (ws.minutes - before_min, r0, r1, noted[-1:]))
check("...and is told as the world, with what could be tried instead", told and "does not happen" in told[-1] and "climb a tall tree" in told[-1],
      told[-1][-300:] if told else "")
refusals.note = real_note

with ws.operation("test", "a hollow") as op:
    kind = features.kinds_here(ws.world.places["greywood"])[0]
    hollow = features.register(ws, "greywood", "the fox hollow", kind, "a hollow under the roots", "known", "authored")
code = next(t.code for t in targets.targets_for(ws, ws.acting).rows if t.ref == hollow.ref)
attempt("I heap brush over the way into the fox hollow.", "heap brush over the way into the fox hollow",
        ruled={"sense": "cost", "why": "brush is to hand", "stakes": {"check": "strength", "hard": "fair"}, "fail": "time_lost",
               "changes": [{"n": 1, "target": code, "becomes": "state", "state": "blocked"}]})
hollow = store.load_entity(hollow.ref)
shut, why = features.open_now(hollow, ws.minutes)
check("an act that blocks a part shuts the way to it, saying when it should be passable again, and tells it", not shut
      and "passable again" in why and told and "WHAT IS DIFFERENT NOW" in told[-1], (why, told[-1][-300:] if told else ""))
check("...and in a day it has worked loose", features.open_now(hollow, ws.minutes + 25 * 60)[0])
attempt("I clear the brush from the fox hollow.", "clear the brush from the fox hollow",
        ruled={"sense": "cost", "why": "it can be pulled away", "stakes": {"check": "strength", "hard": "fair"}, "fail": "time_lost",
               "changes": [{"n": 1, "target": code, "becomes": "state", "state": "cleared"}]})
check("clearing it opens the way at once", features.open_now(store.load_entity(hollow.ref), ws.minutes)[0])
ws.enter("trading_square")
road = next(t for t in targets.targets_for(ws, ws.acting).rows if t.ref in ws.world.roads)
n_fx = len(store.load_world_state()["effects"])
attempt("I bar the north gate with a cart.", "bar the north gate with a cart", roll="partial",
        ruled={"sense": "cost", "why": "a cart is to hand", "stakes": {"check": "strength", "hard": "fair"}, "fail": "time_lost",
               "changes": [{"n": 1, "target": road.code, "becomes": "access", "state": "closed"}]})
check("a partial whose closing of a way was refused leaves the way unbarred: no closure, no mark, nothing told of it",
      len(store.load_world_state()["effects"]) == n_fx and not any("bar the north gate" in m for m in store.load_place("trading_square").marks)
      and "barred for a while" not in told[-1], told[-1][-300:])
attempt("I ring the alarm bell again.", "ring the alarm bell again")
check("what an act makes true besides its own changes is told to the narrator", told and "word of it will go round" in told[-1],
      told[-1][-300:] if told else "")
stub.act_ruling = {"sense": "yes", "why": "anyone can"}
with ws.operation("act:waiting", "I blow the hunting horn."):
    T = targets.targets_for(ws, ws.acting)
    act.decide(ws, ws.acting, T, act.ask(ws, ws.acting, T, "blow the hunting horn", "I blow the hunting horn."), True,
               "blow the hunting horn", "I blow the hunting horn.", continuing="the attempt they began a moment ago,")
said = store.load_world_state()["news"][-1]["text"]
check("an act taken up after waiting makes true what its own words read as, never the words it was told with",
      "blow the hunting horn" in said and "began" not in said, said)
ws.narrate = real_narrate

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

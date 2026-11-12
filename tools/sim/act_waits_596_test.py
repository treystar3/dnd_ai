"""(f596) An act whose ruling could not be made waits for it (the owner, 2026-11-11; 2026-11-08: "every consequential act persists as an
event, including those awaiting interpretation"). The act path on (engine/act.py), a ruling call that fails keeps the act for the
character in the save, grants nothing and rolls nothing; the narrator is told only the attempt beginning, and its time passes. At the
next input, before that line is read and in an operation of its own (its call asked outside the transaction), the ruling is asked again:
made, the act resolves as any other and is told as how the attempt turned out (a no too), before the new line plays, never handed the
new line's words. It survives a reload; it lapses when the character has left the place or it has waited too long; after its tries,
or when its own operation fails, a try is spent, and past them it is told as come to nothing, each counted as a ruling that failed.
Never taken up in a fight. The same act typed again waits once; a character keeps only so many waiting; two characters' waiting acts
stay apart; with the act path off, nothing is taken up. Nothing handed the narrator limits how long it writes.
Run: python tools/sim/act_waits_596_test.py"""
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
import config
from engine import act, features, pulse, targets
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_waits_596", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
told, said = [], []
ws.narrate = lambda event, text="": told.append(event) or said.append(text)
from engine import refusals
noted = []
refusals.note = lambda kind, text, why="", place="", turn=-1, asked="": noted.append((kind, text, why))
with ws.operation("test", "set the scene") as op:
    kind = features.kinds_here(ws.world.places["trading_square"])[0]
    door = features.register(ws, "trading_square", "the cellar door", kind, "a stout door under the steps", "known", "authored")
    store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
check("the scene is set", op.state == "committed")
config.ACT = True


def code_of(ref):
    return next(t.code for t in targets.targets_for(ws, ws.acting).rows if t.ref == ref)


def other(text):
    with ws.operation("action:other", text) as op_:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text), text)
    return op_


working = stub.a_ActRuling
def broken(u, k):
    raise LLMError("the model is down")


# ---- the call fails: the act waits
stub.act_ruling = {"sense": "cost", "why": "a stout door", "changes": [{"n": 1, "target": code_of(door.ref), "becomes": "state", "state": "barred"}]}
stub.a_ActRuling = broken
n_deeds, minutes = len(store.load_world_state().get("deeds", [])), ws.minutes
told.clear()
op = other("I bar the cellar door with the bench.")
door = store.load_entity(door.ref)
check("a ruling that could not be made keeps the act waiting, grants nothing and rolls nothing", op.state == "committed"
      and [w["text"] for w in act.waiting(ws, ws.acting)] == ["I bar the cellar door with the bench."]
      and "barred" not in features.now_of(door, ws.minutes) and len(store.load_world_state().get("deeds", [])) == n_deeds)
check("...the narrator is told only the attempt beginning, and its time passes", told and "NOT DECIDED YET" in told[-1]
      and "never how it turns out" in told[-1] and ws.minutes == minutes + act.A["pending"]["minutes"], told[-1:])
g2 = simlib.campaign("act_waits_596", fresh=False)
check("it waits in the save: still there when the save is opened again", [w["text"] for w in act.waiting(g2.scene, g2.scene.acting)]
      == ["I bar the cellar door with the bench."])

# ---- the next input: ruled first, then the line
stub.a_ActRuling = working
seen_ops = []
real = ws.asked_operation
ws.asked_operation = lambda kind, text, body, **k: seen_ops.append(kind) or real(kind, text, body, **k)
told.clear()
from engine import checks
roll = checks.roll
checks.roll = lambda odds, rng=None, c=None: ("success", 1)        # the dice are not what is under test
ws.turn("I look around.")
checks.roll = roll
ws.asked_operation = real
door = store.load_entity(door.ref)
check("at the next input the waiting act is ruled first, in an operation of its own, before the line", seen_ops[:1] == ["act:waiting"]
      and "line" in seen_ops, seen_ops)
check("...made real as any act is, and no longer waiting", "barred" in features.now_of(door, ws.minutes) and act.waiting(ws, ws.acting) == [])
first = next((i for i, x in enumerate(told) if "the attempt they began a moment ago" in x), None)
check("...told as how the attempt turned out, before what the new line does", first == 0, told[:2])
row = next((d for d in reversed(store.load_world_state()["deeds"]) if d["kind"] == "acted"), None)
check("...and a deed of the character's, as any act", row is not None and row["by"] == ws.acting and row["changes"] == ["state"], row)

# ---- a no on take-up is told as how the attempt turned out
stub.a_ActRuling = broken
other("I lever the cellar door off its hinges.")
stub.a_ActRuling = working
stub.act_ruling = {"sense": "no", "why": "iron hinges", "answer": "The hinges are pinned with iron and do not budge."}
told.clear()
ws.turn("I look around.")
check("a no for a waiting act is told as how the attempt they began turned out", told and "does not happen" in told[0]
      and "the attempt they began" in told[0] and act.waiting(ws, ws.acting) == [], told[:1])

# ---- tries, lapsing, the cap, two characters, the switch
stub.a_ActRuling = broken
other("I chalk a sign on the cellar door.")
told.clear()
other("I chalk a sign on the cellar door!")
check("the same act typed again waits once", [w["text"] for w in act.waiting(ws, ws.acting)] == ["I chalk a sign on the cellar door!"]
      and told and "NOT DECIDED YET" in told[-1])
for i in range(act.A["pending"]["tries"] - 1):
    ws.turn("I wait a moment.")
check("each failed try counts, and it keeps waiting until its tries are spent", act.waiting(ws, ws.acting)
      and act.waiting(ws, ws.acting)[0]["tries"] == act.A["pending"]["tries"] - 1)
told.clear(); said.clear(); noted.clear()
ws.turn("I wait a moment more.")
end = next((i for i, x in enumerate(told) if "comes to nothing" in x), None)
check("...then it is told ending, as come to nothing, never rolled, and is no longer waiting", act.waiting(ws, ws.acting) == [] and end is not None)
check("...told with the act's own words, never the new line's", end is not None and said[end] == "I chalk a sign on the cellar door!", said)
check("...and counted as a ruling that failed", [(k, t) for k, t, _ in noted if k == "ruling_failed"] == [("ruling_failed", "I chalk a sign on the cellar door!")], noted)
check("nothing handed the narrator limits how long it writes", not any("few words" in x or "unremarked" in x for x in told), told)

stub.a_ActRuling = working
other_fails = act.decide
stub.a_ActRuling = broken
other("I knock twice on the cellar door.")
stub.a_ActRuling = working
def crash(*a, **k):
    raise RuntimeError("something broke")
act.decide = crash
r_ = ws.turn("I look at the sky.")
act.decide = other_fails
check("a take-up whose own operation fails spends a try apart, and the line is still taken whole", r_ is True
      and act.waiting(ws, ws.acting) and act.waiting(ws, ws.acting)[0]["tries"] == 1, (r_, act.waiting(ws, ws.acting)))
ws.combat = object()
before_fight = [dict(w) for w in act.waiting(ws, ws.acting)]
ws.take_up_acts("I swing at it.")
ws.combat = None
check("never taken up in a fight", [dict(w) for w in act.waiting(ws, ws.acting)] == before_fight)
store.meta.minutes += act.A["pending"]["lapse_hours"] * 60 + 1
store.save_meta()
told.clear(); noted.clear()
with ws.operation("test", "much later"):
    act.take_up(ws, ws.acting, "I wait.")
check("an act left waiting longer than lapse_hours lapses, told as left unfinished, counted", act.waiting(ws, ws.acting) == []
      and told and "left unfinished" in told[-1] and noted and "too long" in noted[-1][2], (told[-1:], noted))
stub.a_ActRuling = broken
other("I start prising a cobble loose.")
ws.player.location = next(p for p in ws.world.places if p != "trading_square" and ws.world.places[p].type != "road")
told.clear()
with ws.operation("test", "elsewhere"):
    act.take_up(ws, ws.acting, "I walk on.")
ws.player.location = "trading_square"
check("an act left waiting where the character no longer is lapses, told as left unfinished", act.waiting(ws, ws.acting) == []
      and told and "left unfinished" in told[-1], told[-1:])
for i in range(act.A["pending"]["most"] + 2):
    other(f"I try thing number {i}.")
check("a character keeps only so many acts waiting, the oldest let go", [w["text"] for w in act.waiting(ws, ws.acting)]
      == [f"I try thing number {i}." for i in range(2, act.A["pending"]["most"] + 2)])
with ws.operation("test", "theirs"):
    data = store.load_act_pending()
    data["another_character"] = [{"words": "x", "text": "Their own act.", "place": "trading_square", "minute": ws.minutes, "tries": 0}]
    store.save_act_pending(data)
    act.take_up(ws, ws.acting, "I wait.")
check("two characters' waiting acts stay apart", [w["text"] for w in act.waiting(ws, "another_character")] == ["Their own act."]
      and len(act.waiting(ws, ws.acting)) == act.A["pending"]["most"])
config.ACT = False
before = list(act.waiting(ws, ws.acting))
seen_ops.clear()
ws.asked_operation = lambda kind, text, body, **k: seen_ops.append(kind) or real(kind, text, body, **k)
ws.turn("I look around again.")
ws.asked_operation = real
check("with the act path off, nothing waiting is taken up and no operation is opened for it", act.waiting(ws, ws.acting) == before
      and "act:waiting" not in seen_ops, seen_ops)
stub.a_ActRuling = working
check("act.yaml passes its startup check", act.problems() == [])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f594) An act's ruling, asked and kept (engine/act.py; docs/design/02 sections 3, 5 and 8; the reuse rule). One call gives the ruling
and its changes, every target named by its code from the act's list (engine/targets.py) and every change from the closed list; a code
or a change outside them is sent back to the model. The engine checks the ruling reading only: a power the character lacks refuses it,
a need the world cannot hold refuses it, and each change is checked in order as one chain (the kind it lands on, a part's state, a
thing's lifecycle, a situation's parts by the situation ruling's own rules), a change that does not hold dropped with every change
that needs it. A ruling is kept per character with what it read, a no among them: the same act at the same place, its targets in the
same state and the character able to do the same, is ruled the same with no call, across a save and reload; a changed target, a new
power or another character asks again; a failed call keeps nothing; the kept are capped and let go when unused.
Run: python tools/sim/act_ruling_594_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
from engine import act, objects, ruling, situation_parts, targets
from llm.contracts import ActRuling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


calls = []
answer = stub.a_ActRuling
stub.a_ActRuling = lambda u, k: calls.append(u) or answer(u, k)

g = simlib.campaign("act_ruling_594", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
with ws.operation("test", "things") as op:
    crate = objects.make(store, "trading_square", "a stack of crates", "fish crates, salt-white", minute=ws.minutes)
    rope = objects.make(store, "trading_square", "a rope ladder", "", minute=ws.minutes)
check("the scene is set", op.state == "committed")
if not ws.present:                                     # someone here to speak to
    ws.present = list(ws.residents[:2])
T = targets.targets_for(ws, ws.acting)
crate_code = next(t.code for t in T.rows if t.ref == crate.ref)
rope_code = next(t.code for t in T.rows if t.ref == rope.ref)
ctx = act.context(ws, T)

# ---- the contract
def bad_answer(d):
    try:
        ActRuling.model_validate(d, context=ctx)
        return ""
    except ValueError as e:
        return str(e)


check("a target named by a code not in the list is sent back", "TARGETS" in bad_answer({"sense": "cost", "uses": ["o99"]}))
check("...and a change not in the list", "CHANGES" in bad_answer({"sense": "cost", "changes": [{"n": 1, "target": crate_code, "becomes": "teleported"}]}))
check("...and more changes than a ruling may carry", "at most" in bad_answer({"sense": "cost", "changes": [
    {"n": i, "target": crate_code, "becomes": "broken"} for i in range(1, act.A["most_changes"] + 2)]}))
r = ActRuling.model_validate({"sense": "no", "answer": "Nothing comes of it.", "uses": [crate_code], "fail": "explodes",
                              "changes": [{"n": 1, "target": crate_code, "becomes": "broken"}]}, context=ctx)
check("a no makes no changes, but keeps what it rested on; a failure not in the list is the first of them", r.changes == []
      and r.uses == [crate_code] and r.fail == act.A["fails"][0], r)
check("...two changes of one number, a need of a later change, and a who that is no target are sent back",
      "own number" in bad_answer({"sense": "cost", "changes": [{"n": 1, "target": crate_code, "becomes": "broken"},
                                                              {"n": 1, "target": crate_code, "becomes": "mended"}]})
      and "earlier" in bad_answer({"sense": "cost", "changes": [{"n": 1, "target": crate_code, "becomes": "broken", "needs": [2]},
                                                               {"n": 2, "target": crate_code, "becomes": "mended"}]})
      and "TARGETS" in bad_answer({"sense": "cost", "changes": [{"n": 1, "target": crate_code, "becomes": "broken", "who": "p99"}]}))
r = ActRuling.model_validate({"sense": "cost", "uses": [f"{crate_code.upper()}: the crates"]}, context=ctx)
check("...a code written either way is read", r.uses == [f"{crate_code.upper()}: the crates"] and act._named(r) == [crate_code])

# ---- the engine's check, reading only
def ruled(**d):
    return ActRuling.model_validate({"sense": "cost", **d}, context=ctx)


v = act.validate(ws, ws.acting, T, ruled(requires=["flight"], instead=["climb the crates"]))
check("wings with no power of flight: refused in the world's words", not v.ok and v.answer == ruling.C["flight"]["lacking"], v)
v = act.validate(ws, ws.acting, T, ruled(uses=[crate_code], stakes={"check": "stealth", "hard": "fair"}))
check("hiding behind a thing that is there stands, and the thing enables it", v.ok and v.enabled, v)
v = act.validate(ws, ws.acting, T, ruled(uses=[next(t.code for t in T.rows if t.kind == "person")]))
check("...relying on a person alone is no thing that enables it", v.ok and not v.enabled)
with ws.operation("test", "a plain thing") as op:
    pebble = objects.make(store, "trading_square", "a pebble", "", minute=ws.minutes)
T = targets.targets_for(ws, ws.acting)
ctx = act.context(ws, T)
crate_code = next(t.code for t in T.rows if t.ref == crate.ref)
rope_code = next(t.code for t in T.rows if t.ref == rope.ref)
v = act.validate(ws, ws.acting, T, ruled(uses=[next(t.code for t in T.rows if t.ref == pebble.ref)]))
check("...nor a thing that is good for nothing in particular (no tags)", v.ok and not v.enabled)
v = act.validate(ws, ws.acting, T, ruled(needs=[{"kind": "thing", "name": "a loose plank", "what": "from a broken cart"}]))
check("nothing to hide behind: the ruling may call for an ordinary thing, which the world can hold", v.ok, v)
part = next((t.code for t in T.rows if t.kind == "part"), None)
road = next(t.code for t in T.rows if t.kind == "road")
chain = [{"n": 1, "target": rope_code, "becomes": "broken"},
         {"n": 2, "target": rope_code, "becomes": "mended", "needs": [1]},
         {"n": 3, "target": road, "becomes": "state", "state": "flooded"},
         {"n": 4, "target": road, "becomes": "access", "state": "closed"},
         {"n": 5, "target": crate_code, "becomes": "believes"},
         {"n": 6, "target": crate_code, "becomes": "hidden_here", "needs": [5]},
         {"n": 7, "target": crate_code, "becomes": "destroyed"},
         {"n": 8, "target": crate_code, "becomes": "broken"}]
v = act.validate(ws, ws.acting, T, ruled(changes=chain))
kept_n = [c.n for c in v.ruling.changes]
why = {c.n: w for c, w in v.dropped}
check("each change is checked in order as one chain", kept_n == [1, 2, 4, 7], (kept_n, why))
check("...a change on a kind it does not land on is dropped, with why", "does not land on" in why.get(3, "") and "does not land on" in why.get(5, ""), why)
check("...and every change that needs one dropped goes with it", "needs a change" in why.get(6, ""), why)
check("...a thing's state is carried along the chain by its lifecycle's own moves: broken then mended stands, destroyed then broken does not",
      2 in kept_n and "destroyed cannot be broken" in why.get(8, ""), why)

# ---- a situation's parts, by the situation ruling's own chain
import random
from engine import pulse, retrieval, situations
from llm.contracts import SituationParts
with ws.operation("test", "a situation") as op:
    st = store.load_world_state() or {}
    for k_, v_ in pulse.empty_state(ws.minutes).items():
        st.setdefault(k_, v_)
    th = {"id": "th594", "title": "The held square", "tier": "rare", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
          "kind": "politics", "groups": ["everyone"]}
    st.setdefault("threads", []).append(th)
    town = pulse.town_of(ws.world, "trading_square")
    folk = retrieval.people_in_town(store, ws.world, town)
    prop = {"people": [{"who": folk[0].id, "stake": "blocks", "want": "left_alone"}, {"who": folk[1].id, "stake": "harmed", "want": "safety"}],
            "evidence": [{"label": "a torn ledger page", "holder": "trading_square", "points_to": folk[0].id, "certainty": "sure"}]}
    acc, _ = situations.check(SituationParts.model_validate(prop), store, ws.world, "rare", random.Random(7), town=town, ways=False,
                              now=ws.minutes, players=(ws.acting,))
    situation_parts.register(store, ws.world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)
check("a situation is set", op.state == "committed")
T = targets.targets_for(ws, ws.acting)
ctx = act.context(ws, T)
seen = {}
real = situation_parts.ruled


def spy(store_, th_, act_, rows, world=None):
    seen.update(th=th_["id"], rows=rows, act=act_)
    k, d = real(store_, th_, act_, rows, world)
    return k[:1], d + [(c, "held back by the test") for c in k[1:]]


situation_parts.ruled = spy
s_parts = [t for t in T.rows if t.code.startswith("s1.")]
ev = next(t.code for t in s_parts if t.kind == "evidence")
harmed = next(t.code for t in s_parts if t.kind == "person" and t.who == folk[1].id)
blocker = next(t.code for t in s_parts if t.kind == "person" and t.who == folk[0].id)
v = act.validate(ws, ws.acting, T, ruled(changes=[{"n": 1, "target": harmed, "becomes": "safe", "because": "force"},
                                                  {"n": 2, "target": blocker, "becomes": "doubts", "about": ev, "because": "evidence"},
                                                  {"n": 3, "target": rope_code, "becomes": "broken", "needs": [2]}]))
situation_parts.ruled = real
check("a situation's changes go to its own ruling, numbered as its parts are", seen.get("th") == "th594"
      and [r_["part"] for r_ in seen.get("rows", [])] == [int(harmed.split(".")[1]), int(blocker.split(".")[1])]
      and seen["rows"][1]["about"] == int(ev.split(".")[1]) and seen["act"]["by"] == ws.acting, seen)
check("...what it drops is dropped here, and what needed it", [c.n for c in v.ruling.changes] == [1]
      and {c.n for c, _ in v.dropped} == {2, 3}, ([c.n for c in v.ruling.changes], v.dropped))
here_code = next((t.code for t in T.rows if t.code.startswith("p") and t.ref in (folk[0].id, folk[1].id)), None)
if here_code is None:
    ws.present = [n for n in ws.residents if n.id in (folk[0].id, folk[1].id)][:1] or ws.present
    T = targets.targets_for(ws, ws.acting)
    ctx = act.context(ws, T)
    here_code = next(t.code for t in T.rows if t.code.startswith("p") and t.ref in (folk[0].id, folk[1].id))
seen.clear()
situation_parts.ruled = spy
v = act.validate(ws, ws.acting, T, ruled(changes=[{"n": 1, "target": here_code, "becomes": "afraid", "because": "force"}]))
situation_parts.ruled = real
who_part = next(t.code for t in T.rows if t.code.startswith("s1.") and t.who == T.get(here_code).ref)
check("a person named by their place here, who is also a situation's part, is held to the situation's rules as that part",
      seen.get("rows") and seen["rows"][0]["part"] == int(who_part.split(".")[1]), seen.get("rows"))

# ---- asked, kept, and reused
stub.act_ruling = {"sense": "cost", "why": "the crates will hide a body", "uses": [crate_code], "stakes": {"check": "stealth", "hard": "fair"},
                   "changes": [{"n": 1, "target": rope_code, "becomes": "broken"}]}
calls.clear()
text = "I hide behind the stack of crates."
first = act.ask(ws, ws.acting, T, "hides behind the crates", text)
check("the ruling is asked in one call, with the act's list in it", len(calls) == 1 and "TARGETS" in calls[0] and crate_code in calls[0]
      and first is not None and first.uses == [crate_code])
with ws.operation("test", "keep") as op:
    act.keep(ws, ws.acting, T, text, first)
check("it is kept for the character in a row of its own, with what it read", op.state == "committed"
      and set(store.load_act_rulings()[ws.acting][-1]["read"]) == {crate.ref, rope.ref} and "act_rulings" not in store.load_world_state())
again = act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), "I hide behind the stack of crates")
check("the same act here, nothing it read changed: the same ruling, with no call, and nothing written to look", again is not None
      and again.uses == first.uses and [c.target for c in again.changes] == [rope_code] and len(calls) == 1, again)
g2 = simlib.campaign("act_ruling_594", fresh=False)
ws2 = g2.scene
ws2.enter("trading_square")
with ws2.operation("test", "reloaded"):
    after = act.kept(ws2, ws2.acting, targets.targets_for(ws2, ws2.acting), text)
check("...and after the save is opened again", after is not None and after.uses == first.uses)
To = targets.targets_for(ws, "another_character")
their = ActRuling.model_validate({"sense": "yes", "why": "theirs"}, context=act.context(ws, To))
with ws.operation("test", "theirs"):
    act.keep(ws, "another_character", To, text, their)
mine_now = act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), text)
theirs_now = act.kept(ws, "another_character", targets.targets_for(ws, "another_character"), text)
check("two characters keep their own rulings for the same act", mine_now is not None and mine_now.why == first.why
      and theirs_now is not None and theirs_now.why == "theirs", (mine_now and mine_now.why, theirs_now and theirs_now.why))
try:
    act.request(ws, "another_character", To, "x", "x")
    refused_other = False
except ValueError:
    refused_other = True
check("...and a ruling is asked only for the scene's own character (one a scene, until multiplayer)", refused_other)
with ws.operation("test", "a new thing lying here"):
    plank = objects.make(store, "trading_square", "a loose plank", "", minute=ws.minutes)
check("a new thing lying here is a changed circumstance even for a ruling that named nothing",
      act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), text) is None)
with ws.operation("test", "the plank goes"):
    objects.change(store, store.load_entity(plank.ref), "gone", ws.minutes)
check("...and gone again, the scene is as it was", act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), text) is not None)
with ws.operation("test", "a changed thing"):
    objects.change(store, store.load_entity(rope.ref), "broken", ws.minutes)
changed = act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), text)
check("a thing it read changed (the rope broken): a changed circumstance, asked again", changed is None)

no_text = "I fly up onto the guildhall roof."
stub.act_ruling = {"sense": "no", "why": "no wings", "answer": "You leap, and the ground keeps you.", "requires": ["flight"]}
T = targets.targets_for(ws, ws.acting)
nope = act.ask(ws, ws.acting, T, "flies onto the roof", no_text)
with ws.operation("test", "keep a no"):
    act.keep(ws, ws.acting, T, no_text, nope)
still = act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), no_text)
check("a no is kept, and stays a no", still is not None and still.sense == "no" and still.answer == nope.answer)
ws.player.character.capabilities = list(getattr(ws.player.character, "capabilities", []) or []) + ["flight"]
winged = act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), no_text)
ws.player.character.capabilities = [c for c in ws.player.character.capabilities if c != "flight"]
check("...until the character can do what they could not: then it is asked again", winged is None)
climb_text = "I climb the stack of crates to the roof."
T = targets.targets_for(ws, ws.acting)
crate_code = next(t.code for t in T.rows if t.ref == crate.ref)
stub.act_ruling = {"sense": "no", "why": "the crates would not bear it", "answer": "The top crate shifts under your hand.", "uses": [crate_code]}
no_on = act.ask(ws, ws.acting, T, "climbs the crates", climb_text)
with ws.operation("test", "keep a no that rested on a thing"):
    act.keep(ws, ws.acting, T, climb_text, no_on)
    objects.change(store, store.load_entity(crate.ref), "broken", ws.minutes)
check("a no that rested on a thing is asked again once that thing has changed", no_on.uses == [crate_code]
      and act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), climb_text) is None)

from llm.gateway import LLMError
was = stub.a_ActRuling
def fail(u, k):
    raise LLMError("the model failed")
stub.a_ActRuling = fail
gone_wrong = act.ask(ws, ws.acting, targets.targets_for(ws, ws.acting), "does a thing", "I do a new thing.")
stub.a_ActRuling = was
check("a failed call gives no ruling (never one made up to roll on)", gone_wrong is None)

# ---- the kept, capped and let go
was_cap = dict(act.A["kept"])
act.A["kept"]["per_character"] = 3
T = targets.targets_for(ws, ws.acting)
plain = ActRuling.model_validate({"sense": "yes"}, context=act.context(ws, T))
with ws.operation("test", "many"):
    for i in range(5):
        act.keep(ws, ws.acting, T, f"I whistle tune number {i}.", plain)
rows = store.load_act_rulings()[ws.acting]
check("a character's kept rulings are capped, the oldest out", len(rows) == 3 and rows[-1]["key"] == act.words_key("I whistle tune number 4."))
act.A["kept"]["per_character"] = was_cap["per_character"]
store.meta.minutes += act.A["kept"]["days"] * 1440 + 1
store.save_meta()
with ws.operation("test", "much later"):
    act.keep(ws, ws.acting, T, "I whistle once more.", plain)
rows = store.load_act_rulings()[ws.acting]
check("...and one unused past its days is let go", [r_["key"] for r_ in rows] == [act.words_key("I whistle once more.")], [r_["key"] for r_ in rows])
check("act.yaml passes its startup check", act.problems() == [])
act.A["kept"]["days"] = 0
check("...and a cap of 0 fails it", len(act.problems()) == 1)
act.A["kept"]["days"] = was_cap["days"]
check("the words the reuse rule compares leave the filler out", act.words_key("I try to hide behind the crates!") == act.words_key("hide behind crates"))
with ws.operation("test", "used again") as op:
    act.use(ws, ws.acting, "I whistle once more.")
check("a kept ruling that stands again is marked used, in the act's own operation", op.state == "committed"
      and store.load_act_rulings()[ws.acting][-1]["used"] == ws.minutes)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

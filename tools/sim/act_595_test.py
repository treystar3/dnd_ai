"""(f595) act(): the one ruling outside combat (engine/act.py; docs/design/02 sections 4 and 6), the only path since f603. An improvised
line goes through act(): the targets, the kept ruling or the model's, the engine's check, the ruling kept, what the
world must hold made (never twice), the roll, what changed written through the game's own writers (a part's state, a thing broken or
moved, a person's trust through the scene's own copy, a situation's part by its own rules), an Acted deed in the ledger when anything
was at stake, and the telling, which carries what changed and what the engine refused (never to be shown). A no is told in the world's
words; a failure costs what its kind costs and changes nothing; a partial success makes only what can be half made; a strong success
counts only when a real thing enables it; a road, a companion, or one outside a situation made to act are refused; with no ruling at
all the act is never rolled (it waits for one: f596). Nothing is handed the narrator with a dash.
Run: python tools/sim/act_595_test.py"""
import random
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
import config
from engine import act, checks, features, objects, pools, pulse, regard, retrieval, ruling, situation_parts, situations, targets
from llm.contracts import SituationParts
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_595", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
if not ws.present:
    ws.present = list(ws.residents[:2])
told = []
ws.narrate = lambda event, text="": told.append(event)
with ws.operation("test", "set the scene") as op:
    kind = features.kinds_here(ws.world.places["trading_square"])[0]
    door = features.register(ws, "trading_square", "the cellar door", kind, "a stout door under the steps", "known", "authored")
    crates = objects.make(store, "trading_square", "a stack of crates", "fish crates", minute=ws.minutes)
    store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})   # a world that has begun
check("the scene is set", op.state == "committed")
HERE = list(ws.present)


def other(text, summary=""):
    """A line the interpreter could not name, as play reaches it (scenes/world.py on_other), in an operation of its own."""
    ws.present = list(HERE)                            # the same people about, line to line
    with ws.operation("action:other", text) as op_:
        ws.on_other(types.SimpleNamespace(kind="other", summary=summary or text), text)
    return op_


def code_of(ref, actor=None):
    ws.present = list(HERE)
    return next(t.code for t in targets.targets_for(ws, actor or ws.acting).rows if t.ref == ref)


# ---- the switch
spied = []
real_act = act.act
act.act = lambda ws_, who, words, text: spied.append(("act", text))
other("I wave at the gulls.")
act.act = real_act
check("an improvised line goes through act(), the old path and its switch retired (f603)", spied == [("act", "I wave at the gulls.")], spied)

# ---- a thing made for the act, and never twice
stub.act_ruling = {"sense": "yes", "why": "a plank is easy to find", "needs": [{"kind": "thing", "name": "a loose plank", "what": "off a broken cart"}]}
told.clear()
op = other("I find a plank to wedge the door with.")
planks = [e for e in objects.here(store, "trading_square", ws.minutes) if "plank" in e.name]
check("a thing the act needs is made, real, and told", op.state == "committed" and len(planks) == 1 and told and "loose plank" in told[-1], (op.state, told[-1:]))
op = other("I find a plank to wedge the door with.")
planks = [e for e in objects.here(store, "trading_square", ws.minutes) if "plank" in e.name]
check("...the same act again finds the plank already there: none made twice", len(planks) == 1, planks)

# ---- a part changed: the door barred
checks_roll = checks.roll
checks.roll = lambda odds, rng=None, c=None: ("success", 1)
stub.act_ruling = {"sense": "cost", "why": "a heavy door", "stakes": {"check": "athletics", "hard": "fair"}, "uses": [code_of(door.ref)],
                   "changes": [{"n": 1, "target": code_of(door.ref), "becomes": "state", "state": "barred"}]}
told.clear()
other("I bar the cellar door.")
door = store.load_entity(door.ref)
check("a part's state changed through the parts' own writer, and the telling carries it", "barred" in features.now_of(door, ws.minutes)
      and told and "WHAT IS DIFFERENT NOW" in told[-1], (features.now_of(door, ws.minutes), told[-1:]))
row = next((d for d in reversed(store.load_world_state().get("deeds", [])) if d["kind"] == "acted"), None)
check("...the act is a deed in the ledger, whose it was, with what it changed", row is not None and row.get("by") == ws.acting
      and row.get("changes") == ["state"] and row.get("degree") == "success", row)

# ---- a road is never shut or opened by hand, and what the engine refused is told as not happening
road = next(t for t in targets.targets_for(ws, ws.acting).rows if t.kind == "road")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "fair"},
                   "changes": [{"n": 1, "target": road.code, "becomes": "access", "state": "closed"},
                               {"n": 2, "target": code_of(door.ref), "becomes": "state", "state": "marked"}]}
before_fx = list(store.load_world_state().get("effects", []))
told.clear()
other("I drag a cart across the road out of town and chalk the door.")
check("a road is not closed by hand (a closure nobody keeps to is no closure), nor the way here barred instead; the rest of the act stands",
      store.load_world_state().get("effects", []) == before_fx and "marked" in features.now_of(store.load_entity(door.ref), ws.minutes),
      [e for e in store.load_world_state().get("effects", []) if e not in before_fx])
check("...and the narrator is told what did not happen, never to show it", told and "WHAT DID NOT HAPPEN" in told[-1]
      and "access closed" in told[-1], told[-1:])

# ---- a person moved: trust, outside any situation
ws.present = list(HERE)
p = next(t for t in targets.targets_for(ws, ws.acting).rows if t.code == "p1")
before = regard.of(store.load_npc(p.ref), ws.acting).trust
stub.act_ruling = {"sense": "cost", "stakes": {"check": "persuasion", "hard": "fair"}, "changes": [{"n": 1, "target": "p1", "becomes": "warmer"}]}
other("I help the stallholder lift her awning back up.")
check("one here warms to the character: their trust moved through regard's one writer, on the scene's own copy, kept through the turn",
      regard.of(store.load_npc(p.ref), ws.acting).trust > before)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "intimidation", "hard": "fair"},
                   "changes": [{"n": 1, "target": "p1", "becomes": "hostile"}, {"n": 2, "target": "p1", "becomes": "flees"}]}
told.clear()
trust = regard.of(store.load_npc(p.ref), ws.acting).trust
other("I glare at the stallholder until she runs.")
check("one outside any situation is never made hostile or made to flee by an act: refused, and told as not happening",
      regard.of(store.load_npc(p.ref), ws.acting).trust == trust and "WHAT DID NOT HAPPEN" in told[-1], told[-1:])
ws.player.party = [{"id": "hire_brena", "name": "Brena", "role": "sellsword"}]
Tc = targets.targets_for(ws, ws.acting)
from llm.contracts import ActRuling
v_ = act.validate(ws, ws.acting, Tc, ActRuling.model_validate({"sense": "cost", "changes": [{"n": 1, "target": "c1", "becomes": "grateful"}]},
                                                               context=act.context(ws, Tc)))
ws.player.party = []
check("...nor is a companion moved by a ruling", v_.ruling.changes == [] and "companion" in v_.dropped[0][1], v_.dropped)

# ---- a situation's part changed through its own writer
with ws.operation("test", "a situation") as op:
    st = store.load_world_state() or {}
    th = {"id": "th595", "title": "The held square", "tier": "rare", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
          "kind": "politics", "groups": ["everyone"]}
    st.setdefault("threads", []).append(th)
    town = pulse.town_of(ws.world, "trading_square")
    folk = retrieval.people_in_town(store, ws.world, town)
    prop = {"people": [{"who": folk[2].id, "stake": "harmed", "want": "safety"}],
            "evidence": [{"label": "a torn ledger page", "holder": "trading_square", "points_to": folk[2].id, "certainty": "sure"}]}
    acc, _ = situations.check(SituationParts.model_validate(prop), store, ws.world, "rare", random.Random(7), town=town, ways=False,
                              now=ws.minutes, players=(ws.acting,))
    situation_parts.register(store, ws.world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)
ev = next(t for t in targets.targets_for(ws, ws.acting).rows if t.code.startswith("s") and t.kind == "evidence")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "investigation", "hard": "fair"},
                   "changes": [{"n": 1, "target": ev.code, "becomes": "found", "because": "skill"},
                               {"n": 2, "target": ev.code, "becomes": "tested", "because": "earlier", "needs": [1]}]}
other("I find the ledger page, hold it up to the light and check the hand.")
th = next(x for x in store.load_world_state()["threads"] if x["id"] == "th595")
idx = int(ev.code.split(".")[1]) - 1
check("a situation's part changed through the situation's own writer, by its own rules (found before tested), on its record",
      th["parts"][idx].get("now") == "tested"
      and any(c.get("becomes") == "tested" for c in th.get("changes") or []), (th["parts"][idx], th.get("changes")))

# ---- a no, told in the world's words
stub.act_ruling = {"sense": "no", "why": "no wings", "answer": "You leap, and the ground keeps you.", "requires": ["flight"]}
told.clear()
other("I fly up onto the guildhall roof.")
check("a no is told in the world's words, nothing made", told and "does not happen" in told[-1] and "the ground keeps you" in told[-1], told[-1:])

# ---- a failure costs what its kind costs
checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
crate_code = code_of(crates.ref)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "hard"}, "uses": [crate_code], "fail": "object_breaks",
                   "changes": [{"n": 1, "target": crate_code, "becomes": "moved", "to": code_of(door.ref)}]}
told.clear()
other("I climb the crates to reach the window.")
check("a failure that breaks what it relied on breaks it, and nothing it would have changed is", store.load_entity(crates.ref).state == "broken"
      and "FAILS" in told[-1] and "breaks" in told[-1] and not store.load_entity(crates.ref).data.get("part")
      and "nothing it was meant to change has changed" in told[-1], told[-1:])
hp = pools.current(ws.player.character, "health")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "hard"}, "fail": "hurt"}
other("I jump the gap between the stalls.")
check("...a failure that hurts takes the share of health its kind gives", pools.current(ws.player.character, "health") < hp)

# ---- a partial success makes only what can be half made
checks.roll = lambda odds, rng=None, c=None: ("partial", 50)
with ws.operation("test", "another crate") as op:
    box = objects.make(store, "trading_square", "a tea chest", "", minute=ws.minutes)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "fair"},
                   "changes": [{"n": 1, "target": code_of(door.ref), "becomes": "state", "state": "lit"},
                               {"n": 2, "target": code_of(box.ref), "becomes": "broken"}]}
told.clear()
marks_before = list(store.load_place("trading_square").marks)
other("I light a lamp by the door and kick the tea chest apart.")
check("a partial success makes only a part's state, and tells the rest as not happening", "lit" in features.now_of(store.load_entity(door.ref), ws.minutes)
      and store.load_entity(box.ref).state == "here" and "half works" in told[-1] and "WHAT DID NOT HAPPEN" in told[-1], told[-1:])
check("...and what the words read as (a thing broken) does not land when the break itself was refused: no mark, nothing told (f603)",
      not any("broken" in m for m in store.load_place("trading_square").marks if m not in marks_before) and "broken: light" not in told[-1],
      store.load_place("trading_square").marks[-2:])
check("nothing handed the narrator carries a dash", all(" - " not in x and "\u2014" not in x for x in told), told[-1:])
n_deeds = len(store.load_world_state()["deeds"])
stub.act_ruling = {"sense": "yes", "why": "easy"}
other("I lean on the rail and watch the gulls.")
check("a plain yes that changes nothing is no deed (the ledger keeps what the world could notice)", len(store.load_world_state()["deeds"]) == n_deeds)
other("I wave at the gulls once more.")
check("...one whose words make something true besides (a signal talked of, f603) is", len(store.load_world_state()["deeds"]) == n_deeds + 1)

# ---- a strong success only with something real enabling it
checks.roll = lambda odds, rng=None, c=None: ("strong success", 1)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "fair"}}
other("I sprint across the square.")
row = next(d for d in reversed(store.load_world_state()["deeds"]) if d["kind"] == "acted")
check("a strong success with nothing real to enable it counts as a success (the owner, 2026-11-11)", row["degree"] == "success", row)
with ws.operation("test", "a rope") as op:
    rope = objects.make(store, "trading_square", "a coil of rope ladder", "", minute=ws.minutes)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "athletics", "hard": "fair"}, "uses": [code_of(rope.ref)]}
other("I swing over the wall on the rope ladder.")
row = next(d for d in reversed(store.load_world_state()["deeds"]) if d["kind"] == "acted")
check("...with a real thing that enables it, it stands", row["degree"] == "strong success", row)
checks.roll = checks_roll

# ---- no ruling at all
was = stub.a_ActRuling
def broken(u, k):
    raise LLMError("the model failed")
stub.a_ActRuling = broken
n_deeds = len(store.load_world_state()["deeds"])
other("I do something nobody has ruled on.")
stub.a_ActRuling = was
check("with no ruling the act is never rolled: no deed, nothing kept, and it waits for its ruling (f596)",
      len(store.load_world_state()["deeds"]) == n_deeds and len(act.waiting(ws, ws.acting)) == 1
      and act.kept(ws, ws.acting, targets.targets_for(ws, ws.acting), "I do something nobody has ruled on.") is None)
check("act.yaml passes its startup check", act.problems() == [])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

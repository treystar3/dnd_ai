"""(f624) A ruling no longer names its feat (docs/design/19 section 14). Measured on the real model, the field inside the ruling named
a feat on 44 of 99 lines that are none, shrank the heaviest sizes and made the ruling write less of itself (`why`, `requires`). So
both rulings ask what they asked before f623, and the body's table takes a feat as a reading of its own (engine/body.py reading:
what an attempt asks of the body, read from the player's words). No call makes that reading yet: until one does an attempt stands
as ruled, and the table, the fall and the warned death answer whoever hands them a reading.
Run: python tools/sim/feat_out_624_test.py"""
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, body, checks, pools, pulse, ruling, targets
from llm import contracts
from llm.contracts import ActRuling, Ruling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("feat_out_624", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
c = ws.player.character
for a in ("strength", "dexterity", "constitution"):
    setattr(c.attributes, a, 10)
c.equipment = {}
c.health = None
T = targets.targets_for(ws, ws.acting)
ctx = act.context(ws, T)

# ---- the rulings ask what they asked before
check("neither ruling's contract holds a feat", "feat" not in ActRuling.model_fields and "feat" not in Ruling.model_fields
      and not hasattr(contracts, "Feat"))
asked = [act.request(ws, ws.acting, T, "lift the trough", "I lift the trough."), ruling.request(ws, "lift the trough", "I lift the trough.")]
check("neither request lists the feats and neither instruction asks for one",
      not any("FEATS" in a for a in asked) and "feat:" not in act.SYSTEM and "feat:" not in ruling.SYSTEM)
schema = act.shape(ws, T).model_json_schema()
check("the act's grammar has no feat to write, in a yes or in a no",
      all("feat" not in br["properties"] and "feat" not in br["required"] for br in schema["anyOf"]), [br["required"] for br in schema["anyOf"]])
check("...and the road's ruling is written against its own contract again", not hasattr(ruling, "shape") and "feats" not in ctx)
old = ActRuling.model_validate({"sense": "yes", "works": "x", "feat": {"kind": "lift", "size": 900}}, context=ctx)
check("a ruling kept while the field stood still reads, and its feat is not read", old.sense == "yes" and not hasattr(old, "feat"))

# ---- a feat is a reading of its own
check("a reading is a kind from the table and a size, or none", body.read("Lift ", 300) == body.Feat("lift", 300) and body.read() == body.Feat()
      and body.Feat().kind == "none" and body.read("none", 9).size == 0)
def refused(*a):
    try:
        body.read(*a)
        return False
    except ValueError:
        return True
check("...a kind the table does not hold, or a feat with no size, is no reading", refused("wingspan", 3) and refused("lift", 0) and refused("lift"))
check("nothing reads an attempt's feat yet: none, whatever is tried",
      all(body.reading(ws, ws.acting, t) == body.Feat() for t in ("I lift the granary door off its hinges.", "I jump from the bell tower.", "I haggle.")))
R = lambda **k: ActRuling.model_validate({"sense": "cost", "why": "x", "works": "It is done.", "stakes": {"check": "strength", "hard": "fair"}, **k},
                                         context=ctx)
me = body.of_character(c)
check("the table judges the reading it is handed, and nothing where it is handed none",
      body.judge(me, set(), R()).how == "none" and body.judge(me, set(), R(), body.Feat()).how == "none"
      and body.judge(me, set(), R(), body.read("lift", 900)).how == "past" and body.judge(me, set(), R(), body.read("breath", 45)).how == "effort")
v0, v1 = act.validate(ws, ws.acting, T, R()), act.validate(ws, ws.acting, T, R(), body.read("lift", 900))
check("the engine's check on a ruling: as ruled with no reading; past the body with one, in the table's words",
      v0.ok and v0.ruling.stakes.hard == "fair" and v0.body.how == "none" and not v1.ok and v1.answer == body.K["lift"]["past"],
      (v0.ok, v1.ok, v1.answer))

# ---- in play: the one place a reading comes from
told, rolled, shown = [], [], []
real_narrate, real_roll, real_odds, real_reading = ws.narrate, checks.roll, ruling.odds, body.reading
ws.narrate = lambda event, text="": told.append(event)
ruling.odds = lambda ws_, effect, r: rolled.append(dict(r)) or real_odds(ws_, effect, r)
import ui.console as uc
uc.ledger = lambda *a, **k: shown.append(str(a[0]) if a else "")
def attempt(text, d, feat=None, roll="success"):
    stub.act_ruling = d
    body.reading = (lambda ws_, actor_id, text_: feat) if feat is not None else real_reading
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    told.clear(); rolled.clear(); shown.clear()
    with ws.operation("action:other", text) as op:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".").removeprefix("I ")), text)
    check(f"   (the line stood: {text})", op.state == "committed", op.state)
    return told[-1] if told else ""
door = {"sense": "cost", "why": "x", "works": "It comes away.", "stakes": {"check": "strength", "hard": "fair"}}
said = attempt("I lift the granary door off its hinges.", {**door, "feat": {"kind": "lift", "size": 900}})
check("with no reading an act stands as ruled, on the ruling's own check and difficulty, whatever feat its ruling may still carry",
      rolled == [{"check": "strength", "hard": "fair"}] and "WORKS" in said, (rolled, said[-200:]))
said = attempt("I heave the granary door off its hinges.", door, body.read("lift", 900))
check("...and the same ruling with a reading past the body is never rolled: a no", not rolled and "does not happen" in said, (rolled, said[-200:]))
top = float(pools.maximum(c, "health"))
down = {"sense": "cost", "why": "x", "works": "You are down.", "stakes": {"check": "dexterity", "hard": "fair"}, "fail": "noise"}
attempt("I step off the top of the bell tower.", {**down, "feat": {"kind": "drop", "size": 90}}, roll="failure")
check("a drop no one has read is an act like any other, landed badly or not: rolled, no warning, no health taken",
      rolled and not act.warned(ws, ws.acting) and float(pools.current(c, "health")) == top, (rolled, pools.current(c, "health")))
attempt("I walk off the top of the bell tower.", down, body.read("drop", 90))
check("...and read as ninety feet it is warned of and not made", not rolled and act.warned(ws, ws.acting, 90)
      and any("90" in s for s in shown) and float(pools.current(c, "health")) == top, (rolled, shown))
act.left(ws, ws.acting)
ws.narrate, checks.roll, ruling.odds, body.reading = real_narrate, real_roll, real_odds, real_reading

# ---- the road: the same reading
noted = []
for fn in ("note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: noted.append((_fn, str(a[0]) if a else "")))
hz = {"tier": "normal", "what": "A span of the bridge gone, the river loud below.", "behind": "parth"}
def road_past(d, feat=None):
    stub.ruling = d
    body.reading = (lambda ws_, actor_id, text_: feat) if feat is not None else real_reading
    noted.clear(); rolled.clear()
    checks.roll = lambda odds, rng=None, c=None: ("success", 1)
    ruling.odds = lambda ws_, effect, r: rolled.append(dict(r)) or real_odds(ws_, effect, r)
    ws.get_past(dict(hz), "I keep going")
    checks.roll, ruling.odds, body.reading = real_roll, real_odds, real_reading
span = {"sense": "cost", "why": "x", "stakes": {"check": "dexterity", "hard": "fair"}}
road_past(span)
check("on the road a way past stands as ruled with no reading", rolled == [{"check": "dexterity", "hard": "fair"}], (rolled, noted))
road_past(span, body.read("jump_across", 30))
check("...and with a reading past the body it is no way through: around", not rolled and any("no pushing straight through" in t for _, t in noted),
      (rolled, noted))
def other(fn):
    try:
        fn()
        return False
    except ValueError:
        return True
check("the road's settlement and the act's check are for the scene's own character, and refuse another's",
      ruling.settled(ws, ws.acting, Ruling.model_validate(span, context={})).sense == "cost"
      and other(lambda: ruling.settled(ws, "someone_else", Ruling.model_validate(span, context={}), body.read("jump_across", 30)))
      and other(lambda: act.validate(ws, "someone_else", T, R(), body.read("lift", 900))))

# ---- the measure: a feat case needs a reading
sys.path.insert(0, "tools")
from tools import ruling_eval
case = {"line": "I lift the trough.", "at": "trading_square", "expect": "no", "kind": "feat", "feat": {"kind": "lift", "size": [200, 900]},
        "model": {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"}, "feat": {"kind": "lift", "size": 400}}}
check("the measure hands a feat case's own reading to the table offline, and live leaves the case unread (no call reads a feat)",
      ruling_eval.unread(case, live=True) and not ruling_eval.unread(case, live=False)
      and not ruling_eval.unread({"line": "x", "expect": "no", "kind": "claim"}, live=True)
      and ruling_eval.reading(case) == body.read("lift", 400) and ruling_eval.reading({"line": "x", "expect": "no"}) == body.Feat())
check("...and scores a reading against its case", ruling_eval.named(case, body.read("lift", 400)) == "ok"
      and ruling_eval.named(case, body.read("carry", 400)) == "kind" and ruling_eval.named(case, body.read("lift", 50)) == "size")

if bad:
    print(f"\n{len(bad)} FAILED: {bad}")
    sys.exit(1)
print("\nall ok")

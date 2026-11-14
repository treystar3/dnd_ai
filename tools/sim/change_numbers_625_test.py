"""(f625) The engine numbers a ruling's changes (docs/design/19 section 14, step 2). Both rulings that list changes, the act's
(ActRuling) and a situation's (JudgeVerdict), had the model write each change's number, which `needs` points at. On the real model
every act ruling with two or more changes once numbered them all 1 and was sent back, and a situation's ruling so numbered keeps
its first change alone (the rest dropped as said twice). A number the engine can count is not asked of the model: a change's number
is its place in the list (the first is 1), `needs` names earlier changes by their place, and neither grammar has a number to write.
Run: python tools/sim/change_numbers_625_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, objects, pulse, pulse_prompts, targets
from llm import gbnf
from llm.contracts import ActRuling, JudgeVerdict

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("change_numbers_625", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
with ws.operation("test", "things") as op:
    crate = objects.make(store, "trading_square", "a stack of crates", "fish crates, salt-white", minute=ws.minutes)
check("the scene is set", op.state == "committed")
T = targets.targets_for(ws, ws.acting)
ctx = act.context(ws, T)
thing = next(t.code for t in T.rows if t.ref == crate.ref)
C = lambda **k: {"target": thing, "becomes": "broken", **k}
A = lambda changes: ActRuling.model_validate({"sense": "cost", "works": "It is done.", "changes": changes}, context=ctx)
def sent_back(fn):
    try:
        fn()
        return ""
    except ValueError as e:
        return str(e)
nums = lambda r: [(c.n, c.needs) for c in r.changes]

# ---- the act's ruling
check("an act's changes are numbered by the engine, each by its place", nums(A([C(), C(), C()])) == [(1, []), (2, []), (3, [])])
check("...whatever numbers the answer carries: all 1, as the real model once wrote them, is three changes",
      nums(A([C(n=1), C(n=1), C(n=1)])) == [(1, []), (2, []), (3, [])], sent_back(lambda: A([C(n=1), C(n=1)])))
check("a need names an earlier change by its place", nums(A([C(), C(needs=[1]), C(needs=[1, 2])])) == [(1, []), (2, [1]), (3, [1, 2])])
check("...a need of itself, of a later change or of none there is, is sent back",
      all("earlier" in sent_back(lambda x=x: A(x)) for x in ([C(needs=[1])], [C(needs=[2]), C()], [C(), C(needs=[5])], [C(), C(needs=[0])])),
      [sent_back(lambda x=x: A(x)) for x in ([C(needs=[1])], [C(needs=[2]), C()], [C(), C(needs=[5])], [C(), C(needs=[0])])])
old = A([C(n=4), C(n=9, needs=[4]), C(n=2, needs=[9, 4])])
check("a ruling written with a number of its own on every change, no two alike (one kept in a save from before), has each need"
      " carried over to the new places", nums(old) == [(1, []), (2, [1]), (3, [2, 1])], nums(old))
again = ActRuling.model_validate(old.model_dump(), context=ctx)
check("...and read back from what was kept it is the same ruling", nums(again) == nums(old) and again.model_dump() == old.model_dump())
check("...numbers that began at 0 are numbers of its own too: a need of 1 is the change written 1, the second",
      nums(A([C(n=0), C(n=1, needs=[0]), C(n=2, needs=[1])])) == [(1, []), (2, [1]), (3, [2])],
      sent_back(lambda: nums(A([C(n=0), C(n=1, needs=[0]), C(n=2, needs=[1])]))))
check("...a need naming a number no change carries is sent back, and where some changes carry none the needs are places",
      "earlier" in sent_back(lambda: A([C(n=4), C(n=9, needs=[7])])) and nums(A([C(n=4), C(needs=[1])])) == [(1, []), (2, [1])])
schema = act.shape(ws, T).model_json_schema()
variants = [v for br in schema["anyOf"] for v in (br["properties"]["changes"].get("items") or {}).get("anyOf", [])]
most = int(act.A["most_changes"])
check("the act's grammar has no number to write, in any shape of change, and a need is a place in the list",
      variants and all("n" not in v["properties"] and "n" not in v["required"] for v in variants)
      and all(v["properties"]["needs"]["items"] == {"type": "integer", "minimum": 1, "maximum": most} for v in variants),
      [v["required"] for v in variants][:3])
text = gbnf.grammar(schema)
check("...in the grammar the server is sent, too", '"\\"n\\""' not in text and '"\\"needs\\""' in text, text[:200])
check("the act's instruction asks for no number and says a need is a place", "n: its number" not in act.SYSTEM
      and "by its place in the list (1 for the first)" in act.SYSTEM)

# ---- a situation's ruling: the same numbers, the same way
V = lambda changes: JudgeVerdict.model_validate({"verdict": "partial", "reason": "x", "changes": changes})
P = lambda **k: {"part": 1, "becomes": "open", **k}
check("a situation's changes are numbered by the engine too, and all 1 is three changes, not one",
      nums(V([P(), P(), P()])) == [(1, []), (2, []), (3, [])] == nums(V([P(n=1), P(n=1), P(n=1)])))
check("...with distinct numbers of their own the needs are carried over", nums(V([P(n=3), P(n=7, needs=[3])])) == [(1, []), (2, [1])])
rows = [c.model_dump() for c in V([P(n=1), P(n=1, needs=[1], because="earlier")]).changes]
check("...so the chain that keeps by number is handed each change under a number of its own (asked and kept whole in a situation:"
      " situation_ruling_547_test)", [r["n"] for r in rows] == [1, 2] and rows[1]["needs"] == [1], rows)
js = JudgeVerdict.model_json_schema()
check("the situation ruling's grammar has no number to write, and a need is a place there too", "n" not in js["$defs"]["RulingChange"]["properties"]
      and js["$defs"]["RulingChange"]["properties"]["needs"]["items"] == {"type": "integer", "minimum": 1, "maximum": 12}
      and "n" not in (js["$defs"]["RulingChange"].get("required") or []) and '"\\"n\\""' not in gbnf.grammar(js)
      and '"\\"needs\\""' in gbnf.grammar(js))
check("its instruction asks for no number and says a need is a place", "{n, part" not in pulse_prompts.JUDGE_PARTS_SYSTEM
      and "n numbers them" not in pulse_prompts.JUDGE_PARTS_SYSTEM and "by its place in the list (1 for the first)" in pulse_prompts.JUDGE_PARTS_SYSTEM)
last = V([P() for _ in range(15)])
check("its cap still holds, numbered after it", len(last.changes) == 12 and [c.n for c in last.changes] == list(range(1, 13)))

# ---- in play: the ruling the real model wrote
import types
from engine import checks
told = []
ws.narrate = lambda event, text="": told.append(event)
checks.roll = lambda odds, rng=None, c=None: ("success", 1)
stub.act_ruling = {"sense": "cost", "why": "x", "works": "It is done.", "stakes": {"check": "strength", "hard": "fair"},
                   "changes": [C(n=1, because="force"), C(n=1, because="force")]}
asked = []
real_ask = act.ask
act.ask = lambda *a, **k: asked.append(1) or real_ask(*a, **k)
with ws.operation("action:other", "I set about the place.") as op:
    ws.on_other(types.SimpleNamespace(kind="other", summary="set about the place"), "I set about the place.")
check("an act whose ruling numbers both its changes 1 stands at the first asking, and is not left waiting for a ruling",
      op.state == "committed" and len(asked) == 1 and told and "WORKS" in told[-1] and not act.waiting(ws, ws.acting),
      (op.state, asked, told[-1][-200:] if told else "", act.waiting(ws, ws.acting)))

if bad:
    print(f"\n{len(bad)} FAILED: {bad}")
    sys.exit(1)
print("\nall ok")

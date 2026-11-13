"""(f613) Three fixes the tuning measure found (docs/measure/2026-11-12_phase2_pod.md section 8):
- "beyond": past what anyone could do with what they have, a difficulty past hard on the act's ruling, and the engine makes it a no (the
  guild hall jump and the vault tunnel were ruled a cost in both passes, with a `works` that did the impossible thing). The road's old
  ruling has no such level.
- `because` is required on every change: one left out read as skill, so a surrender won by force was refused (the wrestle, pass 1).
- One stance a person: a person takes at most one change from each group of act.yaml one_a_person (how they stand and what they do;
  how they feel; what they believe), a later one dropped with its reason (the wrestle, pass 2: surrenders, committed and warmer at once).
Run: python tools/sim/act_beyond_613_test.py"""
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, checks, pulse, targets
from llm.contracts import ActRuling, Ruling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_beyond_613", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})
T = targets.targets_for(ws, ws.acting)
schema = act.shape(ws, T).model_json_schema()
yes = schema["anyOf"][0]

# ---- beyond
check("the act's ruling may say an attempt is beyond anyone with what they have", "beyond" in yes["properties"]["stakes"]["properties"]["hard"]["enum"],
      yes["properties"]["stakes"])
check("...the road's old ruling has no such level", "beyond" not in Ruling.model_json_schema()["$defs"]["Stakes"]["properties"]["hard"]["enum"])
check("...and the prompt says what it is", "beyond" in act.SYSTEM and "beyond" in act.A and act.A["beyond"].get("answer"))
JUMP = {"sense": "cost", "why": "a sheer stone wall", "works": "You reach the roof of the guild hall.", "stakes": {"check": "strength", "hard": "beyond"},
        "fail": "hurt", "instead": ["climb the outer stair"]}
r = ActRuling.model_validate(JUMP, context=act.context(ws, T))
v = act.validate(ws, ws.acting, T, r)
check("a ruling that says beyond is a no, told in the world's words with the ruling's own reason, and what could be tried instead", not v.ok
      and v.answer.startswith(act.A["beyond"]["answer"]) and "a sheer stone wall" in v.answer
      and v.instead == ["climb the outer stair"] and "beyond" in v.why, (v.ok, v.answer, v.why))

told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="": told.append(event)
stub.act_ruling = JUMP
real_roll = checks.roll
rolled = []
checks.roll = lambda odds, rng=None, c=None: rolled.append(odds) or ("success", 1)
before = ws.minutes
with ws.operation("action:other", "I jump to the top of the guild hall.") as op:
    ws.on_other(types.SimpleNamespace(kind="other", summary="jump to the top of the guild hall"), "I jump to the top of the guild hall.")
checks.roll = real_roll
check("...in play it is never rolled, never shown done: the act does not happen and a moment passes", op.state == "committed" and not rolled
      and told and "does not happen" in told[-1] and "roof" not in told[-1] and ws.minutes == before + 1, (rolled, told[-1:] if told else ""))
ws.narrate = real_narrate
check("the act's data checks clean", act.problems() == [], act.problems())

# ---- one stance a person: a situation of the act corpus's own shape, the guard set against the act
from tools import ruling_eval as R
b = R.Bench(save="act_beyond_613")
try:
    case = {"line": "I wrestle {person:1} to the ground until they give up the fight.", "at": "trading_square", "expect": "cost",
            "situation": {"tier": "uncommon", "title": "The grain hoard", "people": [{"here": True, "stake": "blocks", "want": "coin", "against": "committed"}],
                          "conditions": [{"kind": "danger", "label": "the hoarders' guard on the granary", "by": "the hoarders", "by_kind": "group"}]},
            "model": {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"}, "works": "They yield.",
                      "changes": [{"n": 1, "target": "@person:1", "becomes": "surrenders", "who": "@person:1", "because": "force"},
                                  {"n": 2, "target": "@person:1", "becomes": "committed", "because": "force"},
                                  {"n": 3, "target": "@person:1", "becomes": "warmer", "because": "force"},
                                  {"n": 4, "target": "@person:1", "becomes": "afraid", "because": "force"}]}}
    b.put(case)
    TT = b.targets()
    variants = act.shape(b.ws, TT).model_json_schema()["anyOf"][0]["properties"]["changes"]["items"]["anyOf"]
    vv = act.validate(b.ws, b.ws.acting, TT, b.act_model(case, TT))
    kept = [c.becomes for c in vv.ruling.changes] if vv.ok else []
    why = {c.becomes: w for c, w in vv.dropped}
    refused_first = {**case, "model": {**case["model"], "changes": [
        {"n": 1, "target": "@person:1", "becomes": "surrenders", "who": "@person:1", "because": "words"},
        {"n": 2, "target": "@person:1", "becomes": "terrified", "because": "force"}]}}
    b.put(refused_first)
    TT2 = b.targets()
    v2 = act.validate(b.ws, b.ws.acting, TT2, b.act_model(refused_first, TT2))
    kept2 = [c.becomes for c in v2.ruling.changes] if v2.ok else []
    why2 = {c.becomes: w for c, w in v2.dropped}
finally:
    b.clear()
    b.close()
check("every change must say what it rests on (because, never left to a default)", variants and all("because" in v["required"] for v in variants)
      and all("" not in v["properties"]["because"]["enum"] for v in variants), [v["required"] for v in variants][:2])
check("a person takes one change of how they stand and what they do: the surrender stands, staying committed against is dropped",
      "surrenders" in kept and "committed" not in kept and "committed" in why and "surrenders" in why["committed"], (kept, why))
check("...and one of how they feel: warmer stands, afraid after it is dropped", "warmer" in kept and "afraid" not in kept and "afraid" in why, (kept, why))
check("...a change the situation refused takes no stance: a surrender by words refused, being terrified by force after it stands",
      kept2 == ["terrified"] and "surrenders" in why2 and "as well as" not in why2.get("surrenders", ""), (kept2, why2))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

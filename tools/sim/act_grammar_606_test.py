"""(f606) The act ruling's grammar, built for the call (docs/measure/2026-11-12_phase2_pod.md: three answers in five failed in the
corpus, a quarter of improvised acts found no ruling in play). Every one of the 77 answers cut off at the answer's limit was a loop in
`fail`, a free string; 28 named a change word that is none; 32 said no without saying what happens instead; some named a target in
words. The grammar the model writes against is now made for the scene: targets by code with only the change words that land on their
kind (never the situation itself), the fail, the check and the capabilities from their lists, a no that must say what happens instead,
and short free text. The engine's own checks stand behind it unchanged, so a ruling validates as it did.
Run: python tools/sim/act_grammar_606_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 6)
simlib.install(stub)
simlib.quiet_console()
from engine import act, checks, features, objects, pulse, retrieval, ruling, situation_parts, situations, targets
from llm import gbnf
from llm.contracts import ActRuling, SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_grammar_606", seed=6, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
ws.present = list(ws.present) or list(ws.residents[:2])
with ws.operation("test", "looters, and a barrel") as op:
    st = store.load_world_state() or {}
    for k, v in pulse.empty_state(ws.minutes).items():
        st.setdefault(k, v)
    th = {"id": "th606", "title": "Looting", "tier": "rare", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Looters.", "effects": []}],
          "kind": "unrest", "groups": ["everyone"], "fallout": {"description": "", "effects": []}}
    st.setdefault("threads", []).append(th)
    prop = {"people": [{"who": ws.present[0].id, "stake": "harmed", "want": "safety"}],
            "conditions": [{"on": "trading_square", "kind": "danger", "label": "looters in the square", "by": "the looting band", "by_kind": "group"}]}
    acc, _ = situations.check(SituationParts.model_validate(prop), store, world, "rare", random.Random(6), town=town, ways=False,
                              now=ws.minutes, players=(ws.acting,))
    situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)
    objects.make(store, "trading_square", "a barrel", minute=ws.minutes)
assert op.state == "committed", op.state

T = targets.targets_for(ws, ws.acting)
Shaped = act.shape(ws, T)
s = Shaped.model_json_schema()
by_kind = {}
for t in T.rows:
    by_kind.setdefault(t.kind, []).append(t.code)
variants = s["anyOf"]
check("the grammar is the act ruling's (its title, so the stand-ins and the log name it), and llama.cpp's converter takes it",
      s.get("title") == "ActRuling" and bool(gbnf.grammar(s)), s.get("title"))

no = next(v for v in variants if v["properties"]["sense"].get("enum") == ["no"])
other = next(v for v in variants if v is not no)
check("a no must say what happens instead: its answer is required and never empty; yes and cost are the other shape",
      "answer" in no["required"] and no["properties"]["answer"].get("minLength") == 1
      and sorted(other["properties"]["sense"]["enum"]) == ["cost", "yes"], (no.get("required"), other["properties"]["sense"]))
props = other["properties"]
check("the fail is one of FAIL, never free text (all 77 answers cut off were a loop there)", props["fail"].get("enum") == list(act.A["fails"]),
      props["fail"])
check("the check is one of CHECKS or an attribute, or none", props["stakes"]["properties"]["check"]["enum"]
      == [""] + sorted(checks.CHECKS) + list(ruling.ATTRS), props["stakes"])
check("what it requires is named from CAPABILITIES", props["requires"]["items"]["enum"] == list(ruling.C), props["requires"])
check("what it uses is named by code", set(props["uses"]["items"]["enum"]) == set(T.codes()), props["uses"])

changes = props["changes"]["items"]["anyOf"]
targets_in = {}
for v in changes:
    for c in v["properties"]["target"]["enum"]:
        targets_in.setdefault(c, []).extend(v["properties"]["becomes"]["enum"])
cond = next(t.code for t in T.rows if t.kind == "condition")
obj = next(t.code for t in T.rows if t.kind == "object")
check("a change names a target by code, with only the words that land on its kind: a condition is lifted, a thing broken or moved",
      sorted(targets_in.get(cond, [])) == sorted(w for w in targets.CH["changes"] if targets.lands_on(w, "condition"))
      and "lifted" in targets_in[cond]
      and "broken" in targets_in.get(obj, []) and "lifted" not in targets_in.get(obj, []), {cond: targets_in.get(cond), obj: targets_in.get(obj)})
check("...and never the situation itself, which no change lands on", not any(c in targets_in for c in by_kind.get("situation", [])),
      [c for c in by_kind.get("situation", []) if c in targets_in])
shape_of = lambda w: next(v for v in changes if w in v["properties"]["becomes"]["enum"])
person_codes = sorted(by_kind.get("person", []))
check("a change a person makes by their own doing names who: surrenders, flees, joins and warns require it, from the people here",
      all("who" in shape_of(w)["required"] and sorted(shape_of(w)["properties"]["who"]["enum"]) == person_codes
          for w in ("surrenders", "flees", "joins", "warns")), shape_of("surrenders"))
empty = lambda sch: sch in ({"enum": [""]}, {"type": "string", "maxLength": 0})
check("...a change the act makes needs no one (who stays empty), and a feeling never names who", empty(shape_of("afraid")["properties"]["who"])
      and "who" not in shape_of("afraid")["required"], shape_of("afraid"))
if by_kind.get("part"):
    check("a change of state names the state it gives, and an access change says open or closed",
          shape_of("state")["properties"]["state"]["enum"] == list(features.F["becomes"]) and "state" in shape_of("state")["required"]
          and shape_of("access")["properties"]["state"]["enum"] == list(targets.CH["changes"]["access"]["args"]), shape_of("access"))
fields = lambda model: set(model.model_fields)
from llm.contracts import ActChange, Need, Stakes
check("the grammar asks for no field the contract lacks, and every field the contract has (a new field is never unwritable)",
      set(props) == fields(ActRuling) and all(set(v["properties"]) == fields(ActChange) for v in changes)
      and set(props["needs"]["items"]["properties"]) == fields(Need) and set(props["stakes"]["properties"]) == fields(Stakes),
      (set(props) ^ fields(ActRuling), [set(v["properties"]) ^ fields(ActChange) for v in changes][:1]))
check("...as many changes as act.yaml allows", props["changes"].get("maxItems") == int(act.A["most_changes"]), props["changes"])
check("free text is short: why, the answer, what to try instead, a change's label",
      props["why"].get("maxLength") and no["properties"]["answer"].get("maxLength") and props["instead"]["items"].get("maxLength")
      and all(v["properties"]["label"].get("maxLength") for v in changes), props["why"])

ctx = act.context(ws, T)
good = {"sense": "cost", "why": "a show of steel", "stakes": {"check": "intimidation", "hard": "fair"}, "fail": "hurt",
        "changes": [{"n": 1, "target": cond, "becomes": "lifted", "because": "force"}]}
a, b = ActRuling.model_validate(good, context=ctx), Shaped.model_validate(good, context=ctx)
check("a ruling validates through the shaped contract exactly as through the act ruling's own", a.model_dump() == b.model_dump()
      and isinstance(b, ActRuling))
try:
    Shaped.model_validate({**good, "changes": [{"n": 1, "target": cond, "becomes": "cleared", "because": "force"}]}, context=ctx)
    stood = True
except ValueError:
    stood = False
check("...and the engine's checks stand behind the grammar: a word that is none is still refused", not stood)

def fits(x, sch) -> bool:
    """The grammar's subset, checked in Python: does this answer fit the shape the model writes against?"""
    if "anyOf" in sch:
        return any(fits(x, a) for a in sch["anyOf"])
    if "enum" in sch:
        return x in sch["enum"]
    t = sch.get("type")
    if t == "object":
        P = sch.get("properties", {})
        return isinstance(x, dict) and all(k in x for k in sch.get("required", [])) and all(k in P and fits(v, P[k]) for k, v in x.items())
    if t == "array":
        return isinstance(x, list) and len(x) <= sch.get("maxItems", 10 ** 6) and all(fits(i, sch.get("items", {})) for i in x)
    if t == "string":
        return isinstance(x, str) and sch.get("minLength", 0) <= len(x) <= sch.get("maxLength", 10 ** 6)
    if t == "integer":
        return isinstance(x, int)
    return True


who = person_codes[-1]
part = (by_kind.get("part") or [None])[0]
fair = [good,
        {"sense": "cost", "why": "steel", "stakes": {"check": "strength", "hard": "fair"}, "fail": "hurt",
         "changes": [{"n": 1, "target": who, "becomes": "surrenders", "who": who, "because": "force"}]},
        {"sense": "no", "why": "no power for it", "answer": "The looters laugh as nothing happens.", "fail": "hurt"},
        {"sense": "yes", "why": "simply done", "uses": [obj], "fail": "noticed", "changes": [{"n": 1, "target": obj, "becomes": "moved",
                                                                                           "because": "skill"}]}]
if part:
    fair.append({"sense": "cost", "why": "a bar", "fail": "hurt", "changes": [{"n": 1, "target": part, "becomes": "state",
                                                                             "state": features.F["becomes"][0], "because": "skill"}]})
check("fair rulings fit the grammar: a lifted danger, a surrender by the one who surrenders, a no that answers, a thing moved, a state",
      all(fits(x, s) for x in fair), [x for x in fair if not fits(x, s)])
unfair = [{**good, "fail": "time_lost, noise, noticed, hurt"},
          {**good, "changes": [{"n": 1, "target": cond, "becomes": "cleared", "because": "force"}]},
          {**good, "changes": [{"n": 1, "target": by_kind["situation"][0], "becomes": "safe"}]},
          {**good, "changes": [{"n": 1, "target": who, "becomes": "surrenders", "because": "force"}]},
          {"sense": "no", "why": "no", "fail": "hurt"}]
check("...and the pod's failures cannot be written: a listed fail, an invented word, the situation itself, a surrender with no one "
      "surrendering, a no with no answer", not any(fits(x, s) for x in unfair), [x for x in unfair if fits(x, s)])

seen = []
from llm import gateway
orig = gateway.generate
def spy(task, system, user, schema, *a, **k):
    seen.append(schema)
    return orig(task, system, user, schema, *a, **k)
gateway.generate = spy
try:
    stub.act_ruling = good
    r = act.ask(ws, ws.acting, T, "drive off the looters", "I drive the looters off.")
finally:
    gateway.generate = orig
check("the act's own call asks with the shaped grammar", seen and "anyOf" in seen[-1].model_json_schema() and r is not None
      and r.changes and r.changes[0].becomes == "lifted", (seen, r))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

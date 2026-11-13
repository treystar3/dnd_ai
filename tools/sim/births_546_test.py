"""(f546) A rare or campaign situation is born with its prose, then given its parts in an operation of their own after the input's
tail, the call asked outside any transaction (the owner, 2026-11-08: "For this implementation, situation parts are generated after the
prose and must agree with established facts"). The parts call is given what the prose established; a person the prose sent away is no
part of it, and words a reader may see that contradict an established line (or could not be checked) are not kept. Each condition
names who or what imposes it, and its effect is its own (of_part). The situation's heart (what threatens it, what is at stake, who or
what controls its conditions) is written once from its original facts. A call that fails is tried again on later inputs, and past its
tries the engine's own parts stand; a rare, campaign or cataclysm situation with none (an old save) takes the engine's own, with no
call. A normal situation asks nothing, and nothing is born during a fight.
Run: python tools/sim/births_546_test.py"""
import json
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
for fn in ("note", "narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
import random
from engine import operation, pulse, pulselog, retrieval, situation_parts, situations

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def thread_of(store, tid):
    return next(x for x in store.load_world_state()["threads"] if x["id"] == tid)


def start(store, world, catalog, t, tier, seed=5):
    state = store.load_world_state() or {}
    for k, v in pulse.empty_state(t).items():
        state.setdefault(k, v)
    ids = {x["id"] for x in state.get("threads", [])}
    ok = pulse.start_thread(store, world, catalog, state, t, random.Random(seed), tier=tier, place_id="trading_square", made_by="model")
    store.save_world_state(state)
    return next((x for x in state["threads"] if x["id"] not in ids), None) if ok else None


pulse.P["eventful_chance"] = 0.0                                    # the world starts nothing of its own while the test runs
pulse.P["engine_roll"]["chance"] = 0.0
pulse.P["engine_roll"]["quiet_hours"] = 10 ** 6
for tier in pulse.P["tiers"].values():
    tier["resolved_by_others"] = 0.0
g = simlib.campaign("births_546", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to)
            and pulse.roads.way_round(world, rid, set()))
away = rows[-1]
seen = {}


def parts_answer(u, k):
    seen["u"] = u
    return {"people": [{"who": rows[0].id, "stake": "harmed", "want": "safety"}, {"who": rows[1].id, "stake": "blocks", "want": "left_alone"},
                       {"who": away.id, "stake": "knows", "want": "believed"}],
            "conditions": [{"on": road, "kind": "danger", "label": "wolves on the road", "by": rows[1].id, "by_kind": "person"},
                           {"on": "trading_square", "kind": "prices", "by": "the toll men", "by_kind": "group"},
                           {"on": "trading_square", "kind": "mark", "label": "a burnt gate", "by": "nobody_at_all", "by_kind": "person"}],
            "evidence": [{"label": "a cut rope", "holder": rows[0].id, "points_to": rows[1].id, "certainty": "sure"},
                         {"label": "a sealed letter from the miller", "holder": rows[0].id, "points_to": rows[1].id, "certainty": "they say"}]}


stub.a_SituationParts = parts_answer
stub.canon = lambda u: ({"verdict": "contradicts", "which": 1} if "NEW STATEMENT: a sealed letter" in u else {"verdict": "new", "which": 0})

# ---- a rare birth: due after the world's operation, given its parts after the input's tail
t0 = ws.minutes
th = start(store, world, ws.catalog, t0, "rare")
check("(a rare situation is born)", th is not None)
check("a rare birth is due its parts and has none yet", th.get("parts_due") == 0 and not th.get("parts"), th)
st = store.load_world_state()
row = next(x for x in st["threads"] if x["id"] == th["id"])
row["truth"] = "The miller never wrote a letter to anyone; the gate burned by chance; there are wolves on the road at night."
row["stages"][0].setdefault("effects", []).append({"kind": "leave", "npc": away.id, "text": "left for the coast"})
store.save_world_state(st)
calls0, legacy0, log0 = stub.calls.get("SituationParts", 0), list(operation.LEGACY), len(pulselog.LOG)
import llm.gateway as gw
asked_tasks = []
_generate = gw.generate
def spy(task, system, user, *a, **k):
    asked_tasks.append((task, user))
    return _generate(task, system, user, *a, **k)
gw.generate = spy
ws.turn("I look around.")
gw.generate = _generate
th = thread_of(store, th["id"])
parts = th.get("parts") or []
check("after the input, the parts operation gave it its parts with one call", parts and stub.calls.get("SituationParts", 0) == calls0 + 1
      and "parts_due" not in th, (len(parts), stub.calls.get("SituationParts")))
check("...asked outside any transaction (never a legacy call)", "situation_parts" not in operation.LEGACY[len(legacy0):], operation.LEGACY)
check("...and a parts row in the pulse's log", any(r.get("kind") == "parts" and r.get("thread") == th["id"] for r in list(pulselog.LOG)))
check("the call was given what the prose established", "ALREADY ESTABLISHED" in seen.get("u", "") and "never wrote a letter" in seen["u"],
      seen.get("u", "")[-600:])
people = [a for a in parts if a["kind"] == "person"]
check("a person the prose sent away is no part of it", all(a["who"] != away.id for a in people) and len(people) == 2, people)
check("every person part is a real person whose worry is this situation's",
      all(store.npc_exists(a["who"]) and store.load_npc(a["who"]).concern_from == th["id"] for a in people), people)
ev = [a for a in parts if a["kind"] == "evidence"]
check("evidence whose words contradict an established line is not kept; the rest stands",
      [a["label"] for a in ev] == ["a cut rope"], ev)
conds = [a for a in parts if a["kind"] == "condition"]
by = {a["what"]: (a.get("by"), a.get("by_kind")) for a in conds}
check("a condition's controller: a person of the parts by their id, words for a group, unknown for someone the parts do not hold",
      by.get("danger") == (rows[1].id, "person") and by.get("prices") == ("the toll men", "group") and by.get("mark") == ("", ""), by)
st = store.load_world_state()
own = [e for e in st["effects"] if e.get("thread") == th["id"] and "of_part" in e]
check("every condition's effect is its own (of_part), so one can be lifted alone (a mark is written on the place, not as an effect)",
      sorted(e["of_part"] for e in own) == sorted(i for i, a in enumerate(parts) if a["kind"] == "condition" and a["what"] != "mark"), own)
agreed = [u for task, u in asked_tasks if task == "situation_agree"]
check("(the review) the words a reader may see are checked on the agreement's own task, never the canon check's",
      agreed and not any(task == "canon_check" for task, _ in asked_tasks), [t for t, _ in asked_tasks])
check("(the review) ...and only those: a mark's words are checked, a danger's never are",
      any("NEW STATEMENT: a burnt gate" in u for u in agreed) and not any("wolves on the road" in u.split("NEW STATEMENT:")[-1] for u in agreed),
      agreed)
h = th.get("heart") or {}
check("the heart: the harmful conditions with their controllers and the one who blocks, as threats",
      {(x["kind"], x.get("what", ""), x.get("by", "")) for x in h.get("threats", [])} >= {("condition", "danger", rows[1].id),
                                                                                       ("condition", "prices", "the toll men"),
                                                                                       ("person", "", "")}
      and not any(x.get("what") == "mark" for x in h.get("threats", [])), h)
check("...and the one harmed and the place, at stake", {("person", rows[0].id)} <= {(x["kind"], x.get("who")) for x in h.get("stakes", [])}
      and any(x["kind"] == "place" and x["place"] == th["place"] for x in h.get("stakes", [])), h)
check("(the review) ...the place's town too, for a situation the model wrote", any(x["kind"] == "place" and x.get("town") == town
      for x in h.get("stakes", [])), h)
frozen = json.dumps(h, sort_keys=True)
st = store.load_world_state()
row = next(x for x in st["threads"] if x["id"] == th["id"])
row["parts"][0]["moved"] = "won_over"
situation_parts.register(store, world, st, row, [], ws.minutes, catalog=ws.catalog, ways=True)
check("the heart is written once: the original facts stand however the parts come to stand", json.dumps(row["heart"], sort_keys=True) == frozen)

# ---- a failed call is tried again on later inputs; past its tries the engine's own parts stand
stub.a_SituationParts = lambda u, k: {"people": [], "resources": [], "ties": [], "conditions": [], "evidence": []}
th2 = start(store, world, ws.catalog, ws.minutes, "rare", seed=11)
tries = situations.S["births"]["tries"]
for i in range(tries):
    ws.turn("I look around.")
    got = thread_of(store, th2["id"])
    if i < tries - 1:
        check(f"a failed call leaves the birth due, tried {i + 1} time(s)", got.get("parts_due") == i + 1 and not got.get("parts"), got.get("parts_due"))
got = thread_of(store, th2["id"])
check("past its tries, the engine's own parts stand (and a heart)", got.get("parts_by") == "engine" and "parts_due" not in got
      and "heart" in got, {k: got.get(k) for k in ("parts_by", "parts_due")})

# ---- an old save's situation, a cataclysm, with no parts: the engine's own, with no call
st = store.load_world_state()
npc = rows[2]
old = {"id": "old546", "title": "The long winter", "tier": "cataclysm", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
       "status": "active", "made": ws.minutes - 100, "clues": [{"text": "It came from the north.", "holder": npc.role, "npc": npc.id, "found": False}],
       "paths": [{"id": "p1", "kind": "persuade", "target": npc.id, "name": "Win them over", "done": False}], "stage": 0,
       "stages": [{"description": "Snow.", "effects": []}], "kind": "natural", "groups": ["everyone"]}
st["threads"].append(old)
st["effects"].append({"id": "eff546", "kind": "closed", "place": road, "text": "drifts of snow", "until": ws.minutes + 9 * 1440,
                      "thread": "old546", "value": 0})
store.save_world_state(st)
calls1 = stub.calls.get("SituationParts", 0)
ws.turn("I look around.")
old = thread_of(store, "old546")
op = old.get("parts") or []
check("a cataclysm with no parts takes the engine's own, with no call",
      old.get("parts_by") == "engine" and stub.calls.get("SituationParts", 0) == calls1, old.get("parts_by"))
check("...its people to win over, its closed road (nature's, tagged its own) and its clue's holder",
      [a["kind"] for a in op] == ["person", "condition", "evidence"] and op[0]["who"] == npc.id and op[1]["by_kind"] == "nature"
      and next(e for e in store.load_world_state()["effects"] if e.get("id") == "eff546").get("of_part") == 1, op)
check("...and its heart: the closed road a threat, the place at stake",
      any(x["kind"] == "condition" and x["what"] == "closed" for x in old["heart"]["threats"])
      and any(x["kind"] == "place" for x in old["heart"]["stakes"]), old.get("heart"))

# ---- (f599) a normal birth asks for its parts once a character can meet it; nothing is born during a fight
th3 = start(store, world, ws.catalog, ws.minutes, "normal", seed=13)
check("(a normal situation is born, here, with no birth due yet)", th3 is not None and "parts_due" not in thread_of(store, th3["id"]))
stub.a_SituationParts = parts_answer
calls2 = stub.calls.get("SituationParts", 0)
ws.turn("I look around.")
check("(f599) a normal one where the character stands is met, and asks for its parts", thread_of(store, th3["id"]).get("parts")
      and stub.calls.get("SituationParts", 0) == calls2 + 1, (stub.calls.get("SituationParts", 0), calls2))
th4 = start(store, world, ws.catalog, ws.minutes, "rare", seed=17)
ws.combat = object()
check("nothing is born during a fight", situation_parts.birth(ws, th4["id"]) is False and "parts" not in thread_of(store, th4["id"])
      and thread_of(store, th4["id"]).get("parts_due") == 0)
ws.combat = None
ws.turn("I look around.")
check("...and after it, the birth goes on", thread_of(store, th4["id"]).get("parts"))


def kinds():
    return [getattr(o, "kind", "") for o in ws.line_ops]


def add_effect(tid, kind, place, eid, days=9):
    st = store.load_world_state()
    st["effects"].append({"id": eid, "kind": kind, "place": place, "text": "", "until": ws.minutes + days * 1440, "thread": tid, "value": 10})
    store.save_world_state(st)


# ---- (the review) a situation the engine finds nothing to build from is done with: no operation every input after
st = store.load_world_state()
st["threads"].append({"id": "empty546", "title": "The quiet terror", "tier": "cataclysm", "place": "trading_square",
                      "times": [ws.minutes, ws.minutes + 9 * 1440], "status": "active", "made": ws.minutes, "clues": [],
                      "paths": [{"id": "k", "kind": "kill", "target": "wolf", "spawn": "", "done": False}], "stage": 0,
                      "stages": [{"description": "Fear.", "effects": []}], "kind": "threat", "groups": ["everyone"]})
store.save_world_state(st)
ws.turn("I look around.")
empty = thread_of(store, "empty546")
check("(the review) a situation with nothing to adopt takes none, and is done with", empty.get("parts") == [] and empty.get("parts_by") == "engine"
      and not situation_parts.waiting(store.load_world_state()), empty.get("parts"))
ws.turn("I look around.")
check("(the review) ...so the next input opens no parts operation", not any(k.startswith("parts") for k in kinds()), kinds())

# ---- (the review) a birth whose every part is dropped spends a try and is asked again, never frozen empty
stub.a_SituationParts = lambda u, k: {"conditions": [{"on": "nowhere_keep", "kind": "closed"}]}
th5 = start(store, world, ws.catalog, ws.minutes, "rare", seed=19)
add_effect(th5["id"], "danger", road, "eff546d")
calls5 = stub.calls.get("SituationParts", 0)
ws.turn("I look around.")
got = thread_of(store, th5["id"])
check("(the review) every part dropped: a try spent, no parts, no heart, still due", got.get("parts_due") == 1 and "parts" not in got
      and "heart" not in got, {k: got.get(k) for k in ("parts_due", "parts", "heart")})
for _ in range(tries - 1):
    ws.turn("I look around.")
got = thread_of(store, th5["id"])
check("(the review) ...past its tries, the engine's own parts, and a heart that holds its own danger",
      got.get("parts_by") == "engine" and any(x["kind"] == "condition" and x["what"] == "danger" for x in got["heart"]["threats"])
      and stub.calls.get("SituationParts", 0) == calls5 + tries, (got.get("heart"), stub.calls.get("SituationParts", 0) - calls5))

# ---- (the review) a fault in a birth spends a try too, and never undoes another situation's adoption
stub.a_SituationParts = parts_answer
_register = situation_parts.register
def broken(*a, **k):
    raise RuntimeError("a fault while registering")
situation_parts.register = broken
th6 = start(store, world, ws.catalog, ws.minutes, "rare", seed=23)
st = store.load_world_state()
st["threads"].append({"id": "cat546", "title": "The red sky", "tier": "cataclysm", "place": "trading_square",
                      "times": [ws.minutes, ws.minutes + 9 * 1440], "status": "active", "made": ws.minutes, "clues": [], "paths": [],
                      "stage": 0, "stages": [{"description": "Red.", "effects": []}], "kind": "natural", "groups": ["everyone"]})
store.save_world_state(st)
add_effect("cat546", "closed", road, "eff546c")
calls6 = stub.calls.get("SituationParts", 0)
ws.turn("I look around.")
check("(the review) a birth that faults: its try spent in an operation of its own", thread_of(store, th6["id"]).get("parts_due") == 1
      and "parts:missed" in kinds(), (thread_of(store, th6["id"]).get("parts_due"), kinds()))
check("(the review) ...while the adoption beside it stands", thread_of(store, "cat546").get("parts_by") == "engine", thread_of(store, "cat546").get("parts"))
for _ in range(tries + 2):
    ws.turn("I look around.")
check("(the review) ...and it is asked no more than its tries, then the engine's own parts stand",
      stub.calls.get("SituationParts", 0) - calls6 == tries and thread_of(store, th6["id"]).get("parts_by") == "engine",
      stub.calls.get("SituationParts", 0) - calls6)
situation_parts.register = _register

# ---- (the review) a registered birth's heart holds the conditions its own telling laid, that no part holds
th7 = start(store, world, ws.catalog, ws.minutes, "rare", seed=29)
add_effect(th7["id"], "closed", "trading_square", "eff546t")
ws.turn("I look around.")
got = thread_of(store, th7["id"])
check("(the review) the heart holds its telling's own closure beside the parts' conditions",
      any(x.get("effect") == "closed@trading_square" and x["what"] == "closed" for x in (got.get("heart") or {}).get("threats", [])),
      got.get("heart"))

# ---- (the second review) a birth that makes someone new where the player stands: everyone read again inside its operation
from engine import retrieval as _r
written = set()
for pid in _r.town_places(world, town):
    written |= set(world.places[pid].residents or {})
fresh_roles = [r for r in sorted(world.roles) if r not in written and r not in set(situations.S.get("never_roles") or ())
               and r not in {x.role for x in _r.people_in_town(store, world, town)}][:6]
most0 = situations.S["register"].get("new_per_town_day")
situations.S["register"]["new_per_town_day"] = 50
crashed = []
for i, role in enumerate(fresh_roles):
    stub.a_SituationParts = lambda u, k, role=role: {"people": [{"who": role, "stake": "harmed", "want": "safety"}]}
    thx = start(store, world, ws.catalog, ws.minutes, "rare", seed=200 + i)
    try:
        ws.turn("I look around.")
    except Exception as e:
        crashed.append((role, type(e).__name__, str(e)[:120]))
        break
check("(the second review) births that make new people here never write outside an operation", not crashed and len(fresh_roles) >= 4,
      (crashed, fresh_roles))

# ---- (the second review) a birth whose kept parts could none of them be made: rolled back whole, a try spent
situations.S["register"]["new_per_town_day"] = 0
role = next(r for r in sorted(world.roles) if r not in written and r not in set(situations.S.get("never_roles") or ())
            and r not in {x.role for x in _r.people_in_town(store, world, town)})        # a trade the town still has nobody of
stub.a_SituationParts = lambda u, k: {"people": [{"who": role, "stake": "harmed", "want": "safety"}]}
th8 = start(store, world, ws.catalog, ws.minutes, "rare", seed=31)
people0 = len(_r.people_in_town(store, world, town))
ws.turn("I look around.")
got = thread_of(store, th8["id"])
check("(the second review) none of its kept parts made: no parts, no heart, a try spent, still due", "parts" not in got and "heart" not in got
      and got.get("parts_due") == 1 and situation_parts.due(store.load_world_state()) is not None, {k: got.get(k) for k in ("parts", "parts_due")})
check("(the second review) ...and nobody was made for it", len(_r.people_in_town(store, world, town)) == people0
      and not any(x.role == role for x in _r.people_in_town(store, world, town)), role)
situations.S["register"]["new_per_town_day"] = most0

# ---- (the second review) the condition its telling already laid is that part's, never laid twice; one threat for it in the heart
stub.a_SituationParts = parts_answer
th9 = start(store, world, ws.catalog, ws.minutes, "rare", seed=37)
add_effect(th9["id"], "danger", road, "", days=1)                   # its telling's danger, laid for a day only
add_effect(th9["id"], "prices", town, "")                           # and its price rise, which the pulse lays on the town itself
ws.turn("I look around.")                                           # the oldest due first: th8, still due, takes its parts now
check("(the second review) the oldest birth due is asked first", thread_of(store, th8["id"]).get("parts") and "parts" not in thread_of(store, th9["id"]))
ws.turn("I look around.")
got = thread_of(store, th9["id"])
rows9 = [e for e in store.load_world_state()["effects"] if e.get("thread") == th9["id"] and e["kind"] == "danger" and e["place"] == road]
check("(the second review) its telling's danger on the road is the part's, tagged, and no second one laid",
      len(rows9) == 1 and "of_part" in rows9[0], rows9)
check("(the second review) ...and the heart holds one threat for it", sum(1 for x in got["heart"]["threats"] if x["kind"] == "condition"
      and x["what"] == "danger" and x["on"] == road) == 1, got["heart"]["threats"])
check("(the third review) a held danger is the parts' own from then on: it lasts the situation's span, renewed with it",
      rows9[0].get("part") is True and int(rows9[0]["until"]) >= int(got["times"][-1]), (rows9[0], got["times"][-1]))
prices9 = [e for e in store.load_world_state()["effects"] if e.get("thread") == th9["id"] and e["kind"] == "prices" and not e.get("good")]
check("(the third review) a price rise proposed on a place of the town is the one its telling laid on the town: one row, tagged",
      len(prices9) == 1 and "of_part" in prices9[0] and prices9[0]["place"] == town, prices9)
check("(the third review) ...and one threat for it in the heart", sum(1 for x in got["heart"]["threats"] if x["kind"] == "condition"
      and x["what"] == "prices") == 1, [x for x in got["heart"]["threats"] if x["kind"] == "condition"])

# ---- (the fourth review) a telling's price drop is no rise to take over; two rises in one town are one
stub.a_SituationParts = lambda u, k: {"people": [{"who": rows[0].id, "stake": "harmed", "want": "safety"}],
                                      "conditions": [{"on": "trading_square", "kind": "prices"},
                                                     {"on": next(p for p in sorted(_r.town_places(world, town)) if p != "trading_square"),
                                                      "kind": "prices"}]}
th10 = start(store, world, ws.catalog, ws.minutes, "rare", seed=41)
st = store.load_world_state()
st["effects"].append({"kind": "prices", "place": town, "value": -10, "until": ws.minutes + 4 * 1440, "thread": th10["id"], "cause": "a glut"})
store.save_world_state(st)
for _ in range(3):
    if thread_of(store, th10["id"]).get("parts"):
        break
    ws.turn("I look around.")
got = thread_of(store, th10["id"])
p10 = [e for e in store.load_world_state()["effects"] if e.get("thread") == th10["id"] and e["kind"] == "prices" and not e.get("good")]
drop10 = [e for e in p10 if int(e["value"]) < 0]
rise10 = [e for e in p10 if int(e["value"]) > 0]
check("(the fourth review) a part's price rise never takes over its telling's price drop: the drop keeps its own days, a rise is laid",
      got.get("parts") and len(drop10) == 1 and "of_part" not in drop10[0] and not drop10[0].get("part") and len(rise10) == 1
      and "of_part" in rise10[0], p10)
check("(the fourth review) two price rises proposed on two places of one town are one rise, one threat", len(rise10) == 1
      and sum(1 for x in got["heart"]["threats"] if x["kind"] == "condition" and x["what"] == "prices") == 1, got.get("heart"))

# ---- (the second review) a tier no longer born, due by an older rule: adopted, never left waiting
born0 = list(situations.S["births"]["tiers"])
situations.S["births"]["tiers"] = ["campaign"]
st = store.load_world_state()
st["threads"].append({"id": "stale546", "title": "The old due", "tier": "rare", "place": "trading_square", "parts_due": 0,
                      "times": [ws.minutes, ws.minutes + 9 * 1440], "status": "active", "made": ws.minutes, "clues": [], "paths": [],
                      "stage": 0, "stages": [{"description": "Old.", "effects": []}], "kind": "threat", "groups": ["everyone"]})
store.save_world_state(st)
calls9 = stub.calls.get("SituationParts", 0)
ws.turn("I look around.")
check("(the second review) ...takes the engine's own parts, with no call", thread_of(store, "stale546").get("parts_by") == "engine"
      and stub.calls.get("SituationParts", 0) == calls9)
situations.S["births"]["tiers"] = born0

# ---- the same seed twice: the same parts and heart
def again(name):
    g2 = simlib.campaign(name, seed=7, location="trading_square")
    w2 = g2.scene
    w2.enter("trading_square")
    t2 = start(g2.store, w2.world, w2.catalog, w2.minutes, "rare")
    w2.turn("I look around.")
    got = thread_of(g2.store, t2["id"])
    out = json.dumps({"parts": got.get("parts"), "heart": got.get("heart")}, sort_keys=True)
    g2.close()
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    return out
check("the same seed twice gives the same parts and heart", again("births_546a") == again("births_546b"))

g.close()
shutil.rmtree("saves/births_546", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

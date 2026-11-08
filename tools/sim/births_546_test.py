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
row["truth"] = "The miller never wrote a letter to anyone; the gate burned by chance."
row["stages"][0].setdefault("effects", []).append({"kind": "leave", "npc": away.id, "text": "left for the coast"})
store.save_world_state(st)
calls0, legacy0, log0 = stub.calls.get("SituationParts", 0), list(operation.LEGACY), len(pulselog.LOG)
ws.turn("I look around.")
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
h = th.get("heart") or {}
check("the heart: the harmful conditions with their controllers and the one who blocks, as threats",
      {(x["kind"], x.get("what", ""), x.get("by", "")) for x in h.get("threats", [])} >= {("condition", "danger", rows[1].id),
                                                                                       ("condition", "prices", "the toll men"),
                                                                                       ("person", "", "")}
      and not any(x.get("what") == "mark" for x in h.get("threats", [])), h)
check("...and the one harmed and the place, at stake", {("person", rows[0].id)} <= {(x["kind"], x.get("who")) for x in h.get("stakes", [])}
      and any(x["kind"] == "place" and x["place"] == th["place"] for x in h.get("stakes", [])), h)
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

# ---- a normal birth asks nothing; nothing is born during a fight
calls2 = stub.calls.get("SituationParts", 0)
th3 = start(store, world, ws.catalog, ws.minutes, "normal", seed=13)
check("(a normal situation is born)", th3 is not None)
ws.turn("I look around.")
check("a normal birth is never due and asks nothing", th3 is not None and "parts_due" not in thread_of(store, th3["id"])
      and stub.calls.get("SituationParts", 0) == calls2)
stub.a_SituationParts = parts_answer
th4 = start(store, world, ws.catalog, ws.minutes, "rare", seed=17)
ws.combat = object()
check("nothing is born during a fight", situation_parts.birth(ws) is False and not thread_of(store, th4["id"]).get("parts"))
ws.combat = None
check("...and after it, the birth goes on", situation_parts.birth(ws) is True and thread_of(store, th4["id"]).get("parts"))

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

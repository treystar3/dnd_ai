"""(f547) The dungeon master's ruling on an act, checked as a chain (the owner, 2026-11-08: "The model interprets consequential actions
and proposes causally linked changes. The engine validates prerequisites, presence, knowledge, authority, resources, and established
world facts before committing them"; "Belief, feeling, willingness, and action remain distinct"; "A lie changes what someone believes,
never what is true"). The owner's own cases: the bribe with too little coin (the payment and the gate it opened dropped, the anger
stands); the noble shown proof of a forgery, won over, ordering his guard off the road and freeing the prisoner; words alone never
lifting a closure; one who refuses or is committed unmoved by words; a terrified guard who gives way and warns his master; a person not
there never moved; a lifting by one with no say over it dropped; a failed act brings no gain. The check reads and never writes; the
writers keep each change once; a met condition is a certain change with no model call.
Run: python tools/sim/situation_ruling_547_test.py"""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc
for fn in ("note", "narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
import copy
from engine import deeds, events, memory, pulse, regard, retrieval, roads, situation_parts, situations, towns
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("situation_ruling_547", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
if len(rows) < 4:                                                # a carpenter the town takes in, as a situation would make one
    situation_parts.make_person(store, world, ws.catalog, "carpenter", rows[0].location, ws.minutes, "ruling547")
    rows = retrieval.people_in_town(store, world, town)
noble, prisoner, guard, carpenter = rows[0], rows[1], rows[2], rows[3]
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to)
            and roads.way_round(world, rid, set()))
R = situations.S["reasons"]
by = ws.acting
PAY = situations.S["register"]["ways"]["pay"]["rare"]


def fresh(tid="th547"):
    """A rare situation with a noble who blocks, his prisoner, the guard he employs on the road, a carpenter, and a forged letter."""
    st = store.load_world_state() or {}
    for k, v in pulse.empty_state(ws.minutes).items():
        st.setdefault(k, v)
    st["threads"] = [x for x in st.get("threads", []) if x["id"] != tid]
    th = {"id": tid, "title": "The occupied square", "tier": "rare", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
          "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Soldiers hold it.",
          "effects": []}], "kind": "politics", "groups": ["everyone"]}
    st["threads"].append(th)
    prop = {"people": [{"who": noble.id, "stake": "blocks", "want": "left_alone"}, {"who": prisoner.id, "stake": "harmed", "want": "safety"},
                       {"who": guard.id, "stake": "gains", "want": "safety", "condition": "paid"},
                       {"who": carpenter.id, "stake": "can_fix", "want": "safety"}],
            "ties": [{"a": noble.id, "b": guard.id, "tie": "employs"}],
            "conditions": [{"on": road, "kind": "closed", "label": "a chain across the road", "by": guard.id, "by_kind": "person"}],
            "evidence": [{"label": "a forged letter", "holder": "trading_square", "points_to": noble.id, "certainty": "sure"}]}
    acc, dropped = situations.check(SituationParts.model_validate(prop), store, world, "rare", random.Random(7), town=town, ways=True,
                                    now=ws.minutes, players=(by,))
    situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=True)
    store.save_world_state(st)
    return st, th


def num(th, kind, who=""):
    return next(i + 1 for i, a in enumerate(th["parts"]) if a["kind"] == kind and (not who or a.get("who") == who))


def act(kind="persuade", npc="", witnesses=(), coin=0, item="", degree="success", words=None):
    return {"kind": kind, "by": by, "npc": npc, "witnesses": sorted(witnesses), "place": "trading_square", "coin": coin, "item": item,
            "count": 1, "degree": degree, "words_only": (kind in situations.S["rulings"]["words_only_acts"]) if words is None else words}


def ch(n, part, becomes, who=0, because="words", about=0, needs=()):
    return {"n": n, "part": part, "who": who, "becomes": becomes, "because": because, "about": about, "needs": list(needs)}


def why(dropped):
    return [r for _, r in dropped]


st, th = fresh()
N, P, G, C = (num(th, "person", x.id) for x in (noble, prisoner, guard, carpenter))
ROAD, EV = num(th, "condition"), num(th, "evidence")
check("(the situation: four people, the employing tie, the closed road the guard holds, the forged letter)",
      len(th["parts"]) == 7 and th["parts"][ROAD - 1]["by"] == guard.id, [a["kind"] for a in th["parts"]])

# ---- the bribe with too little coin: the payment and what it opened are dropped; the anger stands
w0 = store._writes
kept, dropped = situation_parts.ruled(store, th, act("gift", guard.id, [guard.id], coin=10, words=False),
                                      [ch(1, G, "open", because="coin"), ch(2, ROAD, "lifted", who=G, because="earlier", needs=[1]),
                                       ch(3, G, "angry")])
check("a bribe of 10 copper where the guard asks more: his yes and the gate it opened are dropped, the anger stands",
      [c["n"] for c in kept] == [3] and why(dropped) == [R["unpaid"], R["rests_on"]], (kept, dropped))
check("...and the check wrote nothing", store._writes == w0, (w0, store._writes))
kept, dropped = situation_parts.ruled(store, th, act("gift", guard.id, [guard.id], coin=PAY, words=False),
                                      [ch(1, G, "open", because="coin"), ch(2, ROAD, "lifted", who=G, because="earlier", needs=[1])])
check("...paid what he asks, his yes stands and he lifts the chain he holds", [c["n"] for c in kept] == [1, 2] and not dropped, dropped)

# ---- the persuaded noble: shown the forgery, won over, he orders his guard off the road and frees the prisoner
clue = th["parts"][EV - 1]["clue"]
th["clues"][clue]["found"] = True
chain = [ch(1, N, "believes", because="evidence", about=EV), ch(2, N, "open", because="earlier", needs=[1]),
         ch(3, ROAD, "lifted", who=N, because="earlier", needs=[2]), ch(4, P, "safe", who=N, because="earlier", needs=[2])]
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), chain)
check("the noble shown the found forgery believes it, is won over, has his guard lift the road and frees the prisoner",
      [c["n"] for c in kept] == [1, 2, 3, 4] and not dropped, dropped)
situation_parts.keep_changes(ws, st, th, act("persuade", noble.id, [noble.id]), kept)
store.save_world_state(st)
eff = [e for e in st["effects"] if e.get("thread") == th["id"] and e.get("of_part") == ROAD - 1]
check("...kept through the game's own writers: his willingness, the road's own effect lifted, the prisoner safe",
      th["parts"][N - 1]["willing"][by] == "open" and eff and all(e.get("lifted") for e in eff) and th["parts"][P - 1]["now"] == "safe"
      and th["parts"][ROAD - 1]["now"] == "lifted", (th["parts"][N - 1], eff))
told = [r for r in memory.records(store, noble.id) if r["kind"] == "told" and r["about"] == f"belief:{th['id']}:{N}"]
check("...what he now believes kept as a claim (a told memory), never as what is", len(told) == 1, told)
check("...and the situation's record holds each change once", [x["becomes"] for x in th["changes"]] == ["believes", "open", "lifted", "safe"],
      th.get("changes"))

# ---- words alone never change the world; a crowd that heard is moved, one that did not is not
st, th = fresh()
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id, guard.id]),
                                      [ch(1, ROAD, "lifted", because="words"), ch(2, N, "angry"), ch(3, G, "afraid"), ch(4, P, "warmer")])
check("words alone lift nothing by themselves; the noble and guard who heard are moved; the prisoner, not there, is not",
      [c["n"] for c in kept] == [2, 3] and why(dropped) == [R["words_only"], R["not_heard"]], (kept, dropped))

# ---- one who refuses, or is committed, is not moved by words alone
st, th = fresh()
th["parts"][N - 1]["willing"] = {by: "refusing"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "open")])
check("one who refuses is not won over by words alone", not kept and why(dropped) == [R["still_refusing"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("gift", noble.id, [noble.id], item="salt", words=False),
                                      [ch(1, N, "open", because="goods")])
check("...but something given changes the circumstance", [c["n"] for c in kept] == [1], dropped)
th["parts"][N - 1]["willing"] = {by: "committed"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "open")])
check("one who is committed is not won over by persuasion", not kept and why(dropped) == [R["still_committed"]], dropped)
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, N, "believes", because="evidence", about=EV), ch(2, N, "open", because="earlier", needs=[1])])
check("...only a changed belief moves them", [c["n"] for c in kept] == [1, 2], dropped)
th["parts"][N - 1]["willing"] = {by: "hostile"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, ROAD, "lifted", who=N, because="words")])
check("one set against the player takes no cooperative action", not kept and why(dropped) == [R["unwilling"]], dropped)

# ---- a lie changes what someone believes, never what is true
st, th = fresh()
truth = th["clues"][th["parts"][EV - 1]["clue"]]["true"]
kept, _ = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]), [ch(1, G, "believes", about=0)])
situation_parts.keep_changes(ws, st, th, act("persuade", guard.id, [guard.id]), kept)
check("a lie believed is the guard's belief; the evidence's truth is the engine's, unchanged",
      th["parts"][G - 1]["beliefs"][by][0]["becomes"] == "believes" and th["clues"][th["parts"][EV - 1]["clue"]]["true"] == truth)
kept, dropped = situation_parts.ruled(store, th, act("search", "", [], words=False), [ch(1, EV, "tested", because="force")])
check("...and evidence not yet found cannot be tested", not kept and why(dropped) == [R["no_evidence"]], dropped)

# ---- the terrified guard gives way and warns his master
st, th = fresh()
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "terrified"), ch(2, ROAD, "lifted", who=G, because="earlier", needs=[1]),
                                       ch(3, G, "warns", who=G, about=N, needs=[1])])
check("a terrified guard gives way (lifts his chain) and warns his master", [c["n"] for c in kept] == [1, 2, 3], dropped)
situation_parts.keep_changes(ws, st, th, act("persuade", guard.id, [guard.id]), kept)
warned = [r for r in memory.records(store, noble.id) if r["kind"] == "told" and r["about"].startswith(f"warned:{th['id']}")]
check("...his master, warned, is wary of the player and remembers who told him", th["parts"][N - 1]["willing"][by] == "wary"
      and len(warned) == 1, (th["parts"][N - 1].get("willing"), warned))

# ---- authority and means: only one with a say over it lifts a condition; only a holder gives up goods
st, th = fresh()
kept, dropped = situation_parts.ruled(store, th, act("persuade", carpenter.id, [carpenter.id]),
                                      [ch(1, C, "open"), ch(2, ROAD, "lifted", who=C, because="earlier", needs=[1])])
check("the carpenter, won over, still has no say over the guard's chain", [c["n"] for c in kept] == [1]
      and why(dropped) == [R["no_authority"]], dropped)
from world.loader import Place
r_ = world.roads[road]
stop = roads.make_stop(world, r_.from_, r_.to, 0.5, 60, "", "", "the chain")
world.add_place(Place(**stop["place"]))                          # a stop on the guard's road, where his chain is
kept, dropped = situation_parts.ruled(store, th, dict(act("kill", "", [], words=False), place=stop["id"]),
                                      [ch(1, ROAD, "lifted", because="force")], world=world)
check("...but the player may clear it by force, there on the road", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("kill", "", [], words=False), [ch(1, ROAD, "lifted", because="force")], world=world)
check("(the third review) ...never from the square, away from it", not kept and why(dropped) == [R["not_there"]], dropped)
kept, dropped = situation_parts.ruled(store, th, dict(act("quest_done", "", [], words=False), place=stop["id"]),
                                      [ch(1, ROAD, "lifted", because="force")], world=world)
check("(the third review) ...nor, there, by any act but force against the one who holds it", not kept
      and why(dropped) == [R["no_means"]], dropped)

# ---- a failed act brings no gain
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id], degree="failure"),
                                      [ch(1, G, "open"), ch(2, G, "angry")])
check("a failed persuasion wins no one over, and may anger", [c["n"] for c in kept] == [2] and why(dropped) == [R["failed_act"]], dropped)

# ---- the ruling through the judge: the model's changes, checked and kept
st, th = fresh()
stub.changes = [ch(1, G, "afraid"), ch(2, ROAD, "lifted", because="words")]
stub.verdict = "partial"
ws.present = [store.load_npc(guard.id)]
changed = events.judge(ws, st, th, {"kind": "persuade", "npc": guard.id, "place": "trading_square", "degree": "success", "by": by})
check("the judge, for a situation with parts, keeps the checked changes and drops the rest", changed
      and [x["becomes"] for x in th.get("changes") or []] == ["afraid"] and th["status"] == "active", th.get("changes"))
stub.changes, stub.verdict = [], "no"

# ---- a met condition is a certain change, with no model call
st, th = fresh()
path = next(p for p in th["paths"] if p.get("target") == guard.id) if any(p.get("target") == guard.id for p in th["paths"]) else \
    {"kind": "part", "target": guard.id, "need": "paid"}
situation_parts.met_way(ws, st, th, path, by)
check("a guard paid what he asks is open to the one who paid, and the record says what met it",
      th["parts"][G - 1]["willing"][by] == "open" and th["parts"][G - 1]["met"][by] == "paid", th["parts"][G - 1])
st, th = fresh()
situation_parts.met_way(ws, st, th, {"kind": "persuade", "target": noble.id, "need": ""}, by)
check("...one who blocked it, won over, is open and stands aside: nothing he imposes himself is left (his guard's chain is the guard's)",
      th["parts"][N - 1]["willing"][by] == "open" and th["parts"][N - 1]["met"][by] == "won over", th["parts"][N - 1])

# ---- (the review) what the model ends, what coin buys, what words do, and what a chain may not launder
st, th = fresh()
stub.changes, stub.verdict = [ch(1, ROAD, "lifted", because="words")], "resolved"
ws.present = [store.load_npc(guard.id)]
events.judge(ws, st, th, {"kind": "persuade", "npc": guard.id, "place": "trading_square", "degree": "success", "by": by})
check("(the review) the model's 'resolved' ends nothing, least of all with every change dropped", th["status"] == "active"
      and not th.get("changes"), (th["status"], th.get("changes")))
stub.changes, stub.verdict = [], "no"
kept, dropped = situation_parts.ruled(store, th, act("gift", guard.id, [guard.id], coin=10, words=False),
                                      [ch(1, ROAD, "lifted", who=G, because="coin"), ch(2, ROAD, "lifted", because="coin")])
check("(the review) coin short of the guard's price buys nothing he does, and coin alone lifts nothing by the player's hand",
      not kept and why(dropped) == [R["unpaid"], R["words_only"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("deliver", carpenter.id, [carpenter.id], item="salt", words=False),
                                      [ch(1, ROAD, "lifted", because="words"), ch(2, P, "safe", because="force"), ch(3, C, "grateful", because="goods")])
check("(the review) a delivery's words lift nothing; the player frees no one who was not there; a delivered good was given",
      [c["n"] for c in kept] == [3] and why(dropped) == [R["words_only"], R["not_heard"]], dropped)
th["parts"][N - 1]["willing"] = {by: "refusing"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "warmer"), ch(2, N, "open")])
check("(the review) one who refuses is not talked round in two steps", [c["n"] for c in kept] == [1] and why(dropped) == [R["still_refusing"]],
      dropped)
th["parts"][N - 1]["willing"] = {by: "hostile"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "wary"), ch(2, N, "open")])
check("(the review) ...nor one who is hostile, by words alone (the third review: not even to wary)", not kept
      and why(dropped) == [R["still_refusing"], R["still_refusing"]], dropped)
th["parts"][N - 1]["willing"] = {by: "committed"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, N, "wary"), ch(2, N, "open"), ch(3, N, "believes", because="words"), ch(4, N, "open", needs=[3])])
check("(the review) one who is committed is moved by no step of words, a belief made by words included",
      [c["n"] for c in kept] == [3] and why(dropped) == [R["still_committed"]] * 3, dropped)
th["parts"][N - 1]["willing"] = {}
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "terrified"), ch(2, G, "warns", who=G, about=N, needs=[1]), ch(3, N, "afraid", needs=[2]),
                                       ch(4, N, "flees", who=N, needs=[2])])
check("(the review) the master the guard warned answers at once: afraid, and gone", [c["n"] for c in kept] == [1, 2, 3, 4], dropped)
kept, dropped = situation_parts.ruled(store, th, act("search", "", [noble.id], words=False),
                                      [ch(1, EV, "found", because="force"), ch(2, N, "believes", because="evidence", about=EV, needs=[1])])
check("(the review) evidence found by this act may be shown at once", [c["n"] for c in kept] == [1, 2], dropped)
many = [ch(i + 1, G, "afraid") for i in range(situations.S["rulings"]["most"] + 1)]
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]), many)
check("(the review) past the most a ruling carries, a change is dropped with its reason, never cut silently",
      len(kept) == situations.S["rulings"]["most"] and why(dropped) == [R["too_many"]], dropped)

# ---- (the review) the writers: a mended tie and a found clue kept as the game keeps them
st, th = fresh()
TIE = num(th, "tie")
scene_noble = store.load_npc(noble.id)
ws.residents = [scene_noble] + [x for x in ws.residents if x.id != noble.id]
before = (store.load_npc(noble.id).relations.get(guard.id) or {}).get("score", 0)
situation_parts.keep_changes(ws, st, th, act("persuade", noble.id, [noble.id, guard.id]), [ch(1, TIE, "mended"), ch(2, N, "warmer")])
after = (store.load_npc(noble.id).relations.get(guard.id) or {}).get("score", 0)
check("(the review) a mended tie moves the relation on the copy that is saved, beside the same person's other changes",
      after == before + situations.S["rulings"]["trust"] and (scene_noble.relations.get(guard.id) or {}).get("score") == after, (before, after))
c_i = th["parts"][EV - 1]["clue"]
situation_parts.keep_changes(ws, st, th, act("search", "", [], words=False), [ch(1, EV, "found", because="force")])
check("(the review) a clue found by a ruling is found as the game finds one: the matter touched and answered",
      th["clues"][c_i]["found"] and th.get("touched") and th.get("answered"), th["clues"][c_i])

# ---- (the review) what the model is shown
a_kill = situation_parts.act_of(ws, {"kind": "kill", "creature": "a grey wolf", "rank": "elite", "level": 3, "place": "trading_square"})
check("(the review) the act says what it was: the creature killed", "grey wolf" in a_kill["text"], a_kill)
st, th = fresh()
th["parts"][N - 1]["willing"] = {by: "open", "someone_else": "refusing"}
lines = situation_parts.parts_lines(store, world, th, by)
road_line, noble_line = lines[ROAD - 1], lines[N - 1]
check("(the review) a condition shows who imposes it and in what words; willingness only toward the one acting",
      guard.name in road_line and "a chain across the road" in road_line and "open toward the player" in noble_line
      and "refusing" not in noble_line, (road_line, noble_line))

# ---- (the second review) one rule moves a person set against the player: something beyond words must reach them
def stance(th, k, w, at=None):
    th["parts"][k - 1]["willing"] = {by: w} if w else {}
    th["parts"][k - 1]["willing_at"] = {by: ws.minutes if at is None else at} if w else {}
    th["parts"][k - 1].pop("answered_seq", None)              # (a stance set by hand: the minute stands for when, as in an older save)


st, th = fresh()
talk = act("persuade", noble.id, [noble.id, guard.id])
for w, chain2, label, whys in (("hostile", [ch(1, N, "wary"), ch(2, N, "joins", who=N)], "a hostile noble made wary by words still joins no one",
                                [R["still_refusing"], R["unwilling"]]),
                               ("refusing", [ch(1, N, "terrified"), ch(2, P, "safe", who=N, because="earlier", needs=[1])],
                                "a refusing noble made terrified by words still frees no one", [R["still_refusing"], R["rests_on"]]),
                               ("committed", [ch(1, N, "wary"), ch(2, N, "surrenders", who=N)],
                                "a committed noble made wary still does not surrender", [R["still_committed"], R["unwilling"]])):
    stance(th, N, w)
    kept, dropped = situation_parts.ruled(store, th, talk, chain2)
    check(f"(the second review) {label}: no softer stance launders the one he held (the third review: words make none)", not kept
          and why(dropped) == whys, (kept, dropped))
stance(th, N, "hostile")
kept, dropped = situation_parts.ruled(store, th, talk, [ch(1, N, "warns", who=N, about=G), ch(2, N, "open")])
check("(the second review) his own warning to his guard does not move him", [c["n"] for c in kept] == [1]
      and why(dropped) == [R["still_refusing"]], (kept, dropped))
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id, carpenter.id]),
                                      [ch(1, C, "flees", who=C), ch(2, N, "open", because="earlier", needs=[1])])
check("(the second review) a stranger to him fleeing is no change that concerns him", [c["n"] for c in kept] == [1]
      and why(dropped) == [R["still_refusing"]], (kept, dropped))
kept, dropped = situation_parts.ruled(store, th, talk, [ch(1, G, "flees", who=G), ch(2, N, "open", because="earlier", needs=[1])])
check("(the second review) ...his own man deserting him is, and may bring him to terms", [c["n"] for c in kept] == [1, 2], dropped)

st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True              # a piece found long ago, never named in this act
for w in ("refusing", "hostile", "committed"):
    stance(th, N, w)
    kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                          [ch(1, N, "open", because="evidence"), ch(2, P, "safe", who=N, because="earlier", needs=[1])])
    check(f"(the second review) a {w} noble is not moved by 'evidence' that names no piece", not kept
          and why(dropped) == [R["no_evidence"], R["rests_on"]], dropped)
stance(th, N, "committed")
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "open", because="evidence", about=EV)])
check("(the second review) one committed, shown the found piece by its number, is moved in one step", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, N, "open", because="evidence", about=EV), ch(2, P, "safe", who=N, because="earlier", needs=[1])])
check("(the second review) ...and, moved, frees his prisoner", [c["n"] for c in kept] == [1, 2], dropped)

st, th = fresh()
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "warns", who=G, about=N), ch(2, N, "believes", because="earlier", needs=[1]),
                                       ch(3, N, "open", because="earlier", needs=[2]), ch(4, P, "safe", who=N, because="earlier", needs=[3]),
                                       ch(5, N, "afraid", needs=[1])])
check("(the second review) a warning carries fear to the master, never the player's words: no belief, no yes, no release",
      [c["n"] for c in kept] == [1, 5] and why(dropped) == [R["not_heard"], R["rests_on"], R["rests_on"]], dropped)

st, th = fresh()
fight = act("assault", noble.id, [noble.id], words=False)
for w in ("hostile", "committed"):
    stance(th, N, w)
    kept, dropped = situation_parts.ruled(store, th, fight, [ch(1, N, "surrenders", who=N, because="force")])
    check(f"(the second review) a {w} noble beaten surrenders", [c["n"] for c in kept] == [1], dropped)
stance(th, N, "committed")
kept, dropped = situation_parts.ruled(store, th, act("quest_done", noble.id, [noble.id], words=False), [ch(1, N, "open", because="force")])
check("(the second review) a job done for one committed does not move him", not kept and why(dropped) == [R["still_committed"]], dropped)
stance(th, N, "refusing")
kept, dropped = situation_parts.ruled(store, th, act("quest_done", noble.id, [noble.id], words=False), [ch(1, N, "open", because="force")])
check("(the second review) ...it may move one who only refused", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("quest_done", noble.id, [noble.id], words=False),
                                      [ch(1, P, "safe", because="force")], world=world)
check("(the second review) ...and a job done is no blow struck for the prisoner", not kept and why(dropped) == [R["not_heard"]], dropped)
stance(th, N, "")
stance(th, G, "refusing")
kept, dropped = situation_parts.ruled(store, th, act("bribe", guard.id, [guard.id], coin=PAY, words=False),
                                      [ch(1, ROAD, "lifted", who=G, because="coin")])
check("(the second review) a refusing guard paid his price in full lifts his chain", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("bribe", guard.id, [guard.id], coin=PAY - 1, words=False),
                                      [ch(1, G, "open", because="words")])
check("(the second review) ...short of it, he is not moved", not kept and why(dropped) == [R["still_refusing"]], dropped)
stance(th, G, "hostile")
kept, dropped = situation_parts.ruled(store, th, act("gift", guard.id, [guard.id], item="ale", words=False), [ch(1, G, "open", because="goods")])
check("(the second review) a hostile guard given something he can hold may come round", [c["n"] for c in kept] == [1], dropped)
stance(th, G, "committed")
kept, dropped = situation_parts.ruled(store, th, act("bribe", guard.id, [guard.id], coin=PAY, words=False), [ch(1, G, "open", because="coin")])
check("(the second review) one committed is not bought", not kept and why(dropped) == [R["still_committed"]], dropped)
stance(th, G, "")
kept, dropped = situation_parts.ruled(store, th, act("bribe", noble.id, [noble.id, guard.id], coin=PAY, words=False),
                                      [ch(1, ROAD, "lifted", who=G, because="coin")])
check("(the second review) paying his master for the guard's act is paying for it", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("bribe", noble.id, [noble.id, guard.id], coin=1, words=False),
                                      [ch(1, ROAD, "lifted", who=G, because="coin")])
check("(the second review) ...but the guard's own price still holds", not kept and why(dropped) == [R["unpaid"]], dropped)

st, th = fresh()
stance(th, G, "hostile", at=ws.minutes - 30)
th["changes"] = [{"n": 1, "part": ROAD, "who": N, "becomes": "lifted", "by": by, "act": "persuade", "minute": ws.minutes - 10}]
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]), [ch(1, G, "open")])
check("(the second review) his chain lifted by his master since he set himself against the player: that change moves him",
      [c["n"] for c in kept] == [1], dropped)
th["changes"][0]["minute"] = ws.minutes - 60
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]), [ch(1, G, "open")])
check("(the second review) ...one made before he took that stance does not", not kept and why(dropped) == [R["still_refusing"]], dropped)
situation_parts.keep_changes(ws, st, th, act("bribe", guard.id, [guard.id], coin=PAY, words=False), [ch(1, G, "terrified")])
check("(the second review) a stance kept records when it was taken", th["parts"][G - 1]["willing_at"][by] == ws.minutes,
      th["parts"][G - 1])

st, th = fresh()
kill = {"kind": "kill", "by": by, "npc": "", "witnesses": [], "place": "trading_square", "coin": 0, "item": "", "count": 1,
        "degree": "", "words_only": False, "text": "killed bandit captain (boss) level 4"}
kept, dropped = situation_parts.ruled(store, th, kill, [ch(1, P, "safe", because="force")], world=world)
check("(the second review) the captor killed where the trouble is: the prisoner, not there, is freed by the player's own hand",
      [c["n"] for c in kept] == [1], dropped)
from engine import towns
far = next(pid for pid in sorted(world.places) if pid not in towns.town_places(world, town) and pid not in world.roads
           and pulse.town_of(world, pid) != town)
kept, dropped = situation_parts.ruled(store, th, dict(kill, place=far), [ch(1, P, "safe", because="force")], world=world)
check("(the second review) ...a kill far from it frees no one", not kept and why(dropped) == [R["not_heard"]], (far, dropped))

# ---- (the third review) no stance softened by words, across acts; a hand only where it is; what is so already; the dead warned
st, th = fresh()
for w, soft, reason in (("refusing", "terrified", R["still_refusing"]), ("hostile", "wary", R["still_refusing"]),
                        ("committed", "hostile", R["still_committed"]), ("committed", "wary", R["still_committed"])):
    stance(th, N, w)
    kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, soft)])
    check(f"(the third review) words do not soften one {w} to {soft}, to be finished by the next act", not kept
          and why(dropped) == [reason], dropped)
stance(th, N, "refusing")
kept, dropped = situation_parts.ruled(store, th, act("assault", noble.id, [noble.id], words=False), [ch(1, N, "terrified", because="force")])
check("(the third review) ...force may terrify him", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "hostile")])
check("(the third review) ...and words may still turn a refusal to hostility", [c["n"] for c in kept] == [1], dropped)
stance(th, N, "committed")
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "warns", who=G, about=N), ch(2, N, "terrified", needs=[1]), ch(3, N, "afraid", needs=[1])])
check("(the third review) a warning frightens one committed, and moves him from nothing", [c["n"] for c in kept] == [1, 3]
      and why(dropped) == [R["still_committed"]], dropped)

st, th = fresh()
kept, dropped = situation_parts.ruled(store, th, act("deliver", carpenter.id, [carpenter.id], item="salt", words=False),
                                      [ch(1, C, "grateful", because="goods"), ch(2, ROAD, "lifted", because="earlier", needs=[1]),
                                       ch(3, num(th, "tie"), "broken", because="earlier", needs=[1])], world=world)
check("(the third review) a delivery to the carpenter lifts no chain on a road and breaks no tie between people not there",
      [c["n"] for c in kept] == [1] and why(dropped) == [R["not_there"], R["not_heard"]], dropped)
kept, dropped = situation_parts.ruled(store, th, dict(act("kill", "", [], words=False), place=far), [ch(1, EV, "found", because="force")],
                                      world=world)
check("(the third review) a kill far away finds no letter lying in the square", not kept and why(dropped) == [R["not_there"]], dropped)
th["clues"].append({"text": "The noble paid the forger.", "holder": "", "npc": noble.id, "found": False, "certainty": "sure", "true": True})
th["parts"].append({"kind": "evidence", "holder": noble.id, "held": "person", "points_to": "trading_square", "label": "", "certainty": "sure",
                    "true": True, "clue": len(th["clues"]) - 1, "engine": True})
EV3 = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, act("kill", "", [], words=False), [ch(1, EV3, "found", because="force")], world=world)
check("(the third review) ...nor what the noble knows, he not being there", not kept and why(dropped) == [R["not_there"]], dropped)
th["parts"].append({"kind": "condition", "on": "trading_square", "what": "danger", "label": "the spring flood", "by": "the river",
                    "by_kind": "nature"})
FLOOD = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, act("kill", "", [], words=False), [ch(1, FLOOD, "lifted", because="force")], world=world)
check("(the third review) a flood is not beaten back", not kept and why(dropped) == [R["no_means"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("quest_done", "", [], words=False), [ch(1, FLOOD, "lifted", because="force")], world=world)
check("(the third review) ...it is dammed, by work done where it is", [c["n"] for c in kept] == [1], dropped)

st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
stance(th, N, "committed")
for a_, label in ((act("deliver", noble.id, [noble.id], item="salt", words=False), "salt handed to him"),
                  (act("quest_done", noble.id, [noble.id], words=False), "a job done for him")):
    kept, dropped = situation_parts.ruled(store, th, a_, [ch(1, N, "open", because="evidence", about=EV)])
    check(f"(the third review) one committed, shown the found letter with {label}, is moved by the letter", [c["n"] for c in kept] == [1],
          dropped)
stance(th, N, "")
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id, noble.id]),
                                      [ch(1, G, "believes", because="evidence", about=EV),
                                       ch(2, G, "warns", who=G, because="evidence", about=N, needs=[1])])
check("(the third review) a warning may rest on the evidence shown first", [c["n"] for c in kept] == [1, 2], dropped)
stance(th, N, "hostile")
kept, dropped = situation_parts.ruled(store, th, act("gift", noble.id, [noble.id], coin=1, words=False), [ch(1, N, "open", because="coin")])
check("(the third review) one copper does not buy one set against the player", not kept and why(dropped) == [R["unpaid"]], dropped)

st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
kill_sq = act("kill", "", [], words=False)
kept, _ = situation_parts.ruled(store, th, kill_sq, [ch(1, EV, "destroyed", because="force")], world=world)
situation_parts.keep_changes(ws, st, th, kill_sq, kept)
kept, dropped = situation_parts.ruled(store, th, kill_sq, [ch(1, EV, "found", because="force")], world=world)
check("(the third review) a letter destroyed is not found again", not kept and why(dropped) == [R["no_evidence"]], dropped)
situation_parts.keep_changes(ws, st, th, kill_sq, [ch(1, EV, "found", because="force")])
check("(the third review) ...and nothing writes over its destruction", th["parts"][EV - 1]["now"] == "destroyed", th["parts"][EV - 1])
stance(th, N, "committed")
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, N, "open", because="evidence", about=EV)])
check("(the third review) ...nor shown", not kept and why(dropped) == [R["no_evidence"]], dropped)

st, th = fresh()
th["parts"][ROAD - 1]["now"] = "lifted"
stance(th, G, "refusing")
kept, dropped = situation_parts.ruled(store, th, dict(act("kill", "", [guard.id], words=False), place=stop["id"]),
                                      [ch(1, ROAD, "lifted", because="force"), ch(2, G, "open", because="earlier", needs=[1])], world=world)
check("(the third review) a chain already lifted is lifted by no one again, and that moves no one", not kept
      and why(dropped) == [R["already"], R["rests_on"]], dropped)
th["parts"][ROAD - 1].pop("now")

st, th = fresh()
far_th = next(pid for pid in sorted(world.places) if pid not in towns.town_places(world, town) and pid not in world.roads)
th["place"], th["town"] = far_th, town                       # an engine-built situation: its own place, and the town its ways were laid in
kept, dropped = situation_parts.ruled(store, th, kill, [ch(1, P, "safe", because="force")], world=world)
check("(the third review) the rescue reads where the trouble is from the town its ways were laid in", [c["n"] for c in kept] == [1],
      (far_th, dropped))

st, th = fresh()
stance(th, N, "committed")
store.save_world_state(st)
for _ in range(2):
    d = deeds.log(store, "persuade", ws.minutes, "trading_square", npc=noble.id, degree="strong success", by=by)
    events.after_deed(ws, d)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
check("(the third review) one committed is not won over by a way met: no yes, and the situation goes on",
      th["status"] == "active" and th["parts"][N - 1]["willing"][by] == "committed", (th["status"], th["parts"][N - 1].get("willing")))
check("(the third review) a failed persuasion wins no one over", not events._won_over(
    {"deeds": [{"kind": "persuade", "minute": ws.minutes, "npc": guard.id, "degree": "failure"}] * 3}, 0, guard.id))

st, th = fresh()
gone_p = store.load_npc(prisoner.id)
gone_p.gone = "dead"
store.save_npc(gone_p)
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]), [ch(1, G, "warns", who=G, about=P)])
check("(the third review) no one warns the dead", not kept and why(dropped) == [R["gone"]], dropped)
gone_p.gone = ""
store.save_npc(gone_p)

# ---- (the fourth review) evidence only to one who saw it; ways by the character and since the stance; a hand where it can be
st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
stance(th, N, "committed")
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "warns", who=G, about=N), ch(2, N, "terrified", because="evidence", about=EV, needs=[1]),
                                       ch(3, N, "afraid", because="evidence", about=EV, needs=[1])])
check("(the fourth review) a warned master is not shown the letter by the warning", [c["n"] for c in kept] == [1]
      and why(dropped) == [R["not_heard"], R["not_heard"]], dropped)

st, th = fresh()
st["deeds"] = []                                                 # this section's deeds only
th["made"] = ws.minutes - 300
stance(th, N, "refusing", at=ws.minutes - 200)
store.save_world_state(st)
for i in range(2):
    events.after_deed(ws, deeds.log(store, "persuade", ws.minutes - 100 + i, "trading_square", npc=noble.id, degree="strong success", by=by))
events.after_deed(ws, deeds.log(store, "kill", ws.minutes - 50, "trading_square", creature="rat", by="char_b"))
th = pulse.thread_of(store.load_world_state(), "th547")
check("(the fourth review) words he refused, or another character's, do not win him over for someone else", th["status"] == "active"
      and "char_b" not in (th["parts"][N - 1].get("willing") or {}), (th["status"], th["parts"][N - 1].get("willing")))
st = store.load_world_state()                                    # (the fifth review) through the writers: he refused, was persuaded
th = pulse.thread_of(st, "th547")                                # twice while refusing, then a gift made him only wary
st["deeds"] = []
stance(th, N, "")
refuse = dict(act("persuade", noble.id, [noble.id]), seq=deeds.tick(st))
situation_parts.keep_changes(ws, st, th, refuse, [ch(1, N, "refusing")])
store.save_world_state(st)
for i in range(2):
    events.after_deed(ws, deeds.log(store, "persuade", ws.minutes, "trading_square", npc=noble.id, degree="strong success", by=by))
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
gift = deeds.log(store, "gift", ws.minutes, "trading_square", npc=noble.id, item="salt", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
g_act = situation_parts.act_of(ws, dict(gift, by=by))
kept, dropped = situation_parts.ruled(store, th, g_act, [ch(1, N, "wary", because="goods")])
situation_parts.keep_changes(ws, st, th, g_act, kept)
store.save_world_state(st)
events.after_deed(ws, deeds.log(store, "kill", ws.minutes, "trading_square", creature="rat", by=by))
th = pulse.thread_of(store.load_world_state(), "th547")
check("(the fourth review) ...nor, once a gift has made him only wary, the words he refused before it", kept and th["status"] == "active"
      and th["parts"][N - 1]["willing"][by] == "wary", (dropped, th["status"], th["parts"][N - 1].get("willing")))
events.after_deed(ws, deeds.log(store, "persuade", ws.minutes, "trading_square", npc=noble.id, degree="strong success", by=by))
th = pulse.thread_of(store.load_world_state(), "th547")
check("(the fifth review) ...words since, he answers: won over", th["status"] == "resolved", th["status"])

st, th = fresh()
th["clues"].append({"text": "The noble paid the forger.", "holder": "", "npc": noble.id, "found": False, "certainty": "sure", "true": True})
th["parts"].append({"kind": "evidence", "holder": noble.id, "held": "person", "points_to": "trading_square", "label": "", "certainty": "sure",
                    "true": True, "clue": len(th["clues"]) - 1, "engine": True})
EV4 = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, dict(act("persuade", carpenter.id, [carpenter.id]), place=far),
                                      [ch(1, EV, "destroyed", who=C), ch(2, EV4, "destroyed", who=C)], world=world)
check("(the fourth review) the carpenter, far away, destroys neither the letter in the square nor what the noble knows", not kept
      and why(dropped) == [R["no_means"], R["no_means"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]), [ch(1, EV4, "destroyed", who=N)], world=world)
check("(the fourth review) ...the noble may destroy what he holds himself", [c["n"] for c in kept] == [1], dropped)
th["parts"].append({"kind": "resource", "good": "salt", "holder": guard.id, "state": "stranded", "wanted_by": carpenter.id})
RES = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, dict(act("deliver", noble.id, [noble.id], item="salt", words=False), place=far),
                                      [ch(1, RES, "moved", because="goods")], world=world)
check("(the fourth review) a sack of salt handed to someone else does not move the stranded load", not kept
      and why(dropped) == [R["no_means"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("deliver", carpenter.id, [carpenter.id], item="salt", words=False),
                                      [ch(1, RES, "moved", because="goods")], world=world)
check("(the fourth review) ...handed to the one it is for, it does", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("persuade", guard.id, [guard.id]),
                                      [ch(1, G, "warns", who=G, about=N), ch(2, G, "warns", who=G, about=C)])
check("(the fourth review) one may warn two people", [c["n"] for c in kept] == [1, 2], dropped)

st, th = fresh()
c_ev = th["parts"][EV - 1]["clue"]
th["clues"][c_ev]["found"] = True
kept, dropped = situation_parts.ruled(store, th, dict(act("quest_done", carpenter.id, [carpenter.id], words=False), place=far),
                                      [ch(1, EV, "tested", because="evidence", about=EV), ch(2, EV, "destroyed", because="force")], world=world)
check("(the fourth review) a found letter goes with the player: tested or burnt anywhere", [c["n"] for c in kept] == [1, 2], dropped)
th["clues"][c_ev].update(found=False, destroyed=True)
from engine import matters
store.save_world_state(st)
got = matters.mark_found(ws, store.load_npc(noble.id), [f"clue:{th['id']}:{c_ev}"])
check("(the fourth review) a destroyed piece is never found again by a telling", not got
      and not pulse.thread_of(store.load_world_state(), th["id"])["clues"][c_ev]["found"], got)

st, th = fresh()
th["tier"] = "cataclysm"
stance(th, N, "hostile")
kept, dropped = situation_parts.ruled(store, th, act("gift", noble.id, [noble.id], coin=1, words=False), [ch(1, N, "open", because="coin")])
check("(the fourth review) in a cataclysm too, one copper buys no one set against the player", not kept and why(dropped) == [R["unpaid"]],
      dropped)

st, th = fresh()
stance(th, C, "refusing", at=ws.minutes - 10)
th["paths"] = [{"kind": "part", "target": carpenter.id, "need": "protected", "protected": by, "protected_at": ws.minutes, "done": False}]
kept, dropped = situation_parts.ruled(store, th, act("persuade", carpenter.id, [carpenter.id]), [ch(1, C, "open")])
check("(the fourth review) one who refused, kept safe since as they asked, may come round", [c["n"] for c in kept] == [1], dropped)
th["paths"][0]["protected_at"] = ws.minutes - 20
kept, dropped = situation_parts.ruled(store, th, act("persuade", carpenter.id, [carpenter.id]), [ch(1, C, "open")])
check("(the fourth review) ...not by what was done before they refused", not kept and why(dropped) == [R["still_refusing"]], dropped)

st, th = fresh()
th["parts"].append({"kind": "condition", "on": "trading_square", "what": "prices", "at": town, "label": "grain dear", "by": "", "by_kind": ""})
PR = len(th["parts"])
other = next(pid for pid in sorted(world.places) if pid != "trading_square" and pid not in world.roads and pulse.town_of(world, pid) == town)
kept, dropped = situation_parts.ruled(store, th, dict(act("deliver", carpenter.id, [carpenter.id], item="salt", words=False), place=other),
                                      [ch(1, PR, "lifted", because="goods")], world=world)
check("(the fourth review) a town's price rise is eased anywhere in the town", [c["n"] for c in kept] == [1], (other, dropped))
kept, dropped = situation_parts.ruled(store, th, dict(act("deliver", carpenter.id, [carpenter.id], item="salt", words=False), place=far),
                                      [ch(1, PR, "lifted", because="goods")], world=world)
check("(the fourth review) ...never from another town", not kept and why(dropped) == [R["not_there"]], dropped)
r_far = next(r for rid, r in sorted(world.roads.items()) if pulse.town_of(world, r.from_) != town and pulse.town_of(world, r.to) != town)
th["place"], th["town"] = r_far.from_, town                    # an engine-built threat at a far place, its ways laid in this town
check("(the fourth review) the roads out of a situation's own place are where its trouble is",
      any(world.roads[x] is r_far for x in situation_parts.trouble_near(world, th, th["parts"])[1]))

# ---- (the fifth review) the one shown the evidence acts on it; what a person has answered, in the world's count; and the rest
st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, P, "safe", who=N, because="evidence", about=EV)])
check("(the fifth review) the noble, shown the letter, frees a prisoner who is not there", [c["n"] for c in kept] == [1], dropped)
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, N, "believes", because="evidence", about=EV), ch(2, P, "safe", who=N, because="evidence", needs=[1])])
check("(the fifth review) ...by way of what he now believes", [c["n"] for c in kept] == [1, 2], dropped)

st, th = fresh()
st["deeds"] = []
th["made"] = ws.minutes - 300
pay_way = {"kind": "part", "target": carpenter.id, "need": "paid", "done": False}
th["paths"] = [pay_way]
store.save_world_state(st)
deeds.log(store, "gift", ws.minutes - 200, "trading_square", npc=carpenter.id, coin=PAY - 10, by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.keep_changes(ws, st, th, act("persuade", carpenter.id, [carpenter.id]), [ch(1, C, "open")])
situation_parts.keep_changes(ws, st, th, act("persuade", guard.id, [guard.id, carpenter.id]), [ch(1, G, "warns", who=G, about=C)])
store.save_world_state(st)
deeds.log(store, "gift", ws.minutes - 100, "trading_square", npc=carpenter.id, coin=10, by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
check("(the fifth review) a stance in the player's favour, or another's warning, takes nothing away from what was paid",
      situation_parts.need_met(th["paths"][0], st, th, by), th["parts"][C - 1])

st, th = fresh()
st["deeds"] = []
th["made"] = ws.minutes - 300
store.save_world_state(st)
d1 = deeds.log(store, "persuade", ws.minutes, "trading_square", npc=noble.id, degree="success", by=by)       # all in one minute
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.keep_changes(ws, st, th, situation_parts.act_of(ws, dict(d1, by=by)), [ch(1, N, "refusing")])
store.save_world_state(st)
g2 = deeds.log(store, "gift", ws.minutes, "trading_square", npc=noble.id, item="salt", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.keep_changes(ws, st, th, situation_parts.act_of(ws, dict(g2, by=by)), [ch(1, N, "wary", because="goods")])
store.save_world_state(st)
deeds.log(store, "persuade", ws.minutes, "trading_square", npc=noble.id, degree="success", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
way = {"kind": "persuade", "target": noble.id}
check("(the fifth review) the words he refused in the very act he set himself against do not count, though in the same minute",
      not events.path_met(way, st, th, None, by), situation_parts.answered_seq(th, noble.id, by))

st, th = fresh()
st["deeds"] = []
th["paths"] = [{"kind": "part", "target": carpenter.id, "need": "protected", "done": False, "near": ["trading_square"], "roads": []}]
store.save_world_state(st)
k1 = deeds.log(store, "kill", ws.minutes, "trading_square", creature="wolf", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.killed(ws, st, k1)
situation_parts.keep_changes(ws, st, th, dict(act("persuade", carpenter.id, [carpenter.id]), seq=deeds.tick(st)), [ch(1, C, "refusing")])
check("(the fifth review) kept safe before they refused does not meet their way", not situation_parts.need_met(th["paths"][0], st, th, by))
store.save_world_state(st)
k2 = deeds.log(store, "kill", ws.minutes, "trading_square", creature="wolf", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.killed(ws, st, k2)
kept, dropped = situation_parts.ruled(store, th, act("persuade", carpenter.id, [carpenter.id]), [ch(1, C, "open")])
check("(the fifth review) ...kept safe again since, it moves them", th["paths"][0].get("protected_seq") == k2.get("seq") and [c["n"] for c in kept] == [1],
      (th["paths"][0], dropped))

st, th = fresh()
c_ev = th["parts"][EV - 1]["clue"]
th["clues"][c_ev]["destroyed"] = True
th["parts"][EV - 1]["now"] = "destroyed"
from engine import threads as threads_mod
check("(the fifth review) a destroyed piece is never retold, nor shown on the road", c_ev not in threads_mod.untold(th)["clues"])
store.save_world_state(st)
matters.road_shown(ws, th["id"])
check("(the fifth review) ...the road shows the matter, but finds no destroyed piece",
      not pulse.thread_of(store.load_world_state(), th["id"])["clues"][c_ev]["found"])

st, th = fresh()
th["place"], th["town"] = town, town
th["parts"].append({"kind": "condition", "on": road, "what": "danger", "label": "wolves on the road", "by": "", "by_kind": "creature"})
check("(the fifth review) a situation in the town itself with a road made dangerous: that road is where its trouble is, not every road",
      situation_parts.trouble_near(world, th, th["parts"])[1] == [road], situation_parts.trouble_near(world, th, th["parts"])[1])

st, th = fresh()
th["parts"].append({"kind": "condition", "on": "trading_square", "what": "prices", "at": town, "label": "salt dear", "by": guard.id,
                    "by_kind": "person"})
PR2 = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, dict(act("kill", "", [], words=False), place=other), [ch(1, PR2, "lifted", because="force")],
                                      world=world)
check("(the fifth review) a price rise the guard imposes is not broken by force elsewhere in town", not kept
      and why(dropped) == [R["not_there"]], dropped)
kept, dropped = situation_parts.ruled(store, th, dict(act("deliver", carpenter.id, [carpenter.id], item="salt", words=False), place=other),
                                      [ch(1, PR2, "lifted", because="goods")], world=world)
check("(the fifth review) ...goods brought ease it anywhere in town", [c["n"] for c in kept] == [1], dropped)
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
kept, dropped = situation_parts.ruled(store, th, dict(act("persuade", noble.id, [noble.id]), place=other), [ch(1, EV, "destroyed", who=N)],
                                      world=world)
check("(the fifth review) the noble, with the player, may destroy the letter the player found and carries", [c["n"] for c in kept] == [1],
      dropped)
th["parts"].append({"kind": "resource", "good": "salt", "holder": guard.id, "state": "stranded", "wanted_by": carpenter.id,
                    "request": {"to": carpenter.id, "count": 6}})
RES2 = len(th["parts"])
for a_, label in ((act("deliver", carpenter.id, [carpenter.id], item="salt", words=False), "one sack where six are asked"),
                  (act("deliver", guard.id, [guard.id], item="salt", words=False), "salt handed back to the load's owner")):
    kept, dropped = situation_parts.ruled(store, th, a_, [ch(1, RES2, "moved", because="goods")], world=world)
    check(f"(the fifth review) {label} does not move the load", not kept and why(dropped) == [R["no_means"]], dropped)

st, th = fresh()
st["deeds"] = []
th["made"] = ws.minutes - 300
store.save_world_state(st)
deeds.log(store, "persuade", ws.minutes - 200, "trading_square", npc=noble.id, degree="strong success", by="char_b")
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
check("(the fifth review) a side another character won over counts for the town", events._won_by_someone(st, th, noble.id))
th["parts"][N - 1].setdefault("willing", {})["char_b"] = "hostile"
th["parts"][N - 1].setdefault("answered_seq", {})["char_b"] = deeds.tick(st)
check("(the fifth review) ...not once he has turned against them", not events._won_by_someone(st, th, noble.id))

# ---- (the sixth review) a way's marks made again, what moved them kept theirs, older saves, and the load itself
def stamp(st, th, k, w):                                          # a stance kept through the writer, as a ruling on a deed would keep it
    situation_parts.keep_changes(ws, st, th, dict(act("persuade", th["parts"][k - 1]["who"], [th["parts"][k - 1]["who"]]),
                                                  seq=deeds.tick(st)), [ch(1, k, w)])


st, th = fresh()
st["deeds"] = []
c_ev = th["parts"][EV - 1]["clue"]
th["clues"][c_ev]["found"] = True
th["paths"] = [{"kind": "part", "target": carpenter.id, "need": "told", "done": False, "name": "The carpenter told"}]
stamp(st, th, C, "refusing")
store.save_world_state(st)
speech = th["clues"][c_ev]["text"]
situation_parts.heard(ws, store.load_npc(carpenter.id), speech)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
told_first = th["paths"][0].get("told_seq")
stamp(st, th, C, "refusing")                                      # refused again since: the telling is answered
situation_parts.keep_changes(ws, st, th, dict(act("gift", carpenter.id, [carpenter.id], item="salt", words=False), seq=deeds.tick(st)),
                             [ch(1, C, "wary", because="goods")])
store.save_world_state(st)
check("(the sixth review) a telling answered by a refusal does not meet the way once they are moved",
      told_first and not situation_parts.need_met(th["paths"][0], st, th, by), th["paths"][0])
situation_parts.heard(ws, store.load_npc(carpenter.id), speech)
th = pulse.thread_of(store.load_world_state(), "th547")
check("(the sixth review) ...told again since, it does", th["paths"][0]["done"] or th["status"] == "resolved", (th["paths"][0], th["status"]))

st, th = fresh()
st["deeds"] = []
th["paths"] = [{"kind": "part", "target": carpenter.id, "need": "protected", "done": False, "near": ["trading_square"], "roads": []}]
stamp(st, th, C, "refusing")
store.save_world_state(st)
k3 = deeds.log(store, "kill", ws.minutes, "trading_square", creature="wolf", by=by)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
situation_parts.killed(ws, st, k3)
talk = dict(act("persuade", carpenter.id, [carpenter.id]), seq=deeds.tick(st))
kept, dropped = situation_parts.ruled(store, th, talk, [ch(1, C, "open")])
situation_parts.keep_changes(ws, st, th, talk, kept)
check("(the sixth review) the protection that moved one who refused still meets their way",
      kept and situation_parts.need_met(th["paths"][0], st, th, by), (dropped, th["paths"][0], th["parts"][C - 1].get("answered_seq")))

import json as _json
from storage import migrations
st, th = fresh()
th["made"] = ws.minutes - 300
st["deeds"] = [{"kind": "persuade", "minute": ws.minutes - 100, "place": "trading_square", "npc": noble.id, "degree": "success", "by": by},
               {"kind": "persuade", "minute": ws.minutes - 90, "place": "trading_square", "npc": noble.id, "degree": "success", "by": by},
               {"kind": "gift", "minute": ws.minutes - 50, "place": "trading_square", "npc": noble.id, "item": "salt", "by": by}]
st.pop("seq", None)
th["parts"][N - 1]["willing"], th["parts"][N - 1]["willing_at"] = {by: "wary"}, {by: ws.minutes - 50}
th["paths"] = [{"kind": "persuade", "target": noble.id, "done": False}]
store._put("world_state", _json.dumps(st))
migrations._v16_world_count(store)
st = store.load_world_state()
th = pulse.thread_of(st, "th547")
check("(the sixth review) an older save's deeds are numbered, and the stance it held keeps what it answered",
      [d.get("seq") for d in st["deeds"]] == [1, 2, 3] and st["seq"] == 3 and th["parts"][N - 1]["answered_seq"] == {by: 2}
      and not events.path_met(th["paths"][0], st, th, None, by), (st["deeds"], th["parts"][N - 1].get("answered_seq")))

st, th = fresh()
st["deeds"] = [{"kind": "persuade", "minute": ws.minutes, "place": "trading_square", "npc": noble.id, "degree": "success"}]
d_p = {"kind": "persuade", "minute": ws.minutes, "place": "trading_square", "npc": noble.id, "degree": "success", "by": by,
       "seq": deeds.tick(st)}
st["deeds"].append(d_p)
th["made"] = ws.minutes - 10
th["parts"][N - 1]["willing"], th["parts"][N - 1]["answered_seq"] = {by: "hostile"}, {by: deeds.tick(st)}
check("(the sixth review) a deed naming no one does not win over for the town a side set against the one who did win him",
      not events._won_by_someone(st, th, noble.id))

st, th = fresh()
th["parts"].append({"kind": "resource", "good": "salt", "holder": guard.id, "state": "stranded",
                    "request": {"npc": guard.id, "kind": "deliver", "good": "salt", "to": carpenter.id}})
RES3 = len(th["parts"])
kept, dropped = situation_parts.ruled(store, th, act("deliver", carpenter.id, [carpenter.id], item="salt", words=False),
                                      [ch(1, RES3, "moved", because="goods")], world=world)
check("(the sixth review) one sack of salt is not the stranded load", not kept and why(dropped) == [R["no_means"]], dropped)
kept, dropped = situation_parts.ruled(store, th, act("deliver", carpenter.id, [carpenter.id], item="a load of salt", words=False),
                                      [ch(1, RES3, "moved", because="goods")], world=world)
check("(the sixth review) ...the load itself, carried to them, is", [c["n"] for c in kept] == [1], dropped)

# ---- (the second review) the found writer and what the act shows
st, th = fresh()
th["clues"].append({"text": "The noble paid the forger.", "holder": "", "npc": noble.id, "found": False, "certainty": "sure", "true": True})
th["parts"].append({"kind": "evidence", "holder": noble.id, "held": "person", "points_to": "trading_square", "label": "", "certainty": "sure",
                    "true": True, "clue": len(th["clues"]) - 1, "engine": True})
EV2 = len(th["parts"])
marks = []
real_mark = store.set_memory_state
store.set_memory_state = lambda *a, **k: marks.append(a) or real_mark(*a, **k)
situation_parts.keep_changes(ws, st, th, act("search", "", [], words=False), [ch(1, EV2, "found", because="force")])
me_name = situation_parts.char_name(ws, by)
check("(the second review) a clue found by hand is the finder's own, and its holder has told no one",
      th["clues"][-1]["by"] == me_name and not marks, (th["clues"][-1], marks))
th["clues"][-1]["found"] = False
situation_parts.keep_changes(ws, st, th, act("quest_done", noble.id, [noble.id], words=False), [ch(1, EV2, "found", because="force")])
store.set_memory_state = real_mark
check("(the second review) one its holder gave up is told by them as the player knows them, and their knowing marked told",
      th["clues"][-1]["by"] == store.load_npc(noble.id).label(by) and marks and marks[0][3] == f"told:{by}", (th["clues"][-1], marks))
a_q = situation_parts.act_of(ws, {"kind": "quest_done", "title": "the ledger", "place": "trading_square"})
check("(the second review) the act names its place, never its id", world.places["trading_square"].name in a_q["text"]
      and "trading_square" not in a_q["text"], a_q)
a_b = situation_parts.act_of(ws, {"kind": "offense", "offense": "assault", "target": noble.id, "witnesses": [], "place": "trading_square"})
check("(the second review) one beaten is the one the act was done to, and the act a beating", a_b["npc"] == noble.id
      and a_b["kind"] == "assault" and not a_b["words_only"], a_b)

# ---- the same chain twice gives the same answer
st, th = fresh()
th["clues"][th["parts"][EV - 1]["clue"]]["found"] = True
a1 = situation_parts.ruled(store, copy.deepcopy(th), act("persuade", noble.id, [noble.id]), chain)
a2 = situation_parts.ruled(store, copy.deepcopy(th), act("persuade", noble.id, [noble.id]), chain)
check("the same chain on the same situation gives the same answer", a1 == a2)

g.close()
shutil.rmtree("saves/situation_ruling_547", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

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
from engine import events, memory, pulse, regard, retrieval, roads, situation_parts, situations
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
kept, dropped = situation_parts.ruled(store, th, act("attack", guard.id, [guard.id], words=False),
                                      [ch(1, ROAD, "lifted", because="force")])
check("...but the player may clear it by force", [c["n"] for c in kept] == [1], dropped)

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
check("(the review) ...nor one who is hostile, by words alone", [c["n"] for c in kept] == [1] and why(dropped) == [R["still_refusing"]], dropped)
th["parts"][N - 1]["willing"] = {by: "committed"}
kept, dropped = situation_parts.ruled(store, th, act("persuade", noble.id, [noble.id]),
                                      [ch(1, N, "wary"), ch(2, N, "open"), ch(3, N, "believes", because="words"), ch(4, N, "open", needs=[3])])
check("(the review) one who is committed is moved by no step of words, a belief made by words included",
      [c["n"] for c in kept] == [1, 3] and why(dropped) == [R["still_committed"], R["still_committed"]], dropped)
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


st, th = fresh()
talk = act("persuade", noble.id, [noble.id, guard.id])
for w, chain2, label in (("hostile", [ch(1, N, "wary"), ch(2, N, "joins", who=N)], "a hostile noble made wary by words still joins no one"),
                         ("refusing", [ch(1, N, "terrified"), ch(2, P, "safe", who=N, because="earlier", needs=[1])],
                          "a refusing noble made terrified by words still frees no one"),
                         ("committed", [ch(1, N, "wary"), ch(2, N, "surrenders", who=N)], "a committed noble made wary still does not surrender")):
    stance(th, N, w)
    kept, dropped = situation_parts.ruled(store, th, talk, chain2)
    check(f"(the second review) {label}: no worse stance launders the one he held", [c["n"] for c in kept] == [1]
          and why(dropped) == [R["unwilling"]], (kept, dropped))
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

"""(f545 part 1) The proposal's own fixes, from what f544's runs showed: every condition on help can be met (one the situation gives no
way to meet is lifted, so the person helps freely), a person who wants coin needs no condition of pay, a stance at odds with itself is
refused, a wanted good names one of the situation who wants it, a false piece of evidence stands only beside a true one pointing
elsewhere (else it is true after all), the words "empty" and "blank" are no answer, and the prompt asks for the town's own people first
and for most people to help freely.
Run: python tools/sim/situation_fixes_545_test.py"""
import copy
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import data_check, pulse, retrieval, situations
from engine import pulse_prompts as pp
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("situation_fixes_545", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
a_, b_, c_ = rows[0], rows[1], rows[2]
goods = sorted(situations._goods())
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
R = situations.S["reasons"]


def parts(**kw):
    return SituationParts.model_validate(kw)


def run(p, tier="rare", seed=7):
    return situations.check(p, store, world, tier, random.Random(seed), town=town, ways=True, now=ws.minutes, players=(ws.acting,))


def person(who, stake="harmed", want="safety", **kw):
    return {"who": who, "stake": stake, "want": want, **kw}


def find(acc, **kw):
    return next((a for a in acc if all(a.get(k) == v for k, v in kw.items())), None)


# ---- stances
acc, dropped = run(parts(people=[person(a_.id, "blocks", "road_open"), person(b_.id, "blocks", "goods_moved"), person(c_.id, "blocks", "left_alone")]))
check("one who blocks an end to it and wants the road open or the goods moved is refused, at odds with itself; blocking and wanting to be "
      "left alone stands", [r for _, r in dropped] == [R["contrary"], R["contrary"]] and [a["who"] for a in acc] == [c_.id], (acc, dropped))
acc, _ = run(parts(people=[person(a_.id, "gains", "coin", condition="paid"), person(b_.id, "harmed", "safety", condition="paid")]))
check("one who wants coin needs no condition of pay: the condition is lifted, the person kept, the lifting noted; one who wants safety "
      "keeps theirs", find(acc, who=a_.id)["condition"] == "" and find(acc, who=a_.id).get("lifted") == "paid"
      and find(acc, who=b_.id)["condition"] == "paid" and "lifted" not in find(acc, who=b_.id), acc)

# ---- a wanted good names who wants it
acc, dropped = run(parts(people=[person(a_.id), person(b_.id)], resources=[{"good": goods[0], "state": "wanted"},
                                                            {"good": goods[1], "state": "wanted", "wanted_by": c_.id},
                                                            {"good": goods[2], "state": "wanted", "wanted_by": a_.id},
                                                            {"good": goods[3], "state": "stranded", "wanted_by": a_.id},
                                                            {"good": goods[4], "state": "wanted", "wanted_by": b_.id, "holder": b_.id}]))
check("a wanted good with no wanter, or a wanter who is not of the situation, is refused", [r for _, r in dropped] == [R["no_wanter"]] * 2, dropped)
check("...one wanted by a person of the situation is kept with its wanter; a stranded good's wanter is no part of it",
      find(acc, good=goods[2]) and find(acc, good=goods[2])["wanted_by"] == a_.id and find(acc, good=goods[3])["wanted_by"] == "", acc)
check("...and one 'held' by its own wanter is held by nobody: the wanter wants it, nobody has it to hand",
      find(acc, good=goods[4]) and find(acc, good=goods[4])["holder"] == "" and find(acc, good=goods[4])["wanted_by"] == b_.id, acc)
card = situations.render(acc, store, world, "k545")
line = next((ln for ln in card.splitlines() if situations._goods()[goods[2]].name in ln.lower()), "")
bare = situations.render([{**find(acc, good=goods[2]), "wanted_by": ""}], store, world, "k545")
check("...and the render names who wants it (nobody else of that line could put the name there)", a_.name in line and a_.name not in bare,
      (card, bare))

# ---- conditions that cannot be met are lifted
acc, _ = run(parts(people=[person(a_.id, "can_fix", "safety", condition="told"), person(b_.id, "knows", "believed", condition="given")]))
check("told with no evidence, and given with no good wanted by that person, are lifted: they help freely, the lifting noted",
      find(acc, who=a_.id)["condition"] == "" and find(acc, who=a_.id)["lifted"] == "told"
      and find(acc, who=b_.id)["condition"] == "" and find(acc, who=b_.id)["lifted"] == "given", acc)
acc, _ = run(parts(people=[person(a_.id, "can_fix", "safety", condition="told"), person(b_.id, "knows", "believed", condition="given")],
                   resources=[{"good": goods[0], "state": "wanted", "wanted_by": b_.id}],
                   evidence=[{"label": "a cut rope", "holder": b_.id, "points_to": road, "certainty": "sure"}]))
check("...told stands when someone else holds a piece of evidence, given when the person wants a good of the situation",
      find(acc, who=a_.id)["condition"] == "told" and find(acc, who=b_.id)["condition"] == "given" and "lifted" not in find(acc, who=a_.id), acc)
acc, _ = run(parts(people=[person(a_.id, "can_fix", "safety", condition="told")],
                   evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": road, "certainty": "sure"}]))
check("...but not when the only evidence is the person's own: nobody tells them what they already hold", find(acc, who=a_.id)["condition"] == "", acc)
acc, _ = run(parts(people=[person(a_.id, "can_fix", "safety", condition="told")],
                   evidence=[{"label": "a cut rope", "holder": town, "points_to": road, "certainty": "sure"}]))
check("...evidence lying at a place is something to find and tell", find(acc, who=a_.id)["condition"] == "told", acc)
acc, _ = run(parts(people=[person(a_.id, condition="trusted"), person(b_.id, condition="protected")]))
check("trusted and protected are always within reach and stand", [a["condition"] for a in acc] == ["trusted", "protected"], acc)

# ---- a false piece needs a true one pointing elsewhere
alone = parts(people=[person(a_.id, "knows", "believed")], evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "hearsay"}])
rolls = [run(alone, seed=s)[0][1] for s in range(60)]
check("a false piece alone is true after all, noted as made true", all(e["true"] for e in rolls) and any(e.get("made_true") for e in rolls), rolls[:3])
same = parts(people=[person(a_.id, "knows", "believed")], evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": road, "certainty": "hearsay"},
                                                                   {"label": "a torn sail", "holder": town, "points_to": road, "certainty": "sure"}])
check("...so is one beside a true piece pointing the same way (nothing to weigh it against)", all(run(same, seed=s)[0][1]["true"] for s in range(60)))
other = parts(people=[person(a_.id, "knows", "believed")], evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "hearsay"},
                                                                    {"label": "a torn sail", "holder": town, "points_to": road, "certainty": "sure"}])
falses = sum(not run(other, seed=s)[0][1]["true"] for s in range(200))
check("...beside a true piece pointing elsewhere it stands, about half the time for hearsay", 60 < falses < 140, falses)
lone = parts(people=[person(a_.id, "knows", "believed")], evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": road, "certainty": "they say"}])
check("...a lone piece they say is never false (it has nothing to be weighed against)", all(run(lone, seed=s)[0][1]["true"] for s in range(60)))
paired = parts(people=[person(a_.id, "knows", "believed")], evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "they say"},
                                                                     {"label": "a torn sail", "holder": town, "points_to": road, "certainty": "sure"}])
said = sum(not run(paired, seed=s)[0][1]["true"] for s in range(400))
check("...beside a true piece elsewhere a piece they say stands false about one time in five, as the data says", 50 < said < 110, said)
one, two = ({"label": "a cut rope", "holder": a_.id, "points_to": b_.id, "certainty": "hearsay"},
            {"label": "a torn sail", "holder": b_.id, "points_to": a_.id, "certainty": "hearsay"})
pair = lambda ev: parts(people=[person(a_.id, "knows", "believed"), person(b_.id, "knows", "believed")], evidence=ev)
ab = [sum(not run(pair([one, two]), seed=s)[0][k]["true"] for s in range(1000)) for k in (2, 3)]
ba = [sum(not run(pair([two, one]), seed=s)[0][k]["true"] for s in range(1000)) for k in (2, 3)]
check("(the review) two pieces pointing at each other are weighed as first decided, so neither's chance hangs on which was proposed "
      "first: each stands false about one time in four", all(180 < n < 320 for n in ab + ba) and abs(ab[0] - ab[1]) < 80, (ab, ba))

# ---- "empty" and "blank" are no answer
from llm import contracts
acc, dropped = run(parts(people=[person(a_.id, label="blank")], resources=[{"good": goods[0], "state": "stranded", "holder": "empty"}],
                         evidence=[{"label": "Empty.", "holder": a_.id, "points_to": road, "certainty": "sure"}]))
check("a holder or a label written as 'empty' or 'blank' is left blank, never a person; evidence of 'empty' is no evidence",
      find(acc, kind="resource")["holder"] == "" and find(acc, kind="person")["label"] == "" and not find(acc, kind="evidence")
      and [r for _, r in dropped] == [R["raw_id"]], (acc, dropped))
check("...the contract itself blanks a held good of 'empty' (the check would blank any word that is no good)",
      contracts.PartPerson.model_validate(person(a_.id, holds="empty")).holds == "")
check("(the review) ...and only the situation's parts: elsewhere 'Blank' and 'Empty.' are things said",
      contracts.GiftProposal.model_validate({"name": "Blank"}).name == "Blank" and "empty" not in contracts.PLACEHOLDERS)

# ---- the prompt
check("the prompt asks for the town's own first, trades from outside only when the trouble needs one", "cast the town's own first" in pp.PARTS_SYSTEM
      and "only when the trouble needs a trade the town lacks" in pp.PARTS_SYSTEM)
check("...for most people to help freely, and says what told and given need", "most people help freely" in pp.PARTS_SYSTEM
      and "give them a wanted resource" in pp.PARTS_SYSTEM and "evidence another person holds" in pp.PARTS_SYSTEM)
check("...and asks who wants a wanted good, never inviting the word 'empty'", "wanted_by: for wanted" in pp.PARTS_SYSTEM
      and "or empty" not in pp.PARTS_SYSTEM)
check("the harmed lines no longer read as money paid", not any("paying for it" in ln for ln in situations.S["phrases"]["stake"]["harmed"]))

# ---- the data
import copy as _copy
keep_spec = _copy.deepcopy(situations.S["proposal"])
situations.S["proposal"]["max_tokens"] = 900
short = situations.problems()
situations.S["proposal"] = keep_spec
check("(f545's re-test) an answer room under half again the answer the turn budget expects is refused at startup",
      any("proposal.max_tokens" in p for p in short) and situations.S["proposal"]["max_tokens"] >= 1400, short)
check("situations.yaml checks clean, and data_check with it", situations.problems() == [] and data_check.check() == [], situations.problems())
keep = copy.deepcopy(situations.S)
situations.S["stances"]["refused"].append(["plots", "road_open"])
situations.S["stances"]["lifted"].append(["coin"])
probs = situations.problems()
situations.S.clear(); situations.S.update(keep)
check("a stance pair outside the lists' words, or not a pair, is refused at startup", sum("stances." in x for x in probs) == 2, probs)
for broken in ({"refuse": [], "lifted": []}, [["blocks", "road_open"]], {"refused": 5, "lifted": []}, None):
    situations.S["stances"] = broken
    try:
        probs = situations.problems()
        ok = any(x.startswith("situations.yaml stances") for x in probs)
    except Exception as e:                                                  # noqa: BLE001 - the check reports, never crashes
        ok, probs = False, repr(e)
    situations.S.clear(); situations.S.update(copy.deepcopy(keep))
    check(f"(the review) stances written as {broken!r} is reported, never a crash and never silently no rule", ok, probs)
_, user = situations.prompt(store, world, store.load_world_state() or {}, world.places[town], "rare", ws.minutes)
acc, dropped = situations.propose(store, world, store.load_world_state() or {}, world.places[town], "rare", ws.minutes, random.Random(1),
                                  players=(ws.acting,))[1:]
check("the stand-in's answer is still kept whole", acc and not dropped, dropped)

import shutil
shutil.rmtree("saves/situation_fixes_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

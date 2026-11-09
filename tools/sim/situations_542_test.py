"""(f542) A situation's parts: the typed contract (llm/contracts.py SituationParts), its closed lists in data/rules/situations.yaml held
equal both ways, the engine's check part by part (engine/situations.py check) and the fixed render (render). A good proposal is accepted
whole; each bad part is dropped alone, with its reason, while the rest stand; a role is the town's own of that trade first (a person
made, or one its places are written with), and only past them someone new, within the tier's cap; the evidence's truth is the engine's,
rolled once on the die it is given, a sure piece never false and a piece lying at a place only ever sure; the render names people,
goods and places and never an id; no state is written.
Run: python tools/sim/situations_542_test.py"""
import copy
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import data_check, pulse, retrieval, roads, situations
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("situations_542", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
check("the town has people of its own to cast", len(rows) >= 3, [(r.id, r.role) for r in rows])
a_, b_, c_ = rows[0], rows[1], rows[2]
made = {r.role for r in rows}
written = {role for pid in retrieval.town_places(world, town) for role in (world.places[pid].residents or {})}
unmade = sorted(written - made - set(situations.S["never_roles"]))
absent = sorted(r for r in world.roles if r not in written and r not in situations.S["never_roles"])
goods = sorted(situations._goods())
good_id = goods[0]
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
lone = next(rid for rid in sorted(world.roads) if not roads.way_round(world, rid))
R = situations.S["reasons"]
P = situations.S["phrases"]
before = (store.load_world_state(), [store.load_npc(r.id).model_dump() for r in rows])
check("the town's places are written with trades not yet met, and the world has trades the town has none of", len(unmade) >= 2
      and len(absent) >= 3, (unmade, absent[:3]))


def parts(**kw):
    return SituationParts.model_validate(kw)


def run(p, tier="rare", seed=7, ways=True, **kw):
    return situations.check(p, store, world, tier, random.Random(seed), town=town, ways=ways, now=ws.minutes, players=(ws.acting,), **kw)


def person(who, stake="harmed", want="safety", **kw):
    return {"who": who, "stake": stake, "want": want, **kw}


# ---- a good proposal, accepted whole
good = parts(people=[person(a_.id, "gains", "coin", condition="paid", label="sells dear"), person(b_.id, "harmed", "road_open")],
             resources=[{"good": good_id, "state": "stranded", "holder": b_.id}],
             ties=[{"a": a_.id, "b": b_.id, "tie": "rival"}],
             conditions=[{"on": road, "kind": "danger"}],
             evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": b_.id, "certainty": "hearsay"}])
acc, dropped = run(good)
check("a good proposal at a rare situation is accepted whole, in order", [a["kind"] for a in acc] == ["person", "person", "resource", "tie",
      "condition", "evidence"] and not dropped, (acc, dropped))
check("...people of the town keep who they are, bound by id", acc[0]["who"] == a_.id and acc[0]["bind"] == "npc" and not acc[0]["new"], acc[:2])
check("...each part carries its shape's version, and evidence its truth and who holds it", all(a["v"] == situations.V for a in acc)
      and isinstance(acc[-1]["true"], bool) and acc[-1]["held"] == "person")
try:
    SituationParts.model_validate({})
    empty_refused = False
except Exception:
    empty_refused = True
check("an answer with no parts at all is refused, so the gateway asks once more", empty_refused)

# ---- each bad part dropped alone, with its reason
p = parts(people=[person(a_.id, "gains", "coin"), person("dragon_king", "blocks"), person("player", "knows", "believed"),
                  person(ws.acting, "knows", "believed"), person(a_.id, "knows", "believed"), person(b_.id, label="lost the trading_square stall")],
          resources=[{"good": "dragon_gold", "state": "wanted"}, {"good": good_id, "state": "scarce", "holder": "dragon_king"},
                     {"good": good_id, "state": "scarce", "holder": a_.id}, {"good": good_id, "state": "wanted", "wanted_by": a_.id, "label": "the a_cut stock"}],
          conditions=[{"on": "atlantis", "kind": "closed"}, {"on": road, "kind": "prices"}, {"on": town, "kind": "prices"}],
          ties=[{"a": a_.id, "b": a_.id, "tie": "kin"}, {"a": a_.id, "b": "nobody", "tie": "owes"}],
          evidence=[{"label": "a boot print", "holder": a_.id, "points_to": "the moon", "certainty": "sure"},
                    {"label": "a ledger", "holder": "nobody", "points_to": a_.id, "certainty": "sure"},
                    {"label": "the stall_book", "holder": a_.id, "points_to": a_.id, "certainty": "sure"}])
acc, dropped = run(p, tier="campaign")
reasons = [r for _, r in dropped]
check("the rest stand: the real person, a real good held by them, the town's prices", [(a["kind"], a.get("who") or a.get("good") or a.get("on"))
      for a in acc] == [("person", a_.id), ("resource", good_id), ("condition", town)], acc)
for key, n in (("not_a_person", 1), ("player", 2), ("twice", 1), ("raw_id", 3), ("not_a_good", 1), ("no_holder", 2), ("not_a_place", 2),
               ("self_tie", 1), ("no_end", 1), ("points_nowhere", 1)):
    check(f"...and {n} part(s) {R[key]!r} dropped for it", reasons.count(R[key]) == n, reasons)
check("prices on a road are dropped: the pulse lays prices on a town, never a road",
      any(d.get("on") == road and d.get("kind") == "prices" and r == R["not_a_place"] for d, r in dropped), dropped)
gone = store.load_npc(c_.id)
gone.gone = "died of a fever"
store.save_npc(gone)
acc, dropped = run(parts(people=[person(c_.id, "knows", "believed")]))
check("a person who is gone is dropped", not acc and [r for _, r in dropped] == [R["gone"]], dropped)
gone.gone = ""
was_role, gone.role = gone.role, "prisoner"
store.save_npc(gone)
acc, dropped = run(parts(people=[person(c_.id, "knows", "believed")]))
check("a trade no situation casts is never a part, named by id or by trade", not acc and [r for _, r in dropped] == [R["not_a_person"]]
      and not run(parts(people=[person("guild_master", "blocks")]))[0], dropped)
gone.role = was_role
store.save_npc(gone)

acc, dropped = situations.check(parts(people=[person("hero_two", "knows", "believed")]), store, world, "rare", random.Random(1), town=town,
                                ways=True, now=ws.minutes, players=(ws.acting, "hero_two"))
check("any character playing is never a part, by their own id (more than one may play)", not acc and [r for _, r in dropped] == [R["player"]], dropped)

# ---- caps by tier, and someone new only past the town's own of that trade
C = situations.S["caps"]
check("(f556) the caps are the owner's: none on parts at any tier, none by kind; new people 0, 0, 2 and 2",
      C["parts"] == {"normal": None, "uncommon": None, "rare": None, "campaign": None} and C["people"] is None and C["each_other"] is None
      and C["new_people"] == {"normal": 0, "uncommon": 0, "rare": 2, "campaign": 2}, C)
check("(f557) ...and a lie is never a roll: no chances, only who has a reason to lie", "false_chance" not in situations.S
      and situations.S["lies"] == {"stakes": ["gains", "blocks"], "wants": ["rid_of_rival", "left_alone"], "ties": ["rival"]},
      situations.S.get("lies"))
def many(tier):
    ppl = [person(r.id) for r in rows[:3]] + [person(unmade[0])]
    return run(parts(people=ppl, resources=[{"good": goods[0], "state": "scarce"}, {"good": goods[1], "state": "wanted", "wanted_by": rows[0].id}],
                     ties=[{"a": rows[0].id, "b": rows[1].id, "tie": "kin"}, {"a": rows[1].id, "b": rows[2].id, "tie": "owes"}],
                     conditions=[{"on": town, "kind": "mark"}]), tier=tier)
for tier, n in situations.S["caps"]["parts"].items():
    acc, dropped = many(tier)
    if n is None:
        check(f"a {tier} situation keeps every part proposed (no total cap)", len(acc) == 9 and not dropped, (len(acc), [r for _, r in dropped]))
    else:
        check(f"a {tier} situation holds {n} parts at most", len(acc) == min(n, 9) and (R["parts_cap"] in [r for _, r in dropped]) == (n < 9),
              (len(acc), [r for _, r in dropped]))
acc, dropped = run(parts(resources=[{"good": goods[i], "state": "scarce"} for i in range(3)]), tier="campaign")
check("(f550) no cap by kind: three goods, all kept", len(acc) == 3 and not dropped, dropped)
acc, dropped = run(parts(people=[person(r.id) for r in rows[:3]] + [person(unmade[0]), person(unmade[1])]), tier="campaign")
check("...five people, all kept", sum(a["kind"] == "person" for a in acc) == 5 and not dropped, dropped)
held = copy.deepcopy(situations.S["caps"])
situations.S["caps"].update(people=4, each_other=2)
acc, dropped = run(parts(people=[person(r.id) for r in rows[:3]] + [person(unmade[0]), person(unmade[1])],
                         resources=[{"good": goods[i], "state": "scarce"} for i in range(3)]), tier="campaign")
check("...and a cap by kind, where the data sets one, still holds: four people, two goods", sum(a["kind"] == "person" for a in acc) == 4
      and sum(a["kind"] == "resource" for a in acc) == 2 and sorted(r for _, r in dropped) == sorted([R["people_cap"], R["kind_cap"]]), dropped)
situations.S["caps"].clear(); situations.S["caps"].update(held)
acc, _ = run(parts(people=[person(a_.role, "can_fix", "coin")]), tier="normal")
check("a role is the town's own of that trade first, even where no one new may be made", acc and acc[0]["who"] == a_.id and acc[0]["bind"] == "npc", acc)
acc, dropped = run(parts(people=[person(unmade[0], "can_fix", "coin")]), tier="normal")
check("...a trade its places are written with, not yet met, is the town's own too, never someone new", acc and acc[0]["bind"] == "town"
      and not acc[0]["new"] and acc[0]["who"] == unmade[0], (acc, dropped))
acc, dropped = run(parts(people=[person(absent[0], "can_fix", "coin")]), tier="normal")
check("a common situation brings no one new", not acc and [r for _, r in dropped] == [R["new_cap"]], dropped)
acc, dropped = run(parts(people=[person(absent[0], "can_fix", "coin"), person(absent[1], "gains", "coin"), person(absent[2], "harmed", "goods_moved")]),
                   tier="rare")
check("a rare one brings two new people at most, for the engine to make", [a["bind"] for a in acc] == ["new", "new"]
      and [r for _, r in dropped] == [R["new_cap"]], (acc, dropped))
acc, dropped = run(parts(people=[person(a_.role, "can_fix", "coin"), person(a_.id, "knows", "believed")]))
check("(f545's second review) a trade and one of that trade named by id are two people: the trade is cast past the one named",
      len(acc) == 2 and acc[1]["who"] == a_.id and acc[0]["who"] != a_.id and not dropped, (acc, dropped))
acc, dropped = run(parts(people=[person(a_.id, "can_fix", "coin"), person(a_.id, "knows", "believed")]))
check("the same person named twice by id is one person: the second is twice", len(acc) == 1 and [r for _, r in dropped] == [R["twice"]], dropped)
acc, dropped = run(parts(people=[person(a_.role, "can_fix", "coin"), person(b_.id)], ties=[{"a": a_.id, "b": b_.id, "tie": "kin"},
                                                                                               {"a": b_.id, "b": a_.role, "tie": "kin"}]))
check("...one named by trade may be referred to by the id it bound to; a tie told twice either way round is once",
      [a["kind"] for a in acc] == ["person", "person", "tie"] and [r for _, r in dropped] == [R["twice"]], (acc, dropped))

# ---- the only way between two places, the roads this proposal shuts counted
acc, dropped = run(parts(conditions=[{"on": lone, "kind": "closed"}]), ways=False)
check("a closure of the only way, from a situation with no way through, is dropped", not acc and [r for _, r in dropped] == [R["only_way"]], dropped)
acc, _ = run(parts(conditions=[{"on": lone, "kind": "closed"}]), ways=True)
check("...and kept when the situation offers one", acc and acc[0]["what"] == "closed")
pair = next(((x, y) for x in sorted(world.roads) for y in sorted(world.roads) if x != y and roads.way_round(world, x) and roads.way_round(world, y)
             and not roads.way_round(world, x, {y})), None)
check("the world has two roads each the other's only way round", pair is not None)
if pair:
    acc, dropped = run(parts(conditions=[{"on": pair[1], "kind": "closed"}, {"on": pair[0], "kind": "closed"}]), ways=False)
    check("...so one proposal never shuts both: the second is the only way once the first is shut", len(acc) == 1
          and [r for _, r in dropped] == [R["only_way"]], dropped)

# ---- (f557) the truth is the engine's: a lie by incentive, never a roll
ev = parts(people=[person(a_.id, "knows", "believed")],
           evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "hearsay"},
                     {"label": "a torn sail", "holder": a_.id, "points_to": road, "certainty": "sure"}])
one, two = run(ev, seed=7), run(ev, seed=7)
check("the same die gives the same parts and the same truth", one == two)
check("(f557) one with no reason to deceive tells what they believe, hearsay or sure, on any die",
      all(run(ev, seed=s)[0][1]["true"] and run(ev, seed=s)[0][2]["true"] for s in range(20)))
say = parts(people=[person(a_.id, "gains", "coin"), person(b_.id, "harmed", "safety")],
            evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": b_.id, "certainty": "sure"},
                      {"label": "a torn sail", "holder": town, "points_to": road, "certainty": "sure"}])   # (f545) beside a true piece
check("(f557) one who gains from the trouble lies about another, however sure they say they are, on every die",
      all(not run(say, seed=s)[0][2]["true"] for s in range(20)), [run(say, seed=s)[0][2] for s in range(2)])
lying = {"label": "a torn sail", "holder": town, "points_to": road, "certainty": "sure"}
acc, dropped = run(parts(evidence=[{**lying, "certainty": "hearsay"}, lying]))
check("evidence lying at a place is only ever sure, and never false", [r for _, r in dropped] == [R["claim_at_place"]] and len(acc) == 1
      and acc[0]["held"] == "place" and all(run(parts(evidence=[lying]), seed=s)[0][0]["true"] for s in range(50)), (acc, dropped))
named = next((pid for pid, pl in world.places.items() if pl.name.lower().removeprefix("the ") == pid and pl.name.lower() != pid), "")
if named:
    acc, dropped = run(parts(conditions=[{"on": town, "kind": "mark", "label": f"smoke over {world.places[named].name.lower()}"}]))
    check(f"a place called by its own name ('{world.places[named].name}') is a name in a label, not an id", acc and not dropped, dropped)

# ---- the render: names, never ids
acc, _ = run(good)
text = situations.render(acc, store, world, "T1")
ids = set(world.places) | set(world.roads) | {r.id for r in rows}
check("the render tells every part, one line each", text.startswith("SITUATION PARTS:") and text.count("\n- ") == len(acc), text)
check("...names people, goods and places, never an id or the machinery", "_" not in text and not any(i in text for i in ids if "_" in i)
      and all(w.lower() in text.lower() for w in (store.load_npc(a_.id).name, situations._goods()[good_id].name, world.roads[road].name)), text)
check("...the same lines every time it is told", situations.render(acc, store, world, "T1") == text)
told_truth = situations.render(acc, store, world, "T1", with_truth=True)
truth_words = [x.rstrip(".") for x in P["is_true"] + P["is_false"]]
check("...and says nothing of the truth unless asked, for a telling", not any(w in text for w in truth_words)
      and any(w in told_truth for w in truth_words), (text, told_truth))
new_one, _ = run(parts(people=[person(unmade[0], "knows", "left_alone")]), tier="rare")
vowel = next((r for r in sorted(world.roles) if r[0] in "aeiou" and r not in situations.S["never_roles"]), "")
check("someone yet to be met is told by trade, with a or an", unmade[0].replace("_", " ") in situations.render(new_one, store, world, "T2").lower()
      and (not vowel or "an " + vowel.replace("_", " ") in situations.render(
          [{"kind": "person", "who": vowel, "bind": "new", "stake": "knows", "want": "believed", "v": 1}], store, world, "T3").lower()))
lies = situations.render(run(parts(evidence=[lying]))[0], store, world, "T4")
check("evidence lying at a place is told as lying there, never as someone's guess", any(x.split("{")[0] in lies for x in P["lies"])
      or "lies at" in lies or "can be found" in lies or "there is" in lies or "sign of it" in lies, lies)

# ---- the data, held to the contract both ways
check("the lists, caps, chances and phrase tables check clean at startup", situations.problems() == [] and data_check.check() == [])
keep = copy.deepcopy(situations.S)


def problems_with(change):
    situations.S.clear(); situations.S.update(copy.deepcopy(keep))
    change(situations.S)
    try:
        return situations.problems()
    finally:
        situations.S.clear(); situations.S.update(copy.deepcopy(keep))
p1 = problems_with(lambda S: S["lists"].update(stakes=S["lists"]["stakes"] + ["conspires"]))
p1b = problems_with(lambda S: S["lists"].update(stakes=S["lists"]["stakes"][1:]))
p3 = problems_with(lambda S: (S.update(false_chance={"hearsay": 0.5}), S["phrases"]["tie"].update(kin=S["phrases"]["tie"]["kin"][:2])))
p4 = problems_with(lambda S: S["phrases"]["stake"].update(gains=["it pays someone", "{name} gains", "{name} wins", "{name} profits"]))
p5 = problems_with(lambda S: S["phrases"].update(holds=["{nonsense}", "{0}", 7, "{good} kept"]))
p6 = problems_with(lambda S: (S["reasons"].pop("only_way"), S["caps"]["parts"].pop("rare")))
check("a list the contract does not hold is refused, either way round", any("lists.stakes" in x for x in p1) and any("lists.stakes" in x for x in p1b), (p1, p1b))
check("...(f557) a lie by a roll, and a phrase table too short to vary", any("false_chance" in x and "never a roll" in x for x in p3)
      and any("tie.kin" in x for x in p3), p3)
check("...a line that leaves out its own slot", any("leaves out ['name']" in x for x in p4), p4)
check("...a line with a slot it may not have, a bad slot or no words, reported, never a crash", len([x for x in p5 if "phrases.holds" in x]) >= 3, p5)
check("...and a missing reason, or a tier left out of the caps", any("reasons.only_way" in x for x in p6) and any("caps.parts.rare" in x for x in p6), p6)
p7 = problems_with(lambda S: (S["caps"]["new_people"].update(rare=None), S["caps"].update(people=0), S["caps"]["parts"].update(normal=-1)))
check("...new people never uncapped, and no cap below its least", any("caps.new_people.rare" in x for x in p7) and any("caps.people" in x for x in p7)
      and any("caps.parts.normal" in x for x in p7), p7)
real = list(situations.S["never_roles"])
situations.S["never_roles"] = real + ["court_jester_of_mars"]
dc = data_check.check()
situations.S["never_roles"] = real
check("...and a trade never cast that is not a role", any("court_jester_of_mars" in x for x in dc), dc)

# ---- nothing written
after = (store.load_world_state(), [store.load_npc(r.id).model_dump() for r in rows])
check("the check and the render write nothing", after == before)
check("no wall clock, no unseeded die in the module", all(w not in open("engine/situations.py", encoding="utf-8").read()
      for w in ("import time", "datetime", "random.random(", "random.choice(", "uuid")))

g.close()
shutil.rmtree("saves/situations_542", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

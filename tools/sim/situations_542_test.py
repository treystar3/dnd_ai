"""(f542) A situation's parts: the typed contract (llm/contracts.py SituationParts), its closed lists in data/rules/situations.yaml held
equal both ways, the engine's check part by part (engine/situations.py check) and the fixed render (render). A good proposal is accepted
whole; each bad part is dropped alone, with its reason, while the rest stand; a role is the town's own of that trade first, and only past
them someone new, within the tier's cap; the evidence's truth is the engine's, rolled once on the die it is given, a sure piece never
false; the render names people, goods and places and never an id; no state is written.
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
good_id = next(iter(sorted(situations._goods())))
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
lone = next(rid for rid in sorted(world.roads) if not roads.way_round(world, rid))
before = (store.load_world_state(), [store.load_npc(r.id).model_dump() for r in rows])


def parts(**kw):
    return SituationParts.model_validate(kw)


def run(p, tier="rare", seed=7, **kw):
    return situations.check(p, store, world, tier, random.Random(seed), town=town, player_id=ws.acting, **kw)


# ---- a good proposal, accepted whole
good = parts(people=[{"who": a_.id, "stake": "gains", "want": "coin", "condition": "paid", "label": "sells dear"},
                     {"who": b_.id, "stake": "harmed", "want": "road_open"}],
             resources=[{"good": good_id, "state": "stranded", "holder": b_.id}],
             ties=[{"a": a_.id, "b": b_.id, "tie": "rival"}],
             conditions=[{"on": road, "kind": "danger"}],
             evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": b_.id, "certainty": "hearsay"}])
acc, dropped = run(good)
check("a good proposal at a rare situation is accepted whole, in order", [a["kind"] for a in acc] == ["person", "person", "resource", "tie",
      "condition", "evidence"] and not dropped, (acc, dropped))
check("...people of the town keep who they are", acc[0]["who"] == a_.id and not acc[0]["new"] and acc[1]["who"] == b_.id, acc[:2])
check("...the evidence's truth is the engine's, on the part", isinstance(acc[-1]["true"], bool))
try:
    SituationParts.model_validate({})
    empty_refused = False
except Exception:
    empty_refused = True
check("an answer with no parts at all is refused, so the gateway asks once more", empty_refused)

# ---- each bad part dropped alone, with its reason
p = parts(people=[{"who": a_.id, "stake": "gains", "want": "coin"},
                  {"who": "dragon_king", "stake": "blocks", "want": "safety"},
                  {"who": "player", "stake": "knows", "want": "believed"},
                  {"who": a_.id, "stake": "knows", "want": "believed"},
                  {"who": b_.id, "stake": "harmed", "want": "safety", "label": "lost the trading_square stall"}],
          resources=[{"good": "dragon_gold", "state": "wanted"}, {"good": good_id, "state": "scarce", "holder": "dragon_king"},
                     {"good": good_id, "state": "scarce", "holder": a_.id}],
          conditions=[{"on": "atlantis", "kind": "closed"}, {"on": road, "kind": "prices"}],
          ties=[{"a": a_.id, "b": a_.id, "tie": "kin"}, {"a": a_.id, "b": "nobody", "tie": "owes"}],
          evidence=[{"label": "a boot print", "holder": a_.id, "points_to": "the moon", "certainty": "sure"},
                    {"label": "a ledger", "holder": "nobody", "points_to": a_.id, "certainty": "sure"}])
acc, dropped = run(p, tier="campaign")
reasons = [r for _, r in dropped]
R = situations.S["reasons"]
check("the rest stand: the real person, a real good held by them, a real road's prices", [(a["kind"], a.get("who") or a.get("good") or a.get("on"))
      for a in acc] == [("person", a_.id), ("resource", good_id), ("condition", road)], acc)
for key in ("not_a_person", "player", "twice", "raw_id", "not_a_good", "no_holder", "not_a_place", "self_tie", "no_end", "points_nowhere"):
    check(f"...and a part {R[key]!r} is dropped for it", R[key] in reasons, reasons)
gone = store.load_npc(c_.id)
gone.gone = "died of a fever"
store.save_npc(gone)
acc, dropped = run(parts(people=[{"who": c_.id, "stake": "knows", "want": "believed"}]))
check("a person who is gone is dropped", not acc and [r for _, r in dropped] == [R["gone"]], dropped)
gone.gone = ""
store.save_npc(gone)

# ---- caps by tier, and someone new only past the town's own of that trade
three = parts(people=[{"who": a_.id, "stake": "gains", "want": "coin"}, {"who": b_.id, "stake": "harmed", "want": "safety"},
                      {"who": c_.id, "stake": "knows", "want": "believed"}])
acc, dropped = run(three, tier="normal")
check("a normal situation holds two parts: the third is over the cap", len(acc) == 2 and [r for _, r in dropped] == [R["parts_cap"]], dropped)
five = parts(people=[{"who": r.id, "stake": "harmed", "want": "safety"} for r in rows[:3]]
             + [{"who": "hermit", "stake": "knows", "want": "left_alone"}, {"who": "wanderer", "stake": "knows", "want": "believed"}])
acc, dropped = run(five, tier="campaign")
check("at most four people in any situation", sum(a["kind"] == "person" for a in acc) == 4 and R["people_cap"] in [r for _, r in dropped], dropped)
role = a_.role
acc, _ = run(parts(people=[{"who": role, "stake": "can_fix", "want": "coin"}]), tier="normal")
check("a role is the town's own of that trade first, even where no one new may be made", acc and acc[0]["who"] == a_.id and not acc[0]["new"], acc)
acc, dropped = run(parts(people=[{"who": "hermit", "stake": "can_fix", "want": "coin"}]), tier="normal")
check("a common situation brings no one new", not acc and [r for _, r in dropped] == [R["new_cap"]], dropped)
acc, dropped = run(parts(people=[{"who": "hermit", "stake": "can_fix", "want": "coin"}, {"who": "wanderer", "stake": "gains", "want": "coin"},
                                 {"who": "bargeman", "stake": "harmed", "want": "goods_moved"}]), tier="rare")
check("a rare one brings two new people at most, for the engine to make", [a["new"] for a in acc] == [True, True]
      and [r for _, r in dropped] == [R["new_cap"]], (acc, dropped))
acc, dropped = run(parts(people=[{"who": "guild_master", "stake": "blocks", "want": "safety"}]))
check("a trade no situation casts is never a part", not acc and [r for _, r in dropped] == [R["not_a_person"]], dropped)

# ---- the only way between two places
cond = parts(conditions=[{"on": lone, "kind": "closed"}])
acc, dropped = run(cond, ways=False)
check("a closure of the only way, from a situation with no way through, is dropped", not acc and [r for _, r in dropped] == [R["only_way"]], dropped)
acc, _ = run(cond, ways=True)
check("...and kept when the situation offers one", acc and acc[0]["what"] == "closed")

# ---- the truth is the engine's, on the die it is given
ev = parts(people=[{"who": a_.id, "stake": "knows", "want": "believed"}],
           evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "hearsay"},
                     {"label": "a torn sail", "holder": a_.id, "points_to": road, "certainty": "sure"}])
one, two = run(ev, seed=7), run(ev, seed=7)
check("the same die gives the same parts and the same truth", one == two)
flips = {run(ev, seed=s)[0][1]["true"] for s in range(40)}
strip = lambda acc_: [{k: v for k, v in a.items() if k != "true"} for a in acc_]
check("another die may turn a hearsay piece false, and nothing else", flips == {True, False}
      and all(strip(run(ev, seed=s)[0]) == strip(one[0]) for s in range(10)), flips)
check("a sure piece is never false, over 200 dice", all(run(ev, seed=s)[0][2]["true"] for s in range(200)))
check("...and 'they say' is false about one time in five (data)", 0.1 < sum(not run(parts(people=[{"who": a_.id, "stake": "knows", "want": "believed"}],
      evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": a_.id, "certainty": "they say"}]), seed=s)[0][1]["true"]
      for s in range(400)) / 400 < 0.3)

# ---- the render: names, never ids
acc, _ = run(good)
text = situations.render(acc, store, world, "T1")
ids = set(world.places) | set(world.roads) | {r.id for r in rows}
check("the render tells every part, one line each", text.startswith("THE PARTS:") and text.count("\n- ") == len(acc), text)
check("...names people, goods and places, never an id or the machinery", "_" not in text and not any(i in text for i in ids if "_" in i)
      and all(w.lower() in text.lower() for w in (store.load_npc(a_.id).name, situations._goods()[good_id].name, world.roads[road].name)), text)
check("...the same lines every time it is told", situations.render(acc, store, world, "T1") == text)
check("...and says nothing of the truth unless asked, for a telling", "true" not in text.lower() and "is not so" not in text
      and any(w in situations.render(acc, store, world, "T1", with_truth=True) for w in ("It is", "It does", "It holds")), text)
new_one, _ = run(parts(people=[{"who": "hermit", "stake": "knows", "want": "left_alone"}]), tier="rare")
check("someone yet to be made is told by trade", "a hermit" in situations.render(new_one, store, world, "T2").lower())

# ---- the data, held to the contract both ways
check("the lists, caps, chances and phrase tables check clean at startup", situations.problems() == [] and data_check.check() == [])
keep = copy.deepcopy(situations.S)
situations.S["lists"]["stakes"] = situations.S["lists"]["stakes"] + ["conspires"]
p1 = situations.problems()
situations.S.clear(); situations.S.update(copy.deepcopy(keep))
situations.S["lists"]["place_kinds"] = ["closed", "flooded"]
p2 = situations.problems()
situations.S.clear(); situations.S.update(copy.deepcopy(keep))
situations.S["false_chance"]["sure"] = 0.1
situations.S["phrases"]["tie"]["kin"] = situations.S["phrases"]["tie"]["kin"][:2]
p3 = situations.problems()
situations.S.clear(); situations.S.update(copy.deepcopy(keep))
check("a list the contract does not hold is refused", any("lists.stakes" in x for x in p1), p1)
check("...and a kind the pulse does not apply", any("place_kinds" in x for x in p2), p2)
check("...a sure piece that could be false, and a phrase table too short to vary", any("false_chance.sure" in x for x in p3)
      and any("tie.kin" in x for x in p3), p3)

# ---- nothing written
after = (store.load_world_state(), [store.load_npc(r.id).model_dump() for r in rows])
check("the check and the render write nothing", after == before)
check("no wall clock, no unseeded die in the module", all(w not in open("engine/situations.py", encoding="utf-8").read()
      for w in ("import time", "datetime", "random.random(", "random.choice(", "uuid")))

g.close()
shutil.rmtree("saves/situations_542", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

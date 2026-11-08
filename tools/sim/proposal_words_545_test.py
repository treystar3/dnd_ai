"""(f545 part 5) What the uncapped run showed the model writing whatever the prompt says, read as it meant: a trade it numbered or
tagged ("merchant_1", "scout_01", "trade: guard", "new_scout") is that trade, cast the town's own first; a name of its own ("marek_vane")
is the trade its label names ("greedy merchant"), the name never kept, and a name whose label names no trade is still no one; two of one
trade it numbered are two of the town's own when the town has two, else one; and a label of words joined by underscores
("flooded_field_owner") is those words, while one that is an id of the world stays refused as machinery. Every later part that names
the person by what the proposal called them finds them.
Run: python tools/sim/proposal_words_545_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import pulse, retrieval, situations
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("proposal_words_545", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
R = situations.S["reasons"]
never = set(situations.S.get("never_roles") or ())
mine = sorted({r.role for r in rows if r.role not in never})
other = next(r for r in sorted(world.roles) if r not in never and r not in {x.role for x in rows}
             and not any(r in (world.places[p].residents or {}) for p in retrieval.town_places(world, town)))
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to) and "_" in rid)


def run(**kw):
    return situations.check(SituationParts.model_validate(kw), store, world, "rare", random.Random(7), town=town, ways=True, now=ws.minutes,
                            players=(ws.acting,))


def person(who, label="", **kw):
    return {"who": who, "stake": "harmed", "want": "safety", "label": label, **kw}


# ---- the trade as the model wrote it
t0 = mine[0]
acc, dropped = run(people=[person(f"{t0}_1", "a worried trader"), person(other)], ties=[{"a": f"{t0}_1", "b": other, "tie": "rival"}])
p0 = next((a for a in acc if a["kind"] == "person"), None)
check("a trade the model numbered is that trade, cast as the town's own", p0 is not None and p0["bind"] == "npc"
      and store.load_npc(p0["who"]).role == t0, (acc, dropped))
check("...and a tie naming them as the model did finds them", any(a["kind"] == "tie" and p0["who"] in (a["a"], a["b"]) for a in acc), acc)
acc, dropped = run(people=[person(f"trade: {other}"), person(f"new_{other}x"), person(f"{other}_01", "")])
check("'trade: X' is the trade X; a trade with a number is that trade; one trade numbered twice, the town having none of it, is one person",
      [a["who"] for a in acc if a["kind"] == "person"] == [other] and acc[0]["bind"] == "new"
      and [r for _, r in dropped] == [R["not_a_person"], R["twice"]], (acc, dropped))

# ---- two of one trade, the town having two
from engine import situation_parts
twice = next((r for r in mine if sum(1 for x in rows if x.role == r) >= 2), None)
if twice is None:                                           # the town given a second of a trade it has, as a situation would make one
    twice = t0
    situation_parts.make_person(store, world, ws.catalog, twice, next(x for x in rows if x.role == twice).location, ws.minutes, "twice")
acc, _ = run(people=[person(f"{twice}_1"), person(f"{twice}_2")])
ids = [a["who"] for a in acc if a["kind"] == "person"]
check("two of one trade the town has two of are its two people", len(ids) == 2 and len(set(ids)) == 2
      and all(a["bind"] == "npc" and store.load_npc(a["who"]).role == twice for a in acc), acc)

# ---- a name of its own
acc, dropped = run(people=[person("marek_vane", f"greedy {t0.replace('_', ' ')}")],
                   resources=[{"good": "salt", "state": "scarce", "holder": "marek_vane", "label": "a short load"}])
pm = next((a for a in acc if a["kind"] == "person"), None)
check("a name of the model's own is the trade its label names, cast the town's own first", pm is not None
      and store.load_npc(pm["who"]).role == t0 and "marek" not in str(acc).lower(), (acc, dropped))
check("...and what it holds is theirs", any(a["kind"] == "resource" and a["holder"] == pm["who"] for a in acc), acc)
acc, dropped = run(people=[person("elara_thorne", "the mediator")])
check("a name whose label names no trade is no one", not acc and [r for _, r in dropped] == [R["not_a_person"]], dropped)

# ---- labels
acc, dropped = run(people=[person(rows[0].id, "flooded_field_owner")], conditions=[{"on": road, "kind": "danger", "label": "rising_waters"}],
                   evidence=[{"label": "broken_axle_pin", "holder": rows[0].id, "points_to": road, "certainty": "sure"}])
check("a label of words joined by underscores is those words, on every kind of part",
      sorted(a["label"] for a in acc) == ["broken axle pin", "flooded field owner", "rising waters"], (acc, dropped))
acc, dropped = run(people=[person(rows[0].id, road)], conditions=[{"on": road, "kind": "mark", "label": "trader_01"}])
check("...while a label that is an id of the world, or carries a number, is still machinery",
      not acc and [r for _, r in dropped] == [R["raw_id"], R["raw_id"]], (acc, dropped))
check("(the reading itself) trade_of and plain", situations.trade_of("elven_warden_1", "", world, never) == "elven_warden"
      and situations.trade_of("x", "the old elven warden", world, never) == "elven_warden"
      and situations.trade_of("guild_master_1", "", world, never) == "" and situations.plain("trading_square", world, store) == "trading_square")

import shutil
shutil.rmtree("saves/proposal_words_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

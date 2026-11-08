"""(f545 part 3) A situation's checked parts written into the world through the game's own writers: its people made real (the town's
own, one of its written trades made now, or someone new, at most two new a day in one town), each with a worry and a mood that say what
gave them; its ties felt both ways; its conditions laid on places and roads, a mark in its own plain words; its evidence a clue its
holder knows, in words that say how sure they are, or one lying at a place to be found by searching there. The situation's end takes
back the worries and moods; what people learned and the ties stay. The ferryman and the carpenter join the trades.
Run: python tools/sim/registration_545_test.py"""
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
from engine import checks, clock, data_check, matters, memory, pulse, pulselog, retrieval, situation_parts, situations
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("registration_545", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
a_, b_ = rows[0], rows[1]
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
R = situations.S["reasons"]
check("the ferryman and the carpenter are trades of the world", {"ferryman", "carpenter"} <= set(world.roles))
written = sorted({role for pid in retrieval.town_places(world, town) for role in (world.places[pid].residents or {})} - {r.role for r in rows}
                 - set(situations.S["never_roles"]))
check("(the town has a trade written into its places that nobody has met yet)", "miller" in written, written)


def thread(tid, title, t):
    th = {"id": tid, "title": title, "tier": "rare", "place": "trading_square", "times": [t, t + 4 * 1440], "status": "active", "made": t,
          "clues": [], "paths": [], "stage": 0, "stages": [{"description": title + ".", "effects": []}], "kind": "trouble",
          "groups": ["everyone"]}
    st = store.load_world_state()
    st.setdefault("threads", []).append(th)
    store.save_world_state(st)
    return th


def born(th, kw, t, seed=7):
    state = store.load_world_state()
    th = next(x for x in state["threads"] if x["id"] == th["id"])
    acc, dropped = situations.check(SituationParts.model_validate(kw), store, world, "rare", random.Random(seed), town=town, ways=True, now=t,
                                    players=(ws.acting,))
    parts = situation_parts.register(store, world, state, th, acc, t, catalog=ws.catalog, ways=True)
    store.save_world_state(state)
    return parts, dropped, state


t0 = ws.minutes
th = thread("th545", "The ford is out", t0)
before = len(pulselog.LOG)
parts, dropped, state = born(th, {
    "people": [{"who": a_.id, "stake": "harmed", "want": "road_open"}, {"who": "miller", "stake": "knows", "want": "believed"},
               {"who": "ferryman", "stake": "gains", "want": "coin"}, {"who": "carpenter", "stake": "can_fix", "want": "safety", "condition": "protected"},
               {"who": b_.id, "stake": "blocks", "want": "left_alone"}],
    "ties": [{"a": a_.id, "b": "miller", "tie": "rival"}, {"a": "ferryman", "b": a_.id, "tie": "owes"}, {"a": "carpenter", "b": b_.id, "tie": "fears"}],
    "conditions": [{"on": "trading_square", "kind": "mark", "label": "scorched grass on the green"},
                   {"on": road, "kind": "danger", "label": "wolves on the road"}, {"on": "trading_square", "kind": "prices"},
                   {"on": road, "kind": "mark", "label": "the_ford_marker"}, {"on": road, "kind": "mark",
                                                                             "label": "where the old ferry rope used to be tied off before the flood took it"}],
    "evidence": [{"label": "a cut rope", "holder": a_.id, "points_to": "ferryman", "certainty": "they say"},
                 {"label": "fresh hoofprints by the ford", "holder": "trading_square", "points_to": road, "certainty": "sure"}]}, t0)
people = {(p.get("role") or p["who"]): p for p in parts if p["kind"] == "person"}
check("(every part was kept by the check but the road mark whose words are machinery)", [r for _, r in dropped] == [R["raw_id"]]
      and len(parts) == 14, (dropped, len(parts)))

# ---- the people, made real
miller = store.load_npc(people["miller"]["who"]) if "miller" in people else None
check("the town's own miller, written into its places and never met, is made now where they are written to live",
      miller is not None and miller.role == "miller" and miller.id in store.load_place(miller.location).residents
      and pulse.town_of(world, miller.location) == town and world.places[miller.location].residents.get("miller"), miller and miller.location)
new = [store.load_npc(people[r]["who"]) for r in ("ferryman", "carpenter") if r in people]
check("someone new of a trade the town lacks is made and named by the engine, of the town, kept as one of its residents",
      len(new) == 2 and all(n.role in ("ferryman", "carpenter") and n.name and pulse.town_of(world, n.location) == town
                            and n.id in store.load_place(n.location).residents and n.description for n in new), [(n.name, n.location) for n in new])
check("...counted against the town's day, kept in the world's state", state["situation_people"][town] == {"day": clock.day(t0), "n": 2},
      state.get("situation_people"))
check("every reference to a trade is now the person made for it", all(p["a"] in {x["who"] for x in people.values()}
                                                                     and p["b"] in {x["who"] for x in people.values()} for p in parts if p["kind"] == "tie"))

# ---- worries and moods with a cause
n_a = store.load_npc(a_.id)
check("each person's worry is the situation's, by what they want", all(store.load_npc(p["who"]).concern_from == "th545"
      and "The ford is out" in store.load_npc(p["who"]).concern for p in people.values()), [(store.load_npc(p["who"]).concern, store.load_npc(p["who"]).concern_from) for p in people.values()])
check("...and their mood is the situation's too, by their stake", all(store.load_npc(p["who"]).mood_source == "thread:th545"
      and store.load_npc(p["who"]).mood for p in people.values()))
check("...the one harmed who wants the road open worries about the road", "road" in n_a.concern or "way" in n_a.concern, n_a.concern)

# ---- ties, both ways
fer, car = people["ferryman"]["who"], people["carpenter"]["who"]
rel = lambda x, y: store.load_npc(x).relations.get(y, {})
check("a rivalry is felt both ways", rel(a_.id, miller.id).get("score", 0) < 0 and rel(miller.id, a_.id).get("score", 0) < 0
      and rel(a_.id, miller.id).get("feeling"), (rel(a_.id, miller.id), rel(miller.id, a_.id)))
check("...a debt as owed and owing", rel(fer, a_.id).get("score", 0) > 0 and rel(a_.id, fer).get("score", 0) < 0
      and "owes" in rel(fer, a_.id)["feeling"] and "owed" in rel(a_.id, fer)["feeling"], (rel(fer, a_.id), rel(a_.id, fer)))
check("...fear only by the one afraid", rel(car, b_.id).get("score", 0) < 0 and car not in store.load_npc(b_.id).relations,
      (rel(car, b_.id), store.load_npc(b_.id).relations))

# ---- conditions, marks in their own words
marks = store.load_place("trading_square").marks
check("a mark keeps the model's own plain words", "scorched grass on the green" in marks, marks)
check("...and one whose words run long is told with a phrase, never the words", (state.get("road_marks") or {}).get(road)
      and not any("ferry rope" in m for m in state["road_marks"][road]) and world.roads[road].name in state["road_marks"][road][-1],
      state.get("road_marks"))
eff = [e for e in state["effects"] if e.get("thread") == "th545"]
check("danger on the road and dearer prices in the town, each the situation's and lasting it", any(e["kind"] == "danger" and e["place"] == road
      and e["value"] == situations.S["register"]["danger"] for e in eff) and any(e["kind"] == "prices" and e["place"] == town for e in eff)
      and all(e["until"] >= t0 + 4 * 1440 for e in eff if e["kind"] in ("danger", "prices")), eff)

# ---- evidence, as clues
th_now = next(x for x in state["threads"] if x["id"] == "th545")
held = next(c for c in th_now["clues"] if c.get("npc") == a_.id)
check("a piece of evidence a person holds is a clue they know, in words that say they only had it from others",
      held["text"].lower().startswith(("they say", "i was told", "word is", "i had it from others")) and "cut rope" in held["text"]
      and fer and store.load_npc(fer).name in held["text"], held)
rows_a = [r for r in memory.records(store, a_.id) if r["kind"] == "knows" and r["about"].startswith("thread:th545:")]
facts = matters.clue_facts(store, world, store.load_npc(a_.id))
check("...kept among what they know (sure of what they were told, never sure of it), offered to them as a clue to tell",
      rows_a and rows_a[0]["text"] == held["text"] and any(f.text == held["text"] for f in facts), (rows_a, facts))
lying = next(c for c in th_now["clues"] if c.get("place"))
check("a piece lying at a place is a clue of that place, nobody's, with its own words to find", lying["place"] == "trading_square"
      and not lying["npc"] and lying["label"] == "fresh hoofprints by the ford" and not lying["found"], lying)
real_roll = checks.roll
checks.roll = lambda odds, rng, c=None: ("success", 0)
ws.player.location = "trading_square"
found = matters.try_find(ws, "I search the green")
checks.roll = real_roll
st2 = store.load_world_state()
lying2 = next(c for c in next(x for x in st2["threads"] if x["id"] == "th545")["clues"] if c.get("place"))
check("...found by searching where it lies: the player's now", found and lying2["found"], lying2)
check("...a found deed, never the situation's end", any(d["kind"] == "found" and d.get("thread") == "th545" for d in st2.get("deeds", []))
      and next(x for x in st2["threads"] if x["id"] == "th545")["status"] == "active")

log = [r for r in list(pulselog.LOG)[before:] if r["kind"] == "parts"]
check("the pulse's log tells what was written in, never the truth of the evidence", log and len(log[-1]["kept"]) == 14
      and not any("true" in p for p in log[-1]["kept"]), log[-1:] and log[-1]["text"])

# ---- the day's cap on new people
th2 = thread("th545b", "The mill wheel is broken", t0 + 60)
parts2, _, state2 = born(th2, {"people": [{"who": a_.id, "stake": "harmed", "want": "safety"}, {"who": "bargeman", "stake": "can_fix", "want": "coin"}],
                               "ties": [{"a": a_.id, "b": "bargeman", "tie": "kin"}]}, t0 + 60)
skipped = [r for r in pulselog.LOG if r["kind"] == "parts"][-1]["skipped"]
check("a third new person in the town the same day is not made, and the tie resting on them goes with them",
      not any(p.get("role") == "bargeman" for p in parts2) and not any(p["kind"] == "tie" for p in parts2)
      and [s["why"] for s in skipped] == [R["new_today"], R["unmade"]], (parts2, skipped))
check("...and a worry another situation gave is never taken over", store.load_npc(a_.id).concern_from == "th545")
th3 = thread("th545c", "A barge aground", t0 + 1440)
parts3, _, state3 = born(th3, {"people": [{"who": "bargeman", "stake": "can_fix", "want": "coin"}]}, t0 + 1440)
check("...the next day the town takes someone new again", any(p.get("role") == "bargeman" for p in parts3)
      and state3["situation_people"][town] == {"day": clock.day(t0 + 1440), "n": 1}, state3.get("situation_people"))

# ---- the end takes back the worries and moods; what was learned and the ties stay
state = store.load_world_state()
th_now = next(x for x in state["threads"] if x["id"] == "th545")
pulse.end_thread(store, state, th_now, "resolved", "The ford is mended.", t0 + 2 * 1440)
store.save_world_state(state)
after = {p["who"]: store.load_npc(p["who"]) for p in people.values()}
check("at the end each person's worry is settled and its mood gone", all(n.concern_from != "th545" and n.mood_source != "thread:th545"
      for n in after.values()) and after[miller.id].concern_state == "settled", [(n.concern, n.concern_state, n.mood_source) for n in after.values()])
check("...what they learned stays theirs, and the ties stay", [r for r in memory.records(store, a_.id) if r["about"].startswith("thread:th545:")]
      and rel(a_.id, miller.id).get("score", 0) < 0)
check("...and its danger and prices end with it", all(e["until"] <= t0 + 2 * 1440 for e in state["effects"] if e.get("thread") == "th545"
      and e["kind"] in ("danger", "prices")))

# ---- the same world makes the same people
g2 = simlib.campaign("registration_545b", seed=7, location="trading_square")
store_keep = store
store = g2.store
ws2 = g2.scene
ws2.enter("trading_square")
st = store.load_world_state()
st.setdefault("threads", []).append({"id": "th545", "title": "The ford is out", "tier": "rare", "place": "trading_square",
                                     "times": [t0, t0 + 4 * 1440], "status": "active", "made": t0, "clues": [], "paths": []})
acc, _ = situations.check(SituationParts.model_validate({"people": [{"who": "ferryman", "stake": "gains", "want": "coin"}]}), store, world, "rare",
                          random.Random(7), town=town, ways=True, now=t0, players=(ws2.acting,))
again = situation_parts.register(store, world, st, st["threads"][-1], acc, t0, catalog=ws2.catalog, ways=True)
check("the same world and situation make the same person, by name", again and store.load_npc(again[0]["who"]).name
      == store_keep.load_npc(fer).name, (again, store_keep.load_npc(fer).name))
store = store_keep

# ---- (the review) a town's anchor is made as the town makes them; given stands as check judged it; the parts' effects last its span
from npc import life
anchor_place = next((pid for pid in retrieval.town_places(world, town) if life._anchors_wanted(store, world, pid).get("watch_captain")), "")
check("(the town has an anchor of a written trade nobody has met: its watch captain)", bool(anchor_place), anchor_place)
if anchor_place:
    want = life._anchors_wanted(store, world, anchor_place)["watch_captain"]
    th4 = thread("th545d", "Thieves in the market", t0 + 1440 + 60)
    parts4, _, _ = born(th4, {"people": [{"who": "watch_captain", "stake": "can_fix", "want": "safety"}]}, t0 + 1440 + 60)
    cap = store.load_npc(next(p["who"] for p in parts4 if p["kind"] == "person"))
    check("...a written trade that is one of the town's anchors is made as that anchor: their name, their note, protected",
          cap.anchor and cap.protected and (not want.name or cap.name == want.name) and cap.location == anchor_place,
          (cap.name, cap.anchor, cap.protected, want))
    check("...and the town makes no second one when the place is entered", not life._anchors_wanted(store, world, anchor_place).get("watch_captain"))
th5 = thread("th545e", "Short of light", t0 + 2 * 1440)
parts5, _, _ = born(th5, {"people": [{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
                          "resources": [{"good": "candles", "state": "wanted", "wanted_by": a_.id}],
                          "conditions": [{"on": road, "kind": "danger"}]}, t0 + 2 * 1440)
check("a given condition on a good the town sells stands through registration, as check judged it (no reach passed)",
      next(p for p in parts5 if p["kind"] == "person")["condition"] == "given", parts5)
state = store.load_world_state()
th_now = next(x for x in state["threads"] if x["id"] == "th545e")
th_now["times"] = [th_now["times"][0], th_now["times"][-1] + 3 * 1440]
pulse.tick_threads(store, world, ws.catalog, state, t0 + 2 * 1440 + 60, __import__("random").Random(1))
dang = [e for e in state["effects"] if e.get("thread") == "th545e" and e["kind"] == "danger"]
check("(the review) a situation put off keeps its parts' danger its whole span", dang and all(e["until"] >= th_now["times"][-1] for e in dang),
      [(e["until"], th_now["times"][-1]) for e in dang])

# ---- the data
check("situations.yaml's register block checks clean, and data_check with it", situation_parts.problems() == [] and data_check.check() == [],
      situation_parts.problems())
import copy
keep = copy.deepcopy(situations.S["register"])
situations.S["register"]["ties"]["rival"]["a"] = [-90, "a rival"]
situations.S["register"]["moods"]["gains"] = ["pleased {name}"]
del situations.S["register"]["worries"]["coin"]
probs = situation_parts.problems()
situations.S["register"] = keep
check("a tie past the pulse's limits, a mood table short or with a slot, a want with no worry are refused at startup",
      any("ties.rival.a" in p for p in probs) and any("moods.gains" in p for p in probs) and any("worries.coin" in p for p in probs), probs)

for name in ("registration_545", "registration_545b"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

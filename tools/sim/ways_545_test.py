"""(f545 part 4, recommendation 1) A situation's parts are ways through it: one who could set it right does, once their condition is met
(asked, paid, given the good they want, trusted, told what the evidence shows, kept safe), and one who stands in the way stands aside once
won over; each a path of the situation, and meeting it ends the situation as the player's doing. Their yes is given with the player there
(the owner: conditions are checked before a yes): a condition met elsewhere waits for the player's next word with them. A request of the
situation done is that part done: a stranded load carried lifts its price rise for good and is no longer the holder's, and the one who
asked is no longer worried by it.
(f545's review) Told needs the clue's own words, not one of its telling's; trusted needs trust earned since the situation began; given
needs as much of the good as their request asks; a load carried to the one who wanted it meets their given; kept safe is a kill in the
town's wild or on a road the trouble makes dangerous; a load is for the one named alone, handed over as a delivery; the mood the one
who settled it keeps is not the parts' to take back.
Run: python tools/sim/ways_545_test.py"""
import copy
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as uc
for fn in ("note", "narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import circumstance, deeds, drift, events, pulse, regard, retrieval, roads, situation_parts, situations, towns
from engine import inventory as inv
from engine.domain_events import Gift, Persuaded
from llm.contracts import ActionIntent as A, SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("ways_545", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
ws.player.character.coins = 10 ** 5
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
W = situations.S["register"]["ways"]
n = [0]


def born(people, **more):
    """A rare situation at the square with these person parts (and any other parts), registered; its id."""
    n[0] += 1
    tid = f"thw{n[0]}"
    t = ws.minutes
    st = store.load_world_state()
    st.setdefault("threads", []).append({"id": tid, "title": f"Trouble {n[0]}", "tier": "rare", "place": "trading_square",
                                         "times": [t, t + 6 * 1440], "status": "active", "made": t, "clues": [], "paths": [], "stage": 0,
                                         "stages": [{"description": "Trouble.", "effects": []}], "kind": "trouble", "groups": ["everyone"],
                                         "fallout": {"description": "", "effects": []}, "resolution": "", "triumph": None})
    store.save_world_state(st)
    state = store.load_world_state()
    th = next(x for x in state["threads"] if x["id"] == tid)
    acc, dropped = situations.check(SituationParts.model_validate({"people": people, **more}), store, world, "rare", random.Random(n[0]),
                                    town=town, ways=True, now=t, players=(ws.acting,))
    situation_parts.register(store, world, state, th, acc, t, catalog=ws.catalog, ways=True,
                             reach=situations.within_reach(world, town, rows))
    store.save_world_state(state)
    store.meta.minutes += 1                                  # what the player does next is after its birth (a deed in that minute is not)
    return tid


def thread(tid):
    return next(x for x in store.load_world_state()["threads"] if x["id"] == tid)


def present(npc_id):
    npc = store.load_npc(npc_id)
    if all(p.id != npc_id for p in ws.present):
        ws.present = list(ws.present) + [npc]
    return ws.npc_by_id(npc_id) or npc


def gift(npc, **kw):
    ws.notice(Gift(minute=ws.minutes, place=ws.player.location, witnesses=(npc.id,), npc=npc.id, name=npc.name, **kw), npc)


def kill_at(place):
    deed = deeds.log(store, "kill", ws.minutes, place, creature="wolf", level=1, rank="normal", spawn="")
    events.after_deed(ws, deed)

# ---- the ways a situation's people open
check("(the town has three people to cast)", len(rows) >= 3, len(rows))
a_, b_, c_ = rows[0], rows[1], rows[2]
tid = born([{"who": b_.id, "stake": "blocks", "want": "left_alone"}, {"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "paid"},
            {"who": c_.id, "stake": "harmed", "want": "safety"}])
paths = thread(tid)["paths"]
check("one who could set it right opens a way through, by their condition; one who stands in the way, one by winning them over",
      [(p["kind"], p["target"], p.get("need")) for p in paths] == [("part", a_.id, "paid"), ("persuade", b_.id, "")], paths)
check("...each named and told in plain words, with the person's own name", all(store.load_npc(p["target"]).name in p["name"] + p["how"]
      and "_" not in p["how"] for p in paths), [p["how"] for p in paths])

# ---- paid: coin handed over, enough of it
npc = present(a_.id)
gift(npc, coin=W["pay"]["rare"] // 3)
check("coin short of what they ask leaves the situation going on", thread(tid)["status"] == "active")
gift(npc, coin=W["pay"]["rare"])
th = thread(tid)
check("...paid in full, they set it right: the situation is over, the player's doing, by that way", th["status"] != "active"
      and th.get("result") == "player" and (th.get("won_path") or {}).get("target") == a_.id, (th["status"], th.get("result"), th.get("won_path")))

# ---- asked (helps freely): a persuasion that landed
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety"}])
npc = present(a_.id)
check("one who helps freely is a way through by asking", thread(tid)["paths"][0]["need"] == "")
ws.notice(Persuaded(minute=ws.minutes, place="trading_square", witnesses=(a_.id,), npc=a_.id, name=npc.name, how="persuasion", degree="success"), npc)
check("...a persuasion that lands ends it", thread(tid)["status"] != "active", thread(tid)["status"])

# ---- won over: the one who blocks, by the existing persuade path
tid = born([{"who": b_.id, "stake": "blocks", "want": "left_alone"}])
npc = present(b_.id)
for _ in range(2):
    ws.notice(Persuaded(minute=ws.minutes, place="trading_square", witnesses=(b_.id,), npc=b_.id, name=npc.name, how="persuasion", degree="success"), npc)
check("the one who stood in the way, won over twice, stands aside and it ends", thread(tid)["status"] != "active")
check("...and the scene's own copy of them, saved after, keeps their worry let go (the end is told to the copy the turn saves)",
      store.load_npc(b_.id).concern_from != tid and ws.npc_by_id(b_.id).concern_from != tid,
      (store.load_npc(b_.id).concern_from, ws.npc_by_id(b_.id).concern_from))

# ---- what drift's pass puts right, and what it leaves
stale = store.load_npc(b_.id)
stale.concern, stale.concern_from, stale.concern_state = "an old worry", tid, "active"
stale.mood, stale.mood_source, stale.mood_until = "low", situation_parts.mood_source(tid), ws.minutes + 3 * 1440
store.save_npc(stale)
st = store.load_world_state()
st["threads"] = [x for x in st["threads"] if x["id"] != tid]           # trimmed from the ended list long since (pulse.FINISHED_KEPT)
store.save_world_state(st)
st = store.load_world_state()
st["drift"] = {**(st.get("drift") or {}), "cursor": 0}
drift.people(store, world, st, ws.minutes + 10, random.Random(3))
fresh = store.load_npc(b_.id)
check("(the review) a worry or mood the parts gave, brought back by a copy saved late, is let go by drift's own pass - however long "
      "ago the situation ended", fresh.concern_from != tid and not fresh.mood, (fresh.concern_from, fresh.mood, fresh.mood_source))
tid = born([{"who": c_.id, "stake": "harmed", "want": "safety"}])
proud = store.load_npc(rows[0].id)
circumstance.set_mood(proud, "proud, after settling it", ws.minutes, f"thread:{tid}")
st = store.load_world_state()
pulse.end_thread(store, st, next(x for x in st["threads"] if x["id"] == tid), "resolved", "Settled.", ws.minutes)
store.save_world_state(st)
check("(the review) ...while the pride of the one who settled it, the situation's by other means, lasts its own days",
      not situation_parts.sweep(store.load_world_state(), proud, ws.minutes + 10) and proud.mood.startswith("proud"), proud.mood)

# ---- trusted: trust earned since the situation began
tid = born([{"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "trusted"}])
npc = present(c_.id)
regard.set_trust(npc, ws.acting, W["trust"] + 5, cause="test", minute=ws.minutes)      # a first meeting that starts high (a famous name)
situation_parts.heard(ws, npc, "Good day.")
check("(the review) one who wants trust is not won at a word by trust they already gave (a first meeting's, or an old friend's)",
      thread(tid)["status"] == "active")
regard.step(npc, ws.acting, W["trust_gain"] // 2, cause="test", minute=ws.minutes)
situation_parts.heard(ws, npc, "Good day.")
check("...nor by a little more", thread(tid)["status"] == "active")
regard.step(npc, ws.acting, W["trust_gain"], cause="test", minute=ws.minutes)
situation_parts.heard(ws, npc, "Good day.")
check("...earned since, spoken with, they set it right", thread(tid)["status"] != "active", thread(tid)["paths"])

# ---- told: a found clue said to them, in its own words
tid = born([{"who": b_.id, "stake": "can_fix", "want": "believed", "condition": "told"}, {"who": a_.id, "stake": "knows", "want": "believed"}],
           evidence=[{"label": "a broken axle pin", "holder": a_.id, "points_to": "trading_square", "certainty": "sure"}])
clue = thread(tid)["clues"][-1]
st = store.load_world_state()
next(x for x in st["threads"] if x["id"] == tid)["clues"][-1]["found"] = True
store.save_world_state(st)
npc = present(b_.id)
situation_parts.heard(ws, npc, "Nice weather.")
check("one who must be told something is not moved by small talk", thread(tid)["status"] == "active")
situation_parts.heard(ws, npc, "Which way to the square? I found it myself, and it points nowhere.")
check("(the review) ...nor by a word of the place it points to, or of the words its telling is phrased in", thread(tid)["status"] == "active")
situation_parts.heard(ws, npc, "Listen: I found a broken pin off an axle, by the trading square.")
check("...told what the evidence shows, in its own words, they set it right", thread(tid)["status"] != "active", clue)
tid = born([{"who": a_.id, "stake": "can_fix", "want": "believed", "condition": "told"}],
           evidence=[{"label": "a cut rope", "holder": a_.id, "points_to": "trading_square", "certainty": "sure"}])
st = store.load_world_state()
next(x for x in st["threads"] if x["id"] == tid)["clues"][-1]["found"] = True
store.save_world_state(st)
situation_parts.heard(ws, present(a_.id), "There is a cut rope at the trading square.")
check("(the review) ...but never by telling them what they hold themselves", thread(tid)["status"] == "active")
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety"}])
st = store.load_world_state()
deeds.log(store, "persuade", next(x for x in st["threads"] if x["id"] == tid)["made"], "trading_square", npc=a_.id, degree="success")
situation_parts.heard(ws, present(a_.id), "Good day.")
check("(the review) a persuasion in the very minute it began, before it was there to ask about, is not asking", thread(tid)["status"] == "active")

# ---- given: as much of the good as they ask, handed over
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
           resources=[{"good": "candles", "state": "wanted", "wanted_by": a_.id}])
th = thread(tid)
check("one who wants a good to hand opens a way by it", th["paths"][0]["need"] == "given" and th["paths"][0]["good"] == "candles"
      and "candles" in th["paths"][0]["how"], th["paths"])
want = next(p for p in th["parts"] if p["kind"] == "resource")["request"]["count"]
npc = present(a_.id)
one = inv.label(inv.make_good("candles", 1))
gift(npc, item=one)
check("(the review) one candle handed over, when they ask for more, is not what they asked", want == 1 or thread(tid)["status"] == "active",
      want)
for _ in range(want - 1):
    gift(npc, item=one)
check("...as many as they ask, and they set it right", thread(tid)["status"] != "active", want)
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
           resources=[{"good": "candles", "state": "wanted", "wanted_by": a_.id}])
npc = present(a_.id)
situation_parts.ask(ws, npc)
ws.take_personal(npc)
q = next(q for q in ws.player.quests if str(q.get("part", "")).startswith(tid + ":"))
ws.to_pack(inv.make_good("candles", q["count"]))
ws.turn_in(a_.id)
check("...or their request for it handed in", thread(tid)["status"] != "active" and not any(x is q for x in ws.player.quests),
      thread(tid)["status"])

# ---- protected: a kill where the trouble is, their yes with the player there
wild = sorted(towns.town_places(world, town) - set(retrieval.town_places(world, town)))
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))
tid = born([{"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "protected"}],
           conditions=[{"on": road, "kind": "danger"}])
far = next(pid for pid in sorted(world.places) if pid not in towns.town_places(world, town) and world.places[pid].type != "road")
kill_at(far)
check("one who must be kept safe is not kept safe by a kill far away", not thread(tid)["paths"][0].get("protected"))
r = world.roads[road]
stop = roads.make_stop(world, r.from_, r.to, 0.5, 60, "fight", "", "a fight on the road")
from world.loader import Place
world.add_place(Place(**stop["place"]))
kill_at(stop["id"])
th = thread(tid)
check("(the review) a kill at a stop on the road the trouble makes dangerous keeps them safe...", bool(th["paths"][0].get("protected")),
      th["paths"])
check("...and they say yes when the player is next with them, not before", th["status"] == "active")
situation_parts.heard(ws, present(c_.id), "It is done; the road is safe.")
check("...spoken with, they set it right", thread(tid)["status"] != "active")
if wild:
    tid = born([{"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "protected"}])
    kill_at(wild[0])
    check("(the review) with no road made dangerous, a kill in the town's own wild keeps them safe", bool(thread(tid)["paths"][0].get("protected")),
          (wild, thread(tid)["paths"]))

# ---- paid away from them: the yes waits for them
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "paid"}])
st = store.load_world_state()
deeds.log(store, "gift", ws.minutes, "trading_square", npc=a_.id, coin=W["pay"]["rare"])
events.after_deed(ws, {"kind": "heard", "minute": ws.minutes, "place": ws.player.location, "npc": b_.id})
check("(the owner: a yes is theirs to give) a condition met is not their yes while the player is with someone else",
      thread(tid)["status"] == "active")
situation_parts.heard(ws, present(a_.id), "Good day.")
check("...and is, at the player's next word with them", thread(tid)["status"] != "active")

# ---- a stranded load carried: that part done, for good
tid = born([{"who": b_.id, "stake": "harmed", "want": "goods_moved"}], resources=[{"good": "salt", "state": "stranded", "holder": b_.id}])
f_before = pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt")
npc = present(b_.id)
situation_parts.ask(ws, npc)
ws.take_personal(npc)
q = next(q for q in ws.player.quests if str(q.get("part", "")).startswith(tid + ":"))
check("the holder of a stranded load asks for it carried to one who deals in it", q["kind"] == "deliver" and "salt" in q["item"], q)
to = store.load_npc(next(p for p in thread(tid)["parts"] if p["kind"] == "resource")["request"]["to"])
key = next(k for k in ws.player.character.key_items if k.id == f"quest_{q['id']}")
other = next(p for p in retrieval.people_in_town(store, world, town) if p.id != to.id and p.id != b_.id)
namesake = copy.copy(store.load_npc(other.id))
namesake.name, namesake.role = to.name.split()[0] + " Oddlow", to.role
ws.record_delivery(key, namesake)
check("(the review) the load is for the one named: not anyone of their trade, nor one who shares their first name",
      next(x for x in ws.player.quests if x["id"] == q["id"])["progress"] == 0)
present(to.id)
ws.on_give(A(kind="give", target=to.id, item=key.name), f"give the load to {to.name}")
check("...handed to them, it is delivered, told as a delivery", next(x for x in ws.player.quests if x["id"] == q["id"])["progress"] == 1
      and ws.player.character.item_history[-1].startswith("Delivered"), ws.player.character.item_history[-1:])
st = store.load_world_state()
st["last"] = ws.minutes - pulse.INTERVAL - 30                         # a pulse boundary passed this turn, its tick still to run
store.save_world_state(st)
ws.turn_in(b_.id)
th = thread(tid)
part = next(p for p in th["parts"] if p["kind"] == "resource")
check("...carried and handed in, that part is done", part.get("done"), part)
check("...its price rise is lifted", f_before > 1 and pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt")
      == pulse.price_factor(store, world, "trading_square", ws.minutes + 1), f_before)
st = store.load_world_state()
pulse.tick_threads(store, world, ws.catalog, st, ws.minutes - 30, random.Random(1))
store.save_world_state(st)
check("(the review) ...for good: the turn's late tick does not renew it", pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt")
      == pulse.price_factor(store, world, "trading_square", ws.minutes + 1))
check("...and the one who asked is no longer worried by it", store.load_npc(b_.id).concern_from != tid
      and store.load_npc(b_.id).concern_state == "settled", (store.load_npc(b_.id).concern, store.load_npc(b_.id).concern_state))
check("...while the situation itself goes on (a load carried is not the trouble ended)", th["status"] == "active")

# ---- a load carried to the one who wanted it meets their given
tid = born([{"who": b_.id, "stake": "harmed", "want": "goods_moved"}, {"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
           resources=[{"good": "salt", "state": "stranded", "holder": b_.id}, {"good": "salt", "state": "wanted", "wanted_by": c_.id},
                      {"good": "salt", "state": "scarce"}])
parts = thread(tid)["parts"]
stranded = next(p for p in parts if p["kind"] == "resource" and p["state"] == "stranded")
check("(the review) a stranded load is carried to the one of the situation who wants it", stranded["request"]["to"] == c_.id, stranded)
npc = present(b_.id)
situation_parts.ask(ws, npc)
ws.take_personal(npc)
q = next(q for q in ws.player.quests if str(q.get("part", "")).startswith(tid + ":"))
key = next(k for k in ws.player.character.key_items if k.id == f"quest_{q['id']}")
present(c_.id)
ws.on_give(A(kind="give", target=c_.id, item=key.name), "give the load")
ws.turn_in(b_.id)
check("(the review) ...the scarce rise of the same good is its own part's, not lifted with the load's",
      pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt") > pulse.price_factor(store, world, "trading_square", ws.minutes + 1))
situation_parts.heard(ws, present(c_.id), "Your salt came.")
check("(the review) ...and, carried and handed in, the one who wanted it has what they asked: they set it right",
      thread(tid)["status"] != "active", thread(tid)["paths"])

# ---- the data
check("the ways' data checks clean", situation_parts.problems() == [], situation_parts.problems())
keep = copy.deepcopy(situations.S["register"]["ways"])
situations.S["register"]["ways"]["how"]["given"] = "Bring {name} something."
situations.S["register"]["ways"]["pay"].pop("rare")
situations.S["register"]["ways"]["told_skip"] = ["the", False]
probs = situation_parts.problems()
situations.S["register"]["ways"] = keep
check("a given way that names no good, a tier with no price, a filler word YAML read as something else, are refused at startup",
      any("ways.how.given" in p for p in probs) and any("ways.pay" in p for p in probs) and any("told_skip" in p for p in probs), probs)

shutil.rmtree("saves/ways_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

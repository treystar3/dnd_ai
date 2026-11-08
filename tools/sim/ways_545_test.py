"""(f545 part 4, recommendation 1) A situation's parts are ways through it: one who could set it right does, once their condition is met
(asked, paid, given the good they want, trusted, told what the evidence shows, kept safe), and one who stands in the way stands aside once
won over; each a path of the situation, and meeting it ends the situation as the player's doing. A request of the situation done is that
part done: a stranded load carried lifts its price rise and is no longer the holder's, and the one who asked is no longer worried by it.
Run: python tools/sim/ways_545_test.py"""
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
from engine import deeds, events, pulse, regard, retrieval, situation_parts, situations
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
    return tid


def thread(tid):
    return next(x for x in store.load_world_state()["threads"] if x["id"] == tid)


def present(npc_id):
    npc = store.load_npc(npc_id)
    if all(p.id != npc_id for p in ws.present):
        ws.present = list(ws.present) + [npc]
    return npc

# ---- the ways a situation's people open
check("(the town has three people to cast)", len(rows) >= 3, len(rows))
a_, b_, c_ = rows[0], rows[1], rows[2]
d_ = b_                                                     # each way is its own situation: one person may be in several
tid = born([{"who": b_.id, "stake": "blocks", "want": "left_alone"}, {"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "paid"},
            {"who": c_.id, "stake": "harmed", "want": "safety"}])
paths = thread(tid)["paths"]
check("one who could set it right opens a way through, by their condition; one who stands in the way, one by winning them over",
      [(p["kind"], p["target"], p.get("need")) for p in paths] == [("part", a_.id, "paid"), ("persuade", b_.id, "")], paths)
check("...each named and told in plain words, with the person's own name", all(store.load_npc(p["target"]).name in p["name"] + p["how"]
      and "_" not in p["how"] for p in paths), [p["how"] for p in paths])

# ---- paid: coin handed over, enough of it
npc = present(a_.id)
ws.notice(Gift(minute=ws.minutes, place="trading_square", witnesses=(a_.id,), npc=a_.id, name=npc.name, coin=W["pay"]["rare"] // 3), npc)
check("coin short of what they ask leaves the situation going on", thread(tid)["status"] == "active")
ws.notice(Gift(minute=ws.minutes, place="trading_square", witnesses=(a_.id,), npc=a_.id, name=npc.name, coin=W["pay"]["rare"]), npc)
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
stale = store.load_npc(b_.id)
stale.concern, stale.concern_from, stale.concern_state = "an old worry", tid, "active"
stale.mood, stale.mood_source = "low", f"thread:{tid}"
check("a worry or mood an ended situation gave, brought back by a copy saved late, is let go by the drift's pass",
      situation_parts.sweep(store.load_world_state(), stale, ws.minutes) and stale.concern_from != tid and not stale.mood)

# ---- trusted: their trust earned, noticed when they are spoken with
tid = born([{"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "trusted"}])
npc = present(c_.id)
situation_parts.heard(ws, npc, "Good day.")
check("one who wants trust is not won by a word while trust is short", thread(tid)["status"] == "active")
regard.step(npc, ws.acting, W["trust"] + 10, cause="test", minute=ws.minutes)
store.save_npc(npc)
situation_parts.heard(ws, store.load_npc(c_.id), "Good day.")
check("...once trusted, spoken with, they set it right", thread(tid)["status"] != "active", thread(tid)["paths"])

# ---- told: a found clue said to them
tid = born([{"who": d_.id, "stake": "can_fix", "want": "believed", "condition": "told"}, {"who": a_.id, "stake": "knows", "want": "believed"}],
           evidence=[{"label": "a broken axle pin", "holder": a_.id, "points_to": "trading_square", "certainty": "sure"}])
th = thread(tid)
clue = th["clues"][-1]
st = store.load_world_state()
next(x for x in st["threads"] if x["id"] == tid)["clues"][-1]["found"] = True
store.save_world_state(st)
npc = present(d_.id)
situation_parts.heard(ws, npc, "Nice weather.")
check("one who must be told something is not moved by small talk", thread(tid)["status"] == "active")
situation_parts.heard(ws, npc, "Listen: " + clue["text"])
check("...told what the evidence shows (a found clue, in its own words), they set it right", thread(tid)["status"] != "active", clue["text"])

# ---- given: the good they want, their request for it done
tid = born([{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
           resources=[{"good": "candles", "state": "wanted", "wanted_by": a_.id}])
th = thread(tid)
check("one who wants a good to hand opens a way by it (candles: Parth's chandler sells them)", th["paths"][0]["need"] == "given"
      and th["paths"][0]["good"] == "candles" and "candles" in th["paths"][0]["how"], th["paths"])
npc = present(a_.id)
situation_parts.ask(ws, npc)
ws.take_personal(npc)
q = next(q for q in ws.player.quests if str(q.get("part", "")).startswith(tid + ":"))
from engine import inventory as inv
ws.to_pack(inv.make_good("candles", q["count"]))
ws.turn_in(a_.id)
check("...their request for it handed in, they set it right", thread(tid)["status"] != "active" and not any(x is q for x in ws.player.quests),
      thread(tid)["status"])

# ---- protected: a kill where the trouble is
tid = born([{"who": c_.id, "stake": "can_fix", "want": "safety", "condition": "protected"}],
           conditions=[{"on": "trading_square", "kind": "danger"}])
state = store.load_world_state()
deed = deeds.log(store, "kill", ws.minutes, "trading_square", creature="wolf", level=1, rank="normal", spawn="")
events.after_deed(ws, deed)
check("one who must be kept safe sets it right once what threatens the place is killed there", thread(tid)["status"] != "active")

# ---- a stranded load carried: that part done
tid = born([{"who": b_.id, "stake": "harmed", "want": "goods_moved"}], resources=[{"good": "salt", "state": "stranded", "holder": b_.id}])
f_before = pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt")
npc = present(b_.id)
situation_parts.ask(ws, npc)
ws.take_personal(npc)
q = next(q for q in ws.player.quests if str(q.get("part", "")).startswith(tid + ":"))
check("the holder of a stranded load asks for it carried to one who deals in it", q["kind"] == "deliver" and "salt" in q["item"], q)
to = next(p for p in retrieval.people_in_town(store, world, town) if p.role == q["to_role"])
key = next(k for k in ws.player.character.key_items if k.id == f"quest_{q['id']}")
ws.record_delivery(key, store.load_npc(to.id))
check("...the load handed to them is delivered", next(x for x in ws.player.quests if x["id"] == q["id"])["progress"] == 1)
ws.turn_in(b_.id)
th = thread(tid)
part = next(p for p in th["parts"] if p["kind"] == "resource")
check("...carried and handed in, that part is done and the load is no longer theirs to sell", part.get("done")
      and store.load_entity(f"stock:{b_.id}:salt").state == "released", (part, store.load_entity(f"stock:{b_.id}:salt")))
check("...its price rise is lifted", f_before > 1 and pulse.price_factor(store, world, "trading_square", ws.minutes + 1, "salt")
      == pulse.price_factor(store, world, "trading_square", ws.minutes + 1), f_before)
check("...and the one who asked is no longer worried by it", store.load_npc(b_.id).concern_from != tid
      and store.load_npc(b_.id).concern_state == "settled", (store.load_npc(b_.id).concern, store.load_npc(b_.id).concern_state))
check("...while the situation itself goes on (a load carried is not the trouble ended)", th["status"] == "active")

# ---- the data
check("the ways' data checks clean", situation_parts.problems() == [], situation_parts.problems())
import copy
keep = copy.deepcopy(situations.S["register"]["ways"])
situations.S["register"]["ways"]["how"]["given"] = "Bring {name} something."
situations.S["register"]["ways"]["pay"].pop("rare")
probs = situation_parts.problems()
situations.S["register"]["ways"] = keep
check("a given way that names no good, a tier with no price, are refused at startup",
      any("ways.how.given" in p for p in probs) and any("ways.pay" in p for p in probs), probs)

shutil.rmtree("saves/ways_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

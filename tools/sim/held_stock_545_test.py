"""(f545 part 3) What a situation's people hold is real: a small stock of the good, theirs to sell until it is gone (or to lose to a
thief), one row a situation so each goes with its own, shown wherever their wares are and sold before their trade's own list; a scarce
or stranded good is dearer in the town, that good alone; a stranded load is (the owner) a price rise, the holder's worry and a request,
no store of its own; the one who wants a good asks for it, and the one whose load is stranded asks for it to be carried to someone
named, each a request opened for the character who speaks with them, let go (the owner, 2026-11-03) when a new conversation opens
without it taken and then not asked of them again, never asked again once handed in; a good they hold that their trade sells too is one
ware, sold from what they hold first; and the situation's end lets go what is still held and what nobody said yes to, with no "had no
yes" said of it.
Run: python tools/sim/held_stock_545_test.py"""
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
from engine import inventory as inv, memory, obligations, pulse, retrieval, situation_parts, situations, towns
from llm.contracts import ActionIntent as A, SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

g = simlib.campaign("held_stock_545", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
ws.player.character.coins = 10 ** 5
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
a_, b_ = rows[0], rows[1]
R = situations.S["register"]
n = [0]


def born(kw, t=None):
    n[0] += 1
    tid, t = f"thh{n[0]}", ws.minutes if t is None else t
    st = store.load_world_state()
    st.setdefault("threads", []).append({"id": tid, "title": f"The salt road is cut {n[0]}", "tier": "rare", "place": "trading_square",
                                         "times": [t, t + 5 * 1440], "status": "active", "made": t, "clues": [], "paths": [], "stage": 0,
                                         "stages": [{"description": "The salt road is cut.", "effects": []}], "kind": "trouble",
                                         "groups": ["everyone"]})
    store.save_world_state(st)
    state = store.load_world_state()
    th = state["threads"][-1]
    acc, dropped = situations.check(SituationParts.model_validate(kw), store, world, "rare", random.Random(7), town=town, ways=True, now=t,
                                    players=(ws.acting,))
    parts = situation_parts.register(store, world, state, th, acc, t, catalog=ws.catalog, ways=True)
    store.save_world_state(state)
    return tid, parts, dropped


def end(tid, status="ended"):
    state = store.load_world_state()
    pulse.end_thread(store, state, next(x for x in state["threads"] if x["id"] == tid), status, "Over.", ws.minutes + 60)
    store.save_world_state(state)


tid, parts, dropped = born({"people": [{"who": a_.id, "stake": "harmed", "want": "goods_moved", "holds": "salt"},
                                       {"who": b_.id, "stake": "harmed", "want": "goods_moved"}],
                            "resources": [{"good": "salt", "state": "stranded", "holder": b_.id},
                                          {"good": "candles", "state": "wanted", "wanted_by": a_.id}, {"good": "grain", "state": "scarce"}]})
check("(all kept)", not dropped and len(parts) == 5, dropped)
CANDLES = f"{tid}:" + str(next(i for i, p in enumerate(parts) if p.get("good") == "candles"))

# ---- held stock
sa = situation_parts.held(store, a_.id, "salt")
check("a person who holds a good holds a real stock of it, that situation's", len(sa) == 1 and R["stock"][0] <= sa[0].data["count"] <= R["stock"][1]
      and sa[0].data["thread"] == tid, [e.data for e in sa])
check("(the owner) a stranded load is a price rise, the holder's worry and a request: no store of its own",
      not situation_parts.held(store, b_.id, "salt") and store.load_npc(b_.id).concern_from == tid)
n_a = store.load_npc(a_.id)
ware = next(w for w in ws.wares_of(n_a) if w.id == "stock:salt")
check("what they hold is among their wares, first, at the good's own price", ws.wares_of(n_a)[0].id == "stock:salt"
      and ware.price == inv.GOODS["salt"].price and ware.item == "salt")
check("...said at the price the game will charge", f"salt: " in " ".join(ws.wares_said(n_a))
      and any(line == f"salt: {__import__('engine.money', fromlist=['words']).words(ws.quote_ware(n_a, ware).price)}" for line in ws.wares_said(n_a)),
      ws.wares_said(n_a))
from npc import life
check("...and the person's own prompt lists it among what they sell", any(w.id == "stock:salt" for w in life._wares(store, world, n_a)))

# ---- a second situation's stock is its own
tid2, _, _ = born({"people": [{"who": a_.id, "stake": "gains", "want": "coin", "holds": "salt"}]})
check("a second situation's salt is a row of its own, never added to the first's",
      sorted(e.data["thread"] for e in situation_parts.held(store, a_.id, "salt")) == sorted([tid, tid2]))
check("...yet one ware of salt in their list", sum(1 for w in ws.wares_of(store.load_npc(a_.id)) if w.id == "stock:salt") == 1)
end(tid2)
check("...and its end lets go its own salt, never the first's", [e.data["thread"] for e in situation_parts.held(store, a_.id, "salt")] == [tid])

# ---- one good's price
f_all = pulse.price_factor(store, world, "trading_square", ws.minutes + 10)
f_salt = pulse.price_factor(store, world, "trading_square", ws.minutes + 10, "salt")
f_grain = pulse.price_factor(store, world, "trading_square", ws.minutes + 10, "grain")
state = store.load_world_state()
check("a stranded good is dearer in the town, that good alone", abs(f_salt - f_all - R["stranded"] / 100) < 1e-9, (f_all, f_salt))
check("...a scarce one more so", abs(f_grain - f_all - R["scarce"] / 100) < 1e-9, (f_all, f_grain))
check("...while the town's market is not dearer for it", towns._effect_total(state, "prices", {town}, ws.minutes + 10) == 0)
q_salt = ws.quote_ware(n_a, ware).price
check("...and the quote of salt carries it", q_salt == ws.price_of(inv.GOODS["salt"].price, n_a, "item", "salt") and q_salt > ws.price_of(inv.GOODS["salt"].price, n_a, "item"),
      q_salt)

# ---- bought until gone, before the trade's own list; stolen
had = situation_parts.held(store, a_.id, "salt")[0].data["count"]
if all(p.id != a_.id for p in ws.present):
    ws.present = list(ws.present) + [n_a]
ws.on_buy(A(kind="buy", target=a_.id, ware="salt"), "buy some salt")
check("buying salt from them takes one from what they hold, and the salt is the player's",
      situation_parts.held(store, a_.id, "salt")[0].data["count"] == had - 1 and any(i.good == "salt" for i in ws.pack))
for _ in range(had - 1):
    ws.on_buy(A(kind="buy", target=a_.id, ware="salt"), "buy some salt")
check("...until none is left: no longer among their wares", not situation_parts.held(store, a_.id, "salt")
      and not any(w.id == "stock:salt" for w in ws.wares_of(store.load_npc(a_.id))))
tid3, _, _ = born({"people": [{"who": b_.id, "stake": "gains", "want": "coin", "holds": "rope"}]})
n_b = store.load_npc(b_.id)
if all(p.id != b_.id for p in ws.present):
    ws.present = list(ws.present) + [n_b]
loot = ws.find_loot(n_b, "the rope", "steal the rope")
before = situation_parts.held(store, b_.id, "rope")[0].data["count"]
ws.take_loot(loot, n_b, n_b.id)
after = situation_parts.held(store, b_.id, "rope")
check("a thief reaching for the rope takes it from what they hold", loot.get("mode") == "ware" and loot["ware"].id == "stock:rope"
      and (after[0].data["count"] if after else 0) == before - 1 and any(i.good == "rope" for i in ws.pack), (loot, before, after))
check("...and a thief's taking the last of it ends it lost", situation_parts.take_stock(store, b_.id, "rope", 99, ws.minutes, "lost") >= 1
      and not situation_parts.held(store, b_.id, "rope") and any(e.state == "lost" for e in store.find_entities(kind="stock") if e.data.get("good") == "rope"))

# ---- one ware a good: what they hold sells first, even when their trade sells the good too
c_ = rows[2]
own = next(((r, w.item) for r in rows for w in world.roles[r.role].sells if w.kind == "item" and w.item in situations._goods()), None)
check("(a person of the town whose trade sells one of the situation's goods)", own is not None)
seller, good = own
tid5, _, _ = born({"people": [{"who": seller.id, "stake": "gains", "want": "coin", "holds": good}]})
n_s = store.load_npc(seller.id)
same = [w for w in ws.wares_of(n_s) if w.kind == "item" and w.item == good]
check("(the review) a good they hold and their trade sells is one ware, theirs held first", len(same) == 1 and same[0].id == f"stock:{good}", same)
check("...and so in their own prompt", sum(1 for w in life._wares(store, world, n_s) if w.kind == "item" and w.item == good) == 1)
if all(p.id != seller.id for p in ws.present):
    ws.present = list(ws.present) + [n_s]
had = situation_parts.held(store, seller.id, good)[0].data["count"]
ws.on_buy(A(kind="buy", target=seller.id, ware=good), f"buy {good}")
check("(the review) ...asked for by the good's own word, it is sold from what they hold", situation_parts.held(store, seller.id, good)[0].data["count"]
      == had - 1, (good, had))
end(tid5)

# ---- asked of the one who speaks with them
ws.on_talk(A(kind="talk", target=a_.id, speech="How are things?"), "How are things?")
req = obligations.current(store, "request", a_.id, ws.acting)
check("the one who wants candles asks the character who speaks with them to bring some", req and req.data["terms"]["kind"] == "gather"
      and req.data["terms"]["good"] == "candles" and req.data["terms"]["part"] == CANDLES
      and ws.request_of(store.load_npc(a_.id))["title"].startswith("Bring"), req and req.data)
ws.take_personal(store.load_npc(a_.id))
check("...a yes makes it the character's, as any request", any(q.get("part") == CANDLES for q in ws.player.quests))
situation_parts.ask(ws, store.load_npc(a_.id))
check("...not asked again while it is held", obligations.current(store, "request", a_.id, ws.acting) is None)
q = next(q for q in ws.player.quests if q.get("part") == CANDLES)
ws.to_pack(inv.make_good("candles", q["count"] * 2))
coins = ws.player.character.coins
ws.on_talk(A(kind="talk", target=a_.id, speech="Here are your candles."), "Here are your candles.")
paid = ws.player.character.coins - coins
ws.convo = []
store.meta.minutes += 30
ws.on_talk(A(kind="talk", target=a_.id, speech="Anything else?"), "Anything else?")
check("(the review) handed in, it is paid once and never asked again: the part is done",
      paid > 0 and ws.player.character.coins - coins == paid and obligations.current(store, "request", a_.id, ws.acting) is None
      and next(p for p in next(x for x in store.load_world_state()["threads"] if x["id"] == tid)["parts"] if p.get("good") == "candles").get("done"),
      (paid, ws.player.character.coins - coins))

situation_parts.ask(ws, store.load_npc(b_.id))
reqb = obligations.current(store, "request", b_.id, ws.acting)
target = next(p for p in parts if p.get("good") == "salt" and p["kind"] == "resource")["request"]["to"]
to = store.load_npc(target)
check("the one whose load is stranded asks for it carried to someone named of the town who deals in it",
      reqb and reqb.data["terms"]["kind"] == "deliver" and "salt" in reqb.data["terms"]["item"] and to.name in reqb.data["terms"]["title"]
      and reqb.data["terms"]["to_id"] == to.id
      and (any(w.item == "salt" for w in world.roles[to.role].sells) or "any" in world.roles[to.role].buys), reqb and reqb.data["terms"])
ws.convo = []
store.meta.minutes += 30
if all(p.id != b_.id for p in ws.present):
    ws.present = list(ws.present) + [store.load_npc(b_.id)]
ws.on_talk(A(kind="talk", target=b_.id, speech="Good day."), "Good day.")
gone = store.load_entity(reqb.ref)
check("(the owner, 2026-11-03) a situation's request left without a yes is let go when a new conversation opens, as any request, "
      "for its reason", gone.state == "released" and gone.data.get("cause") == "no_answer", gone.data)
check("...and is not asked again of that character", obligations.current(store, "request", b_.id, ws.acting) is None)
situation_parts.ask(ws, store.load_npc(b_.id))
check("...however often they speak", obligations.current(store, "request", b_.id, ws.acting) is None)

# ---- (the second review) one load, one carrier: by who holds it now, never by an old record
tid6, parts6, _ = born({"people": [{"who": b_.id, "stake": "harmed", "want": "goods_moved"}],
                        "resources": [{"good": "wine", "state": "stranded", "holder": b_.id}]})
key6 = f"{tid6}:" + str(next(i for i, p in enumerate(parts6) if p.get("good") == "wine"))
other_ask = obligations.open_(store, "request", b_.id, "char2", "Deliver the wine", ws.minutes,
                              terms={"kind": "deliver", "part": key6, "title": "Deliver the wine"}, key=f"part:{key6}:char2")
situation_parts.ask(ws, store.load_npc(b_.id))
ws.take_personal(store.load_npc(b_.id))
check("(the second review) a yes to a part lets go the same request open to another character",
      store.load_entity(other_ask.ref).state == "released" and key6 in situation_parts.carried(store), store.load_entity(other_ask.ref).state)
q6 = next(q for q in ws.player.quests if q.get("part") == key6)
ws.on_abandon_quest(A(kind="abandon_quest", item=q6["title"]), f"abandon {q6['title']}")
gave_up = not any(q.get("part") == key6 for q in ws.player.quests)
check("(the second review) ...given up, it is carried by no one, free for another character", gave_up and key6 not in situation_parts.carried(store),
      [q.get("part") for q in ws.player.quests])
situation_parts.ask(ws, store.load_npc(b_.id))
check("...but never asked again of the one who gave it up", obligations.current(store, "request", b_.id, ws.acting) is None
      and ws.acting in next(p for p in next(x for x in store.load_world_state()["threads"] if x["id"] == tid6)["parts"]
                            if p.get("good") == "wine").get("declined", []))
end(tid6)

# ---- (the third review) never a load to carry to the dead
tid7, parts7, _ = born({"people": [{"who": b_.id, "stake": "harmed", "want": "goods_moved"}],
                        "resources": [{"good": "flour", "state": "stranded", "holder": b_.id}]})
to7 = next(p for p in parts7 if p.get("good") == "flour")["request"]["to"]
dead = store.load_npc(to7)
dead.gone = "drowned at the ford"
store.save_npc(dead)
for e in obligations.open_ones(store, "request"):
    obligations.close(store, e, "released", "over", ws.minutes, remember=False)
situation_parts.ask(ws, store.load_npc(b_.id))
r7 = obligations.current(store, "request", b_.id, ws.acting)
check("(the third review) a load whose one to receive it is gone is asked of no one", r7 is None
      or not str((r7.data.get("terms") or {}).get("part", "")).startswith(tid7 + ":"), r7 and r7.data)
dead.gone = ""
store.save_npc(dead)
end(tid7)

# ---- the end lets go what is held and unanswered, saying no "had no yes"
tid4, _, _ = born({"people": [{"who": c_.id, "stake": "gains", "want": "coin", "holds": "cloth"}],
                   "resources": [{"good": "rope", "state": "wanted", "wanted_by": c_.id}]})
situation_parts.ask(ws, store.load_npc(c_.id))
reqc = obligations.current(store, "request", c_.id, ws.acting)
check("(another situation's person asks their own)", reqc is not None and str(reqc.data["terms"]["part"]).startswith(tid4 + ":"))
end(tid)
end(tid4)
check("at the situation's end what is still held of it moves on", not situation_parts.held(store, c_.id, "cloth"))
closed = store.load_entity(reqc.ref)
check("...a request nobody said yes to is let go, for its reason", closed.state == "released" and closed.data.get("cause") == "over", closed.data)
check("...without the asker keeping 'had no yes' of it (the matter ended; nobody turned them down)",
      not any("had no yes" in r["text"] for r in memory.records(store, c_.id)))
check("its price rises end with it", pulse.price_factor(store, world, "trading_square", ws.minutes + 2 * 1440, "salt")
      == pulse.price_factor(store, world, "trading_square", ws.minutes + 2 * 1440))

shutil.rmtree("saves/held_stock_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

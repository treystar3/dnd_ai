"""(f545 part 3) What a situation's people hold is real: a small stock of the good, theirs to sell until it is gone (or to lose to a
thief), shown wherever their wares are; a scarce or stranded good is dearer in the town, that good alone; the one who wants a good asks
for it, and the one whose load is stranded asks for it to be carried, each a request opened for the character who speaks with them;
and the situation's end lets go what is still held and what nobody said yes to.
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
from engine import inventory as inv, obligations, pulse, retrieval, situation_parts, situations, towns
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
t0 = ws.minutes
st = store.load_world_state()
st.setdefault("threads", []).append({"id": "thh", "title": "The salt road is cut", "tier": "rare", "place": "trading_square",
                                     "times": [t0, t0 + 5 * 1440], "status": "active", "made": t0, "clues": [], "paths": [], "stage": 0,
                                     "stages": [{"description": "The salt road is cut.", "effects": []}], "kind": "trouble", "groups": ["everyone"]})
store.save_world_state(st)
state = store.load_world_state()
th = state["threads"][-1]
acc, dropped = situations.check(SituationParts.model_validate({
    "people": [{"who": a_.id, "stake": "harmed", "want": "goods_moved", "holds": "salt"}, {"who": b_.id, "stake": "harmed", "want": "goods_moved"}],
    "resources": [{"good": "salt", "state": "stranded", "holder": b_.id}, {"good": "candles", "state": "wanted", "wanted_by": a_.id},
                  {"good": "grain", "state": "scarce"}]}), store, world, "rare", random.Random(7), town=town, ways=True, now=t0, players=(ws.acting,))
parts = situation_parts.register(store, world, state, th, acc, t0, catalog=ws.catalog, ways=True)
store.save_world_state(state)
check("(all kept)", not dropped and len(parts) == 5, dropped)
CANDLES = "thh:" + str(next(i for i, p in enumerate(parts) if p.get("good") == "candles"))

# ---- held stock
sa, sb = store.load_entity(f"stock:{a_.id}:salt"), store.load_entity(f"stock:{b_.id}:salt")
lo, hi = situations.S["register"]["stock"]
llo, lhi = situations.S["register"]["load"]
check("a person who holds a good holds a real stock of it, the situation's", sa and sa.state == "held" and lo <= sa.data["count"] <= hi
      and sa.data["thread"] == "thh" and not sa.data["load"], sa)
check("...and a stranded load is a larger stock, marked a load", sb and llo <= sb.data["count"] <= lhi and sb.data["load"], sb)
n_a = store.load_npc(a_.id)
check("what they hold is among their wares, at the good's own price", any(w.id == "stock:salt" and w.item == "salt" for w in ws.wares_of(n_a)))
check("...said at the price the game will charge", any(line.startswith("salt:") for line in ws.wares_said(n_a)), ws.wares_said(n_a))
from npc import life
check("...and the person's own prompt lists it among what they sell", any(w.id == "stock:salt" for w in life._held_wares(store, a_.id)))

# ---- one good's price
f_all = pulse.price_factor(store, world, "trading_square", t0 + 10)
f_salt = pulse.price_factor(store, world, "trading_square", t0 + 10, "salt")
f_grain = pulse.price_factor(store, world, "trading_square", t0 + 10, "grain")
R = situations.S["register"]
check("a stranded good is dearer in the town, that good alone", abs(f_salt - f_all - R["stranded"] / 100) < 1e-9, (f_all, f_salt))
check("...a scarce one more so", abs(f_grain - f_all - R["scarce"] / 100) < 1e-9, (f_all, f_grain))
check("...while the town's market is not dearer for it", towns._effect_total(state, "prices", {town}, t0 + 10) == 0)
q_salt = ws.quote_ware(n_a, next(w for w in ws.wares_of(n_a) if w.id == "stock:salt")).price
check("...and the quote of salt carries it", q_salt == ws.price_of(inv.GOODS["salt"].price, n_a, "item", "salt") and q_salt > ws.price_of(inv.GOODS["salt"].price, n_a, "item"),
      q_salt)

# ---- bought until gone
had = sa.data["count"]
ws.present = list(ws.present) + [n_a] if all(n.id != a_.id for n in ws.present) else ws.present
ws.on_buy(A(kind="buy", target=a_.id, ware="salt"), "buy some salt")
check("buying salt from them takes one from what they hold, and the salt is the player's",
      store.load_entity(f"stock:{a_.id}:salt").data["count"] == had - 1 and any(i.good == "salt" for i in ws.pack))
for _ in range(had - 1):
    ws.on_buy(A(kind="buy", target=a_.id, ware="salt"), "buy some salt")
check("...until none is left: the stock is sold out, and no longer among their wares",
      store.load_entity(f"stock:{a_.id}:salt").state == "sold_out" and not any(w.id == "stock:salt" for w in ws.wares_of(store.load_npc(a_.id))))
check("a thief's taking ends it lost", situation_parts.take_stock(store, b_.id, "salt", 99, t0, "lost") and store.load_entity(f"stock:{b_.id}:salt").state == "lost")
situation_parts.give_stock(store, store.load_npc(b_.id), "salt", 8, "thh", t0, load=True)

# ---- asked of the one who speaks with them
ws.on_talk(A(kind="talk", target=a_.id, speech="How are things?"), "How are things?")
req = obligations.current(store, "request", a_.id, ws.acting)
check("the one who wants candles asks the character who speaks with them to bring some", req and req.data["terms"]["kind"] == "gather"
      and req.data["terms"]["good"] == "candles" and req.data["terms"]["part"] == CANDLES
      and ws.request_of(store.load_npc(a_.id))["title"].startswith("Bring"), req and req.data)
situation_parts.ask(ws, store.load_npc(a_.id))
check("...asked once while it waits on a yes", len([e for e in obligations.open_ones(store, "request", a_.id, ws.acting)]) == 1)
situation_parts.ask(ws, store.load_npc(b_.id))
reqb = obligations.current(store, "request", b_.id, ws.acting)
check("the one whose load is stranded asks for it to be carried to someone of the town who deals in it",
      reqb and reqb.data["terms"]["kind"] == "deliver" and "salt" in reqb.data["terms"]["item"] and reqb.data["terms"]["to_role"]
      and reqb.data["terms"]["to_role"] in world.roles, reqb and reqb.data["terms"])
ws.take_personal(store.load_npc(a_.id))
check("...a yes makes it the character's, as any request", any(q.get("part") == CANDLES for q in ws.player.quests))
situation_parts.ask(ws, store.load_npc(a_.id))
check("...and a part taken on is never asked again", obligations.current(store, "request", a_.id, ws.acting) is None)

# ---- the end lets go what is held and unanswered; what was taken on stays
state = store.load_world_state()
pulse.end_thread(store, state, next(x for x in state["threads"] if x["id"] == "thh"), "ended", "The salt road opened again.", t0 + 1440)
store.save_world_state(state)
check("at the situation's end what is still held of it moves on", store.load_entity(f"stock:{b_.id}:salt").state == "released")
check("...a request nobody said yes to is let go, for its reason", reqb and store.load_entity(reqb.ref).state == "released"
      and store.load_entity(reqb.ref).data.get("cause") == "over", store.load_entity(reqb.ref).data)
check("...and the request the character took on stays theirs", any(q.get("part") == CANDLES for q in ws.player.quests))
check("its price rises end with it", pulse.price_factor(store, world, "trading_square", t0 + 2 * 1440, "salt")
      == pulse.price_factor(store, world, "trading_square", t0 + 2 * 1440))

shutil.rmtree("saves/held_stock_545", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

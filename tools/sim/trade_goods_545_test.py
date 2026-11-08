"""(f545 part 2) Trade goods: the world gains what a town makes, eats, burns and builds with (salt, grain, flour, cloth, sawn planks,
dried fish, wine, lamp oil, rope, candles), sold by the merchant and the trades that make them and bought by anyone who buys "any",
carried and never used. A situation turns on these and the land's herbs and meat, never on the player's kit (f544: tomes and the codex
read as cargo absurdly). A condition "given" stands only when the good is within the player's reach: sold in the town, given by the
land, or held by someone else of the situation. No item is minted per good to ask what a name means, so adding goods moves no ids.
Run: python tools/sim/trade_goods_545_test.py"""
import random
import re
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 8))
import ui.console as uc
for fn in ("note", "narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
import yaml
from engine import data_check, inventory as inv, pulse, quests, retrieval, situations, streams
from llm.contracts import ActionIntent as A, QuestOffer, SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

TRADE = ["salt", "grain", "flour", "cloth", "sawn_planks", "dried_fish", "wine", "lamp_oil", "rope", "candles"]
g = simlib.campaign("trade_goods_545_test", seed=8, location="trading_square")
ws, store = g.scene, g.store
world = ws.world
ws.player.character.coins = 10 ** 5

# ---- the goods and who deals in them
trade = {g: inv.GOODS[g] for g in TRADE if g in inv.GOODS}
check("the ten trade goods are goods of the world, of kind trade", list(trade) == TRADE and all(g.kind == "trade" for g in trade.values()),
      sorted(set(TRADE) - set(trade)))
check("...none grows wild or drops from a creature, so no forage, garden, kill or roll over the goods draws one",
      not any(g.grows_in or g.drops_from for g in trade.values()))
sellers = {g: sorted(r.id for r in world.roles.values() for w in r.sells if w.kind == "item" and w.item == g) for g in TRADE}
check("...each is sold by some trade (the merchant, the baker, the fisher, the lumberjack, the innkeeper, the chandler)",
      all(sellers.values()) and "merchant" in sellers["salt"] and sellers["flour"] == ["baker"], sellers)
check("...and bought by the trades that buy anything", all("any" in world.roles[r].buys for r in ("merchant", "tinker", "quartermaster")))
roles_doc = yaml.safe_load(open("data/world/roles.yaml"))
serves_was = {"merchant", "baker", "fisher", "lumberjack", "innkeeper", "chandler"}
check("...sold only by trades that already served the player, so who is made first in a scene is unmoved",
      {r for s in sellers.values() for r in s} <= serves_was and all(r.get("buys") or r.get("sells") for r in roles_doc
                                                                       if r["id"] in {"fisher", "lumberjack"}))

# ---- the situation's goods: trade first, never the kit
listed = list(situations._goods())
check("a situation's goods are the trade goods first, then the land's herbs and meat and the one remedy", listed[:10] == TRADE
      and {"silverleaf", "moonpetal", "venison", "healing_draught"} <= set(listed))
check("...never the player's kit: no tome, codex, tonic, torch or ration", not any(inv.GOODS[g].kind in ("book", "codex") for g in listed)
      and not {"mana_tonic", "torch", "trail_ration"} & set(listed))

# ---- naming a good never mints one
names = ["salt", "a sack of salt", "wolf hides", "the draught", "silverleaf pressed flat", "rope ladder", "dried fish", "wild garlic", "x"]
check("good_named means what find() over one of every good would, for every name tried",
      all(inv.good_named(n) == ((inv.find([inv.make_good(g) for g in inv.GOODS], n) or inv.make_good("salt")).good
                                if inv.find([inv.make_good(g) for g in inv.GOODS], n) else "") for n in names))
streams.begin(8, 1)
snap = streams.snapshot()
inv.good_named("a sack of salt"); inv.is_good("a jar of wine")
offer = quests.map_offer(world, None, QuestOffer(kind="gather", what="salt", count=3), "x", "Hollis", 600)
asked = streams.new_id(10)
streams.restore(snap)
streams.new_id(8)                                                           # the request's own id, and nothing else
check("...so asking draws no id: past the request's own id, the next is the one it would have been without asking", asked == streams.new_id(10))
check("a request to gather salt is a request for the good salt", offer and offer["kind"] == "gather" and offer.get("good") == "salt"
      and offer["title"] == "Bring 3 salt", offer)

# ---- a gift is a story object unless it is a good by name
for name, story in (("a sealed letter", True), ("a rope ladder", True), ("a cloth-wrapped key", True), ("a jar of wine", False),
                    ("two sacks of salt", False), ("a sealed codex", False), ("silverleaf", False), ("a hot meal", False)):
    check(f"a gift of {name!r} is {'a story object' if story else 'a good, never a story object'}", ws.story_object(name) is story)

# ---- bought, carried, sold, never used
ws.enter("tilted_plough")
keeper = next((n for n in ws.present if n.role == "innkeeper"), None)
check("(the inn at Parth has its keeper)", keeper is not None)
if keeper:
    coins = ws.player.character.coins
    ws.on_buy(A(kind="buy", target=keeper.id, ware="wine"), "buy a jar of wine")
    held = [i for i in ws.pack if i.good == "wine"]
    check("the innkeeper sells a jar of wine: it is in the pack, and paid for", held and held[0].quantity == 1
          and ws.player.character.coins < coins, [i.name for i in ws.pack])
    ws.on_use(A(kind="use", item="wine"), "drink the wine")
    check("...a trade good is carried, never used: the jar is still there", sum(i.quantity for i in ws.pack if i.good == "wine") == 1)
    ws.enter("trading_square")
    tinker = next((n for n in retrieval.people_in_town(store, world, "parth") if n.role == "tinker"), None)
    check("(Parth's square has its tinker)", tinker is not None)
    if tinker:
        coins = ws.player.character.coins
        item = inv.take(ws.pack, "wine", 1)
        paid = ws.finish_sale(item, store.load_npc(tinker.id), quiet=True)
        check("...and the tinker, who buys anything, pays for it", paid > 0 and ws.player.character.coins == coins + paid
              and not any(i.good == "wine" for i in ws.pack), paid)

# ---- given needs a good within reach
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
reach = situations.within_reach(world, town, rows)
check("Parth's reach: what its trades sell and the land gives, not what only a merchant sells (it has none)",
      {"candles", "flour", "wine", "silverleaf", "venison"} <= reach and not {"salt", "grain", "cloth"} & reach, sorted(reach))
a_, b_ = rows[0], rows[1]


def run(**kw):
    return situations.check(SituationParts.model_validate(kw), store, world, "rare", random.Random(7), town=town, ways=True, now=600,
                            players=(ws.acting,))[0]


def who(acc, w):
    return next(a for a in acc if a["kind"] == "person" and a["who"] == w)
acc = run(people=[{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
          resources=[{"good": "salt", "state": "wanted", "wanted_by": a_.id}])
check("given salt in a town that sells none, held by nobody of the situation, is lifted: a door with no key",
      who(acc, a_.id)["condition"] == "" and who(acc, a_.id).get("lifted") == "given", acc)
acc = run(people=[{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}, {"who": b_.id, "stake": "gains", "want": "coin",
                                                                                               "holds": "salt"}],
          resources=[{"good": "salt", "state": "wanted", "wanted_by": a_.id}])
check("...stands when another of the situation has salt to part with", who(acc, a_.id)["condition"] == "given", acc)
acc = run(people=[{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given", "holds": "salt"}],
          resources=[{"good": "salt", "state": "wanted", "wanted_by": a_.id}])
check("...but not when the only one who has it is the one who wants it", who(acc, a_.id)["condition"] == "", acc)
acc = run(people=[{"who": a_.id, "stake": "can_fix", "want": "safety", "condition": "given"}],
          resources=[{"good": "candles", "state": "wanted", "wanted_by": a_.id}])
check("...and stands for candles, which Parth's chandler sells", who(acc, a_.id)["condition"] == "given", acc)

# ---- the prompt and the data
_, user = situations.prompt(store, world, {}, world.places["trading_square"], "rare", 600)
goods_line = next(ln for ln in user.splitlines() if ln.startswith("GOODS (id: name): "))
check("the proposal's GOODS line lists the trade goods first, by id and name", goods_line.startswith("GOODS (id: name): salt: salt; grain: grain")
      and "tome_" not in goods_line and "codex" not in goods_line, goods_line[:120])
check("the data checks clean", situations.problems() == [] and data_check.check() == [], (situations.problems(), data_check.check()))
keep = list(situations.S["goods"])
situations.S["goods"] = keep + ["tome_second_circle", "dragon_gold", "salt"]
probs = situations.problems()
situations.S["goods"] = keep
check("a situation's goods list naming kit, no good, or a good twice is refused at startup",
      any("kit" in p for p in probs) and any("dragon_gold" in p for p in probs) and any("twice" in p for p in probs), probs)
merchant = world.roles["merchant"]
merchant.sells.append(merchant.sells[0].model_copy(update={"id": "x", "item": "salt_of_the_earth"}))
import engine.data_check as dc
real_load = dc._load
dc._load = lambda rel: ([{**r, "sells": (r.get("sells") or []) + [{"id": "x", "name": "a bad thing", "price": 1, "kind": "item",
                                                                     "item": "salt_of_the_earth"}]} if r["id"] == "merchant" else r
                         for r in real_load(rel)] if rel == "data/world/roles.yaml" else real_load(rel))
probs = dc.check()
dc._load = real_load
merchant.sells.pop()
check("a ware naming no good is refused at startup (it used to fail only when someone bought it)",
      any("salt_of_the_earth" in p for p in probs), probs)

shutil.rmtree("saves/trade_goods_545_test", ignore_errors=True)
print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)

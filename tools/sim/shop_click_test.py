"""The shop pane's Buy and Sell buttons run the same code as the typed commands: same prices, same effects, no model call."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from llm.contracts import ActionIntent
from engine import money, inventory as inv, items, crafting
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
lines = []
console.note = lambda m: lines.append(m)

shutil.rmtree("saves/shop_click_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("shop_click_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 3; char.coins = money.to_smallest(gold=500)
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
c = ws.player.character
for n in ws.present:
    n.met_player = True
d = ws.shop_data()
check("sellers listed", len(d["sellers"]) > 0, [s["name"] for s in d["sellers"]])
check("purse shown", d["purse"] == money.fmt(c.coins))

# --- a listed ware ---
seller = next(s for s in d["sellers"] if any(w["kind"] == "ware" for w in s["wares"]))
ware = next(w for w in seller["wares"] if w["kind"] == "ware")
coins0, packn = c.coins, len(c.inventory)
ws.command(f"#shopbuy ware {seller['id']} {ware['key']}")
paid = coins0 - c.coins
check("button buys a ware at the quoted price", paid == ware["price"], (paid, ware["price"]))
npc = next(n for n in ws.present if n.id == seller["id"])
role_ware = next(w for w in world.roles[npc.role].sells if w.id == ware["key"])
ws.halted = False
c.coins = coins0
ws.on_buy(ActionIntent(kind="buy", ware=ware["key"], target=npc.id), "buy it")
check("typed buying costs the same", coins0 - c.coins == ware["price"], (coins0 - c.coins, ware["price"]))

# --- stock gear ---
d = ws.shop_data()
stock_seller = next((s for s in d["sellers"] if any(w["kind"] == "stock" for w in s["wares"])), None)
check("a merchant has gear stock", stock_seller is not None)
if stock_seller:
    item = next(w for w in stock_seller["wares"] if w["kind"] == "stock")
    c.coins = money.to_smallest(gold=500)
    coins0, packn = c.coins, len(c.inventory)
    ws.command(f"#shopbuy stock {stock_seller['id']} {item['key']}")
    check("button buys stock at the quoted price", coins0 - c.coins == item["price"], (coins0 - c.coins, item["price"]))
    check("the item is in the pack", len(c.inventory) == packn + 1 or any(i.uid == item["key"] for i in c.inventory))
    check("and gone from the stock", all(w["key"] != item["key"] for s in ws.shop_data()["sellers"] for w in s["wares"]))
    c.coins = 0
    packn = len(c.inventory)
    other = next((w for s in ws.shop_data()["sellers"] for w in s["wares"] if w["kind"] == "stock"), None)
    if other:
        sid = next(s["id"] for s in ws.shop_data()["sellers"] if other in s["wares"])
        ws.command(f"#shopbuy stock {sid} {other['key']}")
        check("can't afford: nothing happens", c.coins == 0 and len(c.inventory) == packn and any("can't afford" in l for l in lines))

# --- selling ---
c.coins = money.to_smallest(gold=5)
pelt = items.make_raw("wolf_hide") if "wolf_hide" in items.MATERIALS else None
mat = next((m for m in items.MATERIALS if items.MATERIALS[m].family in ("hide", "metal", "wood", "bone", "herb")), None)
ws.pack.clear()
ws.to_pack(items.make_raw(mat)); ws.to_pack(items.make_raw(mat))
d = ws.shop_data()
check("sellable pack items are listed", len(d["sell"]) >= 1, d["sell"])
if d["sell"]:
    x = d["sell"][0]
    coins0 = c.coins
    ws.command(f"#shopsell {x['buyer']} {x['uid']}")
    check("button sells for the quoted price", c.coins - coins0 == x["total"], (c.coins - coins0, x["total"]))
    check("the whole stack goes", all(i.uid != x["uid"] for i in ws.pack) and not any(inv.category(i) == inv.category(items.make_raw(mat)) for i in ws.pack))
    ws.to_pack(items.make_raw(mat)); ws.to_pack(items.make_raw(mat))
    coins0 = c.coins
    buyer = next(n for n in ws.present if n.id == x["buyer"])
    ws.on_sell(ActionIntent(kind="sell", item=inv.label(ws.pack[0]), count=ws.pack[0].quantity, target=buyer.id), "sell it")
    check("typed selling pays the same", c.coins - coins0 == x["total"], (c.coins - coins0, x["total"]))
# --- refusals ---
coins0 = c.coins
ws.command("#shopsell nobody nothing"); ws.command("#shopbuy ware nobody nothing")
check("bad ids change nothing", c.coins == coins0 and any("no longer on offer" in l for l in lines))
# equipped gear and key items are never offered
check("equipped gear is not sellable", all(i.uid not in {e.uid for e in c.equipment.values()} for i in [type("x", (), {"uid": s["uid"]}) for s in ws.shop_data()["sell"]]))
# a room you already hold is not sold to you twice
inn = next(p.id for p in world.places.values() if p.type == "inn")
ws.enter(inn)
for n in ws.present:
    n.met_player = True
sl = next((x for x in ws.shop_data()["sellers"] if any(w["key"] == "room" for w in x["wares"])), None)
check("an innkeeper sells rooms", sl is not None)
if sl:
    c.coins = money.to_smallest(gold=50)
    ws.command(f"#shopbuy ware {sl['id']} room")
    check("the first room is sold", ws.has_room() and c.coins < money.to_smallest(gold=50), lines[-2:])
    again = c.coins
    lines.clear()
    ws.command(f"#shopbuy ware {sl['id']} room")
    check("a second room here is refused and costs nothing", c.coins == again and any("already have a room" in l for l in lines), lines[-2:])
print("\nFAILED: " + ", ".join(bad) if bad else "\nall ok")
sys.exit(1 if bad else 0)

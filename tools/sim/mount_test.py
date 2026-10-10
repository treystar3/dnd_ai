"""Mounts: city stables sell them, #mount chooses; and non-companion classes can be gifted an animal at a story's end."""
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
from engine import mounts, arcs, combat, money

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

shutil.rmtree("saves/mount_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("mount_test")
store.meta.seed = 5; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 10; char.coins = money.to_smallest(gold=100)
store.save_player(PlayerState(character=char, location="eldervale"))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character

cities = [p.id for p in world.places.values() if p.type == "city"]
check("every city has a stable with a cheap mount", all(mounts.stock(world, 5, t) and mounts.stock(world, 5, t)[0]["price"] <= mounts.M["always_stock_up_to"] for t in cities))
check("stock is fixed for a campaign", mounts.stock(world, 5, "eldervale") == mounts.stock(world, 5, "eldervale"))
check("stocks differ between cities", len({tuple(m["id"] for m in mounts.stock(world, 5, t)) for t in cities}) > 1)
check("towns have no stable", mounts.stable_town(world, "parth") == "" and mounts.stock(world, 5, "") == [])
check("rewards-only mounts are never sold", all(m["id"] not in ("war_griffon", "storm_drake") for t in cities for m in mounts.stock(world, 5, t)))

ws.player.location = "eldervale"
stock = {m["id"] for m, _ in ws.stable_stock()}
check("the stable shows in the city", len(stock) == 3, stock)
ws.show_stable(); ws.show_mounts()

pick = next(iter(stock))
def buy(word):
    ws.halted = False
    ws.on_buy(ActionIntent(kind="buy", ware=word), f"buy the {word}")
price = dict((m["id"], p) for m, p in ws.stable_stock())[pick]
coins0 = c.coins
buy(pick.replace("_", " "))
check("buying takes the coin and gives the mount", ws.player.mounts and ws.player.mounts[0]["id"] == pick and c.coins == coins0 - price, (c.coins, coins0, price))
check("the first mount is ridden at once", ws.player.mount == pick and ws.mount_info()["id"] == pick)
buy(pick.replace("_", " "))
check("you cannot buy the same mount twice", len(ws.player.mounts) == 1)

other = next(i for i in stock if i != pick)
c.coins = 5
buy(other.replace("_", " "))
check("too poor: nothing happens", len(ws.player.mounts) == 1 and c.coins == 5)
c.coins = money.to_smallest(gold=500)
buy(other.replace("_", " "))
if len(ws.player.mounts) == 2:
    check("a second mount does not take over", ws.player.mount == pick)
    ws.mount_command(other.replace("_", " "))
    check("#mount chooses the mount to ride", ws.player.mount == other and ws.mount_info()["id"] == other)
    ws.mount_command("none")
    check("#mount none goes on foot", ws.player.mount == "" and ws.mount_info() is None)
    ws.mount_command("griffon"); check("a mount you don't own can't be picked", ws.player.mount == "")
else:
    check("second purchase", False, ws.player.mounts)

# level requirement
c.level = 10
ws.player.mounts = []; ws.player.mount = ""; c.coins = money.to_smallest(gold=5000)
far = next(t for t in cities if any(m["id"] == "marsh_strider" for m in mounts.stock(world, 5, t)) )if any(m["id"] == "marsh_strider" for t in cities for m in mounts.stock(world, 5, t)) else None
if far:
    ws.player.location = far; ws.halted = False
    ws.on_buy(ActionIntent(kind="buy", ware="marsh strider"), "buy the marsh strider")
    check("a mount can need a level", not ws.player.mounts)
    c.level = 40; ws.halted = False
    ws.on_buy(ActionIntent(kind="buy", ware="marsh strider"), "buy the marsh strider")
    check("...and sells once you have it", bool(ws.player.mounts))
else:
    print("note: no city stocks the marsh strider with this seed")

# mounts away from a city
ws.player.location = "parth"; ws.halted = False; before = c.coins
ws.on_buy(ActionIntent(kind="buy", ware="horse"), "buy a horse")
check("outside a city no mount is sold", c.coins == before)
# a house purchase is not mistaken for a mount
check("buying something else is left alone", ws.mount_buy(ActionIntent(kind="buy", ware="bread"), "buy bread") is False)

# ---- gift animals
def run(uses, size, n=400):
    got = 0
    for i in range(n):
        ch, _ = simlib.make_character("warrior", random.Random(i)); ch.uses_companions = uses
        if arcs.gift_companion(ch, {"id": f"a{i}", "size": size}, world): got += 1
    return got / n
check("simple stories give no animal", run(False, "simple") == 0)
chain, arc = run(False, "chain"), run(False, "arc")
check("chains sometimes do and arcs more often", 0.08 < chain < 0.25 and 0.3 < arc < 0.5 and arc > chain, (chain, arc))
check("companion classes are not given one", run(True, "arc") == 0)
ch, _ = simlib.make_character("warrior", random.Random(3))
g = next(x for x in (arcs.gift_companion(ch, {"id": f"b{i}", "size": "arc"}, world) for i in range(50)) if x)
check("the gift is a real creature from the bestiary, marked as a gift", g.creature in world.bestiary and g.source == "gift", g)
ch.companions.append(g)
check("only one gift at a time", all(arcs.gift_companion(ch, {"id": f"c{i}", "size": "arc"}, world) is None for i in range(50)))

shape = world.bestiary[g.creature]
gifted = combat.companion_fighter(shape, 30, "ally_g", g.name, gift=True)
bonded = combat.companion_fighter(shape, 30, "ally_b", g.name)
check("a gifted animal is weaker than a bonded one", gifted.max_hp < bonded.max_hp * 0.6 and gifted.weapon_damage < bonded.weapon_damage * 0.6,
      (gifted.max_hp, bonded.max_hp, round(gifted.weapon_damage, 1), round(bonded.weapon_damage, 1)))
check("it still fights as a companion", combat.is_companion(gifted))
# ---- perks of the gifted animals
import yaml
from engine import pools
defs = {m["id"]: m for m in yaml.safe_load(open("data/rules/passive_mechanics.yaml"))}
G = arcs.A["gift_companion"]["animals"]
check("every animal has perks that exist as world mechanics", all(a.get("perks") and all(k in defs and defs[k]["kind"] == "world" for k in a["perks"]) for a in G))
check("perks are smaller than a class's", all(v <= defs[k]["values"][0] for a in G for k, v in a["perks"].items()), "")
check("no two animals share the same pair", len({tuple(sorted(a["perks"])) for a in G}) == len(G))
for a in G:
    ch2, _ = simlib.make_character("warrior", random.Random(5)); ch2.passives = []
    base = {k: pools.mechanic(ch2, k) for k in a["perks"]}
    gift_c = next(x for x in (arcs.gift_companion(ch2, {"id": f"p{i}", "size": "arc"}, world) for i in range(400)
                              if True) if x and x.creature == a["creature"]) if True else None
    ch2.companions.append(gift_c)
    got = {k: pools.mechanic(ch2, k) for k in a["perks"]}
    check(f"{a['creature']} perks reach the character", all(base[k] is None and got[k] == a["perks"][k] for k in a["perks"]), got)
    check(f"{a['creature']} perk text reads", len(arcs.perk_text(gift_c)) > 20, arcs.perk_text(gift_c))
ch3, _ = simlib.make_character("warrior", random.Random(6)); ch3.passives = []
check("without the animal the perks are gone", all(pools.mechanic(ch3, k) is None for a in G for k in a["perks"]))
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)

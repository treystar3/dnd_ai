"""Property: a deed is sold only in the far lands and only by the land agent; the house is a place of its own with a bed and the item box;
upgrades are bought standing in it and do what they say (a strongroom grows the box, a garden grows herbs, a hearth feeds you, a reliquary
only in the far lands); a house survives a reload."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("ranger", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from llm.contracts import ActionIntent
from engine import property as prop
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/property_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("property_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("ranger", random.Random(2))
char.coins = 60_000_000
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
notes, narrated = [], []
console.note = lambda t, *a, **k: notes.append(t)
ws._narrate_now = lambda event, player_text="": narrated.append(event)
store.meta.minutes = 4 * 60                                          # noon: the land agent is at work
c = ws.player.character
P = prop.P
buy = lambda what: ws.property_buy(ActionIntent(kind="buy", ware=what), f"buy {what}")

# ---- the old towns sell nothing; the far lands do, through the agent
ws.enter("valecourt")
ws.halted = False
check("a house is not for sale in an older town, though its entry stands for houses already owned", buy("a house") and ws.halted and any("No houses are for sale" in n for n in notes), notes[-1:])
town = "cinderhold"
ws.enter(town)
agent = next((n for n in ws.present if n.role == P["agent_role"]), None)
check("the land agent of a far-lands city is at work at noon", agent is not None, [n.role for n in ws.present])
price = P["homes"][town]["price"]
coins0 = c.coins
notes.clear(); ws.halted = False
check("the deed is bought from the agent for its price", buy("a house") and c.coins == coins0 - price and town in ws.player.homes, (c.coins, ws.player.homes))
home = prop.home_id(town)
check("...and the house is a place of its own, in the town, with the item box", home in world.places and world.places[home].parent == town and world.places[home].storage)
check("...bought once: the agent will not sell it twice", (notes.clear(), buy("a house"), any("already own" in n for n in notes))[-1], notes[-1:])

# ---- upgrades, standing in the house
ws.enter(home)
check("in your house you can store things and have a bed", ws.can_store() and ws.has_room())
cap0 = ws.stash_cap()
coins0 = c.coins
check("a strongroom grows the item box", buy("a strongroom") and "strongroom" in ws.player.homes[town]["upgrades"] and ws.stash_cap() == cap0 + P["upgrades"]["strongroom"]["stash_bonus"]
      and c.coins == coins0 - P["upgrades"]["strongroom"]["price"], (ws.stash_cap(), cap0))
check("a reliquary can be built here, in the far lands", buy("a reliquary") and ws.stash_cap() == cap0 + P["upgrades"]["strongroom"]["stash_bonus"] + P["upgrades"]["reliquary"]["stash_bonus"])
check("the same upgrade is not sold twice", (notes.clear(), buy("a strongroom"), any("already have" in n for n in notes))[-1], notes[-1:])
check("a workshop puts a free forge and workbench in the house", buy("a workshop") and set(world.places[home].stations) >= {"forge", "workbench"} and all(s["fee"] == 0 for s in world.places[home].stations.values()),
      world.places[home].stations)
check("a garden and a hearth are bought", buy("a garden") and buy("a hearth") and {"garden", "hearth"} <= set(ws.player.homes[town]["upgrades"]))
packed = len(ws.pack)
c.stamina = 1.0
h = ws.player.homes[town]
h["last_garden"] = h["last_hearth"] = -1
ws.enter(town); ws.enter(home)
check("coming home, the garden has grown herbs and the hearth restores you", len(ws.pack) > packed and c.stamina > 1.0 and any("From the garden" in n for n in notes), (len(ws.pack), packed, c.stamina))
day = h["last_garden"]
packed = len(ws.pack)
ws.enter(town); ws.enter(home)
check("...once a day", len(ws.pack) == packed and h["last_garden"] == day)

# ---- a reload keeps the house, and puts it back on the map
store.save_player(ws.player)
p2 = store.load_player()
w2 = load_world()
prop.register(w2, p2)
check("a reload keeps the deed and its upgrades, and the house is on the map again", town in p2.homes and set(p2.homes[town]["upgrades"]) >= {"strongroom", "workshop", "garden", "hearth", "reliquary"}
      and home in w2.places, (p2.homes, home in w2.places))

shutil.rmtree("saves/property_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

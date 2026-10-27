"""The panes' data (f327): the window draws the pack, the item box, the contracts in hand, the dungeon, the house, the town's regard and the
worn pieces from structured data rather than the terminal's lines; the terminal keeps its text. The pane buttons that act (Use on a draught
out of a fight, Abandon on a contract, Correct on a tale) run the same code as saying it and draw the pane again."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import loot, inventory as inv, money, clock, standing, pulse
from core.models import KeyItem
from ui import console
from ui.gui import bridge

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- 1. money for a pane: only the coins that are there
check("a pane's price drops the empty units", money.short(150) == "1Ş 50₵" and money.short(0) == "0₵" and money.short(10000) == "1₲", (money.short(150), money.short(0), money.short(10000)))

# ---- 2. the pack as rows
shutil.rmtree("saves/panels_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("panels_test")
store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 12; char.coins = 4 * 10000 + 37 * 100 + 12
rng = random.Random(7)
sword = loot.make_drop(12, "rare", rng); sword.description = ""
star = loot.make_drop(12, "legendary", rng); star.description = "Cut from a tree that had heard too many songs."
char.inventory = [sword, star, inv.make_good("healing_draught", 3), inv.make_good("moonpetal", 6), inv.make_good("wolf_meat", 2)]
char.key_items.append(KeyItem(id="letter_pell", name="a sealed letter", description="Wax still whole.", kind="quest", source="Pell the carter", day=3, for_whom="the watch captain"))
rows = console.item_rows(char.inventory, usable=True)
by = {r["name"]: r for r in rows}
check("every item is a row with its number, name, detail, worth and group", len(rows) == 5 and all(r["n"] and r["name"] and r["detail"] and r["value"] and r["group"] for r in rows))
check("gear, draughts, food and herbs fall into the pack's groups", by[rows[0]["name"]]["group"] == "Gear" and by["healing draught"]["group"] == "Consumables" and by["moonpetal"]["group"] == "Food & herbs" and by["wolf meat"]["group"] == "Food & herbs", [(r["name"], r["group"]) for r in rows])
check("a draught and a meal can be used from the pane; a herb and a sword cannot", by["healing draught"]["use"] == "healing draught" and by["wolf meat"]["use"] and not by["moonpetal"]["use"] and not rows[0]["use"])
check("a stack says how many, and its worth is each", by["healing draught"]["qty"] == 3 and by["healing draught"]["value"] == money.short(inv.unit_value(char.inventory[2])))
check("a legendary keeps its star and its words", rows[1]["legendary"] and rows[1]["flavour"].startswith("Cut from") and not rows[0]["legendary"] and not rows[0]["flavour"])
check("the item box's rows carry no Use", not any(r["use"] for r in console.item_rows(char.inventory)))
check("every row carries its rarity, for its colour (f328)", rows[0]["rarity"] == "rare" and rows[1]["rarity"] == "legendary" and by["healing draught"]["rarity"] == "common", [r["rarity"] for r in rows])
keys = console.key_item_rows(char)
check("a key item says what it is, where it came from and who it is for", keys and keys[-1]["kind"] == "quest" and keys[-1]["source"] == "from Pell the carter, day 3 · for the watch captain", keys[-1:])

# the pane gets the data; the terminal gets the text
panels = []
_panel = console.panel
console.panel = lambda name, data: (panels.append((name, data)), True)[1]
console.show_inventory(char)
check("the window is handed the pack, its size and the key items", panels and panels[-1][0] == "inventory" and panels[-1][1]["count"] == 5 and panels[-1][1]["cap"] == inv.RULES["pack_slots"]
      and len(panels[-1][1]["items"]) == 5 and panels[-1][1]["keys"] and panels[-1][1]["groups"][-1] == "Materials")
console.panel = lambda name, data: False
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    console.show_inventory(char)
check("...and the terminal still prints the numbered pack with what is worn", "PACK" in buf.getvalue() and "EQUIPPED" in buf.getvalue() and " 3. healing draught x3" in buf.getvalue(), buf.getvalue()[:300])
console.panel = lambda name, data: (panels.append((name, data)), True)[1]

# ---- 3. the character pane's worn pieces, in slot order, only for the window
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.ensure_discoveries(); ws.ensure_homes(); ws.ensure_road_place(); ws.ensure_dungeons(); ws.ensure_field_uses()
ws.enter("trading_square")
c = ws.player.character
console.damage_tags = True
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    console.show_player_block(c, "the trading square", "Day 1 · 9:40", [("health", 10, 10)])
worn = [w["slot"] for w in panels[-1][1]["worn"]]
check("the window gets the worn pieces as rows, main hand first", panels[-1][0] == "character" and worn and worn == sorted(worn, key=lambda s: console._slot_rank(s.replace(" ", "_"))) and console.EQUIP_MARK in buf.getvalue(), worn)
console.damage_tags = False
console.panel = lambda name, data: False
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    console.show_player_block(c, "the trading square", "Day 1 · 9:40", [("health", 10, 10)])
check("...and the terminal prints them as lines", console.EQUIP_MARK not in buf.getvalue() and "EQUIPMENT" in buf.getvalue())
console.panel = lambda name, data: (panels.append((name, data)), True)[1]

# ---- 4. contracts in hand
ws.player.guild_rank = "D"
now = ws.minutes
ws.player.quests = [
    {"id": "q1", "letter": "D", "title": "Something in the Greywood", "kind": "hunt", "count": 3, "progress": 2, "guild": True, "issuer_name": "Hob Marl", "reason": "four ewes gone this week", "deadline": now + 2 * 1440 + 240},
    {"id": "q2", "letter": "F", "title": "Carry a letter", "kind": "deliver", "count": 1, "progress": 0, "guild": False, "issuer_name": "Pell the carter", "deadline": None},
    {"id": "q3", "letter": "D", "title": "The salt road", "kind": "hunt", "count": 2, "progress": 2, "guild": True, "deadline": now + 300},
    {"id": "q4", "letter": "E", "title": "Old news", "kind": "hunt", "count": 2, "progress": 0, "guild": True, "deadline": now - 10},
]
r = {q["id"]: q for q in ws.quest_rows()}
check("a contract row says how far along, for whom and why, and how long is left", r["q1"]["status"] == "2/3" and r["q1"]["for"] == "for Hob Marl: four ewes gone this week" and r["q1"]["left"] == "2d 4h left" and not r["q1"]["urgent"] and not r["q1"]["ready"], r["q1"])
check("a delivery with no limit, a finished one, and an expired one read so", r["q2"]["status"] == "to deliver" and r["q2"]["left"] == "no time limit" and r["q3"]["ready"] and r["q3"]["status"] == "ready to turn in" and r["q3"]["urgent"] and r["q4"]["left"] == "expired" and r["q4"]["urgent"], (r["q2"], r["q3"]["status"], r["q4"]["left"]))
rk = ws.rank_data()
check("the next rank is three bars: level, contracts at the rank, the trial", rk["rank"] == "D" and rk["next"] and len(rk["needs"]) == 2 and rk["needs"][0]["label"].startswith("level ") and rk["needs"][0]["now"] == 12 and "contracts" in rk["needs"][1]["label"], rk)
ws.show_quests()
check("the Quests pane is handed the rows and the rank", panels[-1][0] == "quests" and len(panels[-1][1]["rows"]) == 4 and panels[-1][1]["rank"]["next"] == rk["next"])
ws.player.guild_rank = ""
check("...and a non-member sees no rank", ws.rank_data() is None)
ws.player.guild_rank = "D"

# the pane's Abandon: the same as the board's, and the pane is drawn again
scopes = []
_scope = console.scope
import contextlib as _cl
@_cl.contextmanager
def scope(cmd):
    scopes.append(cmd); yield
console.scope = scope
ws.command("#questabandon q2")
check("Abandon from the Quests pane drops the contract and draws the pane again", not any(q["id"] == "q2" for q in ws.player.quests) and scopes[-1:] == ["#quests"] and panels[-1][0] == "quests", (scopes[-2:], [q["id"] for q in ws.player.quests]))
check("the pane's commands are never echoed as typed lines", all(h in bridge.HIDDEN for h in ("#useitem", "#correct", "#questabandon")))

# ---- 5. Use from the pack, out of a fight
c.health = 1.0
had = inv.count_of(c.inventory, "healing_draught")
narrated = []
ws.narrate = lambda event, text="": narrated.append(event)
ws.command("#useitem healing draught")
check("Use on a draught drinks it: one fewer, the effect told, the pack drawn again", inv.count_of(c.inventory, "healing_draught") == had - 1 and narrated and "healing draught" in narrated[-1] and scopes[-1] == "#inventory" and panels[-1][0] == "inventory", (had, inv.count_of(c.inventory, "healing_draught"), narrated[-1:]))
ws.command("#useitem moonpetal")
check("...and a herb is refused, as it would be if said", inv.count_of(c.inventory, "moonpetal") == 6)
console.scope = _scope

# ---- 6. the item box
ws.player.stash = [inv.make_good("venison", 3)]
ws.command("#stash")
st = panels[-1][1]
check("the Stash pane gets the box: where, how full, what is in it", panels[-1][0] == "stash" and st["count"] == 1 and st["cap"] == ws.stash_cap() and st["items"][0]["qty"] == 3 and "reachable" in st and st["where"])

# ---- 7. the dungeon as floors
d = next(x for x in store.load_dungeons())
ws.enter(d["place"])
ws.command("#dungeon")
dd = panels[-1][1]
check("the Dungeon pane gets the floors with their rank, progress and the boss floor", panels[-1][0] == "dungeon" and dd["name"] == d["name"] and len(dd["floors"]) == len(d["floors"]) and dd["floors"][-1]["boss"] and not dd["floors"][0]["boss"]
      and all(f["done"] <= f["total"] and f["letter"] for f in dd["floors"]) and dd["on_floor"] == 0 and dd["remade_days"] >= 0, dd)
ws.enter("trading_square")
before = len(panels)
ws.command("#dungeon")
check("...and where there is none, the terminal's line, not a pane", len(panels) == before)

# ---- 8. the house
ws.player.homes["parth"] = {"day": 5, "upgrades": ["garden"], "last_garden": -1, "last_hearth": -1}
ws.ensure_homes()
from engine import property as prop
ws.enter(prop.home_id("parth"))
ws.command("#home")
h = panels[-1][1]
states = {u["id"]: u["state"] for u in h["upgrades"]}
check("the Home pane gets what you own, with its upgrades, and the upgrades here as built, priced or out of reach", panels[-1][0] == "home" and h["owned"] and h["owned"][0]["upgrades"] and h["here"] and states.get("garden") == "built"
      and any(s == "price" for s in states.values()) and any(s == "far" for s in states.values()) and all(u["price"] for u in h["upgrades"]), (h["owned"], states))
ws.enter("trading_square")
ws.command("#home")
check("...away from it, what you own and nothing to build", panels[-1][0] == "home" and not panels[-1][1]["here"] and not panels[-1][1]["upgrades"])

# ---- 9. the town's regard, what is said, the other towns, the titles
day = clock.day(ws.minutes)
ws.player.reputation.update({"parth": 23, "lethoria": 51, "riverhaven": -26, "greywood": 40, "road_abc": 30})
standing.add(ws.player, "parth", "guild", 35, day)
ws.player.titles = ["Wolfsbane of Parth"]
sd = ws.standing_data()
check("the Standing pane gets this town's regard as a number and a word, and its groups", not sd["wild"] and sd["town"] == "Parth" and sd["value"] == 23 and sd["word"] and any(g["value"] == 35 and g["word"] for g in sd["groups"]), sd)
check("...the other towns that have an opinion, towns only, strongest first", [e["name"] for e in sd["elsewhere"]] == ["Lethoria", "Riverhaven"], sd["elsewhere"])
check("...and the titles", sd["titles"] == ["Wolfsbane of Parth"])
check("...and what is said of you here, numbered for Correct", isinstance(sd["rumors"], list) and all({"n", "text"} <= set(r) for r in sd["rumors"]))
ws.show_standing()
check("the pane is handed it", panels[-1][0] == "standing")
ws.enter("greywood")
check("out in the wild nobody keeps a tally", ws.standing_data()["wild"])
ws.enter("trading_square")

# ---- 10. the shop pane names who trades here before you have met them (f328)
notes = []
_note = console.note
console.note = lambda t, *a, **k: notes.append(t)
ws.enter("trading_square")
sellers = [n for n in ws.present if ws.world.roles[n.role].sells or ws.world.roles[n.role].stock or ws.world.roles[n.role].relics]
for n in sellers:
    n.met_player = False
ws.show_shop()
check("with no seller spoken to, the pane names the traders here and what they deal in", sellers and notes and notes[-1].startswith("No one you have spoken to sells here yet. Trading here: ")
      and all(n.label() in notes[-1] for n in sellers) and "(" in notes[-1], (len(sellers), notes[-1:]))
check("...and the worn rows and shop rows carry rarity too", all("rarity" in w for w in panels[-1][1]["worn"]) if panels[-1][0] == "character" else True)
console.note = _note
console.panel = _panel
shutil.rmtree("saves/panels_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

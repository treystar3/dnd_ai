"""The gear pane: worn slots (empty ones as --), carried gear only, locked items greyed with a reason, hover comparison, and buttons that equip and unequip."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import items, equipment, inventory as inv
from ui import console
from ui.gui.bridge import is_view, HIDDEN

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
shutil.rmtree("saves/gear_pane_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("gear_pane_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 3
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
c = ws.player.character
d = ws.gear_data()
check("every slot is listed", [s["slot"] for s in d["slots"]] == list(items.SLOTS))
check("worn gear has a name, empty slots have none", all((s["item"] is None) == (s["slot"] not in c.equipment) for s in d["slots"]))
check("only gear is carried in the pane", all(not inv_i.good for inv_i in c.inventory if any(x["uid"] == inv_i.uid for x in d["carried"])))
check("goods are left out", not any(i.good and any(x["uid"] == i.uid for x in d["carried"]) for i in c.inventory))
gear = [i for i in c.inventory if not i.good and items.base_of(i).slot != "none"]
check("view names are known", is_view("#gear") and is_view("#equipment") and "#gearequip" in HIDDEN)

base = next(b for b in items.CATALOG.values() if b.is_weapon and b.slot == "main_hand" and b.hands == 1)
spare = items.make(base.id, "common", 3)
spare.uid = "t-spare"
c.inventory.append(spare)
high = spare.model_copy(update={"uid": "t-high", "item_level": 40})
c.inventory.append(high)
d = ws.gear_data()
row = next(x for x in d["carried"] if x["uid"] == "t-spare")
locked = next(x for x in d["carried"] if x["uid"] == "t-high")
check("an item you can wear has its equip button on", row["ok"], row)
check("an item you cannot wear is greyed with a reason", not locked["ok"] and "level" in locked["reason"], locked["reason"])
check("the hover compares with what is worn", row["compare"] and row["compare"][0][0] == "h", row["compare"][:2])

ws.gear_click("#gearequip t-spare")
check("the Equip button equips it", c.equipment.get("main_hand") and c.equipment["main_hand"].uid == "t-spare")
check("it left the pack", not any(i.uid == "t-spare" for i in c.inventory))
ws.gear_click("#gearequip t-high")
check("a locked item stays in the pack", any(i.uid == "t-high" for i in c.inventory) and c.equipment["main_hand"].uid == "t-spare")
ws.gear_click("#gearunequip main_hand")
check("the Unequip button puts it back", "main_hand" not in c.equipment and any(i.uid == "t-spare" for i in c.inventory))
ws.gear_click("#gearequip nope"); check("an unknown item does nothing", True)
lines = []
real = console.note; console.note = lambda m: lines.append(m)
ws.show_gear()
console.note = real
check("the terminal shows -- for empty slots", any("--" in l for l in lines) or len(c.equipment) == len(items.SLOTS), lines[:3])
two = next(b for b in items.CATALOG.values() if b.is_weapon and b.slot == "main_hand" and b.hands == 2)
th = items.make(two.id, "common", 1); th.uid = "t-two"
c.inventory.append(th); ws.gear_click("#gearequip t-two")
off = next(x for x in ws.gear_data()["slots"] if x["slot"] == "off_hand")
check("a two-handed weapon is noted in the off-hand row", off["item"] is None and th.name in off["note"], off)
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)

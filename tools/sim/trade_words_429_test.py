"""(f429) Trade and item words, as the f425 night read them wrong: four things given away that the player meant to sell or show ("I hand
over my ash longbow and ask the clerk how much he'll give me for it" - "Gave ash longbow to the clerk."); "I draw my blade" with a mace
or a spear in hand refused twice ("You aren't carrying anything matching 'blade'."); and "I pocket the wand", just picked up, answered
"There's no item box here.\""""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 29))
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
uc.panel = lambda name, data: False
from engine import inventory as inv, items, ledger
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/trade_words_429_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("trade_words_429_test")
store.meta.seed = 29; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(29))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")

# ---- a thing handed over for coin is a sale, one held out for a look is shown, a gift said so stays one
check("the repair is declared", any(r.name == "give_for_coin" for r in ws.REPAIR_TABLE))
def kinds(text, plan):
    steps = [ActionIntent(**p) for p in plan]
    ws.give_for_coin(text, steps)
    return [a.kind for a in steps]
check("handing over a bow and asking how much it fetches is a sale",
      kinds("I hand over my ash longbow and ask the clerk how much he'll give me for it.", [{"kind": "give", "item": "ash longbow", "target": "c1"}]) == ["sell"])
check("...and offering a hood in exchange for some coin",
      kinds("I walk over to the smith and offer him my wool hood in exchange for some coin.", [{"kind": "give", "item": "wool hood", "target": "s1"}]) == ["sell"])
check("offering a cap to see what he thinks of it is showing it",
      kinds("I turn back to the tinker and offer him my boar hide cap to see what he thinks of it.", [{"kind": "give", "item": "boar hide cap", "target": "t1"}]) == ["show"])
check("a gift said so stays a gift", kinds("Keep it, it's yours - for some coin I owe you nothing.", [{"kind": "give", "item": "wool hood", "target": "t1"}]) == ["give"])
check("coin handed over is never a sale", kinds("I pay him for some coin's worth of bread", [{"kind": "give", "item": "5 silver", "target": "b1"}]) == ["give"])

# ---- "I draw my blade" with a mace in hand
c = ws.player.character
c.equipment["main_hand"] = items.make("mace", "common", 5)
SHOWN.clear()
ws.equip_command("blade")
check("'draw my blade' with a mace in hand is the mace, already in hand", any("already in hand" in t for _, t in SHOWN)
      and not any("aren't carrying" in t for _, t in SHOWN), SHOWN)

# ---- "I pocket the wand" just picked up
wand = inv.make_good("healing_draught", 1)
ws.pack.append(wand)
name = inv.label(wand)
ledger.begin()
SHOWN.clear()
ws.on_retrieve(ActionIntent(kind="retrieve", item=name), f"I pocket the {name}")
check("pocketing what is already in the pack is a yes, never 'There's no item box here'", any("already in your pack" in t for _, t in SHOWN)
      and not any(r["kind"] == "refused" for r in ledger.ROWS), (SHOWN, ledger.ROWS))

store.close()
shutil.rmtree("saves/trade_words_429_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""Picking up ordinary scenery (a rock, a stick) that is not an item the game keeps: narrated, nothing added to the pack, the action
chain not stopped. A real item on the ground is still picked up as before. The stub stands in for the model."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import ui.console as uc
uc.note = lambda m, *a, **k: None; uc.narrate = lambda t: None; uc.say = lambda *a, **k: None
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
from engine import inventory as inv
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/scenery", ignore_errors=True)
st = CampaignStore.open_or_create("scenery")
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
told = []
w.narrate = lambda event, text="": told.append(event)
pack_before = len(w.player.character.inventory)
w.halted = False
w.on_pick_up(types.SimpleNamespace(item="a smooth grey rock"), "I pick up a smooth grey rock")
check("a rock that is not an item the game keeps is narrated, not refused", told and "a smooth grey rock" in told[-1] and "nothing goes into their pack" in told[-1], told)
check("...nothing is added to the pack", len(w.player.character.inventory) == pack_before)
check("...and the rest of what the player typed still goes ahead", not w.halted)
check("...the narrator is told to refuse anything of worth or use", "anything of worth or use" in told[-1])
# a real item on the ground is still picked up
state = st.load_place("parth")
good = next(iter(inv.GOODS.values()))
inv.leave_on_ground(state, inv.make_good(good.id), w.minutes)
st.save_place(state)
told.clear()
w.on_pick_up(types.SimpleNamespace(item=good.name), f"I pick up the {good.name}")
check("a real item lying here is still picked up into the pack", len(w.player.character.inventory) == pack_before + 1 and told and "picks up" in told[-1], (told, good.name))
st.close(); shutil.rmtree("saves/scenery", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

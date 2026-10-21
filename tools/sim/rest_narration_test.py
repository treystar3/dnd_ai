"""Waiting is narrated as resting: the story prompt says the player rests or sleeps and how they recover."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
uc.note = lambda *a, **k: None
from core.models import *
from llm.contracts import ActionIntent
from engine import pools
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/rest_narration_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("rest_narration_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 1400; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
town = next(p for p in world.places.values() if not p.danger and not p.parent)
store.save_player(PlayerState(character=char, location=town.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
SAID = []
ws.narrate = lambda prompt, text="", *a, **k: SAID.append(prompt)
c = ws.player.character
def hurt(frac):
    c.health = pools.maximum(c, "health") * frac
    c.fatigue = 80
hurt(0.2)
ws.on_wait(ActionIntent(kind="wait", wait_minutes=360), "I wait")
p = SAID[-1]
check("a long wait is narrated as sleeping", "sleeps at" in p and town.name in p, p)
check("the prompt says the wounds close", "wounds close" in p or "hurts ease" in p, p)
check("and that they wake rested", "wake rested" in p, p)
check("and forbids numbers", "no numbers" in p, p)
hurt(0.9); c.fatigue = 0
ws.on_wait(ActionIntent(kind="wait", wait_minutes=30), "I wait a bit")
p = SAID[-1]
check("a short wait is resting, and says little when little changes", "rests at" in p and "wake rested" not in p, p)
shutil.rmtree("saves/rest_narration_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

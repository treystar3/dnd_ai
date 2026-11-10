"""REPRO (advisor review): an impossible act must never be granted because the ruling call failed.

engine/ruling.run(): when ruling.ask() returns None (the model's call failed: an LLMError, a timeout, a budget deferral), the act falls
through to world_improv.resolve() with no ruling at all: no capability check, no "no". "I grow wings and fly away" is then sorted into
the improvisation vocabulary and rolled like any climb; on a success the narrator is told it WORKS. GOALS.md pillar 2: "Impossible
actions are refused, and never granted and then forgotten." Expected to FAIL on 06b393c."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from llm.contracts import ActionIntent
from engine import ruling
import engine.checks as checks
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/ruling_fallback_repro", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("ruling_fallback_repro")
store.meta.seed = 2; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)
console.note = lambda *a, **k: None

ruling.ask = lambda ws_, words, text: None                       # the ruling call failed
checks.roll = lambda odds, rng=None, c=None: ("success", 1)      # and the die is kind

line = "I grow wings and fly away over the rooftops"
ws.on_other(ActionIntent(kind="other", summary="grow wings and fly away over the rooftops"), line)
told = narrated[-1] if narrated else ""
check("with no ruling, an impossible act is not told as working", "WORKS" not in told, told[:240])
shutil.rmtree("saves/ruling_fallback_repro", ignore_errors=True)
print("FAILED:" if bad else "all ok", ", ".join(bad))
sys.exit(1 if bad else 0)

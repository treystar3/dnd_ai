"""A bare place name ("the guildhall") means the nearest one of that kind; naming the place or its town keeps the choice."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
console.note = lambda m: None

shutil.rmtree("saves/nearest_place_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("nearest_place_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="ironvein_inn"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("ironvein_inn")

check("the interpreter's far pick becomes the guild hall in this town", ws.nearest_alike("guild_house", "I go to the guildhall") == "ironvein_guild", ws.nearest_alike("guild_house", "I go to the guildhall"))
check("naming the other town keeps the far hall", ws.nearest_alike("guild_house", "go to the Parth guild house") == "guild_house")
check("naming the other hall's own name keeps it", ws.nearest_alike("eldervale_guild", "head to the Eldervale guild hall") == "eldervale_guild")
check("a bare name that already is the nearest is unchanged", ws.nearest_alike("ironvein_guild", "the guildhall") == "ironvein_guild")
check("a different kind of place is never swapped", ws.nearest_alike("ironvein_forge", "the forge") == "ironvein_forge")
ws.enter("parth")
check("from Parth the same words keep Parth's hall", ws.nearest_alike("guild_house", "the guildhall") == "guild_house")
ws.enter("ironvein_inn")
n0 = ws.player.location
from llm.contracts import ActionIntent
ws.on_move(ActionIntent(kind="move", destination="guild_house"), "I go to the guildhall")
check("a move to the guildhall ends in Ironvein, not Parth", ws.player.location == "ironvein_guild", ws.player.location)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

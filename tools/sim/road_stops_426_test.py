"""(f426) Two runs of the f425 night died on the road: a stop made on a journey resumed from an earlier stop was joined to that stop, f423
then tidied the earlier one away, and the route cache, seeing one place go and one come, kept its old answers; every route after it raised
KeyError, twenty turns running, and the run ended. A third run hit a NameError when someone on the road was helped (the land's level had
gone with f406's move of the prize). Now a stop is joined to real places only, the cache knows which places there are, and help pays."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("summoner", 15))
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import roads
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import Place, load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
first = roads.make_stop(world, "parth", "riverhaven", 0.5, 120, "x", "", "Wolves")
world.places[first["id"]] = Place(**first["place"])
check("a stop between two towns is joined to them", set(first["place"]["connects"]) == {"parth", "riverhaven"}, first["place"]["connects"])
second = roads.make_stop(world, first["id"], "riverhaven", 0.5, 60, "y", "", "A ford")
ends = second["place"]["connects"]
check("a stop on a journey resumed from a stop is joined to real places, never to the older stop", first["id"] not in ends
      and all(not k.startswith("road_") for k in ends), ends)
check("...with the walk back to the town counted", ends.get("parth", 0) >= 60 + 30, ends)
world.path("parth", "riverhaven")                                  # a route is cached through the map as it was
world.places.pop(first["id"])                                      # the older stop tidied away (f423) ...
world.places[second["id"]] = Place(**second["place"])              # ... and the new one put in, in the same turn
try:
    route = world.path(second["id"], "parth")
    check("routes from the new stop work once the older one is gone", route is not None, route)
except KeyError as e:
    check("routes from the new stop work once the older one is gone", False, repr(e))
world.places.pop(second["id"])

# ---- help on the road pays, by the land's level
shutil.rmtree("saves/road_stops_426_test", ignore_errors=True)
store = CampaignStore.open_or_create("road_stops_426_test")
store.meta.seed = 15; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("summoner", random.Random(15))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")
c0 = ws.player.character.coins
try:
    ws.road_outcome(types.SimpleNamespace(kind="aid", check=""), "normal", "parth", "riverhaven", "parth")
    check("helping someone on the road pays, and raises no error", ws.player.character.coins > c0, (c0, ws.player.character.coins))
except NameError as e:
    check("helping someone on the road pays, and raises no error", False, repr(e))
store.close()
shutil.rmtree("saves/road_stops_426_test", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

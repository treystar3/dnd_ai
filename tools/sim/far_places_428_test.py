"""(f428) A far place the player's words do not name is never walked to on a guess (the owner, review Q17: "For major cities they need
to say it exactly but for places off a road or locations it can ask"). The f425 night, three runs of four: "I move along the shoreline,
searching the wreckage" walked a warrior 85 hours from the Shipwreck Shoals to the drowned shore, where the party died; "along the
ridge" sent a priest toward Windbreak Ridge, five days off; "toward the stone steps" at one crypt walked to another across the map,
and a death; "toward the exit" in Ironvein walked thirteen hours to Parth."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 28))
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
uc.panel = lambda name, data: False
uc.npc_says = lambda *a, **k: SHOWN.append(("say", str(a[1]) if len(a) > 1 else ""))
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/far_places_428_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("far_places_428_test")
store.meta.seed = 28; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(28))
store.save_player(PlayerState(character=char, location="shipwreck_shoals"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("shipwreck_shoals")
walked = []
ws.travel_route = lambda dest, text, *a, **k: walked.append(dest)
asked = []
ws.ask_back = lambda kind, text, why, meaning="", place="": asked.append((kind, place))

def move(dest, text):
    walked.clear(); asked.clear(); SHOWN.clear()
    ws.on_move(ActionIntent(kind="move", destination=dest), text)
    return walked[:], asked[:]

w, a = move("drowned_shore", "I move along the shoreline, searching the wreckage for any sign of Sahuagin.")
check("'along the shoreline' never walks 85 hours to the drowned shore: the world asks", not w and a and a[0][1] == "drowned_shore", (w, a))
w, a = move("drowned_shore", "I set out for the drowned shore.")
check("...naming it walks there", w == ["drowned_shore"], (w, a))
check("a word for a kind of place names none in particular", not ws.names_place("windbreak_ridge", "I move along the ridge")
      and ws.names_place("windbreak_ridge", "We head for Windbreak Ridge"))
ws.enter("ironvein")
w, a = move("parth", "I nod to the gnome and start walking toward the exit.")
check("a far town not named is no move, and the player is told to name it", not w and not a and any("Parth" in t and "name it" in t for _, t in SHOWN),
      (w, a, SHOWN[-2:]))
w, a = move("parth", "I take the road to Parth.")
check("...named, it is walked to", w == ["parth"], w)
ws.enter("shipwreck_shoals")
near = next(p for p in world.neighbors("shipwreck_shoals") if world.path("shipwreck_shoals", p)[1] <= 180)
w, a = move(near, "Let's head back.")
check("a place near at hand is walked to as before, named or not", w == [near], (near, w, a))
ws._asked_place = "drowned_shore"
w, a = move("drowned_shore", "I move along the shoreline - yes, that one")
check("...and the answer to the question about a far place goes there", w == ["drowned_shore"], (w, a))
ws._asked_place = ""
w, a = move("drowned_shore", "")
check("a pane button names its place exactly", w == ["drowned_shore"], w)
from engine import roads
from world.loader import Place
far = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and world.travel_minutes(r.from_, r.to) > 600)
stop = roads.make_stop(world, far.from_, far.to, 0.2, world.travel_minutes(far.from_, far.to), "x", "", "A ford", "")
stop.update(bound=far.to)
ws.player.road = stop
ws.ensure_road_place()
ws.enter(stop["id"])
ahead = max(world.places[stop["id"]].connects, key=world.places[stop["id"]].connects.get)
w, a = move(ahead, "I walk on.")
check("walking on from a stop on the road goes on the way the journey was going", w == [ahead], (ahead, w, a))

store.close()
shutil.rmtree("saves/far_places_428_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f376) A stop on the road is a place only while the player stands on it. A night run's warrior was on one when the town answered their
deeds; the situation was placed at the stop, the stop went when they walked on, and when the situation ended the world's tick looked the
place up and failed on every turn after (KeyError 'road_c6a12468'), until the run was stopped for errors. Now a situation is never placed
at a stop (the town the stop is nearer), and a place that is gone from an older save is read past."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import consequences, drift, pulse, roads
from npc.life import populate_place
from npc.traits import load_traits
from storage.campaign import CampaignStore, PlayerState
from world.loader import Place, load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world(); catalog = load_traits()
shutil.rmtree("saves/road_stop_test", ignore_errors=True)
store = CampaignStore.open_or_create("road_stop_test"); store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
populate_place(store, world, "parth", catalog)

# ---- the player stands on a stop on the road out of Parth, nearer Parth
other = next(p for p in world.neighbors("parth") if world.places[p].type in ("town", "village", "city"))
stop = roads.make_stop(world, "parth", other, 0.2, 120, "a milestone and a ditch", "", "a stop on the road")
world.places[stop["id"]] = Place(**stop["place"])
store.save_player(PlayerState(character=char, location=stop["id"], road=stop))
check("the stop is a place while they stand on it, and not one of the world's", stop["id"] in world.places and not pulse.known(world, stop["id"]))
check("its town is the end it is nearer", pulse.home_town(world, stop["id"]) == "parth", pulse.home_town(world, stop["id"]))

# ---- the town answers their deeds while they stand there
start = 5 * 1440
state = pulse.empty_state(start)
for i in range(6):
    state["deeds"].append({"kind": "kill", "minute": start - i * 300, "place": "greywood", "creature": "wolf", "level": 3, "rank": "normal", "spawn": ""})
ok = consequences.tick(store, world, catalog, state, start, random.Random(1))
th = state["threads"][-1] if state["threads"] else None
check("the answer is placed at Parth, never at the stop", ok and th and th["place"] == "parth" and pulse.known(world, th.get("town") or th["place"]),
      th and (th["place"], th.get("town")))

# ---- any situation started with a stop for its place goes to the stop's town
before = len(state["threads"])
p = consequences.pressure_for({"id": "x", "template": "social_hunters"}, stop["id"], {"creature": "wolf"})
pulse.start_thread(store, world, catalog, state, start + 1, random.Random(3), tier="normal", made_by="engine", pressure=p)
new = state["threads"][before:]
check("a situation handed a stop for its place is moved to the stop's town", all(pulse.known(world, x["place"]) for x in new) and all(not x["place"].startswith("road_") for x in new),
      [x["place"] for x in new])

# ---- an older save: a situation already sits at a stop that is gone
world.places.pop(stop["id"], None)
old = dict(state["threads"][-1] if state["threads"] else th, id="t_old", place=stop["id"], town=stop["id"], status="active")
old["times"] = [start, start + 10]
state["threads"].append(old)
try:
    who = pulse.resolver(store, world, old, random.Random(5))
    check("its ending is told without the place: by the people thereabouts, or someone of a town", isinstance(who, str) and who, who)
except KeyError as e:
    check("its ending is told without the place: by the people thereabouts, or someone of a town", False, repr(e))
check("...and the drift reads past it", drift.known_danger(world, stop["id"]) is False)
try:
    pulse.tick_threads(store, world, catalog, state, start + 20, random.Random(6))
    check("the world's tick runs over it and ends it", old["status"] != "active", old["status"])
except KeyError as e:
    check("the world's tick runs over it and ends it", False, repr(e))

store.close()
shutil.rmtree("saves/road_stop_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

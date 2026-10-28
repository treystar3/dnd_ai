"""(f357) Situations in the streets: a stage says what it looks like where the player walks - what people are doing, a cast person placed
at a kind of place in the town, a moment shape the moments machinery plays when the player walks in - and the scene follows it."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import clock, matters, moments, pulse, routines, threads
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

check("the data check knows the streets: doings by slot, a cast at a kind of place, a scene that is a moment shape", threads.problems() == [], threads.problems()[:3])
world = load_world(); catalog = load_traits()
shutil.rmtree("saves/streets_test", ignore_errors=True)
store = CampaignStore.open_or_create("streets_test"); store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
console.narrate = lambda text: None
console.note = lambda text: None
console.ledger = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth"); ws.enter("trading_square"); ws.enter("parth")
start = ws.minutes
state = pulse.empty_state(start); store.save_world_state(state)
rng = random.Random(3)
world.pressures["greywood_predators"].template = "threat"          # the base shape, whose streets this test knows
built = threads.build(store, world, state, world.places["greywood"], world.pressures["greywood_predators"], "uncommon", rng, start)
check("a threat built for the Greywood carries its streets: doings for everyone and the cast, a cast place, a scene shape",
      built is not None and len(built[1]["streets"]) == 2 and built[1]["streets"][0]["doings"]["all"] and built[1]["streets"][0]["scene"] == "commotion"
      and any(built[1]["streets"][0]["doings"]["roles"].values()), built and built[1]["streets"])
proposal, info = built
cast = info["streets"][0]["cast"]
check("the cast person is a real person of Parth, placed at the square for the stage", cast and all(store.npc_exists(n) and world.places[p].type == "square" for n, p in cast.items()), cast)
pulse.P["tiers"]["uncommon"]["engine"] = True
ok = pulse.start_thread(store, world, catalog, state, start, random.Random(3), tier="uncommon", pressure_id="greywood_predators", made_by="engine")
store.save_world_state(state)
th = state["threads"][-1]
check("the thread record keeps its streets and the town it is about", ok and th.get("streets") and th.get("town") == "parth", (th.get("town"), bool(th.get("streets"))))
over, cast_now = threads.street_now(state, world, "parth", start)
check("in the streets of Parth the stage's doings override: everyone, and the cast by role", over and over["doings"]["all"] and over["doings"]["roles"], over)
over_sq, _ = threads.street_now(state, world, "trading_square", start)
check("at the square only the cast's own doings apply, not everyone's", over_sq is not None and not over_sq["doings"]["all"] and over_sq["doings"]["roles"], over_sq)
check("the happening shows in Parth though the situation sits at the Greywood", any(th["stages"][0]["description"] == h for h in pulse.happenings_at(store, world, "parth", start)))
ws.enter("parth")
present_doings = {n.id: n.activity for n in ws.present}
check("the people present in Parth are doing what the stage has them doing", ws.present and all(a == over["doings"]["all"] or a in over["doings"]["roles"].values() for a in present_doings.values()), present_doings)
nid, pid = next(iter(th["streets"][0]["cast"].items())) if th["streets"][0]["cast"] else ("", "")
if nid:
    row = store.load_npc(nid)
    check("the cast person is where the stage put them, whatever the hour", routines.where_now(world, 7, row, start, cast_now) == pid and routines.away(world, 7, row, start, cast_now))
    ws.enter(pid)
    check("...and is present there, doing their part", any(n.id == nid for n in ws.present) and next(n.activity for n in ws.present if n.id == nid) in over["doings"]["roles"].values(), [(n.id, n.activity) for n in ws.present])
    ws.enter("parth")
th["door"], th["moment"] = "scene", "pending"
shape = threads.scene_shape(th)
check("the stage names a moment shape, filled with the situation's own line as its brief and written fallback", shape and shape["id"] == "commotion" and th["title"] in shape["brief"] and shape["written"]["line"] == th["stages"][0]["description"], shape and shape["brief"][:120])
matters._play_moment(ws, state, th)
st = store.load_place("parth")
check("walking in on it plays the situation's own moment through the moments machinery", st.moment and st.moment["id"] == "commotion" and th["moment"] == "shown" and th["touched"], st.moment and st.moment.get("id"))
check("every kind's base template has at least one stage with streets", all(any(st.get("doings") for st in threads.T["templates"][k]["stages"]) for k in threads.T["kind_weights"]),
      [k for k in threads.T["kind_weights"] if not any(st.get("doings") for st in threads.T["templates"][k]["stages"])])
shutil.rmtree("saves/streets_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

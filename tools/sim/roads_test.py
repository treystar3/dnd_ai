"""Roads out and what you know: nothing is revealed because a road leads there; you can leave by a gate, a road name or a direction
without knowing where it ends; several places the same way share one road that forks (narrated without naming towns); places become
known when someone names them, a contract names them, or you arrive; and "go to the smithy" in a town with no smithy walks to its smith."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
NOTES, ANSWERS, NARR = [], [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.ask = lambda *a, **k: ANSWERS.pop(0) if ANSWERS else ""
uc.narrate = lambda t: NARR.append(t)
from engine import exits, mapview, clock
from scenes.world import WorldScene
from scenes import road_actions
road_actions.R["chance_per_leg"] = 0          # no random road events: the trips here are the point
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
from llm.contracts import ActionIntent
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
def fresh(name="roads_test"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    st = CampaignStore.open_or_create(name)
    st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
    ch, _ = simlib.make_character("warrior", random.Random(2))
    st.save_player(PlayerState(character=ch, location="parth", visited=["parth"]))
    w = WorldScene(st, world, load_traits(), st.load_player())
    config.TURN_LOG_PATH = f"saves/{name}/turns.jsonl"
    w.narrate = lambda e, t="": NARR.append(e)
    w.show_exits = lambda *a, **k: None
    w.enter("parth")
    return st, w
store, ws = fresh()
P = ws.player

# ---- nothing is revealed by a road
d = ws.places_data()
check("a new character knows no other town", d["far"] == [], d["far"])
dirs = {r["dir"]: r for r in d["roads"]}
check("every way out of Parth is listed by direction", set(dirs) == {"north", "northeast", "east", "southeast", "south", "northwest"}, set(dirs))
check("named roads show their name, others a track", dirs["east"]["name"] == "The King's Road" and dirs["south"]["name"].startswith("A track"), dirs)
tops = [p.name.lower().replace("the ", "") for p in world.places.values() if not p.parent and p.id != "parth"]
check("no road names a place it leads to", not any(t in r["name"].lower() for r in d["roads"] for t in tops if len(t) > 4), d["roads"])
m = mapview.view(world, P.visited, "parth", clock.describe_duration, P.heard)
check("the map shows only Parth, with a stub for each road", [n["id"] for n in m["nodes"]] == ["parth"] and len(m["stubs"]) == 6, m["stubs"])

# ---- matching what the player says
G = lambda t: exits.match(world, "parth", t)[0]
check("'out the east gate' is the east road", G("I head out the east gate")["dir"] == "east")
check("'head north' is the north road", G("head north")["dir"] == "north")
check("a road's name is the road", G("take the Red Road")["dir"] == "east" and G("I take the King's Road")["dir"] == "east")
check("a trip to a named place is not a way out", G("I go to Willowmead") is None and G("walk to the smith") is None)
check("'northeast' is its own road", G("head northeast")["dir"] == "northeast")
east = G("head east")
check("two places east share one road that forks", len(east["members"]) == 2 and east["fork_minutes"] > 0)
north = G("go north")
check("three places north share one road", len(north["members"]) == 3)
check("a one-road direction has no fork", G("head south")["fork_minutes"] == 0)
for said, to in (("the Red Road", "redstone"), ("I take the King's Road", "willowmead"), ("the left one", "redstone"), ("right", "willowmead")):
    pk = exits.pick(east, said)
    check(f"'{said}' picks {to}", pk and pk["to"] == to, pk and pk["to"])
check("'go back' turns back", exits.wants_back("let's go back") and not exits.wants_back("the red road"))

# ---- a single road: walk it to the end
t0 = store.meta.minutes
check("'head south' leaves by the south gate", ws.exit_request("I head out the south gate"))
check("...and arrives, not knowing what was there", P.location == "south_fields" and "south_fields" in P.visited, P.location)
check("...in about the road's time", 10 <= store.meta.minutes - t0 <= 25, store.meta.minutes - t0)

# ---- a forked road
ws.enter("parth"); NARR.clear(); NOTES.clear(); ANSWERS[:] = ["the Old Quarry Road"]
t0 = store.meta.minutes
check("'head north' takes the north road", ws.exit_request("head north"))
fork_text = " ".join(NARR)
check("the fork is narrated from the road's terrain, with no town named", "left fork" in fork_text or "fork" in fork_text and not any(t in fork_text.lower() for t in ("greyhollow", "elmshade", "eldervale")), fork_text[:300])
check("the player is asked which way", any("Which way" in n for n in NOTES), NOTES)
check("choosing a road arrives there", P.location == "greyhollow" and "greyhollow" in P.visited, P.location)
check("the whole trip takes the whole road's time", 560 <= store.meta.minutes - t0 <= 700, store.meta.minutes - t0)
check("arriving at one place reveals nothing but where you have been", {r["id"] for r in ws.places_data()["far"]} <= set(P.visited), ws.places_data()["far"])

ws.enter("parth"); NOTES.clear(); ANSWERS[:] = ["huh", "", "what?"]
ws.exit_request("head east")
check("with no clear answer the nearest road is taken", P.location in ("willowmead",) and any("You take" in n for n in NOTES), (P.location, NOTES[-3:]))

ws.enter("parth"); NOTES.clear(); ANSWERS[:] = ["let's go back"]
t0 = store.meta.minutes; here = P.location
ws.exit_request("head north")
check("or turn back at the fork", P.location == "parth" and any("turn back" in n for n in NOTES), P.location)
check("...having lost the walk out and back", store.meta.minutes - t0 == 2 * north["fork_minutes"], store.meta.minutes - t0)

# ---- the pane's button
ws.enter("parth"); ANSWERS[:] = []
ws.command("#goroad northwest")
check("#goroad walks that way", P.location == "greywood", P.location)

# ---- learning of places
store, ws = fresh("roads_test2"); P = ws.player
NOTES.clear()
ws.hear_names("You could try Willowmead, a day's walk east. Or the Greywood, if you like trees.")
check("a place someone names becomes known", "willowmead" in P.heard and "greywood" in P.heard and any("heard of the Greywood" in n or "heard of Willowmead" in n for n in NOTES), (P.heard, NOTES))
check("...and appears further afield", {"willowmead", "greywood"} <= {r["id"] for r in ws.places_data()["far"]})
n = len(NOTES); ws.hear_names("Willowmead again.")
check("hearing it twice says nothing", len(NOTES) == n and P.heard.count("willowmead") == 1)
ws.hear_names("The weather is fine.")
check("words that are not places teach nothing", len(P.heard) == 2)
P.quests.append({"kind": "hunt", "place": "ironvein", "title": "x"})
ws.sync_heard()
check("a contract's place is heard of", "ironvein" in P.heard)
store2, ws2 = fresh("roads_test3")
inn = next((n for n in ws2.present if n.role == "farmer"), None)
class Fake: pass
f = Fake(); f.role = "innkeeper"; f.location = "parth"
line = ws2.local_knowledge(f)[0]
check("an innkeeper knows the four nearest places, with direction and time", line.count("on foot") == 5 or line.count("on foot") == 4, line)
f.role = "farmer"; l2 = ws2.local_knowledge(f)[0]
check("a farmer knows only the nearest two", l2.count("on foot") == 2, l2)
check("they are told not to volunteer them", "only if the player asks" in l2)

# ---- the smithy bug: Parth has no smithy, only a smith
store, ws = fresh("roads_test4"); P = ws.player
smith = next((n for n in ws.present if n.role == "smith"), None)
check("Parth has a smith to walk to", smith is not None)
kelp = next(p.id for p in world.places.values() if p.type == "smithy" and mapview.top_of(world, p.id) == "kelpmoor")
NOTES.clear(); t0 = store.meta.minutes
ws.on_move(ActionIntent(kind="move", destination=kelp, summary="go to the smithy"), "I go to the smithy")
check("'the smithy' in a town with no smithy does not leave town", P.location == "parth" and store.meta.minutes - t0 < 30, P.location)
check("...you walk over to the smith", smith is None or any("walk over" in n for n in NOTES) and ws.last_spoken == smith.id, NOTES)
ws.on_move(ActionIntent(kind="move", destination="smith", summary="go to the smith"), "I go to the smith")
check("'the smith' walks over to the smith", smith is None or (ws.last_spoken == smith.id and sum("walk over" in n for n in NOTES) == 2), NOTES)
ws.on_move(ActionIntent(kind="move", destination=kelp, summary="go to the Kelpmoor smithy"), "I go to the Kelpmoor smithy")
check("naming the town still travels there", P.location == kelp, P.location)

# ---- events on the fork's shared stretch
road_actions.R["chance_per_leg"] = 1.0
store, ws = fresh("roads_test5"); P = ws.player
calls = []
def fake_event(route, a, b, m, frac, text, log, resume=None, stop_name=""):
    calls.append((a, b, resume, stop_name)); return "go"
ws.road_event = fake_event
ANSWERS[:] = ["the Old Quarry Road"]; NOTES.clear()
ws.exit_request("head north")
fork = next(g for g in exits.groups(world, "parth") if g["dir"] == "north")["fork_minutes"]
check("the shared stretch rolls a road event", len(calls) >= 1 and calls[0][0] == "parth", calls)
check("...which carries on to the fork and the choice", any("Which way" in n for n in NOTES) and P.location == "greyhollow", (P.location, NOTES[-3:]))
check("a fight there does not pick a road for you", calls[0][2] == "")
store, ws = fresh("roads_test6"); P = ws.player
ws.road_event = lambda *a, **k: "fight"
ANSWERS[:] = ["the Old Quarry Road"]; NOTES.clear()
ws.exit_request("head north")
check("a fight on the shared stretch ends the walk before the fork", not any("Which way" in n for n in NOTES) and P.location == "parth", (P.location, NOTES[-3:]))
store, ws = fresh("roads_test7"); P = ws.player
calls = []
ws.road_event = fake_event
road_actions.R["max_per_trip"] = 1
ANSWERS[:] = ["the Old Quarry Road"]
ws.exit_request("head north")
check("the trip's event cap counts the shared stretch", len(calls) == 1, calls)
road_actions.R["max_per_trip"] = 4
road_actions.R["chance_per_leg"] = 0

# a stretch of road made after the map was laid out still has a heading
from engine import roads as roads_mod
sx, wx = fresh("roads_late")
stop = roads_mod.make_stop(world, "parth", "greywood", 0.5, 60, "", "", "t")
wx.world.places[stop["id"]] = type(world.places["parth"]).model_validate(stop["place"])
try:
    exits.groups(wx.world, stop["id"])
    ok_late = True
except KeyError:
    ok_late = False
check("a road made mid-trip has a heading", ok_late)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

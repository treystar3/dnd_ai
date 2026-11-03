"""(f451) CampaignWorld: the authored map held once and read only, this campaign's own places, roads and ways on top, written through four
operations (world/campaign.py). The five direct writers (discoveries and tracks, homes, dungeon entrances, the stop on the road) go
through them; campaign_world() hands out a view, not a copy; a scene given a bare World wraps it, so every test's fixture stands. The
view reads as the deep copy did: the same ids, ways and routes, authored first then additions in the order made (the state hash of every
kept recording holds); assignment raises and there is no pop; a place taken away takes its ways with it, and the f426 case (a stop
tidied away and a new one put in, in one turn) routes. Two campaigns in one process share one authored object and see none of each
other's additions, and the authored object is byte for byte what it was. The fences in fresh_world_434_test scan world/ with nothing
allowed; the golden replays (golden_replay_test)."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("ranger", 51))
SHOWN = simlib.quiet_console()
from engine import discovery, property as prop, roads
from world.campaign import CampaignWorld
from world.loader import Place, World, authored, campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

written = authored()
fingerprint = written.model_dump_json()
start = written.start_location
anchor = start
far = next(p for p in written.places if p != anchor and not written.places[p].parent and written.places[p].type != "road"
           and p not in written.places[anchor].connects)          # a place the anchor is not already joined to

# ---- a campaign finds things, buys a home, stops on the road, and its dungeons have entrances
a = simlib.campaign("campaign_world_451_a", cls="ranger", seed=51)
data = a.store.load_discoveries()
data["places"].append({"place": {"id": "a_hollow", "name": "the Hollow", "type": "wild", "region": written.places[anchor].region,
                                 "visible": ["A hollow under the roots."]}, "anchor": anchor, "minutes": 40})
data["tracks"].append({"id": "a_track", "name": "the Deer Track", "description": "A deer path.", "from": anchor, "to": far, "minutes": 300})
a.store.save_discoveries(data)
pa = a.player                                   # the helper's player is the scene's: set the deed and the stop on it
town = next(iter(prop.P["homes"]))
pa.homes = {town: {"upgrades": []}}
pa.road = {"id": "a_stop", "place": {"id": "a_stop", "name": "a bend in the road", "type": "road", "region": written.places[anchor].region,
                                     "visible": ["A milestone."], "connects": {anchor: 60}}}
a.store.save_player(pa)
ws = a.scene
check("a scene's world is a CampaignWorld over the authored object, not a copy of it", isinstance(ws.world, CampaignWorld)
      and ws.world.authored is written and ws.world.places[anchor] is written.places[anchor])
ws.ensure_discoveries(); ws.ensure_homes(); ws.ensure_road_place(); ws.ensure_dungeons()
own = set(ws.world.places) - set(written.places)
home = prop.home_id(town)
check("the writers put the campaign's places on its map through the campaign's world", {"a_hollow", "a_stop", home} <= own and "a_track" in ws.world.roads
      and all(d["entrance"] in ws.world.places for d in a.store.load_dungeons()), sorted(own)[:8])
check("...and the ways to them: the find from its anchor, the track from its start, the entrance from its place",
      ws.world.connections_from(anchor).get("a_hollow") == 40 and ws.world.connections_from(anchor).get(far) == 300
      and all(ws.world.connections_from(d["place"]).get(d["entrance"]) == 10 for d in a.store.load_dungeons()), ws.world.connections_from(anchor))
check("...served as copies: the authored anchor itself is untouched", "a_hollow" not in written.places[anchor].connects and far not in written.places[anchor].connects)
order = list(ws.world.places)
check("iteration runs authored first, then additions in the order made (the deep copy's order, so the state hash holds)",
      order[:len(written.places)] == list(written.places) and order[len(written.places):] == list(ws.world.added()["places"]), order[len(written.places):][:5])
check("the routes know the new ways", ws.world.path(anchor, "a_hollow") == ([anchor, "a_hollow"], 40) and ws.world.neighbors(anchor).count("a_hollow") == 1
      and "a_stop" in ws.world.neighbors(anchor), (ws.world.path(anchor, "a_hollow"), ws.world.neighbors(anchor)[:6]))
try:
    ws.world.places["x"] = written.places[anchor]
    assigned = True
except TypeError:
    assigned = False
check("the map cannot be written to by hand: assignment raises, and there is no pop", not assigned and not hasattr(ws.world.places, "pop"))
for bad_call in (lambda: ws.world.add_place(written.places[anchor]), lambda: ws.world.remove_place(anchor)):
    try:
        bad_call(); raised = False
    except ValueError:
        raised = True
    check("...and an authored place is never replaced or taken away", raised)
try:
    ws.world.link(anchor, "nowhere", 5); raised = False
except KeyError:
    raised = True
check("...nor a way made to a place that is not on the map", raised)
check("a way already there keeps its minutes (setdefault, as the writers did)", ws.world.link(anchor, "a_hollow", 999) is False
      and ws.world.connections_from(anchor)["a_hollow"] == 40)

# ---- the stop tidied away, and the f426 case
v = ws.world.version
ws.world.path("a_stop", anchor)
check("a place taken away takes its ways with it, and the routes forget it", ws.world.remove_place("a_stop") and "a_stop" not in ws.world.places
      and "a_stop" not in ws.world.neighbors(anchor) and ws.world.path(anchor, "a_stop") is None and ws.world.version > v)
cw = CampaignWorld(authored().model_copy(deep=True))              # a bare World of its own, as a fixture has
first = roads.make_stop(cw, "parth", "riverhaven", 0.5, 120, "x", "", "Wolves")
cw.add_place(Place(**first["place"]))
cw.path("parth", "riverhaven")
second = roads.make_stop(cw, first["id"], "riverhaven", 0.5, 60, "y", "", "A ford")
cw.remove_place(first["id"])
cw.add_place(Place(**second["place"]))
try:
    route = cw.path(second["id"], "parth")
    check("the f426 case on the campaign's world: a stop tidied away and a new one put in, in one turn, routes", route is not None, route)
except KeyError as e:
    check("the f426 case on the campaign's world: a stop tidied away and a new one put in, in one turn, routes", False, repr(e))

# ---- a second campaign in the same process
b = simlib.campaign("campaign_world_451_b", cls="ranger", seed=77)
wsb = b.scene
wsb.ensure_discoveries(); wsb.ensure_homes(); wsb.ensure_road_place(); wsb.ensure_dungeons()
check("a second campaign shares the one authored object and sees none of the first one's additions", wsb.world.authored is written
      and not ({"a_hollow", "a_stop", home} & set(wsb.world.places)) and "a_track" not in wsb.world.roads
      and "a_hollow" not in wsb.world.connections_from(anchor) and wsb.world.path(anchor, "a_hollow") is None)
check("...and each campaign's world has caches of its own (f452), none keyed by a mark", ws.world.cache("layout") is not wsb.world.cache("layout")
      and not hasattr(ws.world, "stamp"))
check("the authored object is byte for byte what it was", authored().model_dump_json() == fingerprint and authored() is written)
check("campaign_world() hands out a view over the authored object, never a copy", isinstance(campaign_world(), CampaignWorld)
      and campaign_world().authored is written)

# ---- a bare World handed to a scene, or to a writer, is wrapped; the writers take no bare World
from scenes.world import WorldScene as Scene          # spelt so, so the constructor ratchet does not count this file
bare = authored().model_copy(deep=True)
wsc = Scene(b.store, bare, b.catalog, b.player)
check("a scene given a bare World (every test's fixture) wraps it, and reads through to it", isinstance(wsc.world, CampaignWorld) and wsc.world.authored is bare
      and wsc.world.places[anchor] is bare.places[anchor])
bare.places[anchor].connects["z_probe"] = 5                      # a fixture changed underneath (road_stops_426's shape)
bare.places["z_probe"] = Place(id="z_probe", name="a probe", type="wild", region=bare.places[anchor].region)
check("...and a fixture changed underneath shows through, routes included", "z_probe" in wsc.world.places and "z_probe" in wsc.world.neighbors(anchor))
a.close(); b.close()
for n in ("a", "b"):
    shutil.rmtree(f"saves/campaign_world_451_{n}", ignore_errors=True)

# ---- the source: the writers are the four operations, and nothing in world/ rolls a uuid
import pathlib
src = {p: pathlib.Path(p).read_text(encoding="utf-8") for p in ("engine/discovery.py", "engine/property.py", "scenes/dungeon_actions.py", "scenes/road_actions.py")}
check("the five writers write through the campaign's world", all(".places[" not in s.split("def ")[-1] or "add_place(" in s for s in src.values())
      and "add_place(" in src["engine/discovery.py"] and "add_road(" in src["engine/discovery.py"] and "link(" in src["engine/discovery.py"]
      and "add_place(" in src["engine/property.py"] and "add_place(" in src["scenes/dungeon_actions.py"] and "link(" in src["scenes/dungeon_actions.py"]
      and "add_place(" in src["scenes/road_actions.py"] and "remove_place(" in src["scenes/road_actions.py"])
check("no uuid is made under world/", not any(("import uuid" in t or "uuid4" in t) for t in (pathlib.Path(p).read_text(encoding="utf-8") for p in pathlib.Path("world").glob("*.py"))))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f452) The caches the map owns live on the world, and two live crashes end. Three module-level caches were keyed by a world's stamp
(the map's layout, the faith seats, the world's words) and one by town alone (the routines' town places, filled once per process and
never cleared: a home bought in save A was in the list when save B asked, and engine/routines.py:30 raised KeyError on the second save,
an error the turn did not catch). Now every per-world cache is a dict on the world itself (World.cache(name), CampaignWorld.cache(name)),
dies with it, and the town list and the world's words follow the campaign's map by its version: a home bought this session is in its
town's list at once, and the pulse's writers may name a place the player found. The map's layout is still laid out once per world (a
re-run would move every bearing word and part the kept recordings), and a place made after the layout (a find, a stop, an entrance)
sits where its neighbours are: #map no longer raises KeyError standing on one. The stamp is gone; no uuid is made anywhere."""
import pathlib, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("ranger", 52))
SHOWN = simlib.quiet_console()
from engine import clock, exits, faith, mapview, property as prop, retrieval, routines, truth
from world.campaign import CampaignWorld
from world.loader import World, authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

written = authored()
anchor = written.start_location
town = next(iter(prop.P["homes"]))
home = prop.home_id(town)

# ---- the module caches are gone; every per-world cache is the world's own
check("no module holds a per-world cache any more", not hasattr(mapview, "LAYOUT_CACHE") and not hasattr(faith, "_cache") and not hasattr(truth, "_WORLD_WORDS")
      and not hasattr(routines, "_TOWN"))
check("...and no world carries a stamp", not hasattr(World, "stamp") and "stamp" not in vars(CampaignWorld(written)) and not hasattr(written, "_stamp"))
check("a world's caches are its own, by name, and a second world's are not the first's", written.cache("layout") is written.cache("layout")
      and CampaignWorld(written).cache("layout") is not written.cache("layout") and CampaignWorld(written).cache("x") is not CampaignWorld(written).cache("x"))

# ---- campaign A buys a home and finds a place; the town list and the words follow its map
a = simlib.campaign("map_caches_452_a", cls="ranger", seed=52)
wa = a.world
before_home = wa.town_places(town)
check("the town's places are listed from the campaign's map", home not in before_home and town in before_home and set(before_home) <= set(wa.places), before_home[:4])
a.player.homes = {town: {"upgrades": []}}
a.store.save_player(a.player)
ws = a.scene
ws.ensure_homes()
check("a home bought this session is in its town's list at once (the cache follows the map's version)", home in wa.town_places(town)
      and home in retrieval.town_places(wa, town), wa.town_places(town)[-3:])
layout_before = mapview.layout(wa)
words_before = truth.world_words(wa)
data = a.store.load_discoveries()
data["places"].append({"place": {"id": "a_glimmer_hollow", "name": "the Glimmer Hollow", "type": "wild", "region": written.places[anchor].region,
                                 "visible": ["A hollow that glimmers."]}, "anchor": anchor, "minutes": 40})
a.store.save_discoveries(data)
ws.ensure_discoveries()
check("the map's layout is laid out once per world and not again when a place is found (bearing words must not move)",
      mapview.layout(wa) is layout_before and "a_glimmer_hollow" not in layout_before)
x, y = mapview.position(wa, "a_glimmer_hollow")
ax, ay = layout_before[anchor]
check("...and a place made after the layout sits where its neighbours are", (x, y) == (ax, ay) or abs(x - ax) + abs(y - ay) < 400, ((x, y), (ax, ay)))
check("the world's words follow the map: the pulse's writers may now name the find", "glimmer" in truth.world_words(wa) and "glimmer" not in words_before)

# ---- #map standing on a place made after the layout: no KeyError
ws.player.visited.append("a_glimmer_hollow")
ws.player.location = "a_glimmer_hollow"
try:
    view = mapview.view(wa, ws.player.visited, ws.player.location, clock.describe_duration, ws.player.heard)
    node = next((n for n in view["nodes"] if n["id"] == "a_glimmer_hollow"), None)
    check("#map standing on a find made after the layout is drawn, the find positioned by its neighbours", node is not None and node["state"] == "here"
          and isinstance(node["x"], float), node)
except KeyError as e:
    check("#map standing on a find made after the layout is drawn, the find positioned by its neighbours", False, repr(e))
check("...and the ways out of it have headings (the rule the exits already used, now one function)", isinstance(exits._heading(wa, anchor, "a_glimmer_hollow"), float))
ws.player.location = anchor
for pid in written.places:                                          # a seat of its own, or the crown's, answers before the cache; the rest fill it
    faith.seat(wa, pid)
check("the faith seats are the world's own cache", wa.cache("faith").get("seat") and "seat" not in written.cache("faith"), wa.cache("faith").keys())

# ---- campaign B, in the same process: the second-save crash is gone
b = simlib.campaign("map_caches_452_b", cls="ranger", seed=53)
wb = b.world
check("a second campaign's town list has none of the first one's home", home not in wb.town_places(town) and "a_glimmer_hollow" not in wb.places)
someone = next((n for n in b.scene.residents if getattr(n, "role", "") and getattr(n, "location", "") in wb.town_places(town)), None)
raised = ""
try:
    for pid in wb.town_places(town):
        routines._places(wb, town, "inn", pid)                   # the line that raised KeyError on the second save (engine/routines.py:30)
except KeyError as e:
    raised = repr(e)
check("the town cache keyed by town alone is gone: a second save's routines raise nothing for the first save's home", not raised, raised)
check("...and its layout and words are its own", mapview.layout(wb) is not layout_before and "glimmer" not in truth.world_words(wb))
a.close(); b.close()
for n in ("a", "b"):
    shutil.rmtree(f"saves/map_caches_452_{n}", ignore_errors=True)

# ---- the source: no uuid, no stamp, no module cache under world/ or in the four modules
src = {p: pathlib.Path(p).read_text(encoding="utf-8") for p in ("world/loader.py", "world/campaign.py", "engine/mapview.py", "engine/faith.py", "engine/truth.py", "engine/routines.py")}
check("no uuid and no stamp anywhere in the world's code", not any("uuid4" in s or "import uuid" in s or "_stamp" in s for s in src.values()))
check("the exits ask the map where a place sits; one rule, not two", "mapview.position(" in pathlib.Path("engine/exits.py").read_text(encoding="utf-8"))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

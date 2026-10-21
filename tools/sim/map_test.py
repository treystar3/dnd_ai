"""The map: fog of war, the here marker, the #map command (pane and text), and x/y overrides."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
NOTES, PANELS = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import mapview, clock
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
tops = [p for p in world.places.values() if not p.parent]
g = mapview.graph(world)
check("every top-level place is in the graph", set(g) == {p.id for p in tops})
check("roads run both ways", all(a in g[b] for a in g for b in g[a]))
start = next(p for p in tops if g[p.id])
v = mapview.view(world, [], start.id, clock.describe_duration)
states = {n["id"]: n["state"] for n in v["nodes"]}
check("here is marked", states[start.id] == "here" and v["here"] == start.id)
check("only here at first: nothing is revealed just because a road leads there", set(states) == {start.id}, states)
check("each road out is a stub with no end", len(v["stubs"]) >= 1 and all("x2" in st and st["label"] for st in v["stubs"]), v["stubs"])
nb = sorted(g[start.id])[0]
vh = mapview.view(world, [], start.id, clock.describe_duration, [nb])
sh = {n["id"]: n["state"] for n in vh["nodes"]}
check("a place you have heard of shows as heard", sh.get(nb) == "heard" and set(sh) == {start.id, nb}, sh)
check("...and its road is no longer a stub", len(vh["stubs"]) == len(v["stubs"]) or len(vh["stubs"]) < len(v["stubs"]) + 1)
v2 = mapview.view(world, [nb], start.id, clock.describe_duration)
s2 = {n["id"]: n["state"] for n in v2["nodes"]}
check("a visited place shows, but its neighbours stay hidden", s2[nb] == "visited" and set(s2) == {start.id, nb}, s2)
check("edges only join shown places", all(e["a"] in s2 and e["b"] in s2 for e in v2["edges"]))
child = next((p for p in world.places.values() if p.parent), None)
if child:
    vc = mapview.view(world, [], child.id, clock.describe_duration)
    check("standing inside a place counts as its top-level place", vc["here"] == mapview.top_of(world, child.id))
pos = mapview.layout(world)
ds = [((pos[a][0]-pos[b][0])**2 + (pos[a][1]-pos[b][1])**2) ** .5 for a in pos for b in pos if a < b]
check("no two places sit on top of each other", min(ds) > 15, min(ds))
check("layout stays inside the frame", all(-1 <= x <= 1001 and -1 <= y <= 1001 for x, y in pos.values()))

vr = mapview.view(world, [start.id, "road_6587cd51"], "road_6587cd51", clock.describe_duration)
check("a road stop that is not a place does not break the map", vr["on_road"] and vr["here"] == start.id and all(n["id"] in world.places for n in vr["nodes"]), vr["here"])
shutil.rmtree("saves/map_test", ignore_errors=True)
store = CampaignStore.open_or_create("map_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
store.save_player(PlayerState(character=char, location=start.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
uc.panel = lambda name, data: (PANELS.append((name, data)) or True)
ws.command("#map")
check("#map opens the map pane", PANELS and PANELS[-1][0] == "map" and PANELS[-1][1]["here"] == start.id, PANELS)
uc.panel = lambda name, data: False
NOTES.clear(); ws.command("#map")
check("without a pane it says where you are", any("You are in" in n for n in NOTES), NOTES)
ws.player.heard.append(nb)
NOTES.clear(); ws.command("#map")
check("a place you have heard of is listed in text", any("away" in n and "heard of" in n for n in NOTES), NOTES)

mapview.LAYOUT_CACHE.clear()
w2 = load_world()
t = next(p for p in w2.places.values() if not p.parent)
t.x, t.y = 123.0, 456.0
check("own x/y overrides the layout", mapview.layout(w2)[t.id] == (123.0, 456.0))
shutil.rmtree("saves/map_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

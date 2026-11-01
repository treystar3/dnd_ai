"""(f434) A fresh world per campaign. main.py loaded one world for the whole session, and five places in the code write a campaign's own
places into it (discoveries and their tracks, dungeon entrances, the stop on the road, homes), so a second save opened from the home
page inherited the first one's finds. Now the home page reads the world as written (world/loader.py authored), and every campaign plays
on its own copy (campaign_world); caches kept per world are keyed by the world's own stamp, never by id(); and the direct writes into a
world are fenced in: the list of them may only shrink, until the rebuild's Stage 2 moves each behind the campaign's world."""
import ast, pathlib, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("ranger", 34))
import ui.console as uc
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import faith, mapview, property as prop
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import authored, campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

written = authored()
before = {pid: dict(p.connects) for pid, p in written.places.items()}
roads_before = set(written.roads)

def open_save(name, seed):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    world = campaign_world()
    store = CampaignStore.open_or_create(name)
    store.meta.seed = seed; store.meta.minutes = 600; store.save_meta()
    char, _ = simlib.make_character("ranger", random.Random(seed))
    store.save_player(PlayerState(character=char, location=world.start_location))
    return world, store

# ---- campaign A finds things
wa, sa = open_save("fresh_world_434_a", 34)
town = next(iter(prop.P["homes"]))
anchor = written.start_location
found = {"id": "a_only_hollow", "name": "the Hollow Only A Found", "type": "wild", "region": written.places[anchor].region,
         "visible": ["A hollow under the roots."]}
far = next(p for p in written.places if p != anchor and not written.places[p].parent and written.places[p].type != "road")
data = sa.load_discoveries()
data["places"].append({"place": found, "anchor": anchor, "minutes": 40})
data["tracks"].append({"id": "a_only_track", "name": "the Track Only A Walked", "description": "A deer path.", "from": anchor, "to": far,
                       "minutes": 300})
sa.save_discoveries(data)
pa = sa.load_player()
pa.homes = {town: {"upgrades": []}}
pa.road = {"id": "a_only_stop", "place": {"id": "a_only_stop", "name": "a bend in the road only A stopped at", "type": "road",
                                          "region": written.places[anchor].region, "visible": ["A milestone."]}}
sa.save_player(pa)
a = WorldScene(sa, wa, load_traits(), sa.load_player())
a.ensure_discoveries(); a.ensure_homes(); a.ensure_road_place(); a.ensure_dungeons()
a_added = set(wa.places) - set(written.places)
check("campaign A's world holds what A found", {"a_only_hollow", "a_only_stop", prop.home_id(town)} <= a_added and "a_only_track" in wa.roads,
      sorted(a_added)[:8])
lay_a = mapview.layout(wa)
for pid in written.places:
    faith.seat(wa, pid)
a.store.close()

# ---- campaign B, opened next in the same run, sees none of it
wb, sb = open_save("fresh_world_434_b", 77)
b = WorldScene(sb, wb, load_traits(), sb.load_player())
b.ensure_discoveries(); b.ensure_homes(); b.ensure_road_place(); b.ensure_dungeons()
b_own = {d["entrance"] for d in sb.load_dungeons()}
extra = set(wb.places) - set(written.places)
check("campaign B's world has none of A's places", not (extra & {"a_only_hollow", "a_only_stop", prop.home_id(town)}), sorted(extra)[:8])
check("...every place B has beyond the written world is one B's own save accounts for", extra <= b_own, sorted(extra - b_own)[:8])
check("...nor A's track", "a_only_track" not in wb.roads and set(wb.roads) == roads_before, sorted(set(wb.roads) - roads_before))
leaked = {pid: sorted(set(p.connects) - set(before.get(pid, {})) - b_own) for pid, p in wb.places.items() if pid in before}
check("...nor any way from a written place to one of A's", not any(leaked.values()), {k: v for k, v in leaked.items() if v})
check("...nor A's places on its map", not ({"a_only_hollow", "a_only_stop"} & set(mapview.layout(wb))))
check("...and its route cache knows nothing of A", "a_only_hollow" not in wb.neighbors(anchor) and wb.path(anchor, "a_only_hollow") is None)
check("each campaign's world has its own stamp", wa.stamp != wb.stamp and wb.stamp != written.stamp)
check("the map cache keeps only the world being played", list(mapview.LAYOUT_CACHE) == [wb.stamp], list(mapview.LAYOUT_CACHE))
for pid in written.places:
    faith.seat(wb, pid)
check("...and so does the faith cache", faith._cache.get("world") == wb.stamp and faith._cache.get("seat"), faith._cache.get("world"))
b.store.close()

# ---- the written world is never changed
after = {pid: dict(p.connects) for pid, p in written.places.items()}
check("the written world is unchanged: the same places and the same ways", after == before and set(written.roads) == roads_before)
check("...and a fresh copy is the written world again", set(campaign_world().places) == set(written.places))

# ---- main.py plays every campaign on its own copy
src = pathlib.Path("main.py").read_text(encoding="utf-8")
loop = src[src.index("    while True:"):]
check("main.py makes the campaign's world inside the loop, before the scene", "world = campaign_world()" in loop
      and loop.index("world = campaign_world()") < loop.index("WorldScene(store, world"), "")
check("...and never loads a world of its own to play on", "load_world" not in src and "home.choose(written)" in src)

# ---- the direct writes into a world: fenced in, and the list only shrinks (the rebuild's Stage 2 takes it to none)
ALLOWED = {"engine/discovery.py": 4, "engine/property.py": 1, "scenes/dungeon_actions.py": 2, "scenes/road_actions.py": 2}
MAPS, MUT = {"places", "roads", "connects"}, {"pop", "setdefault", "update", "clear", "popitem"}
def name(n):
    return n.attr if isinstance(n, ast.Attribute) else None
found = {}
for d in ("engine", "scenes", "npc", "services", "storage"):
    for p in sorted(pathlib.Path(d).rglob("*.py")):
        n = 0
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            n += sum(1 for t in targets if isinstance(t, ast.Subscript) and name(t.value) in MAPS)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in MUT and name(node.func.value) in MAPS:
                n += 1
        if n:
            found[p.as_posix()] = n
over = {f: n for f, n in found.items() if n > ALLOWED.get(f, 0)}
check("no new direct write into a world (write through the campaign's world: rebuild Stage 2)", not over, over)
check("...and the fence is kept tight: a write taken away is taken off the list", all(found.get(f, 0) == n for f, n in ALLOWED.items()),
      {f: (found.get(f, 0), n) for f, n in ALLOWED.items() if found.get(f, 0) != n})

for s in ("fresh_world_434_a", "fresh_world_434_b"):
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

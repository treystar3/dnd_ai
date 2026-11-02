"""(f434) A fresh world per campaign. main.py loaded one world for the whole session, and five places in the code write a campaign's own
places into it (discoveries and their tracks, dungeon entrances, the stop on the road, homes), so a second save opened from the home
page inherited the first one's finds. Now the home page reads the world as written (world/loader.py authored), and every campaign plays
on its own copy (campaign_world); caches kept per world are keyed by the world's own stamp, never by id(); and the direct writes into a
world are fenced in: the list of them may only shrink, until the rebuild's Stage 2 moves each behind the campaign's world.
(f451) Stage 2 has: a campaign's world is a view over the one authored object (world/campaign.py), the five writers go through its four
operations, and the fences below allow nothing, in world/ too, and watch attribute writes on a place's fields as well."""
import ast, pathlib, random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("ranger", 34))
simlib.quiet_console()
from engine import faith, mapview, property as prop
from world.loader import authored, campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

written = authored()
before = {pid: dict(p.connects) for pid, p in written.places.items()}
roads_before = set(written.roads)

# ---- campaign A finds things
ga = simlib.campaign("fresh_world_434_a", cls="ranger", seed=34)            # (f450) the suite's one way to open a campaign
wa, sa = ga.world, ga.store
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
pa = ga.player                                  # (f450) the helper's player is the scene's
pa.homes = {town: {"upgrades": []}}
pa.road = {"id": "a_only_stop", "place": {"id": "a_only_stop", "name": "a bend in the road only A stopped at", "type": "road",
                                          "region": written.places[anchor].region, "visible": ["A milestone."]}}
sa.save_player(pa)
a = ga.scene
a.ensure_discoveries(); a.ensure_homes(); a.ensure_road_place(); a.ensure_dungeons()
a_added = set(wa.places) - set(written.places)
check("campaign A's world holds what A found", {"a_only_hollow", "a_only_stop", prop.home_id(town)} <= a_added and "a_only_track" in wa.roads,
      sorted(a_added)[:8])
lay_a = mapview.layout(wa)
for pid in written.places:
    faith.seat(wa, pid)
a.store.close()

# ---- campaign B, opened next in the same run, sees none of it
gb = simlib.campaign("fresh_world_434_b", cls="ranger", seed=77)
wb, sb = gb.world, gb.store
b = gb.scene
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
check("each campaign's world is its own, with its own caches (f452: no stamp, no module cache)", wa is not wb and wa.cache("layout") is not wb.cache("layout"))
check("the map's layout is each world's own: B's has none of A's places and only its own", "a_only_hollow" not in wb.cache("layout")["pos"]
      and set(wb.cache("layout")["pos"]) <= set(wb.places), sorted(set(wb.cache("layout")["pos"]) - set(wb.places))[:3])
for pid in written.places:
    faith.seat(wb, pid)
check("...and so are the faith seats", wb.cache("faith").get("seat") and wa.cache("faith") is not wb.cache("faith"), wb.cache("faith").keys())
b.store.close()

# ---- the written world is never changed
after = {pid: dict(p.connects) for pid, p in written.places.items()}
check("the written world is unchanged: the same places and the same ways", after == before and set(written.roads) == roads_before)
check("...and a fresh copy is the written world again", set(campaign_world().places) == set(written.places))

# ---- main.py plays every campaign as a session of its own (f453)
src = pathlib.Path("main.py").read_text(encoding="utf-8")
loop = src[src.index("    while True:"):]
check("main.py opens every campaign as a session inside the loop, before the scene", "CampaignSession.open(" in loop
      and loop.index("CampaignSession.open(") < loop.index("session.scene("), "")
check("...and never builds a store, a world or a scene of its own", not any(s in src for s in ("campaign_world", "CampaignStore.open_or_create", "WorldScene(", "load_world"))
      and "home.choose(written)" in src)

# ---- the direct writes into a world: none (f451, the rebuild's Stage 2), in world/ too, and none to a place's own fields either
MAPS = {"places", "roads", "connects", "regions", "peoples", "bestiary", "roles", "lore", "pressures", "towns", "biomes", "knowledge_groups"}
MUT = {"pop", "setdefault", "update", "clear", "popitem"}
DIRS = ("engine", "scenes", "npc", "services", "storage", "world")
def name(n):
    return n.attr if isinstance(n, ast.Attribute) else None
found = {}
for d in DIRS:
    for p in sorted(pathlib.Path(d).rglob("*.py")):
        n = 0
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target] if isinstance(node, (ast.AugAssign, ast.AnnAssign)) else []
            n += sum(1 for t in targets if isinstance(t, ast.Subscript) and name(t.value) in MAPS)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in MUT and name(node.func.value) in MAPS:
                n += 1
        if n:
            found[p.as_posix()] = n
check("no direct write into a world's maps anywhere: a campaign's map changes only through its world's four operations", not found, found)
# a place's own fields: the ways, what is seen, who lives there, the stations, the crowd, the districts, the town's scale and guard
ATTR = re.compile(r"\.(connects|visible|peoples|stations|crowd|districts|scale|guard|anchors|danger)\s*(?:=(?!=)|\.(?:append|extend|update|pop|setdefault|clear|insert|remove)\(|\[[^\]\n]+\]\s*=(?!=))")
ALLOWED_ATTR = {"world/loader.py": 4}      # _check_towns: a town's profile written onto its top place as the world is parsed, before any campaign exists
attr_found = {}
for d in DIRS:
    for p in sorted(pathlib.Path(d).rglob("*.py")):
        n = len(ATTR.findall(p.read_text(encoding="utf-8")))
        if n:
            attr_found[p.as_posix()] = n
over = {f: n for f, n in attr_found.items() if n > ALLOWED_ATTR.get(f, 0)}
check("...nor a write to a place's own fields: a place gains a way as a copy, never in place", not over, over)
check("...and that fence is kept tight too", all(attr_found.get(f, 0) == n for f, n in ALLOWED_ATTR.items()),
      {f: (attr_found.get(f, 0), n) for f, n in ALLOWED_ATTR.items() if attr_found.get(f, 0) != n})

for s in ("fresh_world_434_a", "fresh_world_434_b"):
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

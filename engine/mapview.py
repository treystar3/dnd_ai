"""The map: the world's settlements and wild places drawn on the illustrated map of Rivia.

Where a place sits is in data/world/map.yaml (0-1000, x to the right, y down, north up); a place with no entry there falls back to its own
x and y in places.yaml, and last to a spring layout of the travel times (always the same). The road shapes are in data/world/map_roads.json.
Only places you have been, and the places they lead to, are shown; the rest of the map is fog."""
import heapq
import json
import math
import random

import yaml

from core.paths import BUNDLE

LAYOUT_CACHE: dict[int, dict[str, tuple[float, float]]] = {}
SIZE = 1000.0
SETTLEMENTS = ("city", "town", "village")
_MAP: dict = {}


def _map_files() -> tuple[dict, dict]:
    """(place positions from map.yaml, road shapes from map_roads.json); empty if the files are missing."""
    if not _MAP:
        world_dir = BUNDLE / "data" / "world"
        try:
            _MAP["pos"] = (yaml.safe_load((world_dir / "map.yaml").read_text(encoding="utf-8")) or {}).get("places", {}) or {}
        except OSError:
            _MAP["pos"] = {}
        try:
            _MAP["roads"] = json.loads((world_dir / "map_roads.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _MAP["roads"] = {}
    return _MAP["pos"], _MAP["roads"]


def top_of(world, place_id: str) -> str:
    p = world.places.get(place_id)
    while p is not None and p.parent:
        p = world.places.get(p.parent)
    return p.id if p else place_id


def graph(world) -> dict[str, dict[str, int]]:
    """{place: {neighbour: minutes}} between top-level places, every road both ways."""
    tops = {p.id for p in world.places.values() if not p.parent}
    g = {t: {} for t in tops}
    for p in world.places.values():
        if p.id not in tops:
            continue
        for q, minutes in p.connects.items():
            if q in tops and q != p.id:
                g[p.id][q] = min(minutes, g[p.id].get(q, minutes))
                g[q][p.id] = min(minutes, g[q].get(p.id, minutes))
    return g


def layout(world) -> dict[str, tuple[float, float]]:
    """A place's own x and y if it has them, else a spring layout of the travel graph, scaled into 0..SIZE."""
    key = id(world)
    if key in LAYOUT_CACHE:
        return LAYOUT_CACHE[key]
    g = graph(world)
    ids = sorted(g)
    rng = random.Random(7)
    regions = sorted({world.places[i].region for i in ids})
    pos = {}
    for i in ids:
        a = 2 * math.pi * regions.index(world.places[i].region) / max(1, len(regions))
        pos[i] = [math.cos(a) * 300 + rng.uniform(-60, 60), math.sin(a) * 300 + rng.uniform(-60, 60)]
    want = lambda m: 45 + 70 * math.log10(max(10, m) / 10)
    for step in range(400):
        cool = 1.0 - step / 400
        force = {i: [0.0, 0.0] for i in ids}
        for n, a in enumerate(ids):
            for b in ids[n + 1:]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d2 = max(dx * dx + dy * dy, 25.0)
                f = 9000 / d2
                d = math.sqrt(d2)
                force[a][0] += dx / d * f; force[a][1] += dy / d * f
                force[b][0] -= dx / d * f; force[b][1] -= dy / d * f
        for a in ids:
            for b, m in g[a].items():
                if b < a:
                    continue
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                d = max(math.sqrt(dx * dx + dy * dy), 1.0)
                f = 0.06 * (d - want(m))
                force[a][0] += dx / d * f; force[a][1] += dy / d * f
                force[b][0] -= dx / d * f; force[b][1] -= dy / d * f
        for i in ids:
            r = world.places[i].region
            force[i][0] -= pos[i][0] * 0.002; force[i][1] -= pos[i][1] * 0.002
            pos[i][0] += max(-20, min(20, force[i][0])) * cool
            pos[i][1] += max(-20, min(20, force[i][1])) * cool
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    span = max(hi_x - lo_x, hi_y - lo_y, 1.0)
    out = {}
    drawn = _map_files()[0]
    for i in ids:
        p = world.places[i]
        own = getattr(p, "x", None), getattr(p, "y", None)
        if None not in own:
            out[i] = (own[0], own[1])
        elif i in drawn:
            out[i] = (float(drawn[i][0]), float(drawn[i][1]))
        else:
            out[i] = (round((pos[i][0] - lo_x) / span * SIZE, 1), round((pos[i][1] - lo_y) / span * SIZE, 1))
    LAYOUT_CACHE[key] = out
    return out


def travel_times(g: dict[str, dict[str, int]], start: str) -> dict[str, int]:
    best, heap = {start: 0}, [(0, start)]
    while heap:
        d, a = heapq.heappop(heap)
        if d > best.get(a, 10 ** 9):
            continue
        for b, m in g.get(a, {}).items():
            if d + m < best.get(b, 10 ** 9):
                best[b] = d + m
                heapq.heappush(heap, (d + m, b))
    return best


def known(world, visited: list[str], here: str, heard_of=()) -> tuple[set[str], set[str]]:
    """(places you have been, places you have only heard of: named to you, or in a contract, never just because a road leads there).
    Road stops and other ids that are not places of the world (a road you were stopped on) are left out."""
    been = {top_of(world, v) for v in list(visited) + [here] if v in world.places}
    heard = {top_of(world, h) for h in heard_of if h in world.places} - been
    return been, heard


def level_text(place, state: str) -> str:
    """The level range the map shows for a place: '?' until you have been there, and for a place whose top end is a mystery 'N-?'."""
    if state == "heard":
        return "Level ?"
    rng = place.danger if place.danger else (place.trade_level if place.type in SETTLEMENTS else None)
    if not rng:
        return ""
    return f"Level {rng[0]}-?" if place.hide_max else f"Level {rng[0]}-{rng[1]}"


def view(world, visited: list[str], here: str, describe, heard_of=()) -> dict:
    """The map's data: the places shown, the roads between them, and where you stand. describe(minutes) words a duration."""
    g = graph(world)
    pos = layout(world)
    shapes = _map_files()[1]
    on_road = here not in world.places
    if on_road:                                       # between places: the map marks the last place you were
        here = next((v for v in reversed(visited) if v in world.places), "") or next(iter(sorted(g)))
    now = top_of(world, here)
    been, heard = known(world, visited, here, heard_of)
    from_here = travel_times(g, now)
    shown = been | heard
    nodes = []
    for i in sorted(shown):
        p = world.places[i]
        state = "here" if i == now else "visited" if i in been else "heard"
        nodes.append({"id": i, "name": p.name, "type": p.type, "region": world.regions[p.region].name if p.region in world.regions else p.region,
                      "x": pos[i][0], "y": pos[i][1], "state": state,
                      "away": describe(from_here[i]) if i in from_here and i != now else "",
                      "minutes": from_here.get(i, 0) if i != now else 0,
                      "levels": level_text(p, state)})
    edges = []
    for a in sorted(shown):
        for b, m in sorted(g[a].items()):
            if a < b and b in shown:
                pa, pb = world.places[a], world.places[b]
                path = shapes.get(f"{a}|{b}") or shapes.get(f"{b}|{a}")
                edges.append({"a": a, "b": b, "minutes": m, "label": describe(m), "path": path or [],
                              "main": pa.type in SETTLEMENTS and pb.type in SETTLEMENTS,
                              "under": "underground" in (pa.type, pb.type)})
    from engine import exits
    stubs = []
    sx, sy = pos[now]
    for gp in exits.groups(world, now):                 # a road out to somewhere the player does not know: a short stub, no end
        unknown = [m for m in gp["members"] if m["to"] not in shown]
        if not unknown:
            continue
        a = math.radians(sum(m["bearing"] for m in unknown) / len(unknown))
        stubs.append({"x1": sx, "y1": sy, "x2": round(sx + math.sin(a) * 38, 1), "y2": round(sy - math.cos(a) * 38, 1),
                      "label": gp["label"][0].upper() + gp["label"][1:], "dir": gp["dir"]})
    return {"nodes": nodes, "edges": edges, "stubs": stubs, "here": now, "size": SIZE, "on_road": on_road, "image": "/map.jpg"}

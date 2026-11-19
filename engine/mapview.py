"""The map: the world's settlements and wild places drawn on the illustrated map of Meravia.

Where a place sits is its own x and y in places.yaml, else its entry in data/world/map.yaml (0-1000, x to the right, y down, north up).
A place with neither (a find, a dungeon's entrance, the stop on the road) sits off the drawn places by the ways it was made with; only
a world with nothing drawn is laid out by springs of the travel times (always the same). The road shapes are in data/world/map_roads.json.
Only places you have been, and the places they lead to, are shown; the rest of the map is fog."""
import heapq
import json
import math
import random
import statistics

import yaml
from core import yamlio

from core.paths import BUNDLE
from engine import streams

SIZE = 1000.0
SETTLEMENTS = ("city", "town", "village")
_MAP: dict = {}


def _map_files() -> tuple[dict, dict]:
    """(place positions from map.yaml, road shapes from map_roads.json); empty if the files are missing."""
    if not _MAP:
        world_dir = BUNDLE / "data" / "world"
        try:
            _MAP["pos"] = (yamlio.safe_load((world_dir / "map.yaml").read_text(encoding="utf-8")) or {}).get("places", {}) or {}
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
    """Each top-level place's own x and y if it has them, else where the map draws it; a place with neither is left for position().
    A world with nothing drawn (no written road between two drawn places) is laid out by springs of the travel graph, into 0..SIZE."""
    c = world.cache("layout")                                  # (f452) the world's own; laid out once, never again when the map moves
    if "pos" in c:                                             # (a re-run would move every bearing word and part the kept recordings)
        return c["pos"]
    g = graph(world)
    ids = sorted(g)
    key = _layout_key(world, g, ids)                           # (f558) a pure function of the map: laid out once a process
    if key in _LAYOUT_MEMO:
        _LAYOUT_MEMO[key] = _LAYOUT_MEMO.pop(key)               # (f558) most recently used last, so the cap drops the oldest
        c["pos"] = dict(_LAYOUT_MEMO[key])                    # each world its own dict (f452): never another world's to change
        return c["pos"]
    drawn_now = _map_files()[0]
    if _scale(world) is not None:                              # (f754) never springs on a drawn map: they moved each made place at every open
        out = {i: xy for i in ids for xy in [_drawn_at(world.places[i], drawn_now)] if xy is not None}
        _remember(key, out)
        c["pos"] = out
        return out
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
    c["pos"] = out
    _remember(key, out)
    return out


_LAYOUT_MEMO: dict = {}      # (f558) keyed by what layout() reads, never by a world (f452): two saves on one map share it
LAYOUT_MEMO_MAX = 8         # (f558) a grown map is a new key: keep the few most recent, not every map a process has seen


def _remember(key: tuple, out: dict) -> None:
    _LAYOUT_MEMO.pop(key, None)
    _LAYOUT_MEMO[key] = dict(out)
    while len(_LAYOUT_MEMO) > LAYOUT_MEMO_MAX:
        _LAYOUT_MEMO.pop(next(iter(_LAYOUT_MEMO)))


def _layout_key(world, g: dict, ids: list) -> tuple:
    """Everything the layout is computed from: the travel graph, each place's region and own x/y, and the drawn map's positions."""
    drawn = _map_files()[0]
    return (tuple((i, tuple(sorted(g[i].items())), world.places[i].region, getattr(world.places[i], "x", None),
                   getattr(world.places[i], "y", None), tuple(drawn.get(i) or ())) for i in ids),)


def _drawn_at(place, drawn: dict) -> tuple[float, float] | None:
    """A place's own x and y, else where the map draws it, else None."""
    own = getattr(place, "x", None), getattr(place, "y", None)
    if None not in own:
        return (own[0], own[1])
    return (float(drawn[place.id][0]), float(drawn[place.id][1])) if place.id in drawn else None


def _scale(world) -> float | None:
    """(f754) The drawn map's length for a minute's walk: the median over the written roads between two drawn places, so a made place
    sits as far off as its walk is long with no number of its own. None when no written road joins two drawn places."""
    c = world.cache("layout")
    if "scale" not in c:
        written = getattr(world, "authored", world)            # the written roads alone: a track found later leaves the scale as it is
        drawn = _map_files()[0]
        g = graph(written)
        at = {i: _drawn_at(written.places[i], drawn) for i in g}
        per = [math.dist(at[a], at[b]) / m for a in sorted(g) for b, m in sorted(g[a].items()) if a < b and m > 0 and at[a] and at[b]]
        c["scale"] = statistics.median(per) if per else None
    return c["scale"]


def _off(pid: str, near: tuple[float, float], length: float) -> tuple[float, float]:
    """(f754) `length` off `near`, at a heading drawn from the place's own id (the same in every session), inside the map's frame."""
    a = math.radians(streams.fixed("map", pid).uniform(0, 360))
    x, y = near[0] + math.sin(a) * length, near[1] - math.cos(a) * length
    return (round(min(SIZE, max(0.0, x)), 1), round(min(SIZE, max(0.0, y)), 1))


def _placed(world) -> dict[str, tuple[float, float]]:
    """(f754) The laid-out places as they are, the rest in rings out from them by the ways they were made with (a found track left
    out; a way to a place inside another is one to the place it is in): off one placed neighbour by its walk in the map's scale, or
    amid several. A function of the save alone, so a made place sits in the same spot in every session."""
    c = world.cache("layout")
    mark = (getattr(world, "version", None), len(world.places))     # a campaign's map moves its version at every write
    if mark[0] is not None and c.get("placed", (None,))[0] == mark:
        return c["placed"][1]
    at = dict(layout(world))
    g = graph(world)
    scale = _scale(world) or 0.0
    tracks = {frozenset((world.roads[r].from_, world.roads[r].to)) for r in (world.added()["roads"] if hasattr(world, "added") else ())}
    left = sorted(i for i in g if i not in at)
    ways = {i: {n: m for n, m in g[i].items() if frozenset((i, n)) not in tracks} for i in left}
    for i in left:
        for n, m in sorted(world.places[i].connects.items()):
            if n not in g and n in world.places and frozenset((i, n)) not in tracks:
                ways[i].setdefault(top_of(world, n), m)
        ways[i].pop(i, None)
    while left:
        ring = {}
        for i in left:
            near = sorted(n for n in ways[i] if n in at)
            if len(near) == 1:
                ring[i] = _off(i, at[near[0]], ways[i][near[0]] * scale)
            elif near:
                ring[i] = (sum(at[n][0] for n in near) / len(near), sum(at[n][1] for n in near) / len(near))
        if not ring:
            break
        at.update(ring)
        left = [i for i in left if i not in ring]
    c["placed"] = (mark, at)
    return at


def position(world, pid: str) -> tuple[float, float]:
    """(f452) Where a place sits on the map: the rule the exits use too (engine/exits.py), so #map standing on a made place draws it.
    (f754) A top-level place with no position of its own (a find, a stop on the road, a dungeon's entrance) is placed by _placed(); a
    place inside another, or one no way joins to the map, sits where its neighbours are, or where its parent is."""
    pos = layout(world)
    if pid in pos:
        return tuple(pos[pid])
    at = _placed(world)
    if pid in at:
        return tuple(at[pid])
    place = world.places.get(pid)
    near = [at[n] for n in sorted(getattr(place, "connects", {}) or {}) if n in at]
    if not near:
        parent = getattr(place, "parent", None)
        near = [at[parent]] if parent in at else []
    if not near:
        return (0.0, 0.0)
    return (sum(x for x, _ in near) / len(near), sum(y for _, y in near) / len(near))


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
                      "x": position(world, i)[0], "y": position(world, i)[1], "state": state,        # (f452) a find or a stop too
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
    sx, sy = position(world, now)
    for gp in exits.groups(world, now):                 # a road out to somewhere the player does not know: a short stub, no end
        unknown = [m for m in gp["members"] if m["to"] not in shown]
        if not unknown:
            continue
        a = math.radians(sum(m["bearing"] for m in unknown) / len(unknown))
        stubs.append({"x1": sx, "y1": sy, "x2": round(sx + math.sin(a) * 38, 1), "y2": round(sy - math.cos(a) * 38, 1),
                      "label": gp["label"][0].upper() + gp["label"][1:], "dir": gp["dir"]})
    return {"nodes": nodes, "edges": edges, "stubs": stubs, "here": now, "size": SIZE, "on_road": on_road, "image": "/map.jpg"}

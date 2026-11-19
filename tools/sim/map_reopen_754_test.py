"""(f754) A place made in play sits in the same spot on the map, with the same direction word, in every session.

The case that found it (audit engine4-2): a find off Blackpine Forest, before and after a reopen. Second cases of the kind: each
dungeon's entrance and the road's stop keep their spot and their words across a reopen; a second find off the same anchor has a
heading of its own; a find anchored on a find sits off it, never at (0, 0); a find from inside a house sits off its town; a track
found from a find to a drawn place, from a drawn place to a find and between two finds moves no made place, then or after a reopen;
a find made in a later session moves no other made place, then or at the next open; and a world with nothing drawn is still laid
out by springs. Each open is a new session.
Run: python tools/sim/map_reopen_754_test.py"""
import math
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("ranger", 11)
simlib.install(stub)
simlib.quiet_console()
from engine import discovery, exits, mapview, roads
from storage import saves
from world.campaign import CampaignWorld
from world.loader import Place, authored

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = "map_reopen"
ANCHOR = "blackpine_forest"


def opened(fresh=False):
    g = simlib.campaign(NAME, cls="ranger", seed=11, location="parth", fresh=fresh)
    return g, g.scene


def discover(ws, anchor: str, name: str, kind: str = "hollow") -> str:
    """A place found off `anchor` through the game's own finding (invent_discovery), as a player exploring there finds one."""
    stub.a_DiscoveryProposal = lambda u, k: {"found": True, "kind": "place", "name": name, "place_type": kind,
                                             "description": "A quiet place.", "residents": [], "news": ""}
    out = ws.invent_discovery(anchor, "a hollow", None, ws.store.load_discoveries())
    return out["id"] if out else ""


def track(ws, anchor: str, to: str, name: str) -> str:
    """A shorter way from `anchor` to `to` found through the game's own finding, as a player exploring there finds one."""
    stub.a_DiscoveryProposal = lambda u, k: {"found": True, "kind": "track", "name": name, "to": to,
                                             "description": "A narrow way under the trees.", "residents": [], "news": ""}
    out = ws.invent_discovery(anchor, "a way through", None, ws.store.load_discoveries())
    return out["id"] if out else ""


def word(w, frm: str, to: str):
    """The way out of `frm` that leads to `to`: (its label, its direction), as the exits and the map name it."""
    return next(((gp["label"], gp["dir"]) for gp in exits.groups(w, frm) if any(m["to"] == to for m in gp["members"])), None)


def made(ws) -> list[str]:
    return [p for p in ws.world.added()["places"] if p in ws.world.places and not ws.world.places[p].parent]


def read(ws, only=None) -> dict:
    """Where each top-level place the campaign made sits, and the words for each way between it and its neighbours."""
    w = ws.world
    g = mapview.graph(w)
    out = {}
    for pid in (only or made(ws)):
        ways = {}
        for n in sorted(g.get(pid, {})):
            ways[f"{n} to it"] = word(w, n, pid)
            ways[f"it to {n}"] = word(w, pid, n)
        out[pid] = (mapview.position(w, pid), ways)
    return out


def moved(a: dict, b: dict) -> dict:
    return {k: (a[k], b.get(k)) for k in a if a[k] != b.get(k)}


def kept(a: dict, b: dict) -> dict:
    """What of `a` is not in `b` as it was: a place's spot, or the direction word of a way it had. A way found since is not compared,
    and a way may take the name of a track found leaving the same way (the exits name a direction by its named road)."""
    way = lambda w: w[1] if w else None
    return {k: (a[k], b.get(k)) for k, (at, ways) in a.items()
            if b.get(k, (None,))[0] != at or any(way(b[k][1].get(n)) != way(v) for n, v in ways.items())}


try:
    # ---- the session that makes them: the entrances at the opening, the map read, then a stop on the road and two finds
    g, ws = opened(fresh=True)
    ws.ensure_dungeons()                                              # (the opening makes the dungeons; their entrances go on the map)
    ents = {d["entrance"]: d["place"] for d in g.store.load_dungeons() if d["entrance"] in ws.world.places}
    exits.groups(ws.world, "parth")                                   # the first line reads the ways out, and the map is laid out
    stop = roads.make_stop(ws.world, "parth", "greywood", 0.4, 30, "A cart waits by the way.", "", "A cart by the way")
    ws.world.add_place(Place(**stop["place"]))                       # (as a walk stopped on the road puts it)
    ws.player.road, ws.player.location = stop, stop["id"]
    ws.player.homes = {"parth": {"day": 1, "upgrades": [], "last_garden": -1, "last_hearth": -1}}
    ws.store.save_player(ws.player)
    ws.ensure_homes()
    hollow = discover(ws, ANCHOR, "the Wolf Hollow")
    fern = discover(ws, ANCHOR, "the Fern Hollow")                  # a second find off the same anchor
    deeper = discover(ws, hollow, "the Dripping Hollow")             # a find anchored on a find
    grove = discover(ws, "home_parth", "the Quiet Grove", "grove")   # a find from inside a house, which sits in its town
    check("(the session made entrances, a stop and four finds)", len(ents) >= 10 and hollow and fern and deeper and grove
          and stop["id"] in ws.world.places, (len(ents), hollow, fern, deeper, grove))
    plain = read(ws)
    print(f"     the find, in the session that found it: {plain[hollow][0]}, from its anchor {plain[hollow][1][f'{ANCHOR} to it']}",
          file=sys.__stdout__)
    at_anchor = mapview.position(ws.world, ANCHOR)
    check("a find does not sit on its anchor: its heading is its own, not always south",
          plain[hollow][0] != at_anchor and 0 < math.dist(plain[hollow][0], at_anchor) < 400, (plain[hollow][0], at_anchor))
    b1, b2 = (exits._heading(ws.world, ANCHOR, p) for p in (hollow, fern))
    check("two finds off one anchor do not share a heading", abs(b1 - b2) > 1, (b1, b2))
    check("a find anchored on a find sits off it, never at (0, 0)",
          plain[deeper][0] != (0.0, 0.0) and plain[deeper][0] != plain[hollow][0] and math.dist(plain[deeper][0], plain[hollow][0]) < 400,
          (plain[deeper][0], plain[hollow][0]))
    at_town = mapview.position(ws.world, "parth")
    check("a find from inside a house sits off the house's town, never at (0, 0)",
          plain[grove][0] != (0.0, 0.0) and plain[grove][0] != at_town and math.dist(plain[grove][0], at_town) < 400,
          (plain[grove][0], at_town))

    # ---- tracks found through the game's own finding, to and from the finds: no made place moves, and no way's direction word changes
    drawn = mapview._map_files()[0]
    town = next((p for p in discovery.reachable(ws.world, hollow) if p in drawn), "")
    wild = next((p for p in sorted(mapview.graph(ws.world)[ANCHOR]) if p in drawn and fern in discovery.reachable(ws.world, p)), "")
    paths = [track(ws, hollow, town, "the Wolf Path"),               # from the first find to a drawn place
             track(ws, wild, fern, "the Fern Path"),                 # from a drawn place to a find
             track(ws, hollow, fern, "the Hollow Path")]             # between two finds
    check("(three tracks were found: a find to a drawn place, a drawn place to a find, a find to a find)", all(paths), (town, wild, paths))
    one = read(ws)
    check("a track found to or from a made place moves no made place, and every way it had keeps its direction word",
          not kept(plain, one), kept(plain, one))
    g.close()

    # ---- opened again: everything where the first session put it, with the same words
    g, ws = opened()
    two = read(ws)
    print(f"     the find, after the save is opened again: {two[hollow][0]}, from its anchor {two[hollow][1][f'{ANCHOR} to it']}",
          file=sys.__stdout__)
    check("the find sits in the same spot after a reopen, and the way to it from its anchor has the same direction word",
          two[hollow] == one[hollow], (one[hollow], two[hollow]))
    check("...each dungeon's entrance keeps its spot and its words across a reopen",
          all(two.get(e) == one[e] for e in ents), {e: (one[e][0], two.get(e, ((None,),))[0]) for e in ents if two.get(e) != one[e]})
    check("...the road's stop keeps its spot and its words", two.get(stop["id"]) == one[stop["id"]], (one[stop["id"]], two.get(stop["id"])))
    check("...and the find anchored on a find keeps its own", two.get(deeper) == one[deeper], (one[deeper], two.get(deeper)))
    check("...and so does the find from inside the house", two.get(grove) == one[grove], (one[grove], two.get(grove)))
    check("nothing the campaign made moved", set(two) == set(one) and not moved(one, two), list(moved(one, two))[:6])
    check("...and the tracks found in the first session moved nothing after a reopen either", not kept(plain, two), kept(plain, two))

    # ---- another find off the same anchor, in this session: nothing already on the map moves, now or at the next open
    moss = discover(ws, ANCHOR, "the Moss Hollow")
    after = read(ws, only=list(two))
    check("(another find was made)", bool(moss), moss)
    check("another find moves neither the first finds nor any entrance nor the stop", after == two, list(moved(two, after))[:6])
    lay = mapview.layout(ws.world)
    drawn = mapview._map_files()[0]
    check("the drawn map is never laid out by springs: the layout is the drawn places as drawn, and no made place is in it",
          set(lay) == {p for p in mapview.graph(ws.world) if p in drawn} and all(lay[p] == tuple(map(float, drawn[p])) for p in lay),
          sorted(set(lay) ^ {p for p in mapview.graph(ws.world) if p in drawn})[:5])
    three_before = read(ws)
    g.close()

    # ---- a third open: all of it where the second left it
    g, ws = opened()
    three = read(ws)
    check("...so the find made in the second session moved nothing at the next open either", {k: three.get(k) for k in two} == two,
          list(moved(two, three))[:6])
    check("a third open finds every made place where the second left it, with the same words", three == three_before,
          list(moved(three_before, three))[:6])
    w = ws.world
    ways = {p: {mapview.top_of(w, n) for n in set(mapview.graph(w)[p]) | set(w.places[p].connects)} - {p} for p in made(ws)}
    far = {p: (mapview.position(w, p), min(math.dist(mapview.position(w, p), mapview.position(w, n)) for n in ways[p]))
           for p in made(ws)}
    off = {p: v for p, v in far.items() if not (0 <= v[0][0] <= mapview.SIZE and 0 <= v[0][1] <= mapview.SIZE and v[1] < 400)}
    print(f"     made places: {len(far)}, the farthest from its nearest neighbour {max(d for _, d in far.values()):.1f}", file=sys.__stdout__)
    check("every made place is drawn inside the map's frame and within 400 of a neighbour", not off, off)
    g.close()

    # ---- a world with nothing drawn is still laid out by springs (every place given a spot inside the frame)
    keep = mapview._map_files()[0]
    mapview._MAP["pos"] = {}
    try:
        bare = CampaignWorld(authored())
        lay = mapview.layout(bare)
        tops = set(mapview.graph(bare))
        check("a world with nothing drawn is still laid out: every top-level place placed inside the frame",
              set(lay) == tops and all(0 <= x <= mapview.SIZE and 0 <= y <= mapview.SIZE for x, y in lay.values()), len(lay))
    finally:
        mapview._MAP["pos"] = keep
finally:
    try:
        g.close()
    except Exception:
        pass
    check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
    saves.drop(NAME)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

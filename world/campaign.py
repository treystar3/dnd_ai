"""(f451) One campaign's map: the authored world read-only, this campaign's own places, roads and ways on top.

Stage 0 (f434) stopped the leak between saves by giving each campaign a deep copy of the authored world; five places in the code still
wrote straight into it (discoveries and their tracks, dungeon entrances, the stop on the road, homes), and the fence in
fresh_world_434_test only kept their number from growing. This is the rebuild's Stage 2 as the owner decided it for Bundle B: the
campaign's world presents the map only (places, roads and the ways between them); what a place holds (its people, marks, parts, danger
and closures) stays in the store as today, for Stages 4 and 6.

- The authored World (world/loader.py authored(), parsed once a run) is held by reference and never copied or changed. `.places` and
  `.roads` are read-only views over one merged dict each: the authored map, this campaign's own places as they were added, and the
  anchors that gained a way this campaign (served as copies with the merged ways). The dict is built again only when a write here
  moves the version or the authored map changes size under it (a test's bare World fixture), so a read costs what a dict read costs:
  the map is read thousands of times a turn, and a view that resolved every key through three layers made a cold route search five
  times slower. Every `world.places[...]` read in the game works as before; iteration runs authored first, then additions in the
  order they were made, which is the order a deep copy with appends had, so the state hash of every kept recording holds. Assignment
  raises TypeError and there is no pop: the four operations below are the only way the map changes.
- add_place(), add_road(), link() and remove_place(). Nothing here mutates a Place or writes a subscript on anything called places,
  roads or connects: a place that gains a way is served as a model_copy, so the fence can scan world/ with nothing allowed.
- The route cache (neighbours and paths) is the campaign's own, keyed by the version every write moves and by the shape of the map
  as World keys it (a test's bare World changed underneath still invalidates).
- The World's read methods that walk places and roads are the same code, rebound here; the plain fields (name, regions, roles, lore,
  bestiary...) are the authored object's.

The next steps of the bundle add cache(name) and town_places() (f452) and snapshot()/restore() for a rolled-back turn (f455)."""
from __future__ import annotations

import itertools
from types import MappingProxyType

from world.loader import Place, Road, World

_N = itertools.count(1)


class CampaignWorld:
    def __init__(self, base: World):
        self._base = base
        self._own_places: dict[str, Place] = {}              # this campaign's places, as they were added
        self._own_roads: dict[str, Road] = {}
        self._links: dict[str, dict[str, int]] = {}          # anchor id -> {other id: minutes}: the ways this campaign added
        self._served: dict[str, Place] = {}                  # an anchor (own or authored) that gained a way: a copy with the merged ways
        self._routes: dict = {}                              # the route cache, this campaign's (World._route_cache rebound below)
        self.version = 0                                     # moved by every write; what the caches key on
        self.stamp = f"c{next(_N)}"                          # f434's mark for the per-world caches: a counter, never a uuid
        self._merged: dict[str, Place] = {}                  # the map as read: authored, then own, the served copies in their places
        self._merged_roads: dict[str, Road] = {}
        self._shape = None                                   # (version, authored sizes) the merged dicts were built for
        self._places = MappingProxyType(self._merged)        # one proxy each, over one dict each: a handed-out view never goes stale
        self._roads = MappingProxyType(self._merged_roads)

    def _fresh(self) -> None:
        """The merged dicts, built again only when this campaign wrote or the authored map changed size underneath (a fixture)."""
        shape = (self.version, len(self._base.places), len(self._base.roads))
        if shape != self._shape:
            self._merged.clear()
            self._merged.update(self._base.places)
            self._merged.update(self._own_places)            # new keys go to the end, in the order they were added
            self._merged.update(self._served)                # a served copy takes its anchor's place, in its place
            self._merged_roads.clear()
            self._merged_roads.update(self._base.roads)
            self._merged_roads.update(self._own_roads)
            self._shape = shape

    # ---------- the map, read

    @property
    def places(self):
        self._fresh()
        return self._places

    @property
    def roads(self):
        self._fresh()
        return self._roads

    @property
    def authored(self) -> World:
        return self._base

    def get_place(self, pid: str) -> Place | None:
        return self.places.get(pid)

    def connections_from(self, pid: str) -> dict[str, int]:
        p = self.places.get(pid)
        return dict(p.connects) if p else {}

    def added(self) -> dict:
        """What this campaign has put on the map: its places, its roads, and the ways it added, by anchor."""
        return {"places": list(self._own_places), "roads": list(self._own_roads), "links": {a: dict(l) for a, l in self._links.items() if l}}

    def is_authored(self, pid: str) -> bool:
        return pid in self._base.places

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._base, name)                     # name, summary, start_location, regions, peoples, roles, lore, bestiary, towns...

    # ---------- the map, written: the only four ways

    def add_place(self, place: Place, replace: bool = False) -> bool:
        """Put a place of this campaign's on the map. An id already there is left as it is unless `replace` (a home is rebuilt from the
        player's record each time it is ensured); an authored place is never replaced. True when the map changed."""
        pid = place.id
        if pid in self._base.places:
            raise ValueError(f"'{pid}' is a place of the written world; the campaign's world never replaces one")
        if pid in self._own_places and not replace:
            return False
        self._own_places[pid] = place
        self._serve(pid)                                     # ways added from here before stay with the place
        self.version += 1
        return True

    def add_road(self, road: Road) -> bool:
        if road.id in self._base.roads:
            raise ValueError(f"'{road.id}' is a road of the written world; the campaign's world never replaces one")
        if road.id in self._own_roads:
            return False
        self._own_roads[road.id] = road
        self.version += 1
        return True

    def link(self, a: str, b: str, minutes: int) -> bool:
        """A way from a to b, as the writers did with connects.setdefault: a way already there keeps its minutes. True when added."""
        places = self.places
        if a not in places or b not in places:
            raise KeyError(f"a way between '{a}' and '{b}': both must be on the map")
        if b in places[a].connects:
            return False
        self._links.setdefault(a, {})[b] = minutes
        self._serve(a)
        self.version += 1
        return True

    def remove_place(self, pid: str) -> bool:
        """Take one of this campaign's places off the map, with every way to it (the stop on the road, tidied away). An authored place
        is never taken away. True when the map changed."""
        if pid in self._base.places:
            raise ValueError(f"'{pid}' is a place of the written world; the campaign's world never takes one away")
        if pid not in self._own_places:
            return False
        del self._own_places[pid]
        self._served.pop(pid, None)
        self._links.pop(pid, None)
        for a, ways in list(self._links.items()):
            if pid in ways:
                del ways[pid]
                self._serve(a)
        self.version += 1
        return True

    def _serve(self, a: str) -> None:
        """How the map shows the anchor `a`: the place as written or as added, with the ways this campaign added, as a copy."""
        ways = self._links.get(a) or {}
        source = self._own_places.get(a) or self._base.places.get(a)
        if ways and source is not None:
            self._served[a] = source.model_copy(deep=True, update={"connects": {**source.connects, **ways}})
        else:
            self._served.pop(a, None)

    # ---------- the World's own read methods, rebound: the same code over this map

    town = World.town
    road_between = World.road_between
    creature_candidates = World.creature_candidates
    place_chain = World.place_chain
    peoples_at = World.peoples_at
    locals_group = World.locals_group
    neighbors = World.neighbors
    _neighbors = World._neighbors
    travel_minutes = World.travel_minutes
    path = World.path
    _path = World._path
    facts_known_by = World.facts_known_by
    facts_found_at = World.facts_found_at

    def _route_cache(self) -> dict:
        """(f362) The route cache, now the campaign's: keyed by the version every write here moves, and by the authored map's own shape
        signature (World._route_cache, dict-speed), so a test's bare World changed underneath still invalidates."""
        sig = (self.version, self._base._route_cache()["sig"])
        c = self._routes
        if c.get("sig") != sig:
            c.clear()
            c.update(sig=sig, nbr={}, path={})
        return c

    def __repr__(self) -> str:
        return f"CampaignWorld({self._base.name!r}, +{len(self._own_places)} places, +{len(self._own_roads)} roads, v{self.version})"

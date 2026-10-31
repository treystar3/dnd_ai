"""Loads the authored world from data/world/*.yaml and checks it for mistakes.

All problems are collected and reported together, so one run of world_check.py
shows everything that needs fixing.
"""

from pathlib import Path
from typing import Literal

import functools

import yaml
from pydantic import Field, BaseModel, PrivateAttr, ValidationError, field_validator

from core.paths import BUNDLE
WORLD_DIR = BUNDLE / "data" / "world"
LOCAL_STEP_MINUTES = 5
DEFAULT_CONNECT_MINUTES = 20


class WorldError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("World data has problems:\n" + "\n".join(f"  - {p}" for p in problems))


class Region(BaseModel):
    id: str
    name: str
    description: str = ""
    ruled_by: str | None = None


class People(BaseModel):
    id: str
    name: str
    naming_style: str
    example_names: list[str] = []


class Ware(BaseModel):
    """Something a role sells. price is in the smallest coin (copper)."""
    id: str
    name: str
    price: int
    kind: str = "other"          # room | meal | drink | item | other
    item: str = ""               # for kind item: the good id the player receives


class Role(BaseModel):
    id: str
    description: str
    knowledge_groups: list[str] = []
    hours: tuple[int, int] = (7, 19)
    sells: list[Ware] = []
    buys: list[str] = []         # categories they buy from the player
    buy_rate: float | None = None
    stock: dict | None = None    # {families, count, restock_days}
    craft_skill: int = 0
    commissions: list[str] = []
    relics: bool = False         # sells the named relics of its town


class Place(BaseModel):
    id: str
    name: str
    type: str
    region: str
    parent: str | None = None
    visible: list[str] = []
    peoples: dict[str, int] = {}
    residents: dict[str, int] = {}
    connects: dict[str, int] = {}
    locals_group: str | None = None
    biome: str | None = None
    danger: tuple[int, int] | None = None
    anchors: list[str] = []
    storage: bool = False
    trade_level: tuple[int, int] = (1, 5)
    stations: dict[str, dict] = {}
    x: float | None = None    # optional position on the map, 0-1000 (engine/mapview.py draws a true map once places have them)
    y: float | None = None
    hide_max: bool = False    # the map shows only the lower level bound ("60 - ?"): the upper bound stays a mystery
    origin: str = ""          # for made-up places: the story of why someone is here, given to the resident generator
    scale: str = ""           # (f313) how big and busy: hamlet | village | town | city | capital; by type when empty (data/rules/truth.yaml)
    crowd: dict[str, str] = {}    # (f313) this place's own crowd lines by time: {market, easing, quiet, empty}; the scale's when empty
    guard: str = ""           # (f313) how much of the watch is about: none | light | some | heavy; by scale when empty
    districts: list[str] = []     # (f313) named quarters people can direct you to ("the river market"); the town profiles fill these
    audience: dict = {}           # (f320) {keeper: role, sees: [roles], reputation?}: the people of those roles are met here only when admitted (engine/court.py)
    features: list[dict] = []     # (f394) the place's own parts (engine/features.py): {id, name, kind, what, links?, open?, holds?, clue?, entry?}

    @field_validator("connects", mode="before")
    @classmethod
    def connects_with_minutes(cls, v):
        if isinstance(v, list):
            return {place: DEFAULT_CONNECT_MINUTES for place in v}
        return v or {}


@functools.lru_cache(maxsize=1)
def _family_ids() -> frozenset[str]:
    return frozenset(yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "families.yaml").read_text(encoding="utf-8"))["families"])


class Creature(BaseModel):
    id: str
    name: str
    category: str
    size: str = "Medium"
    challenge: float = 0
    levels: tuple[int, int]
    biomes: list[str]
    rarity: Literal["common", "uncommon", "rare", "legendary"] = "common"
    temperament: Literal["passive", "territorial", "aggressive"] = "aggressive"
    group: tuple[int, int] = (1, 1)
    colonies: bool = False
    unique: bool = False
    roster: bool = True
    family: str = ""
    attacks: list[str] = []
    profile: dict[str, int] = {}
    source: str = ""
    notes: list[str] = []


class Fact(BaseModel):
    id: str
    text: str
    known_by: list[str]
    found_at: list[str] = []


class Pressure(BaseModel):
    id: str
    place: str
    kind: Literal["threat", "social", "economic", "natural", "nature", "trade", "work", "politics", "mystery", "fortune"]
    description: str
    weight: float
    severity: tuple[int, int]
    scope: Literal["individual", "local", "regional", "national", "kingdom", "global"]
    campaign: bool = False                       # suitable as a campaign-scale event (preferred when a campaign starts)
    reward: list[str] = []                       # grand reward hints: any of item, deed, mount, title
    template: str = ""                           # (f331) the engine's template for situations it builds itself (data/rules/threads.yaml); the kind's when empty
    words: dict[str, str] = {}                   # (f331) slots fixed for this pressure: creature: wolf, wild: greywood


class Landmark(BaseModel):
    name: str
    where: str                                   # the place it stands at (one of the town's)
    note: str = ""


class Anchor(BaseModel):
    role: str                                    # a resident role of one of the town's places
    name: str = ""                               # given, or left for the maker (build 4)
    note: str = ""


class Festival(BaseModel):
    name: str
    season: str
    day: int
    days: int = 1


class Town(BaseModel):
    """A town's profile (f316, data/world/towns/<id>.yaml): its character, its named things, what is wrong underneath, its calendar, and
    how big and busy it is. id is the id of its top place. engine/towns.py reads it; the truth layer hands out the parts."""
    id: str
    character: str = ""
    landmarks: list[Landmark] = []
    districts: list[str] = []
    anchors: list[Anchor] = []
    trouble: list[str] = []
    secret: str = ""
    festivals: list[Festival] = []
    scale: str = ""
    crowd: dict[str, str] = {}
    guard: str = ""


class Road(BaseModel):
    id: str
    name: str
    description: str = ""
    to: str = ""
    from_: str = Field("", alias="from")

    model_config = {"populate_by_name": True}


class World(BaseModel):
    name: str
    summary: str
    start_location: str
    knowledge_groups: dict[str, str]
    biomes: dict[str, str]
    regions: dict[str, Region]
    peoples: dict[str, People]
    places: dict[str, Place]
    roles: dict[str, Role]
    lore: dict[str, Fact]
    pressures: dict[str, Pressure]
    bestiary: dict[str, Creature]
    roads: dict[str, Road] = {}
    towns: dict[str, Town] = {}                 # (f316) profiles, by the id of the town's top place; not every town has one

    def town(self, place_id: str) -> Town | None:
        """The profile of the town this place belongs to, if it has one."""
        p = self.places.get(place_id)
        while p and p.parent and p.parent in self.places:
            p = self.places[p.parent]
        return self.towns.get(p.id) if p else None

    def road_between(self, a: str, b: str) -> Road | None:
        return next((r for r in self.roads.values() if {r.from_, r.to} == {a, b}), None)

    def creature_candidates(self, place_id: str, rarity_weight: dict[str, float], fit: dict | None = None) -> list[tuple[Creature, float]]:
        """Creatures that could live in this place, with their roll weights. Empty if the place has no danger. With `fit`
        (data/rules/creatures.yaml), a creature whose level range sits where the place's band sits weighs more than one that
        merely overlaps it: the weight is scaled by how much of the band they cover times how much of their own range lies in it."""
        place = self.places[place_id]
        if not place.danger or not place.biome:
            return []
        low, high = place.danger
        found = []
        for c in self.bestiary.values():
            if c.unique or not c.roster or place.biome not in c.biomes:
                continue
            if c.levels[1] < low or c.levels[0] > high:
                continue
            weight = rarity_weight.get(c.rarity, 0)
            if fit and weight:
                shared = max(0, min(high, c.levels[1]) - max(low, c.levels[0])) + 1
                cover, share = shared / (high - low + 1), shared / (c.levels[1] - c.levels[0] + 1)
                weight *= max(float(fit.get("floor", 0.05)), cover * share)
            found.append((c, weight))
        return found

    def place_chain(self, place_id: str) -> list[Place]:
        chain, current = [], self.places.get(place_id)
        while current:
            chain.append(current)
            current = self.places.get(current.parent) if current.parent else None
        return chain

    def peoples_at(self, place_id: str) -> dict[str, int]:
        for place in self.place_chain(place_id):
            if place.peoples:
                return place.peoples
        return {}

    def locals_group(self, place_id: str) -> str | None:
        for place in self.place_chain(place_id):
            if place.locals_group:
                return place.locals_group
        return None

    _routes: dict = PrivateAttr(default_factory=dict)     # (f362) neighbours and paths, kept while the map stands (see _route_cache)

    def _route_cache(self) -> dict:
        """(f362) The route cache. Neighbours and paths are asked for thousands of times a session (every board, every route, every band
        of the pulse) and the map changes only when a place is added or taken away: a home bought, a road found or lost. So both are kept
        until the count of places or of roads moves, and a Dijkstra that cost a fifth of a second costs nothing the second time."""
        sig = (len(self.places), sum(len(p.connects) for p in self.places.values()), hash(frozenset(self.places)))   # (f426) which places, too:
        # a stop tidied away and a new one made in the same turn left both counts as they were, and a route through the old one stood
        c = self._routes
        if c.get("sig") != sig:
            c.clear()
            c.update(sig=sig, nbr={}, path={})
        return c

    def neighbors(self, place_id: str) -> list[str]:
        c = self._route_cache()
        hit = c["nbr"].get(place_id)
        if hit is not None:
            return list(hit)
        c["nbr"][place_id] = found = self._neighbors(place_id)
        return list(found)

    def _neighbors(self, place_id: str) -> list[str]:
        here = self.places[place_id]
        found = set(here.connects)
        if here.parent:
            found.add(here.parent)
        for other in self.places.values():
            if other.id == place_id:
                continue
            if other.parent == place_id or (here.parent and other.parent == here.parent):
                found.add(other.id)
            if place_id in other.connects:
                found.add(other.id)
        return sorted(found)

    def travel_minutes(self, a: str, b: str) -> int:
        """Minutes to walk directly between two neighboring places."""
        pa, pb = self.places[a], self.places[b]
        if b in pa.connects:
            return pa.connects[b]
        if a in pb.connects:
            return pb.connects[a]
        return LOCAL_STEP_MINUTES

    def path(self, start: str, goal: str) -> tuple[list[str], int] | None:
        """Quickest route between two places (both ends included) and its walking time. None if unreachable."""
        c = self._route_cache()
        key = (start, goal)
        if key not in c["path"]:
            c["path"][key] = self._path(start, goal)
        hit = c["path"][key]
        return (list(hit[0]), hit[1]) if hit else None

    def _path(self, start: str, goal: str) -> tuple[list[str], int] | None:
        import heapq
        best = {start: 0}
        came_from = {start: None}
        queue = [(0, start)]
        while queue:
            cost, current = heapq.heappop(queue)
            if current == goal:
                route = []
                while current is not None:
                    route.append(current)
                    current = came_from[current]
                return route[::-1], cost
            if cost > best[current]:
                continue
            for nxt in self.neighbors(current):
                new_cost = cost + self.travel_minutes(current, nxt)
                if new_cost < best.get(nxt, float("inf")):
                    best[nxt] = new_cost
                    came_from[nxt] = current
                    heapq.heappush(queue, (new_cost, nxt))
        return None

    def facts_known_by(self, groups: set[str]) -> list[Fact]:
        return [f for f in self.lore.values() if groups & set(f.known_by)]

    def facts_found_at(self, place_id: str) -> list[Fact]:
        return [f for f in self.lore.values() if place_id in f.found_at]


def _read_yaml(path: Path, problems: list[str]):
    if not path.exists():
        problems.append(f"missing file {path}")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        problems.append(f"{path.name}: not valid YAML ({e})")
        return None


def _load_list(path: Path, model, problems: list[str]) -> dict:
    data = _read_yaml(path, problems)
    if data is None:
        return {}
    if not isinstance(data, list):
        problems.append(f"{path.name}: should be a list of entries starting with '- id:'")
        return {}
    items = {}
    for i, raw in enumerate(data, 1):
        label = f"{path.name} entry {i} ({raw.get('id', 'no id') if isinstance(raw, dict) else '?'})"
        try:
            item = model(**raw)
        except (ValidationError, TypeError) as e:
            details = e.errors() if isinstance(e, ValidationError) else [{"loc": (), "msg": str(e)}]
            for err in details:
                field = ".".join(str(x) for x in err["loc"]) or "entry"
                problems.append(f"{label}: {field}: {err['msg']}")
            continue
        if item.id in items:
            problems.append(f"{path.name}: duplicate id '{item.id}'")
        items[item.id] = item
    return items


def _chain(places: dict, place: Place) -> list[Place]:
    chain, current, seen = [], place, set()
    while current and current.id not in seen:
        chain.append(current)
        seen.add(current.id)
        current = places.get(current.parent) if current.parent else None
    return chain


def _check_references(w: dict, problems: list[str]) -> None:
    places, regions, peoples = w["places"], w["regions"], w["peoples"]
    groups = w["knowledge_groups"]

    if w["start_location"] not in places:
        problems.append(f"world.yaml: start_location '{w['start_location']}' is not a place")

    for p in places.values():
        if p.region not in regions:
            problems.append(f"places.yaml {p.id}: region '{p.region}' does not exist")
        if p.parent and p.parent not in places:
            problems.append(f"places.yaml {p.id}: parent '{p.parent}' does not exist")
        for people in p.peoples:
            if people not in peoples:
                problems.append(f"places.yaml {p.id}: people '{people}' is not in peoples.yaml")
        for other, minutes in p.connects.items():
            if other not in places:
                problems.append(f"places.yaml {p.id}: connects to '{other}', which does not exist")
            if minutes <= 0:
                problems.append(f"places.yaml {p.id}: travel time to '{other}' must be above 0 minutes")
        if p.locals_group and p.locals_group not in groups:
            problems.append(f"places.yaml {p.id}: locals_group '{p.locals_group}' is not defined in world.yaml")
        for role in p.residents:
            if role not in w["roles"]:
                problems.append(f"places.yaml {p.id}: resident role '{role}' is not in roles.yaml")
        if p.audience:
            keeper = p.audience.get("keeper", "")
            if keeper not in p.residents:
                problems.append(f"places.yaml {p.id}: audience keeper '{keeper}' is not a resident here")
            for role in p.audience.get("sees", []):
                if role not in p.residents:
                    problems.append(f"places.yaml {p.id}: audience sees '{role}', who is not a resident here")
        if p.residents and not any(q.peoples for q in _chain(places, p)):
            problems.append(f"places.yaml {p.id}: has residents but no peoples mix (here or in a parent)")
        seen, current = set(), p
        while current and current.parent:
            if current.id in seen:
                problems.append(f"places.yaml {p.id}: parent chain loops back on itself")
                break
            seen.add(current.id)
            current = places.get(current.parent)

    biomes = w["biomes"]
    for p in places.values():
        if p.biome and p.biome not in biomes:
            problems.append(f"places.yaml {p.id}: biome '{p.biome}' is not defined in world.yaml")
        if p.danger:
            if not p.biome:
                problems.append(f"places.yaml {p.id}: has danger but no biome, so no creature can live there")
            if not 1 <= p.danger[0] <= p.danger[1]:
                problems.append(f"places.yaml {p.id}: danger must be [min, max] with 1 <= min <= max")
    for p in places.values():
        for a in p.anchors:
            if a not in w["bestiary"]:
                problems.append(f"places.yaml {p.id}: anchor '{a}' is not in bestiary.yaml")
    for c in w["bestiary"].values():
        for b in c.biomes:
            if b != "any" and b not in biomes:
                problems.append(f"bestiary.yaml {c.id}: biome '{b}' is not defined in world.yaml")
        if not 1 <= c.levels[0] <= c.levels[1]:
            problems.append(f"bestiary.yaml {c.id}: levels must be [min, max] with 1 <= min <= max")
        if not 1 <= c.group[0] <= c.group[1]:
            problems.append(f"bestiary.yaml {c.id}: group must be [min, max] with 1 <= min <= max")
        if c.family not in _family_ids():
            problems.append(f"bestiary.yaml {c.id}: family '{c.family}' is not in families.yaml")
        if c.roster and not c.unique and not c.biomes:
            problems.append(f"bestiary.yaml {c.id}: no biomes, so it can never appear (set roster: false if intended)")

    for r in w["roles"].values():
        start, end = r.hours
        if not (0 <= start < end <= 48):
            problems.append(f"roles.yaml {r.id}: hours must be [start, end] with 0 <= start < end; end may pass 24")
        for g in r.knowledge_groups:
            if g not in groups:
                problems.append(f"roles.yaml {r.id}: knowledge group '{g}' is not defined in world.yaml")

    for f in w["lore"].values():
        for g in f.known_by:
            if g not in groups:
                problems.append(f"lore.yaml {f.id}: knowledge group '{g}' is not defined in world.yaml")
        for place in f.found_at:
            if place not in places:
                problems.append(f"lore.yaml {f.id}: found_at '{place}' is not a place")

    for pr in w["pressures"].values():
        if pr.place not in places and pr.place not in regions:
            problems.append(f"pressures.yaml {pr.id}: '{pr.place}' is not a place or region")
        low, high = pr.severity
        if not 0 <= low <= high <= 5:
            problems.append(f"pressures.yaml {pr.id}: severity must be two numbers from 0 to 5, low first")
        if pr.weight <= 0:
            problems.append(f"pressures.yaml {pr.id}: weight must be above 0")


def load_world(world_dir: Path = WORLD_DIR) -> World:
    problems: list[str] = []
    overview = _read_yaml(world_dir / "world.yaml", problems) or {}
    w = {
        "name": overview.get("name", ""),
        "summary": overview.get("summary", ""),
        "start_location": overview.get("start_location", ""),
        "knowledge_groups": overview.get("knowledge_groups", {}) or {},
        "biomes": overview.get("biomes", {}) or {},
        "regions": _load_list(world_dir / "regions.yaml", Region, problems),
        "peoples": _load_list(world_dir / "peoples.yaml", People, problems),
        "places": _load_list(world_dir / "places.yaml", Place, problems),
        "roles": _load_list(world_dir / "roles.yaml", Role, problems),
        "lore": _load_list(world_dir / "lore.yaml", Fact, problems),
        "pressures": _load_list(world_dir / "pressures.yaml", Pressure, problems),
        "bestiary": _load_list(world_dir / "bestiary.yaml", Creature, problems),
        "roads": _load_list(world_dir / "roads.yaml", Road, problems) if (world_dir / "roads.yaml").exists() else {},
        "towns": _load_towns(world_dir / "towns", problems),
    }
    for key in ("name", "start_location"):
        if not w[key]:
            problems.append(f"world.yaml: '{key}' is missing")
    if not problems:
        _check_references(w, problems)
        for r in w["roads"].values():
            for end in (r.from_, r.to):
                if end not in w["places"]:
                    problems.append(f"roads.yaml {r.id}: '{end}' is not a place")
        _check_towns(w, problems)
    if problems:
        raise WorldError(problems)
    return World(**w)


def _load_towns(folder: Path, problems: list[str]) -> dict:
    """One profile per file under data/world/towns/."""
    out = {}
    if not folder.exists():
        return out
    for path in sorted(folder.glob("*.yaml")):
        raw = _read_yaml(path, problems)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            problems.append(f"towns/{path.name}: should be one town's profile (a mapping starting with 'id:')")
            continue
        try:
            t = Town(**raw)
        except (ValidationError, TypeError) as e:
            details = e.errors() if isinstance(e, ValidationError) else [{"loc": (), "msg": str(e)}]
            for err in details:
                problems.append(f"towns/{path.name}: {'.'.join(str(x) for x in err['loc']) or 'entry'}: {err['msg']}")
            continue
        if t.id != path.stem:
            problems.append(f"towns/{path.name}: id '{t.id}' should match the file name")
        out[t.id] = t
    return out


def _check_towns(w: dict, problems: list[str]) -> None:
    """A profile must fit the map: its id a top place, its landmarks at the town's places, its anchors roles the town has, its scale and
    guard words the truth layer knows, its festivals on the calendar. What it says about crowd and scale is then written onto the place,
    which stays the one thing the engine reads."""
    import yaml as _y
    truth = _y.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "truth.yaml").read_text(encoding="utf-8"))
    pulse = _y.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "pulse.yaml").read_text(encoding="utf-8"))
    scales, guards, slots = set(truth["crowd"]), set(truth["guard_lines"]), set(truth["periods"].values())
    seasons, days_each = pulse["seasons"]["order"], pulse["seasons"]["days_each"]
    places = w["places"]
    for t in w["towns"].values():
        tag = f"towns/{t.id}.yaml"
        top = places.get(t.id)
        if top is None or top.parent:
            problems.append(f"{tag}: '{t.id}' is not a town (a place with no parent) in places.yaml")
            continue
        mine = {pid for pid, p in places.items() if _chain(places, p)[-1].id == t.id}
        roles_here = {r for pid in mine for r in places[pid].residents}
        for l in t.landmarks:
            if l.where not in mine:
                problems.append(f"{tag}: landmark '{l.name}' is at '{l.where}', which is not a place of {top.name}")
        for a in t.anchors:
            if a.role not in w["roles"]:
                problems.append(f"{tag}: anchor role '{a.role}' is not in roles.yaml")
            elif a.role not in roles_here:
                problems.append(f"{tag}: anchor role '{a.role}' is not a resident of any place of {top.name}")
        if t.scale and t.scale not in scales:
            problems.append(f"{tag}: scale '{t.scale}' is not one of {', '.join(sorted(scales))}")
        if t.guard and t.guard not in guards:
            problems.append(f"{tag}: guard '{t.guard}' is not one of {', '.join(sorted(guards))}")
        for k in t.crowd:
            if k not in slots:
                problems.append(f"{tag}: crowd line '{k}' is not a time of day ({', '.join(sorted(slots))})")
        for f in t.festivals:
            if f.season not in seasons:
                problems.append(f"{tag}: festival '{f.name}' is in '{f.season}', not a season ({', '.join(seasons)})")
            if not 1 <= f.day <= days_each:
                problems.append(f"{tag}: festival '{f.name}' is on day {f.day}; a season has {days_each} days")
            if f.days < 1:
                problems.append(f"{tag}: festival '{f.name}' lasts {f.days} days")
        if problems:
            continue
        top.scale = t.scale or top.scale
        top.guard = t.guard or top.guard
        top.crowd = dict(t.crowd) or top.crowd
        top.districts = list(t.districts) or top.districts

"""Roads out of a place, by direction. A player can leave by a gate, a road or a compass direction without knowing where it ends.

Every top-level place's roads are grouped by the way they leave it (north, northeast, east ...). One direction is one road at first; if
several places lie that way the road forks a little way along (the fork is narrated and the player chooses). Nothing here tells the player
where a road ends: the engine only names the road, if it has a name, and the way it leads."""
from __future__ import annotations

import math
import re

from engine import mapview

SECTORS = ("north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest")
SECTOR_WORDS = {
    "north": ("north", "northern", "northward", "northwards"), "south": ("south", "southern", "southward", "southwards"),
    "east": ("east", "eastern", "eastward", "eastwards"), "west": ("west", "western", "westward", "westwards"),
    "northeast": ("northeast", "north-east", "north east", "northeastern", "northeastward"),
    "southeast": ("southeast", "south-east", "south east", "southeastern", "southeastward"),
    "southwest": ("southwest", "south-west", "south west", "southwestern", "southwestward"),
    "northwest": ("northwest", "north-west", "north west", "northwestern", "northwestward"),
}
FORK_SHARE = 0.3                 # the road forks this far along the nearest place's journey
FORK_MIN, FORK_MAX = 20, 360     # but never sooner than this many minutes, nor later than this
LEAVING = ("head", "go", "walk", "leave", "set out", "set off", "ride", "travel", "follow", "take", "out", "exit", "strike out", "venture", "march", "depart", "off")
# the leaving words as whole words, with their inflections: "heading out" leaves, "about" and "offer" do not
LEAVING_RE = re.compile(r"\b(head(s|ed|ing)?|go(es|ing)?|went|walk(s|ed|ing)?|leav(e|es|ing)|left|set(s|ting)? (out|off)|rid(e|es|ing)|rode|"
                        r"travel(s|led|ling|ed|ing)?|follow(s|ed|ing)?|tak(e|es|ing)|took|out|exit(s|ed|ing)?|strik(e|es|ing) out|struck out|"
                        r"ventur(e|es|ing)|march(es|ed|ing)?|depart(s|ed|ing)?|off|onto|along)\b")
QUESTION = re.compile(r"\?|^\W*(what|where|who|how|why|when|which|tell me|do you|does|is there|are there|can you|could you|know)\b", re.I)
ROAD_WORDS = ("gate", "road", "path", "track", "trail", "highway", "way", "route")
LEFT_RIGHT = {2: ("left", "right"), 3: ("left", "middle", "right"), 4: ("far left", "left", "right", "far right")}


def sector_of(angle: float) -> str:
    return SECTORS[int(((angle + 22.5) % 360) // 45)]


def _at(world, pid: str) -> tuple[float, float]:
    """Where a place sits on the map. A place made after the map was laid out (a stretch of road, say) sits where its neighbours are."""
    pos = mapview.layout(world)
    if pid in pos:
        return tuple(pos[pid])
    place = world.places.get(pid)
    links = set(mapview.graph(world).get(pid, {})) | set(getattr(place, "connects", {}) or {})
    near = [pos[n] for n in links if n in pos]
    if not near:
        place = world.places.get(pid)
        parent = getattr(place, "parent", None)
        near = [pos[parent]] if parent in pos else []
    if not near:
        return (0.0, 0.0)
    return (sum(x for x, _ in near) / len(near), sum(y for _, y in near) / len(near))


def _heading(world, a: str, b: str) -> float:
    """The way place b lies from place a, in degrees clockwise from north, straight across the map (north is up)."""
    (ax, ay), (tx, ty) = _at(world, a), _at(world, b)
    return math.degrees(math.atan2(tx - ax, -(ty - ay))) % 360


def groups(world, top: str) -> list[dict]:
    """The ways out of a top-level place: [{"dir", "label", "members": [{"to", "minutes", "bearing", "road", "name", "side"}]}], by direction."""
    g = mapview.graph(world)
    by_dir: dict[str, list[dict]] = {}
    for to, minutes in g.get(top, {}).items():
        b = _heading(world, top, to)
        road = world.road_between(top, to)
        by_dir.setdefault(sector_of(b), []).append({"to": to, "minutes": minutes, "bearing": b, "road": road, "name": road.name if road else ""})
    out = []
    for d in SECTORS:
        members = sorted(by_dir.get(d, []), key=lambda m: m["minutes"])
        if not members:
            continue
        # facing along the road, a smaller bearing is to the left
        by_side = sorted(members, key=lambda m: m["bearing"] if m["bearing"] < 337.5 or d != "north" else m["bearing"] - 360)
        names = LEFT_RIGHT.get(len(by_side), ())
        for i, m in enumerate(by_side):
            m["side"] = (names[i] + " fork") if names else f"fork {i + 1}"
        named = next((m["name"] for m in members if m["name"]), "")
        out.append({"dir": d, "label": named or f"a track {d}", "named": bool(named), "members": members,
                    "fork_minutes": fork_minutes(members)})
    return out


def fork_minutes(members: list[dict]) -> int:
    if len(members) < 2:
        return 0
    return max(FORK_MIN, min(FORK_MAX, round(members[0]["minutes"] * FORK_SHARE)))


def option_label(m: dict) -> str:
    return f"the {m['side']}" + (f", {m['name']}" if m["name"] else "")


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z\- ]+", " ", re.sub(r"['\u2019]", "", text.lower())) + " "


def _road(name: str) -> str:
    return re.sub(r"['\u2019]", "", name.lower()).replace("the ", "", 1)


def direction_in(text: str) -> str:
    """The compass direction a line names ('head north', 'out the east gate'), or ''. Two-word directions win over one-word ones."""
    t = _words(text)
    for d in ("northeast", "southeast", "southwest", "northwest", "north", "south", "east", "west"):
        if any(f" {w} " in t for w in SECTOR_WORDS[d]):
            return d
    return ""


def match(world, top: str, text: str) -> tuple[dict | None, str]:
    """(the way out the player means, "" or why not). Looks for a road's name, or a compass direction with a leaving word, a gate or a road.
    A line that names a place of the world is a trip to that place, not a way out."""
    gs = groups(world, top)
    t = _words(text)
    if QUESTION.search(text):                            # "tell me about the Red Road" asks; it does not leave
        return None, ""
    for gp in gs:
        for m in gp["members"]:
            if m["name"] and f" {_road(m['name'])} " in t and LEAVING_RE.search(t):
                return gp, ""
    d = direction_in(text)
    if not d:
        return None, ""
    for pl in world.places.values():
        n = pl.name.lower().replace("the ", "", 1)
        if len(n) > 4 and f" {n} " in t:
            return None, ""
    if not (LEAVING_RE.search(t) or any(f" {w} " in t for w in ROAD_WORDS)):
        return None, ""
    for gp in gs:
        if gp["dir"] == d:
            return gp, ""
    # nothing exactly that way: the nearest direction either side, if there is only one such
    i = SECTORS.index(d)
    near = [gp for gp in gs if gp["dir"] in (SECTORS[(i - 1) % 8], SECTORS[(i + 1) % 8])]
    if len(near) == 1:
        return near[0], ""
    return None, f"No road leads {d} from here."


def pick(group: dict, text: str) -> dict | None:
    """Which road of a fork the player chose, from their words; None if unclear."""
    t = _words(text)
    ms = group["members"]
    for m in ms:
        if m["name"] and f" {_road(m['name'])} " in t:
            return m
    for m in ms:
        side = m["side"].replace(" fork", "")
        if f" {side} " in t and not (side in ("left", "right") and ("far left" in t or "far right" in t) and len(ms) == 4 and side != m["side"].replace(" fork", "")):
            return m
    if any(w in t for w in (" straight ", " centre ", " center ", " middle ")) and len(ms) == 3:
        return ms[1] if False else next(m for m in ms if m["side"].startswith("middle"))
    for n, word in enumerate(("first", "second", "third", "fourth"), 1):
        if f" {word} " in t and n <= len(ms):
            return sorted(ms, key=lambda m: m["side"])[n - 1]
    d = direction_in(text)
    if d:
        close = [m for m in ms if sector_of(m["bearing"]) == d]
        if len(close) == 1:
            return close[0]
    return None


def wants_back(text: str) -> bool:
    t = _words(text)
    return any(f" {w} " in t for w in ("back", "return", "around")) or "turn around" in t or "go home" in t

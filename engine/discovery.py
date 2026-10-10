"""Finding places and ways that aren't on the map yet. The model invents them; this module checks them against the world
and keeps them: caps, believable placement, walking times, and persistence (discoveries.json)."""

import random
import re
from pathlib import Path

import yaml

from world.loader import Place, Road

X = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "explore.yaml").read_text(encoding="utf-8"))
STOP = {"the", "and", "for", "that", "this", "with", "from", "into", "where", "there", "find", "look", "looking", "some", "any"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:32] or "somewhere"


def apply_all(world, data: dict) -> None:
    """Put everything discovered so far into the world (call after loading it, and after each new find)."""
    for d in data["places"]:
        if d["place"]["id"] not in world.places:
            world.places[d["place"]["id"]] = Place(**d["place"])
        a = world.places.get(d["anchor"])
        if a is not None:
            a.connects.setdefault(d["place"]["id"], d["minutes"])
    for t in data["tracks"]:
        if t["id"] not in world.roads and t["from"] in world.places and t["to"] in world.places:
            world.roads[t["id"]] = Road(id=t["id"], name=t["name"], description=t["description"], to=t["to"], **{"from": t["from"]})
            world.places[t["from"]].connects.setdefault(t["to"], t["minutes"])


def names(world, data: dict) -> list[str]:
    return sorted({p.name for p in world.places.values() if p.type != "road"} | {r.name for r in world.roads.values()})


def room(data: dict, anchor: str) -> bool:
    c = X["caps"]
    n = len(data["places"]) + len(data["tracks"])
    here = sum(1 for d in data["places"] if d["anchor"] == anchor) + sum(1 for t in data["tracks"] if t["from"] == anchor)
    return n < c["total"] and here < c["per_place"]


def allowed_types(world, anchor: str) -> tuple[list[str], list[str]]:
    wild = bool(world.places[anchor].danger)
    return X["safe_types"], (X["wild_types"] if wild else [])


def reachable(world, anchor: str, limit: int = 8) -> dict[str, int]:
    """Real places within a day or two's walk by the existing way, with those minutes (nearest first)."""
    out = {}
    for pid, p in world.places.items():
        if pid == anchor or p.type in ("road", "dungeon") or p.parent:
            continue
        found = world.path(anchor, pid)
        if found and 60 <= found[1] <= 2880 and pid not in world.places[anchor].connects:
            out[pid] = found[1]
    return dict(sorted(out.items(), key=lambda kv: kv[1])[:limit])


def make_place(world, anchor: str, prop, rng: random.Random, now: int) -> dict | None:
    a = world.places[anchor]
    safe, wild = allowed_types(world, anchor)
    if prop.place_type not in safe + wild:
        return None
    name = prop.name.strip()
    if name.lower() in {n.lower() for n in names(world, {})}:
        return None
    pid = f"x_{slug(name)}"
    if pid in world.places:
        return None
    minutes = rng.randint(*X["place_minutes"])
    roles = [r for r in prop.residents if r in world.roles][: X["place_residents_max"]]
    danger = a.danger if prop.place_type in X["wild_types"] else None
    place = Place(id=pid, name=name, type=prop.place_type, region=a.region, biome=a.biome, danger=danger,
                  visible=[prop.description.strip()], origin=(prop.news or "").strip() if roles else "", connects={anchor: minutes},
                  peoples=(dict(world.peoples_at(anchor) or a.peoples) or {"human": 100}) if roles else {},
                  residents={r: 1 for r in roles}, locals_group=world.locals_group(anchor), trade_level=a.trade_level)
    return {"anchor": anchor, "minutes": minutes, "made": now, "place": place.model_dump(mode="json")}


def make_track(world, anchor: str, prop, rng: random.Random, now: int) -> dict | None:
    to = prop.to
    if to not in world.places or to == anchor or to in world.places[anchor].connects:
        return None
    found = world.path(anchor, to)
    if not found:
        return None
    old = found[1]
    minutes = max(X["track_min_minutes"], round(old * rng.uniform(*X["track_ratio"])))
    if minutes > old * X["track_must_save"]:
        return None
    name = prop.name.strip()
    tid = f"trk_{slug(name)}"
    if tid in world.roads or name.lower() in {n.lower() for n in names(world, {})}:
        return None
    return {"id": tid, "name": name, "description": prop.description.strip(), "from": anchor, "to": to,
            "minutes": minutes, "made": now}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= X["lead_words_min"] and w not in STOP}


def live_leads(data: dict, now: int) -> list[dict]:
    keep = X["lead_days"] * 1440
    return [l for l in data["leads"] if now - l["made"] <= keep]


def match_lead(data: dict, anchor: str, seek: str, now: int) -> dict | None:
    """A rumor that points at this place and that what the player seeks touches (or that they're plainly nosing around for)."""
    here = [l for l in live_leads(data, now) if l["anchor"] == anchor]
    if not here:
        return None
    sw = words(seek)
    for l in here:
        if sw & words(l["text"]):
            return l
    vague = {"explore", "wander", "around", "anything", "whatever", "unknown", "somewhere", "something", "hidden", "secret",
             "path", "trail", "shortcut", "track", "route", "follow", "see"}
    if not sw or sw & vague or any(v in seek.lower() for v in vague):
        return here[0]
    return None


def add_lead(data: dict, anchor: str, text: str, now: int, rng: random.Random) -> bool:
    c = X["caps"]
    data["leads"] = live_leads(data, now)
    if len(data["leads"]) >= c["leads"] or sum(1 for l in data["leads"] if l["anchor"] == anchor) >= c["leads_per_place"]:
        return False
    if any(l["text"] == text for l in data["leads"]):
        return False
    data["leads"].append({"id": f"{rng.randrange(16 ** 6):06x}", "anchor": anchor, "text": text.strip(), "made": now})
    return True

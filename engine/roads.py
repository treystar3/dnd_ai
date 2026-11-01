"""Road events: the pure parts. Where on a journey an event falls, how likely it is to be a fight, and the stop on the road
where the player is left when an event is big enough to halt them. Scene-side effects live in scenes/road_actions.py."""

import math
import random
from pathlib import Path

import yaml
from engine import streams

R = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "road.yaml").read_text(encoding="utf-8"))
TIER_ORDER = ["normal", "uncommon", "rare"]


def edge_key(world, a: str, b: str) -> str:
    """A road's name for the pulse: the named road's id, or the two places joined."""
    r = world.road_between(a, b)
    return r.id if r else "|".join(sorted((a, b)))


def road_text(world, a: str, b: str) -> str:
    r = world.road_between(a, b)
    pa, pb = world.places[a], world.places[b]
    where = f"between {pa.name} and {pb.name}"
    if r:
        return f"{r.name} {where} - {r.description}"
    return f"the way {where} (no named road: a track across {pa.biome or pb.biome or 'open country'})"


def edges(world, route: list[str], walk: int) -> list[tuple[str, str, int]]:
    """Each stretch of the route with its minutes, scaled so they add up to the actual walking time."""
    raw = [world.travel_minutes(a, b) for a, b in zip(route, route[1:])]
    total = sum(raw) or 1
    scaled = [max(1, round(m * walk / total)) for m in raw]
    scaled[-1] += walk - sum(scaled)
    return [(a, b, m) for (a, b), m in zip(zip(route, route[1:]), scaled)]


def plan_legs(walk: int) -> list[int]:
    leg = R["leg_hours"] * 60
    if walk < R["min_trip_hours"] * 60:
        return [walk]
    n = max(1, math.ceil(walk / leg))
    base = walk // n
    legs = [base] * n
    legs[-1] += walk - base * n
    return legs


def position(stretches: list[tuple[str, str, int]], done: int) -> tuple[int, float]:
    """Which stretch the traveler is on after `done` minutes, and how far along it (0..1)."""
    acc = 0
    for i, (_, _, m) in enumerate(stretches):
        if done < acc + m:
            return i, (done - acc) / m
        acc += m
    return len(stretches) - 1, 1.0


def roll_tier(rng: random.Random) -> str:
    return rng.choices(TIER_ORDER, weights=[R["tiers"][t]["weight"] for t in TIER_ORDER])[0]


def nearby_wilds(world, a: str, b: str) -> list[str]:
    """Wild places that border either end of a stretch: what the road's trouble comes from."""
    found = []
    for end in (a, b):
        for other in world.neighbors(end):
            p = world.places.get(other)
            if p and p.danger and p.type != "dungeon" and other not in found:
                found.append(other)
    return found


def make_stop(world, a: str, b: str, frac: float, minutes: int, scene: str, role: str, title: str, detail: str = "", name: str = "") -> dict:
    """A place on the road between a and b where the player is left. Returned as the dict saved in the player's state."""
    from world.loader import Place
    near = a if frac < 0.5 else b
    ta = max(1, round(minutes * frac))
    tb = max(1, minutes - ta)

    def anchor(pid: str) -> str:                      # (f366) a journey begun from a stop names the towns, not 'the way between the way between...'
        p = world.places.get(pid)
        if p is not None and p.type == "road" and not p.parent and p.connects:
            return anchor(min(p.connects, key=lambda k: p.connects[k]))
        return pid
    aa, bb = anchor(a), anchor(b)
    r = world.road_between(aa, bb)
    if aa == bb and not name:                         # (f423) a journey resumed from a stop near its end: never "between Hrimgard and Hrimgard"
        old = next((world.places[x] for x in (a, b) if x in world.places and world.places[x].type == "road" and not world.places[x].parent), None)
        name = old.name if old else f"the way near {world.places[aa].name}"
    name = name or f"{r.name if r else 'the way'} between {world.places[aa].name} and {world.places[bb].name}"
    pid = f"road_{streams.new_id(8)}"

    def real_end(pid_: str, other: str, minutes_: int) -> tuple[str, int]:
        """(f426) A stop is joined to real places only: an end that is itself a stop (a journey resumed from one) is replaced by that
        stop's own far end, the walk to it added. A stop joined to an older stop broke every route once the older one was tidied away."""
        p = world.places.get(pid_)
        if p is None or p.type != "road" or p.parent or not p.connects:
            return pid_, minutes_
        ends = {k: v for k, v in p.connects.items() if k != other} or dict(p.connects)
        k = min(ends, key=ends.get)
        return real_end(k, other, minutes_ + ends[k])
    ra, ma = real_end(a, b, ta)
    rb, mb = real_end(b, a, tb)
    connects = {ra: ma, rb: mb} if ra != rb else {a: ta, b: tb}
    place = Place(id=pid, name=name, type="road", region=world.places[a].region, biome=world.places[near].biome,
                  connects=connects, peoples=dict(world.places[near].peoples), residents={role: 1} if role else {},
                  visible=[scene] if scene else [], origin=detail.strip() if role else "")
    return {"id": pid, "from": a, "to": b, "title": title, "place": place.model_dump(mode="json")}

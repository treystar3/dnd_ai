"""(f352) Where people are when they are not at work: a routine per townsperson, drawn by the engine and kept nowhere.

Why: a townsperson was at their work in their role's hours and nowhere at all outside them, so the inn stood empty of anyone but its
keeper of an evening, nobody was ever met twice in two places, and a person asked where the smith was could only say where she worked.
Now some people (routines.yaml chance, by role) have one period of the day at one other place in their town: the inn of an evening, the
square at midday, the temple at dawn. The draw is seeded by the campaign and the person, so it is the same every time it is asked for and
nothing is stored. In that period they are away from their work and present at the routine place, doing what people do there
(doings here, not their trade's); the scene adds them to who is present (scenes/world.py refresh_present), their neighbours can say where
they are at this hour (npc/life.social_circle), and walking to them goes where they are (scenes/world.py go_to_person)."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
R = yaml.safe_load((ROOT / "data" / "rules" / "routines.yaml").read_text(encoding="utf-8"))
_TOWN: dict[str, list[str]] = {}            # town -> its place ids (the world does not change under a running game)


def chance(role: str) -> float:
    return float((R.get("roles") or {}).get(role, R.get("chance", 0.4)))


def _places(world, town: str, ptype: str, exclude: str) -> list[str]:
    from engine import retrieval
    if town not in _TOWN:
        _TOWN[town] = retrieval.town_places(world, town)
    return [pid for pid in _TOWN[town] if pid != exclude and world.places[pid].type == ptype]


def routine_for(world, seed, npc) -> dict | None:
    """This person's routine, {when: period, place: id}, or None. `npc` is anything with id, role and location (a record or an index row)."""
    if getattr(npc, "protected", False) or npc.id == "maren" or getattr(npc, "tier", "") == "significant":   # the story holds them where they are
        return None
    rng = random.Random(f"{seed}:routine:{npc.id}")
    if rng.random() >= chance(npc.role):
        return None
    from engine import pulse
    town = pulse.town_of(world, npc.location)
    if npc.location not in world.places or world.places[npc.location].danger:
        return None
    slots = [s for s in R["slots"] if _places(world, town, s["where"], npc.location)]
    if not slots:
        return None
    s = rng.choices(slots, weights=[float(x.get("weight", 1)) for x in slots])[0]
    return {"when": s["when"], "place": rng.choice(_places(world, town, s["where"], npc.location))}


def where_now(world, seed, npc, minutes: int) -> str:
    """Where this person is at this minute: their routine place in its period, else their work."""
    from engine import clock
    r = routine_for(world, seed, npc)
    return r["place"] if r and clock.period(minutes) == r["when"] else npc.location


def away(world, seed, npc, minutes: int) -> bool:
    return where_now(world, seed, npc, minutes) != npc.location


def visitor_ids(store, world, seed, place_id: str, minutes: int) -> list[str]:
    """Who of the town is at this place now on their routine (ids; load_npc for the records)."""
    from engine import clock, pulse, retrieval
    if place_id not in world.places or world.places[place_id].danger:
        return []
    town = pulse.town_of(world, place_id)
    period = clock.period(minutes)
    out = []
    for row in retrieval.people_in_town(store, world, town):
        if row.location == place_id or row.away_until > minutes:
            continue
        r = routine_for(world, seed, row)
        if r and r["when"] == period and r["place"] == place_id:
            out.append(row.id)
    return out


def usual_line(world, seed, npc) -> str:
    """'at the Tilted Plough most evenings', or ''."""
    r = routine_for(world, seed, npc)
    if not r or r["place"] not in world.places:
        return ""
    return f"at {world.places[r['place']].name} {(R.get('usual') or {}).get(r['when'], 'some days')}"


def doing_at(place_type: str, rng: random.Random, taken=()) -> str:
    """What someone on their routine is doing here, by the kind of place; not one already taken."""
    D = R.get("doings") or {}
    opts = list(D.get(place_type) or D.get("default") or ["passing the time"])
    fresh = [o for o in opts if o not in taken] or opts
    return rng.choice(fresh)


def problems(place_types: set[str], periods: set[str], roles: set[str]) -> list[str]:
    bad = []
    for s in R.get("slots") or []:
        if s.get("when") not in periods:
            bad.append(f"routines.yaml slot: '{s.get('when')}' is not a period of the day")
        if s.get("where") not in place_types:
            bad.append(f"routines.yaml slot: '{s.get('where')}' is not a kind of place")
    for role in (R.get("roles") or {}):
        if role not in roles:
            bad.append(f"routines.yaml roles: '{role}' is not a role")
    for k, v in (R.get("doings") or {}).items():
        if k != "default" and k not in place_types:
            bad.append(f"routines.yaml doings: '{k}' is not a kind of place")
        if not v or len(v) < 3:
            bad.append(f"routines.yaml doings.{k}: three or more")
    if not (R.get("doings") or {}).get("default"):
        bad.append("routines.yaml doings: needs a default list")
    return bad

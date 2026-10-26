"""Which god a place follows, and how its people sound when they speak of the faith. Lore only: no gameplay effect.

A city follows its own god. Everywhere else follows the god of the realm it sits in: the crown's lands follow Lethoria's Sun Warden,
a city's own lands follow that city. A place with no ruler follows the nearest city by walking time. The tone notes are suggestions
for the narrator, never lines to repeat (data/world/faith.yaml)."""
from __future__ import annotations

from pathlib import Path

import yaml

from engine import events, pulse

F = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "faith.yaml").read_text(encoding="utf-8"))
GODS, VOICES = F["gods"], F["voices"]
_cache: dict = {}


def seat(world, place_id: str) -> str | None:
    """The city whose god this place follows."""
    town = pulse.town_of(world, place_id)
    p = world.places.get(town)
    if not p:
        return None
    if p.type == "city" and town in GODS:
        return town
    region = world.regions.get(p.region)
    ruler = (region.ruled_by or "").lower() if region else ""
    if "crown" in ruler:
        return "lethoria"
    for city in GODS:
        if city in world.places and world.places[city].name.lower() == ruler:
            return city
    key = (id(world), town)
    if key not in _cache:
        dist = events.distances(world, town)
        near = sorted((dist.get(c, 10 ** 9), c) for c in GODS if c in world.places and world.places[c].type == "city")
        _cache[key] = near[0][1] if near else None
    return _cache[key]


def god_of(world, place_id: str) -> dict | None:
    s = seat(world, place_id)
    return GODS.get(s) if s else None


def voice_of(role: str) -> str:
    for voice, roles in VOICES["roles"].items():
        if role in roles:
            return voice
    return "folk"


def line(world, npc) -> str | None:
    """The prompt line telling this person which god their people follow and how they talk about it."""
    g = god_of(world, npc.location)
    if not g:
        return None
    voice = voice_of(npc.role)
    return (f"Your people follow {g['name']}. Cares about: {g['cares']}. Faithful draw on: {g['imagery']}. In daily life: {g['habits']}. "
            f"They swear: {g['swears']}. How you speak of it: {VOICES[voice]}. These are loose notes, not lines to quote - vary your own "
            "words, bring faith up only when it fits, and never lecture. Other peoples' gods are held to be real but not yours.")

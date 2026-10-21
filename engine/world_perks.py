"""Creation perks outside a fight (f211): the rules a character is born with that change how the world answers them. The engine
modules that own a system (engine/checks.py, engine/law.py, engine/standing.py, engine/combat.py) call the one function here that
belongs to them; the scenes call the rest through scenes/passive_hooks.py. Every number is in data/rules/perks.yaml (world:)."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "perks.yaml").read_text(encoding="utf-8"))["world"]


def owns(c, mid: str) -> bool:
    """Whether the character was born with (or otherwise holds) this world perk."""
    if c is None:
        return False
    from engine import pools
    return pools.mechanic(c, mid) is not None


def value(c, mid: str) -> float:
    from engine import pools
    return pools.mechanic(c, mid) or 0


# ---------- checks ----------

def gamble(c, degree: str) -> str:
    """All or Nothing: no middle. A partial success is a success; a failure stays a failure, and the scene makes it a bad one (bad())."""
    if degree == "partial" and owns(c, "all_or_nothing"):
        return "success"
    return degree


def bad(c, degree: str) -> bool:
    """Whether this failure is one of All or Nothing's bad ones: the scene then takes trust, standing or heat for it."""
    return degree == "failure" and owns(c, "all_or_nothing")


def best_hands(c, check: str, party: list[dict]) -> tuple[str, float]:
    """Borrowed Hands: the companion whose hands are better than yours at this check, and the points that lends.
    A hire's attributes come from their role's profile (data/rules/party.yaml); the player's from what they allocated."""
    if not owns(c, "borrowed_hands") or not party:
        return "", 0.0
    from core.rules import STATS
    from engine import checks
    from engine.party import P as PARTY
    attr = STATS[check].attribute
    names = attr if isinstance(attr, list) else [attr] if attr else []
    if not names:
        return "", 0.0
    mine = checks.attribute_value(c, check)
    best, who = mine, ""
    for m in party:
        if not m.get("active", True) or m.get("fallen"):
            continue
        prof = PARTY["profiles"].get(PARTY["roles"].get(m.get("role", ""), {}).get("profile", ""), {})
        theirs = max((prof.get(a, 0) for a in names), default=0)
        if theirs > best:
            best, who = theirs, m.get("name", "a companion").split()[0]
    return who, (best - mine) * checks.RULES["attribute_weight"]


# ---------- the law and the news ----------

def heat_today(c, rec: dict, day: int, decayed: int) -> int:
    """Nobody: heat never outlasts the day it was earned."""
    if owns(c, "nobody") and day > rec.get("day", day):
        return 0
    return decayed


def famous_here(c, world, origin: str, town: str) -> bool:
    """Famous: news from a town a road connects to this one arrives at once and in full."""
    if not owns(c, "famous") or origin == town:
        return False
    a, b = world.places.get(origin), world.places.get(town)
    if a is None or b is None:
        return False
    if hasattr(world, "road_between") and world.road_between(origin, town):
        return True
    return town in a.connects or origin in b.connects


def unseen(c) -> bool:
    """Nobody: news about you never moves anyone's standing - no one connects it to the face in front of them."""
    return owns(c, "nobody")


# ---------- gear and the body ----------

def fitted(c, item) -> bool:
    """Shaped to You: armor the player made themselves carries no weight penalty on them."""
    return bool(item.source == "your own work" and owns(c, "shaped_to_you"))


def gift_mechanics(c) -> dict[str, float]:
    """Symbiosis: the beast's gift the character carries from a meal of their own hunt, until they sleep."""
    g = c.gift if owns(c, "symbiosis") else {}
    return dict(g.get("mechanics") or {}) if g else {}


def gift_for(family: str) -> dict[str, float]:
    """What a meal of this family gives (data/world/families.yaml gift:, else the default)."""
    from engine import behaviors
    fam = behaviors.FAMILIES.get(family, {}) if family else {}
    return dict(fam.get("gift") or P["symbiosis"]["default_gift"])

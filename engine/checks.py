"""Checks: uncertain things outside combat - reading people, persuading, sneaking, recalling lore, performing.

The engine decides the outcome; the narrator and NPCs are told it and must honor it.
"""

import random
from pathlib import Path

import yaml

from core.models import Character
from core.rules import STATS
from engine import streams

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "data" / "rules" / "checks.yaml").read_text(encoding="utf-8"))
CHECKS = ("insight", "persuasion", "intimidation", "deception", "stealth", "perception", "lore", "performance")
SOCIAL = ("persuasion", "intimidation", "deception")


def attribute_value(c: Character, check: str) -> float:
    """The attribute a check runs on: what the character allocated. Points that gear adds never count for a check;
    gear helps a check only through a bonus that names it (see gear_points)."""
    attr = STATS[check].attribute
    names = attr if isinstance(attr, list) else [attr] if attr else []
    return max((getattr(c.attributes, a) for a in names), default=RULES["attribute_center"])


def passive_points(c: Character, check: str, active_triggers: set[str]) -> float:
    return sum(p.magnitude for p in c.passives
               if not p.mechanic and p.modifies and p.modifies.value == check and p.trigger.value in active_triggers)


def gear_points(c: Character, check: str, active_triggers: set[str]) -> float:
    """Points that worn gear gives this specific check (a '+20 stealth' ring is 20). Attribute points never come through here."""
    from engine import items as _items
    total = 0.0
    for item in c.equipment.values():
        for e in _items.effects(item):
            if e.modifies == check and e.trigger in active_triggers:
                total += e.magnitude
    return total


def chance(c: Character, check: str, active_triggers: set[str], npc=None,
           extra: list[tuple[str, float]] = ()) -> tuple[float, list[str]]:
    """Percent chance, and the reasons (for debug)."""
    why = []
    value = RULES["base"]
    attr_part = (attribute_value(c, check) - RULES["attribute_center"]) * RULES["attribute_weight"]
    value += attr_part
    why.append(f"attribute {attr_part:+.0f}")
    passive = passive_points(c, check, active_triggers)
    if passive:
        value += passive
        why.append(f"passives {passive:+.0f}")
    worn = gear_points(c, check, active_triggers)
    if worn:
        value += worn
        why.append(f"gear {worn:+.0f}")
    for label, amount in extra:
        value += amount
        why.append(f"{label} {amount:+.0f}")
    if getattr(c, "hunger", 0) or getattr(c, "fatigue", 0):
        from engine import needs
        worn_down = needs.penalties(c)["checks"]
        if worn_down:
            value += worn_down
            why.append(f"hunger and fatigue {worn_down:+.0f}")
    tutored = getattr(c, "trained", {}).get(check, 0)
    if tutored:
        value += tutored
        why.append(f"training {tutored:+d}")
    if npc is not None:
        tw = RULES["trust_weight"].get(check, 0)
        if tw:
            t = (npc.trust - 50) * tw
            value += t
            why.append(f"trust {t:+.0f}")
        for trait in npc.traits:
            mod = RULES["traits"].get(trait, {}).get(check, 0)
            if mod:
                value += mod
                why.append(f"{trait} {mod:+d}")
    return max(RULES["min"], min(RULES["max"], value)), why


def roll(odds: float, rng: random.Random | None = None, c: Character | None = None) -> tuple[str, int]:
    """The die. With the character given, the perks that change what a roll means act here (All or Nothing: no partials)."""
    r = (rng or streams.get("checks")).randint(1, 100)
    margin = odds - r
    degree = "failure"
    for name, need in RULES["degrees"].items():
        if margin >= need:
            degree = name
            break
    if c is not None:
        from engine import world_perks
        degree = world_perks.gamble(c, degree)
    return degree, r


def label(check: str, degree: str) -> str:
    return f"{check.capitalize()} — {degree}"

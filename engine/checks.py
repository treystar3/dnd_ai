"""Checks: uncertain things outside combat - reading people, persuading, sneaking, recalling lore, performing.

The engine decides the outcome; the narrator and NPCs are told it and must honor it.
"""

import random
from pathlib import Path

import yaml

from core.models import Character
from core.rules import STATS
from engine import pools

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "data" / "rules" / "checks.yaml").read_text(encoding="utf-8"))
CHECKS = ("insight", "persuasion", "intimidation", "deception", "stealth", "perception", "lore", "performance")
SOCIAL = ("persuasion", "intimidation", "deception")


def attribute_value(c: Character, check: str) -> float:
    attr = STATS[check].attribute
    names = attr if isinstance(attr, list) else [attr] if attr else []
    from engine import stats as _stats
    gear = _stats.gear_attributes(c) if c.equipment else {}
    return max((_stats.effective(c, a, gear) for a in names), default=RULES["attribute_center"])


def chance(c: Character, check: str, active_triggers: set[str], npc=None,
           extra: list[tuple[str, float]] = ()) -> tuple[float, list[str]]:
    """Percent chance, and the reasons (for debug)."""
    why = []
    value = RULES["base"]
    attr_part = (attribute_value(c, check) - RULES["attribute_center"]) * RULES["attribute_weight"]
    value += attr_part
    why.append(f"attribute {attr_part:+.0f}")
    passive = sum(p.magnitude for p in c.passives
                  if not p.mechanic and p.modifies and p.modifies.value == check and p.trigger.value in active_triggers)
    if passive:
        value += passive
        why.append(f"passives {passive:+.0f}")
    for label, amount in extra:
        value += amount
        why.append(f"{label} {amount:+.0f}")
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


def roll(odds: float, rng: random.Random | None = None) -> tuple[str, int]:
    r = (rng or random).randint(1, 100)
    margin = odds - r
    for degree, need in RULES["degrees"].items():
        if margin >= need:
            return degree, r
    return "failure", r


def label(check: str, degree: str) -> str:
    return f"{check.capitalize()} — {degree}"

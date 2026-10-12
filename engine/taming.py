"""Taming: a companion class binds a wild creature it has beaten down. Pure rules - the model only describes the moment.

Rules live in data/rules/taming.yaml.
"""

import uuid
from pathlib import Path

import yaml

from core.models import Companion

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "taming.yaml").read_text(encoding="utf-8"))

KIND = {"undead": "undead", "elemental": "elemental", "construct": "construct", "fey": "spirit", "celestial": "spirit"}


def cap(level: int) -> int:
    return T["cap"]["base"] + level // T["cap"]["per_levels"]


def active_slots(level: int) -> int:
    return T["active"]["base"] + level // T["active"]["per_levels"]


def strongest(fighters: list, level: int) -> list:
    """The companions that take the field: the strongest few, by health times damage."""
    return sorted(fighters, key=lambda f: f.max_hp * f.weapon_damage, reverse=True)[:active_slots(level)]


def tamed(character) -> list[Companion]:
    return [c for c in character.companions if c.source == "tamed"]


def check(character, enemy, creature) -> str:
    """Why this creature can't be tamed right now, or '' when it can."""
    if not character.uses_companions:
        return "You have no gift for binding wild creatures."
    if creature is None or creature.unique or enemy.rank in T["refuse_ranks"]:
        return f"{enemy.name.capitalize()} cannot be bound."
    if creature.category not in T["categories"]:
        return f"{enemy.name.capitalize()} is not something that can be tamed."
    if enemy.level > character.level + T["level_margin"]:
        return f"{enemy.name.capitalize()} is far too strong for you to bind."
    if enemy.hp > enemy.max_hp * T["max_health_share"]:
        return f"{enemy.name.capitalize()} is still too strong and wild - wear it down first."
    if len(tamed(character)) >= cap(character.level):
        return "You already keep as many tamed companions as you can lead - release one first."
    return ""


def chance(character, enemy, creature) -> float:
    from engine import stats as _stats
    best = max(_stats.effective(character, "wisdom"), _stats.effective(character, "charisma"))
    p = (T["base_chance"] + T["per_attribute"] * best - T["rarity_penalty"].get(creature.rarity, 0)
         - T["size_penalty"].get(creature.size, 0))
    return max(T["min_chance"], min(T["max_chance"], p))


def role_of(creature) -> str:
    prof = creature.profile or {}
    top = max(("strength", "dexterity", "constitution"), key=lambda a: prof.get(a, 10))
    return {"strength": "striker", "dexterity": "scout", "constitution": "guardian"}[top]


def bind(character, creature, enemy_name: str) -> Companion:
    comp = Companion(id=f"{creature.id}_{uuid.uuid4().hex[:4]}", name=creature.name, creature=creature.id,
                     kind=KIND.get(creature.category, "beast"), role=role_of(creature), level=character.level,
                     description=f"A {creature.name.lower()} tamed in the wild.", source="tamed")
    character.companions.append(comp)
    return comp


def release(character, words: str):
    """Let a tamed companion go. Returns it, or None."""
    low = words.lower()
    pool = tamed(character)
    pick = next((c for c in pool if c.name.lower() in low or c.creature.replace("_", " ") in low), None) or (pool[-1] if pool else None)
    if pick:
        character.companions.remove(pick)
    return pick


# ---------- Bind a Beast (the taught-only ability; see data/rules/taming.yaml, bind) ----------

def binder(character):
    """The character's Bind a Beast ability, or None."""
    return next((a for a in character.actives if a.field_use == "bind_beast"), None)


def bind_check(character, enemy, creature) -> str:
    """Why this creature can't be bound with the ability, or '' when it can. A hurt creature is easier; an unhurt one is allowed."""
    B = T["bind"]
    comp = character.uses_companions
    if creature is None or creature.unique or enemy.rank in T["refuse_ranks"]:
        return f"{enemy.name.capitalize()} cannot be bound."
    if creature.category not in T["categories"]:
        return f"{enemy.name.capitalize()} is not something that can be bound."
    if not comp and creature.rarity in B["refuse_rarity"]:
        return f"{enemy.name.capitalize()} is far beyond anything you could bind."
    if enemy.level > character.level + (T["level_margin"] if comp else B["level_margin"]):
        return f"{enemy.name.capitalize()} is too strong for you to bind."
    if len(tamed(character)) >= cap(character.level):
        return "You already keep as many bound creatures as you can lead - release one first."
    return ""


def bind_chance(character, enemy, creature, tier) -> float:
    """The taming odds, less a penalty for a creature that is not hurt, and never above what the ability's tier allows."""
    B = T["bind"]
    p = chance(character, enemy, creature)
    share = enemy.hp / max(1.0, enemy.max_hp)
    if share > B["healthy_share"]:
        p -= B["unhurt_penalty"] * (share - B["healthy_share"]) / (1 - B["healthy_share"])
    return max(T["min_chance"], min(B["ceiling"][getattr(tier, "value", tier)], p))

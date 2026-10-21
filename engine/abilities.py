"""Converts LLM proposals into authoritative Abilities and Passives.

All numbers come from these tables. The LLM never supplies a number.
Values are placeholders until combat and the action system exist; tune them here only.
"""

import re

from core.models import (
    POOL_TARGETS,
    Ability,
    Effect,
    Passive,
    Summoned,
    PowerTier,
    Resource,
    UseContext,
    Trigger,
)
from engine import field
from llm.contracts import ActiveProposal, PassiveProposal

TIER_COST = {PowerTier.LIGHT: 5, PowerTier.MODERATE: 10, PowerTier.HEAVY: 18}
TIER_COOLDOWN = {PowerTier.LIGHT: 0, PowerTier.MODERATE: 1, PowerTier.HEAVY: 3}

PASSIVE_MAGNITUDE = {PowerTier.LIGHT: 10, PowerTier.MODERATE: 20}
ALWAYS_ON_SCALE = 0.5


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _cooldown(p: ActiveProposal) -> int:
    """By tier - except a movement ability, whose cooldown is its kind's (data/rules/movement.yaml)."""
    if p.effect == Effect.BUFF and getattr(p, "buff", ""):
        from engine import ability_traits as AT
        return AT.buff_rounds(p.buff) + int(AT.T.get("buff_rest", 3))     # longer than it lasts: cast at the best moment (f247)
    if p.effect == Effect.MOBILITY and getattr(p, "movement", ""):
        from engine import movement
        k = movement.KINDS.get(p.movement)
        if k:
            return int(k["cooldown"])
    return TIER_COOLDOWN[p.tier]


def materialize_active(p: ActiveProposal) -> Ability:
    summoned = Summoned(name=p.summons.name.strip(), description=p.summons.description.strip()) if p.summons else None
    use = field.function_for(p)
    context = p.context
    if context != UseContext.COMBAT and not use and not field.SELF_FUNCTIONED.get(p.effect.value):
        context = UseContext.COMBAT        # nothing it could do outside a fight: keep it a combat ability
    return Ability(
        id=slugify(p.name),
        name=p.name.strip(),
        description=p.description.strip(),
        effect=p.effect,
        tier=p.tier,
        reach=p.reach,
        resource=Resource(p.resource),
        context=context,
        tags=p.tags,
        cost=TIER_COST[p.tier],
        cooldown=_cooldown(p),
        summoned=summoned, summon_form=(getattr(p, "summon_form", "") or "striker") if p.effect == Effect.SUMMON else "",
        rider=p.rider, shape=p.shape, buff=p.buff, buff_stat=p.buff_stat, command=p.command, channel=p.channel, movement=p.movement,
        heal_form=getattr(p, "heal_form", ""), element=getattr(p, "element", ""),
        expressions=list(getattr(p, "expressions", []) or []), spell_form=getattr(p, "spell_form", ""),
        power=getattr(p, "power", 0), cost_percent=getattr(p, "cost_percent", 0), cast_turns=getattr(p, "cast_turns", 0),
        martial_form=getattr(p, "martial_form", ""), hits=getattr(p, "hits", 0), maneuver=getattr(p, "maneuver", ""),
        field_use=use if context != UseContext.COMBAT else "",
    )


def materialize_passive(p: PassiveProposal, offered: dict | None = None) -> Passive:
    tier = PowerTier(p.tier)
    if p.kind == "mechanic":
        from core.rules import FamilyOption
        option = (offered or {}).get(p.mechanic) or FamilyOption(mechanic=p.mechanic)
        index = 0 if tier == PowerTier.LIGHT else 1
        return Passive(id=slugify(p.name), name=p.name.strip(), description=p.description.strip(), tier=tier,
                       tags=p.tags, mechanic=option.mechanic, when=option.when, value=option.strength(index))
    trigger = Trigger.ALWAYS if p.modifies in POOL_TARGETS else p.trigger
    magnitude = PASSIVE_MAGNITUDE[tier]
    if trigger == Trigger.ALWAYS:
        magnitude = round(magnitude * ALWAYS_ON_SCALE)
    return Passive(
        id=slugify(p.name),
        name=p.name.strip(),
        description=p.description.strip(),
        modifies=p.modifies,
        trigger=trigger,
        tier=tier,
        tags=p.tags,
        magnitude=magnitude,
    )

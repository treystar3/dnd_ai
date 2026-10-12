"""Converts LLM proposals into authoritative Abilities, Passives and Companions.

All numbers come from these tables. The LLM never supplies a number.
Values are placeholders until combat and the action system exist; tune them here only.
"""

import re

from core.models import (
    POOL_TARGETS,
    Ability,
    CompanionRole,
    CompanionTemplate,
    Passive,
    PowerTier,
    Resource,
    UseContext,
    Trigger,
)
from engine import field
from llm.contracts import ActiveProposal, CompanionProposal, PassiveProposal

TIER_COST = {PowerTier.LIGHT: 5, PowerTier.MODERATE: 10, PowerTier.HEAVY: 18}
TIER_COOLDOWN = {PowerTier.LIGHT: 0, PowerTier.MODERATE: 1, PowerTier.HEAVY: 3}

ROLE_STATS = {
    CompanionRole.STRIKER: {"health": 10, "damage": 6},
    CompanionRole.GUARDIAN: {"health": 20, "damage": 3},
    CompanionRole.SCOUT: {"health": 8, "damage": 2},
    CompanionRole.SUPPORT: {"health": 12, "damage": 2},
}
COMPANION_TIER_SCALE = {PowerTier.LIGHT: 1.0, PowerTier.MODERATE: 1.5, PowerTier.HEAVY: 2.0}

PASSIVE_MAGNITUDE = {PowerTier.LIGHT: 10, PowerTier.MODERATE: 20}
ALWAYS_ON_SCALE = 0.5


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def materialize_companion(p: CompanionProposal, tier: PowerTier) -> CompanionTemplate:
    base = ROLE_STATS[p.role]
    scale = COMPANION_TIER_SCALE[tier]
    return CompanionTemplate(
        id=slugify(p.name),
        name=p.name.strip(),
        description=p.description.strip(),
        kind=p.kind,
        role=p.role,
        tier=tier,
        health=round(base["health"] * scale),
        damage=round(base["damage"] * scale),
    )


def materialize_active(p: ActiveProposal) -> Ability:
    companion = materialize_companion(p.summons, p.tier) if p.summons else None
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
        cooldown=TIER_COOLDOWN[p.tier],
        companion=companion,
        rider=p.rider, shape=p.shape, buff=p.buff, buff_stat=p.buff_stat, command=p.command,
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

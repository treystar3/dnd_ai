"""Health, stamina and mana: maximums from attributes and level, and recovery over time.

Formulas and tuning live in data/rules/pools.yaml.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from core.models import Character, ModifierTarget, Trigger
from core.rules import ATTRIBUTES

RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "rules" / "pools.yaml"
POOLS = ("health", "stamina", "mana")


class PoolRule(BaseModel):
    base: float
    per_level: float = 0
    attributes: dict[str, float]
    modifier: str


class PoolRules(BaseModel):
    pools: dict[str, PoolRule]
    regen_per_hour: dict[str, float]
    mana_casting: dict


def _load() -> PoolRules:
    rules = PoolRules(**yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")))
    problems = []
    for name in POOLS:
        if name not in rules.pools or name not in rules.regen_per_hour:
            problems.append(f"pools.yaml must define '{name}' under pools and regen_per_hour")
            continue
        for attr in rules.pools[name].attributes:
            if attr not in ATTRIBUTES:
                problems.append(f"pools.yaml {name}: unknown attribute '{attr}'")
        if rules.pools[name].modifier not in {m.value for m in ModifierTarget}:
            problems.append(f"pools.yaml {name}: unknown modifier '{rules.pools[name].modifier}'")
    if problems:
        raise ValueError("\n".join(problems))
    return rules


RULES = _load()


def _bonus_parts(c: Character, target: str, triggers: set[str]) -> tuple[float, float]:
    """(percentage as a fraction, flat amount): passives and percentage gear give the first, flat gear stats the second."""
    from engine import items, sets
    pct = sum(p.magnitude for p in c.passives
              if not p.mechanic and p.modifies.value == target and p.trigger.value in triggers)
    flat = 0.0
    gear = [e for item in c.equipment.values() for e in items.effects(item)] + sets.effects(c.equipment)
    for e in gear:
        if e.modifies == target and e.trigger in triggers:
            if e.flat:
                flat += e.magnitude
            else:
                pct += e.magnitude
    return pct / 100, flat


def _passive_bonus(c: Character, target: str, triggers: set[str]) -> float:
    return _bonus_parts(c, target, triggers)[0]


def reference_pool(pool: str, level: int) -> float:
    """The size of a typical character's pool at this level. Flat gear bonuses are shares of it."""
    if pool == "mana":
        return reference_mana(level)
    from engine import items
    rule = RULES.pools[pool]
    a = items.RULES["flat_gear"]["attribute"]
    attr = a["start"] + a["per_level"] * (max(1, level) - 1)
    return rule.base + rule.per_level * (max(1, level) - 1) + sum(w * attr for w in rule.attributes.values())


MENTAL = ("intelligence", "wisdom", "charisma")


def casting_attribute(c: Character) -> str:
    """The attribute a character's spells and mana come from: their own choice, else their first mental primary, else intelligence."""
    if c.casting_attribute in MENTAL:
        return c.casting_attribute
    return next((a for a in c.primary_attributes if a in MENTAL), "intelligence")


def reference_mana(level: int) -> float:
    """The mana pool of a dedicated caster at this level. Ability costs are shares of this, so they do not shrink with a small pool."""
    m = RULES.mana_casting
    r = m["reference"]
    raw = (RULES.pools["mana"].base + RULES.pools["mana"].per_level * (max(1, level) - 1)
           + m["cast_weight"] * (r["attribute_start"] + r["attribute_per_level"] * (max(1, level) - 1)) + m["other_weight"] * r["other_attribute"])
    return raw


def maximum(c: Character, pool: str) -> int:
    from engine import stats
    rule = RULES.pools[pool]
    gear = stats.gear_attributes(c) if c.equipment else {}
    at = lambda a: stats.effective(c, a, gear)
    raw = (rule.base + rule.per_level * (max(1, c.level) - 1)
           + sum(at(a) * w for a, w in rule.attributes.items()))
    if pool == "mana":
        m = RULES.mana_casting
        cast = casting_attribute(c)
        others = max(at(a) for a in MENTAL if a != cast)
        raw += m["cast_weight"] * at(cast) + m["other_weight"] * others
    pct, flat = _bonus_parts(c, rule.modifier, {Trigger.ALWAYS.value})
    return max(1, round(raw * (1 + pct) + flat))


def snapshot(c: Character) -> dict[str, int]:
    return {p: maximum(c, p) for p in POOLS}


def apply_growth(c: Character, before: dict[str, int]) -> None:
    """When maximums rise, current values rise by the same amount."""
    for pool in POOLS:
        gained = maximum(c, pool) - before[pool]
        if gained > 0:
            setattr(c, pool, current(c, pool) + gained)


def current(c: Character, pool: str) -> float:
    value = getattr(c, pool)
    return maximum(c, pool) if value is None else min(value, maximum(c, pool))


def fill_missing(c: Character) -> None:
    for pool in POOLS:
        if getattr(c, pool) is None:
            setattr(c, pool, float(maximum(c, pool)))


def recover(c: Character, minutes: int, in_combat: bool = False, conditions: set[str] | None = None) -> None:
    """Restore pools for time passing. Recovery bonuses apply when their trigger is true right now."""
    if in_combat or minutes <= 0:
        return
    triggers = {Trigger.ALWAYS.value, Trigger.OUT_OF_COMBAT.value} | (conditions or set())
    speed = (1 + _passive_bonus(c, "recovery", triggers)) * (1 + (mechanic(c, "inner_calm") or 0) / 100)
    shared = (mechanic(c, "shared_rest") or 0) / 100 if "with_companion_present" in triggers else 0
    for pool in POOLS:
        top = maximum(c, pool)
        pool_speed = speed * (1 + shared)
        if pool == "mana":
            pool_speed *= 1 + (mechanic(c, "mana_well") or 0) / 100
            if "at_night" in triggers and mechanic(c, "night_bound") is not None:
                pool_speed *= 2
        gained = top * RULES.regen_per_hour[pool] * pool_speed * minutes / 60
        setattr(c, pool, min(float(top), current(c, pool) + gained))


def mechanic(c: Character, mechanic_id: str) -> float | None:
    """Total value of a passive mechanic the character has, or None if they don't have it."""
    found = [p.value for p in c.passives if p.mechanic == mechanic_id]
    from engine import items
    for item in c.equipment.values():
        le = items.LEGENDARY.get(item.legendary_effect)
        if le and le.world == mechanic_id:
            found.append(le.value)
        found += [v for k, v in ((item.trait or {}).get("world") or {}).items() if k == mechanic_id]
    found += [comp.perks[mechanic_id] for comp in c.companions if mechanic_id in comp.perks]
    from engine import sets
    if mechanic_id in sets.world(c.equipment):
        found.append(sets.world(c.equipment)[mechanic_id])
    return sum(found) if found else None

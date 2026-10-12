"""What a new character wakes up with: a rudimentary weapon (or a companion for companion classes) and some coin.

The model only chooses from lists. The engine builds the items, the companion and the purse.
"""

import re


from core.models import Character, Companion, Effect
from engine import items, money
from llm.contracts import StartingKit
from llm.gateway import generate
from world.loader import World

KIT_SYSTEM = """You equip a new character in a fantasy role-playing game with the plainest possible starting gear.
For an ordinary class, choose the one weapon id from WEAPON OPTIONS that best fits how they fight AND uses one of
  their STRONGEST ATTRIBUTES - a weapon driven by a weak attribute is nearly useless to them.
  Casters use a focus (wand, staff, charm), performers an instrument, archers a bow or sling,
  and martial artists who fight bare-handed use hand wraps.
For a class that relies on companions, instead choose one creature id from COMPANION OPTIONS that fits their
  theme, and give it a short fitting name. Leave weapon empty in that case.
Respond only with JSON matching the schema."""

COMPANION_CATEGORIES = {"beast", "fey", "plant", "elemental", "celestial", "dragon", "construct", "undead"}


def weapon_options() -> list[items.BaseItem]:
    return [b for b in items.CATALOG.values() if b.is_weapon and not b.requires]


def companion_options(world: World) -> list:
    return [c for c in world.bestiary.values()
            if c.category in COMPANION_CATEGORIES and c.levels[0] <= 2 and not c.unique
            and c.roster and c.rarity in ("common", "uncommon") and "cracked_plains" not in c.biomes]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def give_starting_kit(c: Character, class_text: str, uses_companions: bool, world: World) -> str:
    """Equip the character. Returns a plain description of what they received, for the narrator."""
    rules = items.RULES
    c.coins += money.to_smallest(**rules["starting_coins"])
    c.kit_given = True
    purse = money.fmt(money.to_smallest(**rules["starting_coins"]))

    summon = next((a for a in c.actives if a.effect == Effect.SUMMON and a.companion), None)
    if uses_companions and summon:
        t = summon.companion
        c.companions.append(Companion(id=t.id, name=t.name, kind=t.kind.value, role=t.role.value,
                                      description=t.description, source=f"summoned with {summon.name}",
                                      tier=t.tier.value, health=t.health, damage=t.damage))
        return f"{t.name}, the companion they summon, is at their side, and they carry a small purse of {purse}."

    weapons = weapon_options()
    creatures = companion_options(world) if uses_companions else []
    attrs = sorted(((a, getattr(c.attributes, a)) for a in type(c.attributes).model_fields), key=lambda x: -x[1])
    lines = [f"CLASS: {class_text}", f"RELIES ON COMPANIONS: {'yes' if uses_companions else 'no'}",
             f"STRONGEST ATTRIBUTES: {', '.join(f'{a} {v}' for a, v in attrs[:2])}"]
    if c.casting_attribute:
        lines.append(f"MAGIC USES: {c.casting_attribute} - a caster's focus should use this attribute "
                     "(wand: intelligence, charm: wisdom, lute: charisma).")
    if uses_companions:
        lines.append("COMPANION OPTIONS:\n" + "\n".join(f"  {b.id}: {b.name} ({b.category}, {b.size})" for b in creatures))
    else:
        lines.append("WEAPON OPTIONS:\n" + "\n".join(f"  {b.id}: {b.name} ({b.reach}, {'/'.join(b.attributes)}, {', '.join(b.tags)})" for b in weapons))
    kit = generate(
        "starting_kit", KIT_SYSTEM, "\n".join(lines), StartingKit, temperature=0.3, max_tokens=200,
        validation_context={"needs_companion": uses_companions, "weapons": [b.id for b in weapons],
                            "companions": [b.id for b in creatures]},
    )
    if uses_companions:
        creature = world.bestiary[kit.companion]
        name = kit.companion_name.strip()
        c.companions.append(Companion(id=_slug(name) or creature.id, name=name, creature=creature.id,
                                      kind=creature.category, description=f"a {creature.name.lower()}",
                                      source="bonded before the player woke"))
        return f"A {creature.name.lower()} named {name} is with them, bonded to them, and they carry a small purse of {purse}."
    weapon = items.make(kit.weapon, rules["starting_rarity"])
    c.equipment[items.base_of(weapon).slot] = weapon
    return f"A {weapon.name} lies beside them, and they carry a small purse of {purse}."

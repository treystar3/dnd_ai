"""Enchanting: binding a creature material's essence, or a general enchantment, into an item.

Rules in data/rules/enchanting.yaml. Material enchantments are built from materials.yaml automatically.
"""

import math
import random
from pathlib import Path

import yaml
from pydantic import BaseModel

from core.models import Character, Enchantment, Item, ItemProperty
from engine import items

RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "enchanting.yaml").read_text(encoding="utf-8"))


class Option(BaseModel):
    id: str
    name: str
    suffix: str
    applies: str                     # weapon | armor | any
    effects: list[ItemProperty] = []
    flags: dict[str, float] = {}
    reagent: str = ""                # raw material id, if one is consumed
    fee_multiplier: float = 1.0


def _material_options() -> dict[str, Option]:
    from world.loader import load_world
    bestiary = load_world().bestiary
    out = {}
    for m in items.MATERIALS.values():
        if not m.drops_from or not (m.any or m.weapon or m.armor or m.weapon_flags or m.armor_flags):
            continue
        first = bestiary.get(m.drops_from[0])
        suffix = RULES["names"].get(m.id) or f"of the {first.name if first else m.name.title()}"
        for kind, effects, flags in (("weapon", m.any + m.weapon, m.weapon_flags), ("armor", m.any + m.armor, m.armor_flags)):
            if effects or flags:
                oid = f"{m.id}_{kind}"
                out[oid] = Option(id=oid, name=f"{m.name} essence", suffix=suffix, applies=kind, reagent=m.id, fee_multiplier=RULES["material_fee"][m.rarity],
                                  effects=[ItemProperty(**e.model_dump()) for e in effects], flags=dict(flags))
    return out


def _general_options() -> dict[str, Option]:
    out = {}
    for g in RULES["general"]:
        out[g["id"]] = Option(id=g["id"], name=g["name"], suffix=g["suffix"], applies=g["applies"],
                              fee_multiplier=g.get("fee_multiplier", 1.0),
                              effects=[ItemProperty(**e) for e in g["effects"]])
    return out


OPTIONS: dict[str, Option] = {**_general_options(), **_material_options()}


def slots(item: Item) -> int:
    return RULES["slots"].get(item.rarity, 0)


DISCOUNT = {"percent": 0}   # set from the player's passives (arcane appraiser) before showing or paying fees


def fee(item: Item, option: Option) -> int:
    used = len(item.enchantments)
    from engine import quests
    return math.ceil(quests.contract_reward(item.item_level) * RULES["fee_share"] * option.fee_multiplier
                     * (1 + RULES["extra_per_used"] * used) * (1 - DISCOUNT["percent"] / 100))


def success_chance(item: Item) -> int:
    return max(5, RULES["success"] - RULES["penalty_per_used"] * len(item.enchantments))


def fits(item: Item) -> set[str]:
    """Every concrete stat this piece of gear could roll: the roll list for its kind, or the lane of a ring or amulet."""
    from engine import accessories, elements, loot
    if accessories.is_accessory(item):
        names = list(accessories.A["lanes"][(item.trait or {}).get("lane", "")]["stats"]) if item.trait else []
    else:
        names = loot.gear_stats(item)
    out = set()
    for n in names:
        if n in loot.TOKENS:
            out |= {f"{e}_{'resistance' if loot.TOKENS[n] == 'resistance' else 'damage'}" for e in elements.ELEMENTS}
        else:
            out.add(n)
    return out


def usable_effects(c: Character | None, item: Item, option: Option) -> list[ItemProperty]:
    """The part of an option that makes sense on this item: stats it can roll, not already enchanted onto it, companion stats only for companion keepers."""
    from engine import loot
    allowed = fits(item)
    taken = {e.modifies for en in item.enchantments for e in en.effects}      # a stat can add to a roll, but not be enchanted twice
    keep = loot.keeps_companions(c) if c is not None else True
    return [e for e in option.effects if e.modifies in allowed and e.modifies not in taken
            and (keep or not e.modifies.startswith("companion_"))]


def available(c: Character, item: Item) -> list[Option]:
    from engine import accessories
    b = items.base_of(item)
    kind = "weapon" if b.is_weapon else "armor"
    have = {i.material for i in c.inventory if i.base == "raw_material"}
    taken = {e.id for e in item.enchantments}
    out = []
    for o in OPTIONS.values():
        if o.applies not in (kind, "any") or o.id in taken or (o.reagent and o.reagent not in have):
            continue
        if not usable_effects(c, item, o) and not (o.flags and not accessories.is_accessory(item)):
            continue
        out.append(o)
    return out


def check(c: Character, item: Item, option: Option) -> str | None:
    if items.base_of(item).slot == "none":
        return "Raw materials can't be enchanted."
    if len(item.enchantments) >= slots(item):
        return f"The {items.display_name(item)} can't hold any more enchantments ({slots(item)} for {item.rarity} items)."
    if c.coins < fee(item, option):
        return "You can't afford the enchanter's fee."
    if option.reagent and not any(i.base == "raw_material" and i.material == option.reagent for i in c.inventory):
        return f"You need a raw {items.MATERIALS[option.reagent].name}."
    return None


def enchant(c: Character, item: Item, option: Option, rng: random.Random) -> tuple[bool, str]:
    """Pay, consume the reagent, and roll. Returns (succeeded, message)."""
    problem = check(c, item, option)
    if problem:
        return False, problem
    cost = fee(item, option)
    chance = success_chance(item)
    c.coins -= cost
    if option.reagent:
        reagent = next(i for i in c.inventory if i.base == "raw_material" and i.material == option.reagent)
        c.inventory = [i for i in c.inventory if i.uid != reagent.uid]
    if rng.uniform(0, 100) >= chance:
        return False, "The binding fails. The reagent is spent and the fee is gone."
    from engine import accessories
    flags = {} if accessories.is_accessory(item) else option.flags
    item.enchantments.append(Enchantment(id=option.id, name=option.name, suffix=option.suffix,
                                         effects=usable_effects(c, item, option), flags=flags))
    if len(item.enchantments) == 1 and not item.title and option.suffix and option.suffix not in item.name:
        item.name = f"{item.name} {option.suffix}"
    if item.title:
        return True, f"The enchantment takes. {items.display_name(item)} now carries {option.name}."
    return True, f"The enchantment takes. Your item is now the {items.display_name(item)}."

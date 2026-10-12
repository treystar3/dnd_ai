"""Reforge and salvage: remaking the rolls on a piece of gear, and breaking gear down into raw material (rules in data/rules/field.yaml)."""
import random

from core.models import Item, ItemProperty
from engine import crafting, enchanting, items, loot
from engine.field import F


def slot_ok(item: Item) -> bool:
    b = items.CATALOG.get(item.base)
    return bool(b and not item.good and item.base != "raw_material" and b.slot not in ("none", "ring", "neck"))


def reforge_problem(item: Item) -> str | None:
    if not slot_ok(item):
        return "Only a worn or carried piece of weapon or armor can be reforged."
    if item.rarity == "legendary" or item.legendary_effect:
        return f"The {items.display_name(item)} is too old and strange to be remade."
    if item.reforged:
        return f"The {items.display_name(item)} has been reforged once already; the metal will not take it again."
    if len(item.properties) < 2:
        return f"The {items.display_name(item)} has too few rolls to reforge."
    return None


def prop_text(item: Item, p: ItemProperty) -> str:
    e = items.to_flat([items.Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude)], item.item_level)[0]
    return items._describe_effect(e)


def reroll(item: Item, keep: int, rng: random.Random) -> list[ItemProperty]:
    """A new set of rolls: the one at index `keep` stays, every other is rolled afresh (never the same stat as the kept one)."""
    kept = item.properties[keep]
    stats = [s for s in loot.gear_stats(item) if s != kept.modifies]
    for _ in range(6):
        fresh = loot.roll_properties(item.rarity, rng, count=len(item.properties) - 1, only=stats)
        if len(fresh) == len(item.properties) - 1 and all(f.modifies != kept.modifies for f in fresh):
            break
    out = [kept] + fresh
    return out


def salvage_problem(item: Item) -> str | None:
    if not slot_ok(item):
        return "Only weapons and armor can be broken down."
    if item.rarity == "legendary" or item.legendary_effect or item.title:
        return f"The {items.display_name(item)} is too precious to break down."
    return None


def material_for(item: Item) -> str | None:
    if item.material in items.MATERIALS:
        return item.material
    b = items.base_of(item)
    fits = [m for m in items.MATERIALS.values() if m.family == b.family and m.rarity == "common"]
    fits.sort(key=lambda m: (not (m.levels[0] <= item.item_level <= m.levels[1]), m.levels[0]))
    return fits[0].id if fits else None


def salvage_yield(item: Item) -> list[tuple[str, int]]:
    """[(material id, pieces)] the item breaks down into: its own material, and the reagent of any enchantment on it."""
    mid = material_for(item)
    out = []
    if mid:
        units = max(1, round(crafting.units_for(items.base_of(item)) * F["salvage"]["share"]))
        out.append((mid, units))
    for en in item.enchantments:
        opt = enchanting.OPTIONS.get(en.id)
        if opt and opt.reagent in items.MATERIALS:
            out.append((opt.reagent, 1))
    return out

"""Loot from defeated enemies. The engine decides everything; the model only names rare+ items."""

import random

from core.models import Item, ItemProperty
from core.rules import STATS, TRIGGERS
from engine import combat, items

L = combat.RULES["loot"]


def roll_rarity(rng: random.Random) -> str:
    weights = L["rarity_weights"]
    return rng.choices(list(weights), weights=list(weights.values()))[0]


WEATHER = ["at_night", "in_daylight", "in_bad_weather"]
FIGHT = ["after_moving", "when_attacked", "while_defending", "first_round_of_combat", "after_defeating_foe"]   # never "against" a kind of enemy
# Which conditions make sense for which stat. A property rolled outside this table would read as nonsense
# ("+18% movement against celestials", "+10% persuasion in the arctic while performing").
FITS = {
    "damage":     FIGHT + ["at_low_health", "while_elevated"] + WEATHER,
    "accuracy":   [t for t in FIGHT if t not in ("when_attacked", "while_defending")] + ["while_elevated"] + WEATHER,
    "defense":    ["when_attacked", "while_defending", "at_low_health"] + WEATHER,
    "evasion":    ["after_moving", "when_attacked", "while_elevated"] + WEATHER,
    "movement":   ["after_moving", "in_wilderness", "in_swamp", "in_arctic", "out_of_combat"] + WEATHER,
    "resolve":    ["at_low_health", "when_attacked"] + WEATHER,
    "recovery":   ["out_of_combat", "in_wilderness", "in_settlements", "at_low_health"] + WEATHER,
    "perception": ["in_wilderness", "in_swamp", "in_arctic", "out_of_combat"] + WEATHER,
    "stealth":    ["in_wilderness", "in_swamp", "in_arctic", "out_of_combat", "in_settlements"] + WEATHER,
    "insight":    ["in_conversation", "in_settlements", "out_of_combat"],
    "persuasion": ["in_conversation", "in_settlements", "out_of_combat"],
    "intimidation": ["in_conversation", "in_settlements", "at_night"],
    "deception":  ["in_conversation", "in_settlements", "at_night"],
    "performance": ["while_performing", "in_settlements", "in_conversation", "at_night"],
    "lore":       ["in_settlements", "out_of_combat", "in_conversation"],
    "crafting":   ["in_settlements", "out_of_combat", "at_night", "in_daylight"],
}


class GearStat:
    """A stat that exists only on gear (an attribute, or a resistance)."""
    def __init__(self, id: str, category: str):
        self.id, self.category = id, category


GEAR_ONLY = [GearStat(i, cat) for cat, ids in items.RULES["gear_only_stats"].items() for i in ids]
TOKENS = items.RULES["random_element"]          # "elemental_resistance" -> picks one element when rolled
GEAR_ONLY += [GearStat(t, "token") for t in TOKENS]


def roll_properties(rarity: str, rng: random.Random, extra: int = 0, only: list[str] | None = None,
                    count: int | None = None) -> list[ItemProperty]:
    """An item's rolled properties: never the same stat twice, and every condition fits its stat. `only` limits the stats (a ring's lane)."""
    count = items.RULES["rarities"][rarity]["properties"] + extra if count is None else count
    if not count:
        return []
    low, high = L["property_magnitude"].get(rarity, L["property_magnitude"]["uncommon"])
    stats = [s for s in list(STATS.values()) + GEAR_ONLY if (s.category != "companion" or only is not None) and s.id not in L.get("not_on_gear", [])
             and (only is None or s.id in only)]
    rng.shuffle(stats)
    out = []
    for stat in stats[:count]:
        sid, cat = stat.id, stat.category
        if cat == "token":
            from engine import elements
            cat = TOKENS[sid]
            suffix = "resistance" if cat == "resistance" else "damage"
            used = {o.modifies for o in out}
            options = [e for e in elements.ELEMENTS if f"{e}_{suffix}" not in used]
            if not options:
                continue
            sid = f"{rng.choice(options)}_{suffix}"
        if L.get("conditional_rolls", False):
            fits = [t for t in FITS.get(sid, []) if t in TRIGGERS]
            trigger = "always" if cat == "pool" or not fits or rng.random() < 0.5 else rng.choice(fits)
        else:
            trigger = "always"              # a rolled property is a plain, permanent bonus
        magnitude = rng.randint(low, high) // (2 if trigger == "always" else 1)
        if cat == "resistance":
            lo, hi = L["resist_magnitude"].get(rarity, L["resist_magnitude"]["uncommon"])
            magnitude = rng.randint(lo, hi)
            if sid == "all_elemental_resistance":
                magnitude = round(magnitude * L.get("all_resist_share", 0.5))
        elif cat == "companion":
            lo, hi = L["companion_magnitude"].get(rarity, L["companion_magnitude"]["uncommon"])
            magnitude = rng.randint(lo, hi)
        elif cat == "onhit":
            lo, hi = L["onhit_magnitude"][sid].get(rarity, L["onhit_magnitude"][sid]["uncommon"])
            magnitude = rng.randint(lo, hi)
        elif cat == "crit":
            table = L["crit_damage_magnitude"] if sid == "crit_damage" else L["crit_magnitude"]
            lo, hi = table.get(rarity, table["uncommon"])
            magnitude = rng.randint(lo, hi)
        out.append(ItemProperty(modifies=sid, trigger=trigger, magnitude=max(1, magnitude)))
    return out


def gear_kind(base) -> str:
    """Which roll list a base uses: weapon melee/finesse/ranged/focus, or armor heavy/medium/light/cloth/shield."""
    if base.is_weapon:
        if base.damage == "magical":
            return "weapon.focus"
        if base.reach == "ranged":
            return "weapon.ranged"
        return "weapon.finesse" if base.attributes[:1] == ["dexterity"] else "weapon.melee"
    if base.slot == "off_hand":
        return "armor.shield"
    return "armor.cloth" if base.ward else f"armor.{base.weight or 'light'}"


def gear_stats(item: Item) -> list[str]:
    """The stats this piece of gear can roll."""
    R = items.RULES["roll_lists"]
    base = items.base_of(item)
    group, kind = gear_kind(base).split(".")
    stats = list(R[group][kind]) + [s for s in R["slot_extra"].get(base.slot, []) if s not in R[group][kind]]
    own = [a for a in base.attributes if a in ("intelligence", "wisdom", "charisma")] if base.is_weapon else []
    stats = [x for s in stats for x in (own if s == "own_attribute" else [s])]
    return [s for s in stats if s not in L.get("not_on_gear", [])]


def keeps_companions(character) -> bool:
    """A companion class, or anyone who has learned a summoning ability."""
    return bool(character and (character.uses_companions or character.companions
                               or any(getattr(a.effect, "value", a.effect) == "summon" for a in character.actives)))


def roll_gear(item: Item, rng: random.Random) -> None:
    """Roll an item's properties. A ring or amulet is assembled whole (engine/accessories.py): lane, stats, trait, power, gift."""
    from engine import accessories
    if accessories.is_accessory(item):
        accessories.roll(item, rng)
    else:
        material = items.material_of(item)
        item.properties = roll_properties(item.rarity, rng, material.extra_properties if material else 0, only=gear_stats(item))


def drops(enemy: combat.Fighter, rng: random.Random, companions: bool = False) -> tuple[int, Item | None]:
    """Returns (copper, item or None) for one defeated enemy."""
    coins = 0
    if enemy.category in L["coin_categories"]:
        rank_mult = combat.RULES["xp"]["rank"][enemy.rank]
        coins = round(rng.uniform(0, L["coins_per_level"]) * enemy.level * rank_mult)
    chance = L["item_chance"].get(enemy.category, L["item_chance"]["default"])
    if enemy.rank != "normal":
        chance = min(1.0, chance * 3)
    item = None
    if rng.random() < chance:
        rarity = roll_rarity(rng)
        bases = pick_bases(rarity, rng, enemy.level)
        base = rng.choice(bases)
        if enemy.rank != "normal" and rarity == "common":
            rarity = "uncommon"
        item = items.make(base.id, rarity, enemy.level, rng=rng)
        roll_gear(item, rng)
        if rarity == "legendary":
            options = items.legendary_options(items.base_of(item), companions)
            if options:
                item.legendary_effect = items.pick_legendary(options, rng).id
    return coins, item


def pick_bases(rarity: str, rng: random.Random, level: int = 10**6) -> list:
    """The bases a drop can be at this item level. A legendary is often a ring or amulet, because those carry the wonders."""
    fits = [b for b in items.CATALOG.values() if b.min_level <= level]
    if rarity == "legendary" and rng.random() < L.get("legendary_jewelry", 0.25):
        return [b for b in fits if b.slot in ("neck", "ring")]
    return [b for b in fits if b.slot != "none" and (b.slot not in ("neck", "ring") or rng.random() < 0.3)]


def make_drop(level: int, rarity: str, rng: random.Random, companions: bool = False) -> Item:
    """One piece of gear of the given rarity and level, with its properties (and legendary effect) rolled."""
    bases = pick_bases(rarity, rng, level)
    item = items.make(rng.choice(bases).id, rarity, level, rng=rng)
    roll_gear(item, rng)
    if rarity == "legendary":
        options = items.legendary_options(items.base_of(item), companions)
        if options:
            item.legendary_effect = items.pick_legendary(options, rng).id
    return item


def boss_drops(enemy: combat.Fighter, rng: random.Random, companions: bool = False) -> tuple[int, list[Item]]:
    """A boss's reward: a purse of coin and several pieces of rare-or-better gear."""
    b = L["boss"]
    coins = rng.randint(*b["coins_per_level"]) * enemy.level
    weights = b["rarity_weights"]
    loot = [make_drop(enemy.level, rng.choices(list(weights), weights=list(weights.values()))[0], rng, companions)
            for _ in range(b["items"])]
    return coins, loot


def material_drops(enemy: combat.Fighter, rng: random.Random) -> list:
    """Raw materials from the creature itself: a wolf's hide, a drake's scales."""
    found = []
    for m in items.MATERIALS.values():
        if enemy.creature in m.drops_from and rng.random() < L.get("material_chance", 0.6):
            found.append(items.make_raw(m.id))
    return found


def found_materials(category: str, level: int, rng: random.Random, bonus: float = 0.0) -> list:
    """Ore, silver and rare timber carried by the right kind of creature once its level reaches the material's."""
    F = L.get("material_finds")
    if not F or not category:
        return []
    fits = [m for m in items.MATERIALS.values()
            if category in m.found_with and m.levels[0] * F["level_floor"] <= level <= m.levels[1]]
    if not fits or rng.random() >= F["chance"] + bonus:
        return []
    weights = [F["rarity"].get(m.rarity, 1) * (1 + m.levels[0] / 50) for m in fits]
    raw = items.make_raw(rng.choices(fits, weights=weights)[0].id)
    raw.quantity = rng.randint(*F["quantity"])
    return [raw]


def food_drops(enemy, rng: random.Random) -> list:
    """Meat from game animals."""
    from engine import inventory
    return [inventory.make_good(g.id, rng.randint(1, 2)) for g in inventory.GOODS.values()
            if enemy.creature in g.drops_from and rng.random() < 0.8]


def has_remains(enemy) -> bool:
    """Whether a fallen creature leaves anything worth skinning or butchering."""
    from engine import inventory
    F = L.get("material_finds")
    if F and any(enemy.category in m.found_with and m.levels[0] * F["level_floor"] <= enemy.level <= m.levels[1]
                 for m in items.MATERIALS.values()):
        return True
    return any(enemy.creature in m.drops_from for m in items.MATERIALS.values()) or \
        any(enemy.creature in g.drops_from for g in inventory.GOODS.values())

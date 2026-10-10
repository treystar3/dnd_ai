"""Items: base catalog (data/world/items.yaml), materials and gems (data/world/materials.yaml),
rules (data/rules/equipment.yaml), and every number an item has.

The engine computes all numbers. The model may name and describe special items, never stat them.
"""

import random
import uuid
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from core.models import Item, ItemProperty
from core.rules import ATTRIBUTES, STATS, TRIGGERS

ROOT = Path(__file__).resolve().parent.parent / "data"
RULES = yaml.safe_load((ROOT / "rules" / "equipment.yaml").read_text(encoding="utf-8"))
SLOTS = RULES["slots"]
WEIGHTS = ["light", "medium", "heavy"]
MATERIAL_RARITY_WEIGHT = {"common": 10, "uncommon": 4, "rare": 1, "legendary": 0.1}
MATERIAL_PRICE = {"common": 1.0, "uncommon": 1.5, "rare": 3.0, "legendary": 10.0}
GEM_MAGNITUDE = {"crude": 2, "common": 4, "uncommon": 6, "rare": 8, "epic": 11, "legendary": 14}
DIAMOND_SPREAD = ["max_health", "max_stamina", "damage", "defense", "resolve"]
FLAGS = {"armor_pierce", "crit_resist", "ward_fraction", "magic_power", "adaptive"}


class BaseItem(BaseModel):
    id: str
    name: str
    family: Literal["metal", "hide", "cloth", "wood"] | None = None
    label: str = ""
    slot: Literal["main_hand", "off_hand", "head", "body", "hands", "feet", "neck", "ring", "none"]
    hands: int = 1
    reach: Literal["melee", "extended", "ranged"] | None = None
    attribute: str | list[str] | None = None
    damage: Literal["physical", "magical"] | None = None
    base: float = 0
    ward: bool = False
    weight: Literal["light", "medium", "heavy"] | None = None
    requires: dict[str, int] = {}
    price: int = 0
    tags: list[str] = []
    min_level: int = 0       # end-game gear: not found, stocked or dropped below this item level

    @property
    def is_weapon(self) -> bool:
        return self.damage is not None

    @property
    def attributes(self) -> list[str]:
        if self.attribute is None:
            return []
        return [self.attribute] if isinstance(self.attribute, str) else list(self.attribute)


class Effect(BaseModel):
    modifies: str
    trigger: str = "always"
    magnitude: int
    flat: bool = False          # the magnitude is an amount of the stat, not a percentage


class Material(BaseModel):
    id: str
    name: str
    family: Literal["metal", "hide", "cloth", "wood"]
    levels: tuple[int, int]
    rarity: Literal["common", "uncommon", "rare", "legendary"] = "common"
    source: str = ""
    note: str = ""
    weapon_multiplier: float = 1.0
    armor_multiplier: float = 1.0
    weight_shift: int = 0
    extra_properties: int = 0
    any: list[Effect] = []
    weapon: list[Effect] = []
    armor: list[Effect] = []
    weapon_flags: dict[str, float] = {}
    armor_flags: dict[str, float] = {}
    drops_from: list[str] = []
    found_with: list[str] = []      # creature categories that carry this material at the right level (ore on a golem, silver in a giant's hoard)


class LegendaryEffect(BaseModel):
    id: str
    name: str
    applies: Literal["weapon", "armor", "jewelry", "any"]
    value: float = 0
    category: str = ""
    damage: str = ""         # only weapons that deal this kind of damage can roll it (magical = wands, staves, charms, lutes)
    tag: str = ""            # only bases with this tag can roll it (ward = robes and hoods)
    world: str = ""          # a wonder: the world-side mechanic this effect gives its wearer (see engine/pools.mechanic)
    companions: bool = False  # only rolls for a character who keeps companions or summons
    enabled: bool = True
    description: str

    def text(self) -> str:
        return self.description.format(value=f"{self.value:g}")


class Gem(BaseModel):
    id: str
    name: str
    focus: str
    rarity: Literal["common", "uncommon", "rare", "legendary"] = "common"


def _load():
    problems = []
    catalog = {}
    for entry in yaml.safe_load((ROOT / "world" / "items.yaml").read_text(encoding="utf-8")):
        b = BaseItem(**entry)
        if b.id in catalog:
            problems.append(f"items.yaml: duplicate item '{b.id}'")
        for a in b.attributes + list(b.requires):
            if a not in ATTRIBUTES:
                problems.append(f"items.yaml {b.id}: unknown attribute '{a}'")
        if b.slot == "main_hand" and not b.is_weapon:
            problems.append(f"items.yaml {b.id}: main_hand items need damage and reach")
        catalog[b.id] = b
    raw = yaml.safe_load((ROOT / "world" / "materials.yaml").read_text(encoding="utf-8"))
    materials = {m["id"]: Material(**m) for m in raw["materials"]}
    gems = {g["id"]: Gem(**g) for g in raw["gems"]}
    for m in materials.values():
        lo, hi = m.levels
        if not 1 <= lo <= hi:
            problems.append(f"materials.yaml {m.id}: levels must be [min, max] with 1 <= min <= max")
        size = RULES["material_bonus_size"][m.rarity]
        for e in m.any + m.weapon + m.armor:
            e.magnitude = max(1, round(e.magnitude * size))
            if e.modifies not in STATS and e.modifies not in GEAR_ONLY_IDS:
                problems.append(f"materials.yaml {m.id}: '{e.modifies}' is not a stat in stats.yaml")
            if e.trigger not in TRIGGERS:
                problems.append(f"materials.yaml {m.id}: '{e.trigger}' is not a trigger in triggers.yaml")
        for f in list(m.weapon_flags) + list(m.armor_flags):
            if f not in FLAGS:
                problems.append(f"materials.yaml {m.id}: unknown flag '{f}'")
    for g in gems.values():
        if g.focus != "all" and g.focus not in STATS:
            problems.append(f"materials.yaml gem {g.id}: focus '{g.focus}' is not a stat")
    if problems:
        raise ValueError("Item data problems:\n" + "\n".join(f"  - {p}" for p in problems))
    return catalog, materials, gems


GEAR_ONLY_IDS = {i for ids in RULES["gear_only_stats"].values() for i in ids}
CATALOG, MATERIALS, GEMS = _load()
LEGENDARY = {e["id"]: LegendaryEffect(**e) for e in yaml.safe_load((ROOT / "rules" / "legendary_effects.yaml").read_text(encoding="utf-8"))}


def legendary_options(base: "BaseItem", companions: bool = False) -> list[LegendaryEffect]:
    """The legendary effects this base can roll. Companion effects roll only for those who keep companions (`companions`)."""
    kind = "weapon" if base.is_weapon else "jewelry" if base.slot in ("neck", "ring") else "armor"
    return [e for e in LEGENDARY.values() if e.enabled and (companions or not e.companions) and e.applies in (kind, "any")
            and (not e.damage or base.damage == e.damage) and (not e.tag or e.tag in base.tags)]


def pick_legendary(options: list[LegendaryEffect], rng: random.Random) -> LegendaryEffect:
    """Pick one. Effects made for a kind of weapon (hand wraps) come up eight times as often as the general ones."""
    return rng.choices(options, weights=[8 if e.tag == "unarmed" else 1 for e in options])[0]


def display_name(item: Item) -> str:
    return f"{item.name}, {item.title}" if item.title else item.name


def base_of(item: Item) -> BaseItem:
    return CATALOG[item.base]


def material_of(item: Item) -> Material | None:
    return MATERIALS.get(item.material)


def level_growth(level: int) -> float:
    return 1 + RULES["item_level_growth"] * (max(1, level) - 1)


# ---------- creating items ----------

def choose_material(family: str | None, level: int, rng: random.Random | None = None, plainest: bool = False) -> str:
    if not family:
        return ""
    fits = [m for m in MATERIALS.values() if m.family == family and m.levels[0] <= level <= m.levels[1]]
    if not fits:
        fits = sorted((m for m in MATERIALS.values() if m.family == family), key=lambda m: abs(m.levels[0] - level))[:1]
    if plainest or rng is None:
        plain = [m for m in fits if m.rarity == "common" and not (m.any or m.weapon or m.armor or m.weight_shift)] or fits
        return min(plain, key=lambda m: m.levels[0]).id
    return rng.choices(fits, weights=[MATERIAL_RARITY_WEIGHT[m.rarity] for m in fits])[0].id


def choose_gem(rng: random.Random) -> str:
    gems = list(GEMS.values())
    return rng.choices(gems, weights=[MATERIAL_RARITY_WEIGHT[g.rarity] for g in gems])[0].id


def make(base_id: str, rarity: str = "common", item_level: int = 1, name: str = "", description: str = "",
         material: str | None = None, gem: str = "", rng: random.Random | None = None) -> Item:
    b = CATALOG[base_id]
    if material is None:
        material = choose_material(b.family, item_level, rng, plainest=rng is None)
    if b.slot in ("ring", "neck") and not gem:
        gem = choose_gem(rng or random.Random(0))
    mat = MATERIALS.get(material)
    label = b.label or b.name
    default = " ".join(x for x in [rarity if rarity == "crude" else "", mat.name if mat else "", label,
                                   f"with {GEMS[gem].name}" if gem else ""] if x)
    return Item(uid=uuid.uuid4().hex[:10], base=base_id, name=name or (default if mat or gem else b.name if rarity != "crude" else f"crude {b.name}"),
                rarity=rarity, item_level=max(1, item_level), material=material, gem=gem, description=description)


def make_raw(material_id: str) -> Item:
    m = MATERIALS[material_id]
    return Item(uid=uuid.uuid4().hex[:10], base="raw_material", name=f"raw {m.name}", rarity="common",
                item_level=m.levels[0], material=material_id)


# ---------- numbers ----------

def scale(item: Item) -> float:
    return RULES["rarities"][item.rarity]["multiplier"] * level_growth(item.item_level)


def material_grade(m) -> float:
    """How good a material is, from the lowest level it appears at. Materials the table doesn't reach take its last point."""
    pts = RULES["material_grade"]
    f = m.levels[0]
    if f <= pts[0][0]:
        return pts[0][1]
    for (l0, g0), (l1, g1) in zip(pts, pts[1:]):
        if f <= l1:
            return g0 + (g1 - g0) * (f - l0) / (l1 - l0)
    return pts[-1][1]


def value(item: Item) -> int:
    """Weapon damage, or armor/ward for everything else."""
    b = base_of(item)
    if not b.base:
        return 0
    m = material_of(item)
    mult = (m.weapon_multiplier if b.is_weapon else m.armor_multiplier) if m else 1.0
    return round(b.base * scale(item) * mult * (material_grade(m) if m else 1.0))


def weight(item: Item) -> str | None:
    b = base_of(item)
    if not b.weight:
        return None
    m = material_of(item)
    shift = m.weight_shift if m else 0
    return WEIGHTS[max(0, min(2, WEIGHTS.index(b.weight) + shift))]


def flat_value(stat: str, points: int, level: int) -> int:
    """What `points` of a flat gear stat come to at an item level."""
    F = RULES["flat_gear"]
    if stat in RULES["gear_only_stats"]["attribute"]:
        a = F["attribute"]
        ref = a["start"] + a["per_level"] * (max(1, level) - 1)
    elif stat in ("max_health", "max_stamina", "max_mana"):
        from engine import pools
        ref = pools.reference_pool(stat.replace("max_", ""), level)
    else:
        ref = F["damage_ref"] * level_growth(level) * (F["defense_hit"] if stat == "defense" else 1)       # damage, defense, elemental damage
    return max(1, round(points * ref / 100)) if points > 0 else 0


def to_flat(effs: list[Effect], level: int) -> list[Effect]:
    """The same effects with the flat stats turned into amounts at this level."""
    stats = RULES["flat_gear"]["stats"]
    return [Effect(modifies=e.modifies, trigger=e.trigger, magnitude=flat_value(e.modifies, e.magnitude, level), flat=True)
            if e.modifies in stats else e for e in effs]


def material_effects(item: Item) -> list[Effect]:
    """The material's built-in bonuses at this item level. Chance stats grow gently with level; amounts scale later, in to_flat."""
    b = base_of(item)
    m = material_of(item)
    if not m or b.slot == "none":
        return []
    grow = min(RULES["material_chance_cap"], 1 + RULES["material_chance_growth"] * max(0, item.item_level - 1))
    out = []
    for e in m.any + (m.weapon if b.is_weapon else m.armor):
        chance = e.modifies not in RULES["flat_gear"]["stats"] and e.modifies not in ("recovery", "crit_chance", "crit_damage") \
            and not e.modifies.endswith("_resistance")
        out.append(Effect(modifies=e.modifies, trigger=e.trigger, magnitude=max(1, round(e.magnitude * grow)) if chance else e.magnitude))
    return out


def innate_effects(item: Item) -> list[Effect]:
    """What the material and gem give before anything is rolled."""
    b = base_of(item)
    out = material_effects(item)
    if item.gem:
        g = GEMS[item.gem]
        size = GEM_MAGNITUDE.get(item.rarity, 4)
        if g.focus == "all":
            out += [Effect(modifies=s, magnitude=max(1, size // 3)) for s in DIAMOND_SPREAD]
        else:
            out.append(Effect(modifies=g.focus, magnitude=size))
    return out


def sourced_effects(item: Item) -> list[tuple[Effect, str]]:
    """Each effect with where it comes from: the material or gem by name, or nothing for a rolled property."""
    b = base_of(item)
    m = material_of(item)
    out: list[tuple[Effect, str]] = [(e, m.name) for e in material_effects(item)] if m else []
    if item.gem:
        g = GEMS[item.gem]
        size = GEM_MAGNITUDE.get(item.rarity, 4)
        gem = [Effect(modifies=s, magnitude=max(1, size // 3)) for s in DIAMOND_SPREAD] if g.focus == "all" else [Effect(modifies=g.focus, magnitude=size)]
        out += [(e, g.name) for e in gem]
    out += [(Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude), "") for p in item.properties]
    out += [(Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude), "enchanted") for en in item.enchantments for p in en.effects]
    kept = [(e, src) for e, src in out if e.magnitude > 0]
    flat = to_flat([e for e, _ in kept], item.item_level)
    return list(zip(flat, [src for _, src in kept]))


def effects(item: Item) -> list[Effect]:
    """Every stat effect an item grants: its material, its gem, and its rolled properties. Never a penalty."""
    out = innate_effects(item)
    out += [Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude) for p in item.properties]
    for ench in item.enchantments:
        out += [Effect(modifies=p.modifies, trigger=p.trigger, magnitude=p.magnitude) for p in ench.effects]
    return to_flat([e for e in out if e.magnitude > 0], item.item_level)


def flags(item: Item) -> dict[str, float]:
    b = base_of(item)
    m = material_of(item)
    out: dict[str, float] = {}
    if m and b.slot != "none":
        out.update(m.weapon_flags if b.is_weapon else m.armor_flags)
    for ench in item.enchantments:
        for k, v in ench.flags.items():
            out[k] = out.get(k, 0) + v
    return out


def price(item: Item) -> int:
    if item.good:
        from engine.inventory import GOODS
        return GOODS[item.good].price
    b = base_of(item)
    m = material_of(item)
    if b.slot == "none" and m:
        mid = (m.levels[0] + m.levels[1]) / 2
        return max(5, round(5 * mid ** 1.3 * MATERIAL_PRICE[m.rarity]))
    mat = MATERIAL_PRICE[m.rarity] if m else 1.0
    gem = MATERIAL_PRICE[GEMS[item.gem].rarity] if item.gem else 1.0
    value = b.price * RULES["rarities"][item.rarity]["price"] * level_growth(item.item_level) * mat * gem
    if item.rarity not in ("epic", "legendary"):
        value = min(value, RULES["ordinary_price_cap"] * level_growth(item.item_level))
    return max(1, round(value))


DAMAGE_LABEL = {"magical": "spell"}                 # what the player sees; "magical" stays the stored id


def _describe_effect(e: Effect) -> str:
    sign = "+" if e.magnitude >= 0 else ""
    when = "" if e.trigger == "always" else f" {e.trigger.replace('_', ' ')}"
    unit = "%" if e.modifies in ("recovery", "crit_chance", "crit_damage", "companion_damage", "companion_durability") or e.modifies.endswith("_resistance") else ""
    return f"{sign}{e.magnitude}{unit} {e.modifies.replace('magical_', 'spell_').replace('_', ' ')}{when}"


FLAG_TEXT = {"armor_pierce": "ignores {v:g}% of armor", "crit_resist": "{v:g}% less likely to be critically hit",
             "ward_fraction": "{v:g}% of its armor also wards against magic", "magic_power": "+{v:g}% spell damage",
             "adaptive": "strikes as physical or spell, whichever the target resists less"}


def summary(item: Item) -> str:
    b = base_of(item)
    if item.good:
        from engine.inventory import GOODS
        g = GOODS[item.good]
        return {"herb": "herb", "food": "food", "consumable": "consumable"}[g.kind] + f" - {g.description}"
    if b.slot == "none":
        m = material_of(item)
        return f"trade good{f' ({m.source.lower()})' if m else ''}"
    if b.is_weapon:
        hands = ", two-handed" if b.hands == 2 else ""
        attrs = "/".join(a[:3].upper() for a in b.attributes)
        core = f"{value(item)} {DAMAGE_LABEL.get(b.damage, b.damage)} damage, {b.reach} reach, {attrs}{hands}"
    elif b.base:
        w = weight(item)
        core = f"{value(item)} {'ward' if b.ward else 'armor'}" + (f", {w}" if w else "")
    else:
        core = "jewelry"
    extras = [_describe_effect(e) + (f" ({src})" if src else "") for e, src in sourced_effects(item)]
    extras += [FLAG_TEXT[k].format(v=v) for k, v in flags(item).items()]
    if item.legendary_effect in LEGENDARY:
        le = LEGENDARY[item.legendary_effect]
        extras.append(f"★ {le.name}: {le.text()}")
    if item.trait or item.relic:
        from engine import accessories
        extras += accessories.lines(item)
    level = f"lv {item.item_level} " if item.item_level > 1 else ""
    return f"{level}{core}" + (f"; {'; '.join(extras)}" if extras else "")

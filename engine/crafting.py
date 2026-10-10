"""Crafting gear, merchants' stock, and commissions. All numbers come from data/rules/crafting.yaml."""

import random
from pathlib import Path

import yaml

from core.models import Character, Item
from engine import items, loot, pools

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "data" / "rules" / "crafting.yaml").read_text(encoding="utf-8"))
RARITY_ORDER = ["crude", "common", "uncommon", "rare", "epic"]
CRAFTABLE = [b for b in items.CATALOG.values() if b.family and b.slot not in ("none", "ring", "neck")]


def units_for(base) -> int:
    key = "main_hand_two_handed" if base.slot == "main_hand" and base.hands == 2 else base.slot
    return RULES["units"][key]


def station_for(base) -> str:
    return RULES["stations"][base.family]


def find_base(text: str, families: list[str] | None = None):
    """The gear base the player means: 'a jerkin', 'iron helm', 'spear'. Longest matching name wins."""
    t = text.lower()
    best, best_len = None, 0
    for b in CRAFTABLE:
        if families and b.family not in families:
            continue
        for name in {b.name, b.label, b.id.replace("_", " ")}:
            if name and name.lower() in t and len(name) > best_len:
                best, best_len = b, len(name)
    return best


def mechanic(c: Character, mid: str) -> float:
    return pools.mechanic(c, mid) or 0


def effective_skill(c: Character) -> float:
    """Practiced skill, plus crafting passives (points), plus Masterwork."""
    bonus = sum(p.magnitude for p in c.passives if not p.mechanic and p.modifies and p.modifies.value == "crafting"
                and p.trigger.value in ("always", "out_of_combat", "in_settlements"))
    return c.crafting_skill + bonus + mechanic(c, "masterwork")


def roll_quality(skill: float, rng: random.Random, boost: float = 0) -> str:
    score = skill + boost + rng.uniform(-RULES["roll_spread"], RULES["roll_spread"])
    reached = [r for r in RARITY_ORDER if score >= RULES["quality"][r]]
    return reached[-1] if reached else "crude"


def item_level(material_id: str, skill: float, rng: random.Random, cap: tuple[int, int] | None = None) -> int:
    lo, hi = items.MATERIALS[material_id].levels
    if cap:
        lo, hi = max(lo, cap[0]), max(lo, min(hi, cap[1]))
    return max(1, lo + round((hi - lo) * min(1.0, skill / 100) * rng.uniform(0.5, 1.0)))


def make_gear(base, material_id: str, skill: float, rng: random.Random, boost: float = 0,
              cap: tuple[int, int] | None = None, floor: str = "crude") -> Item:
    rarity = roll_quality(skill, rng, boost)
    if RARITY_ORDER.index(rarity) < RARITY_ORDER.index(floor):
        rarity = floor
    item = items.make(base.id, rarity, item_level(material_id, skill, rng, cap), material=material_id, rng=rng)
    loot.roll_gear(item, rng)
    return item


def skill_gain(c: Character, gear: bool, material_id: str = "") -> float:
    base = RULES["gear_skill_gain"] if gear else RULES["goods_skill_gain"]
    challenge = 1.0
    if material_id:
        challenge += items.MATERIALS[material_id].levels[0] / 25
    gain = base * challenge * max(0.15, 1.2 - c.crafting_skill / 100) * (1 + mechanic(c, "quick_study") / 100)
    return gain


def raise_skill(c: Character, gain: float) -> tuple[float, float]:
    before = c.crafting_skill
    c.crafting_skill = min(100.0, before + gain)
    return before, c.crafting_skill


def materials_in(bag: list[Item], family: str) -> dict[str, int]:
    counts = {}
    for i in bag:
        m = items.material_of(i)
        if i.base == "raw_material" and m and m.family == family:
            counts[m.id] = counts.get(m.id, 0) + i.quantity
    return counts


def pick_material(bag: list[Item], family: str, text: str, need: int) -> tuple[str | None, dict[str, int]]:
    """The material the player means (named in their words), or the one they have most of. None if not enough."""
    have = materials_in(bag, family)
    named = [m for m in have if items.MATERIALS[m].name.lower() in text.lower()]
    for m in named + sorted(have, key=lambda x: -have[x]):
        if have[m] >= need:
            return m, have
    return None, have


def use_material(bag: list[Item], material_id: str, count: int) -> None:
    for i in [i for i in bag if i.base == "raw_material" and i.material == material_id]:
        moved = min(i.quantity, count)
        i.quantity -= moved
        count -= moved
        if i.quantity <= 0:
            bag.remove(i)
        if count <= 0:
            return


# ---------- merchants' stock ----------

def restock_due(npc, stock_rule: dict, day: int) -> bool:
    return npc.stock_day < 0 or day >= npc.stock_day + stock_rule.get("restock_days", 3)


def lay_out_stock(npc, stock_rule: dict, trade_level: tuple[int, int], day: int, seed: int) -> None:
    rng = random.Random(f"{seed}:{npc.id}:{day}")
    bases = [b for b in CRAFTABLE if b.family in stock_rule["families"] and b.min_level <= trade_level[1]]
    stock = []
    for _ in range(stock_rule.get("count", 6)):
        level = rng.randint(*trade_level)
        base = rng.choice([b for b in bases if b.min_level <= level])
        weights = RULES["stock_rarity_weights"]
        for tier in RULES.get("stock_rarity_by_level", []):   # deeper markets stock better goods
            if level >= tier["from_level"]:
                weights = tier["weights"]
        rarity = rng.choices(list(weights), weights=list(weights.values()))[0]
        item = items.make(base.id, rarity, level, material=items.choose_material(base.family, level, rng), rng=rng)
        loot.roll_gear(item, rng)
        stock.append(item.model_dump())
    npc.stock, npc.stock_day = stock, day


def stock_items(npc) -> list[Item]:
    return [Item.model_validate(i) for i in npc.stock]


def remove_from_stock(npc, uid: str) -> None:
    npc.stock = [i for i in npc.stock if i["uid"] != uid]

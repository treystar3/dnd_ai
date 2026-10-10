"""The pack, the item box and the ground: stacking, slots, finding items by name, goods and recipes.

Goods (herbs, food, consumables) and raw materials stack; gear takes a slot per piece.
"""

import math
import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel

from core.models import Item
from engine import items

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "data" / "rules" / "inventory.yaml").read_text(encoding="utf-8"))
RAW_STACK = 10


class Good(BaseModel):
    id: str
    name: str
    kind: str                       # herb | food | consumable
    price: int
    stack: int = 10
    restores: dict[str, float] = {}
    cures: list[str] = []
    combat: bool = False
    grows_in: dict[str, float] = {}
    drops_from: list[str] = []
    description: str = ""


class Ingredient(BaseModel):
    good: str = ""
    kind: str = ""
    count: int = 1


class Recipe(BaseModel):
    id: str
    makes: dict[str, int]
    ingredients: list[Ingredient]


GOODS = {g["id"]: Good(**g) for g in yaml.safe_load((ROOT / "data" / "world" / "goods.yaml").read_text(encoding="utf-8"))}
RECIPES = {r["id"]: Recipe(**r) for r in yaml.safe_load((ROOT / "data" / "rules" / "recipes.yaml").read_text(encoding="utf-8"))}
for _r in RECIPES.values():
    for _g in list(_r.makes) + [i.good for i in _r.ingredients if i.good]:
        if _g not in GOODS:
            raise ValueError(f"recipes.yaml {_r.id}: unknown good '{_g}'")


def make_good(good_id: str, quantity: int = 1) -> Item:
    g = GOODS[good_id]
    return Item(uid=uuid.uuid4().hex[:10], base="goods", name=g.name, good=good_id, quantity=quantity)


def stack_size(item: Item) -> int:
    if item.good:
        return GOODS[item.good].stack
    if item.base == "raw_material":
        return RAW_STACK
    return 1


def same_stack(a: Item, b: Item) -> bool:
    return stack_size(a) > 1 and (a.base, a.good, a.material, a.rarity) == (b.base, b.good, b.material, b.rarity)


def label(item: Item) -> str:
    name = items.display_name(item)
    return f"{name} x{item.quantity}" if item.quantity > 1 else name


def unit_value(item: Item) -> int:
    return GOODS[item.good].price if item.good else items.price(item)


def category(item: Item) -> str:
    if item.good:
        return GOODS[item.good].kind
    if item.base == "raw_material":
        m = items.material_of(item)
        return m.family if m else "material"
    b = items.base_of(item)
    if b.is_weapon:
        return "weapon"
    return "jewelry" if b.slot in ("neck", "ring") else "armor"


def add(bag: list[Item], item: Item, capacity: int) -> Item | None:
    """Put an item (or stack) into a bag. Returns whatever did not fit, or None."""
    left = item.quantity
    if stack_size(item) > 1:
        for have in bag:
            if left and same_stack(have, item) and have.quantity < stack_size(have):
                room = stack_size(have) - have.quantity
                moved = min(room, left)
                have.quantity += moved
                left -= moved
    while left and len(bag) < capacity:
        moved = min(stack_size(item), left)
        bag.append(item.model_copy(update={"uid": uuid.uuid4().hex[:10], "quantity": moved}))
        left -= moved
    return item.model_copy(update={"quantity": left}) if left else None


def find(bag: list[Item], name: str) -> Item | None:
    """The best match for something the player named: 'the draught', 'wolf hides', 'my old sword'."""
    words = [w.rstrip("s") for w in name.lower().replace("-", " ").split() if w not in ("the", "my", "a", "an", "some", "of")]
    best, best_score = None, 0
    for it in bag:
        text = f"{items.display_name(it)} {it.good} {it.material} {items.base_of(it).name}".lower().replace("_", " ")
        score = sum(1 for w in words if w and w in text)
        if score > best_score:
            best, best_score = it, score
    return best


def take(bag: list[Item], name: str, count: int = 1) -> Item | None:
    """Remove up to count of the named item from a bag (across stacks). Returns what was removed."""
    first = find(bag, name)
    if not first:
        return None
    if stack_size(first) == 1:
        bag.remove(first)
        return first
    wanted, got = max(1, count), 0
    for have in [b for b in bag if same_stack(b, first)]:
        moved = min(have.quantity, wanted - got)
        have.quantity -= moved
        got += moved
        if have.quantity <= 0:
            bag.remove(have)
        if got >= wanted:
            break
    return first.model_copy(update={"quantity": got}) if got else None


def count_of(bag: list[Item], good: str = "", kind: str = "") -> int:
    return sum(i.quantity for i in bag if i.good and (i.good == good or (kind and GOODS[i.good].kind == kind)))


def remove_goods(bag: list[Item], good: str = "", kind: str = "", count: int = 1) -> None:
    for have in [i for i in bag if i.good and (i.good == good or (kind and GOODS[i.good].kind == kind))]:
        moved = min(have.quantity, count)
        have.quantity -= moved
        count -= moved
        if have.quantity <= 0:
            bag.remove(have)
        if count <= 0:
            return


def can_craft(bag: list[Item], recipe: Recipe) -> list[str]:
    """Missing ingredients, as words. Empty when the recipe can be made."""
    missing = []
    for ing in recipe.ingredients:
        have = count_of(bag, ing.good, ing.kind)
        if have < ing.count:
            what = GOODS[ing.good].name if ing.good else f"any {ing.kind}"
            missing.append(f"{ing.count - have} more {what}")
    return missing


def find_recipe(name: str) -> Recipe | None:
    key = name.lower().replace(" ", "_").rstrip("s")
    for r in RECIPES.values():
        names = [r.id] + [GOODS[g].name for g in r.makes]
        if any(key in n.replace(" ", "_") or n.replace(" ", "_").rstrip("s") in key for n in names):
            return r
    return None


def ground_items(state, now: int) -> list[Item]:
    """Items still lying in a place; drops ones that have been there too long."""
    limit = RULES["ground_days"] * 1440
    state.ground = [g for g in state.ground if now - g["minute"] < limit]
    return [Item.model_validate(g["item"]) for g in state.ground]


def leave_on_ground(state, item: Item, now: int) -> None:
    state.ground.append({"item": item.model_dump(), "minute": now})


def pick_up(state, name: str, now: int) -> Item | None:
    ground_items(state, now)
    bag = [Item.model_validate(g["item"]) for g in state.ground]
    found = find(bag, name)
    if not found:
        return None
    for g in state.ground:
        if g["item"]["uid"] == found.uid:
            state.ground.remove(g)
            break
    return found

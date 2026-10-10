"""Equipping and unequipping. All rules are checked here."""

from core.models import Character, Item
from engine import items

LEVEL_MARGIN = items.RULES.get("equip_level_margin")


def level_needed(item: Item) -> int:
    """The character level at which this item can be worn: its item level less the margin the rules allow."""
    return max(1, item.item_level - LEVEL_MARGIN) if LEVEL_MARGIN is not None else 1

OFF_HAND_WEAPON_TAG = "light"


def _target_slot(c: Character, item: Item) -> str:
    b = items.base_of(item)
    if b.slot == "ring":
        return "ring_1" if "ring_1" not in c.equipment else "ring_2"
    return b.slot


def two_handed_equipped(c: Character) -> bool:
    main = c.equipment.get("main_hand")
    return bool(main and items.base_of(main).hands == 2)


def check(c: Character, item: Item) -> str | None:
    b = items.base_of(item)
    if b.slot != "none" and c.level < level_needed(item):
        return f"You need to be level {level_needed(item)} to use the {item.name}."
    short = [f"{a} {need}" for a, need in b.requires.items() if getattr(c.attributes, a) < need]
    if short:
        return f"You need {', '.join(short)} to use the {item.name}."
    if b.slot == "off_hand" and two_handed_equipped(c):
        return f"Your hands are full with the {c.equipment['main_hand'].name}."
    return None


def equip(c: Character, item: Item) -> str:
    """Equip an item from the inventory. Returns a message. Displaced items go back to the inventory."""
    error = check(c, item)
    if error:
        return error
    b = items.base_of(item)
    slot = _target_slot(c, item)
    displaced = []
    if slot in c.equipment:
        displaced.append(c.equipment.pop(slot))
    if b.hands == 2 and "off_hand" in c.equipment:
        displaced.append(c.equipment.pop("off_hand"))
    c.inventory = [i for i in c.inventory if i.uid != item.uid] + displaced
    c.equipment[slot] = item
    put_away = f" You put away the {', '.join(d.name for d in displaced)}." if displaced else ""
    return f"You equip the {item.name}.{put_away}"


def unequip(c: Character, slot: str) -> str:
    if slot not in c.equipment:
        return f"Nothing is equipped in your {slot.replace('_', ' ')}."
    item = c.equipment.pop(slot)
    c.inventory.append(item)
    return f"You put away the {item.name}."


def find(c: Character, query: str, where: str) -> Item | None:
    """Find an item by number (1-based) or by name in the inventory or equipment."""
    pool = c.inventory if where == "inventory" else list(c.equipment.values())
    q = query.strip().lower()
    if q.isdigit() and where == "inventory":
        n = int(q)
        return pool[n - 1] if 1 <= n <= len(pool) else None
    matches = [i for i in pool if q and (q in i.name.lower() or q == i.base)]
    return matches[0] if len(matches) >= 1 else None


def slot_of(c: Character, item: Item) -> str | None:
    return next((s for s, i in c.equipment.items() if i.uid == item.uid), None)

"""Armor sets: matching pieces of the same material give a bonus (data/world/sets.yaml).

Only armor counts - head, body, hands, feet and a shield. Weapons, rings and amulets never do. Two pieces give the `two` bonus and four
give `four` as well. A bonus is a few stat effects, combat mechanics (the ones legendary armor uses) and world mechanics.
"""

from pathlib import Path

import yaml

from engine import items

D = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "sets.yaml").read_text(encoding="utf-8"))
SETS: dict = D["sets"]
THRESHOLDS: list[int] = D["thresholds"]
NAMES = {2: "two", 4: "four"}
ARMOR_SLOTS = ("head", "body", "hands", "feet", "off_hand")


def counts(equipment: dict) -> dict[str, int]:
    """How many worn armor pieces are made of each material."""
    out: dict[str, int] = {}
    for item in equipment.values():
        b = items.base_of(item)
        if b.is_weapon or b.slot not in ARMOR_SLOTS or not item.material:
            continue
        out[item.material] = out.get(item.material, 0) + 1
    return out


def active(equipment: dict) -> list[tuple[str, int, dict]]:
    """[(material, pieces needed, bonus)] for every set bonus currently earned, lowest first."""
    out = []
    for material, n in counts(equipment).items():
        s = SETS.get(material)
        if not s:
            continue
        for need in THRESHOLDS:
            if n >= need and NAMES[need] in s:
                out.append((material, need, s[NAMES[need]]))
    return out


def effects(equipment: dict) -> list[items.Effect]:
    out = [items.Effect(modifies=m, trigger=t, magnitude=v) for _, _, b in active(equipment) for m, t, v in b.get("effects", [])]
    levels = [i.item_level for i in equipment.values() if getattr(i, "item_level", 0)]
    return items.to_flat(out, round(sum(levels) / len(levels)) if levels else 1)


def fight(equipment: dict) -> dict[str, float]:
    """Combat mechanics earned, as {mechanic id: value} (a flag with no value counts as 1, as it does on a legendary item)."""
    out: dict[str, float] = {}
    for _, _, b in active(equipment):
        for k, v in b.get("fight", {}).items():
            out[k] = out.get(k, 0) + (v or 1)
    return out


def world(equipment: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for _, _, b in active(equipment):
        for k, v in b.get("world", {}).items():
            out[k] = out.get(k, 0) + v
    return out


def describe(bonus: dict) -> str:
    parts = []
    for m, t, v in bonus.get("effects", []):
        parts.append(items._describe_effect(items.Effect(modifies=m, trigger=t, magnitude=v)))
    for k, v in bonus.get("fight", {}).items():
        le = items.LEGENDARY.get(k)
        parts.append(le.description.format(value=f"{(v or le.value):g}") if le else k)
    for k, v in bonus.get("world", {}).items():
        le = next((x for x in items.LEGENDARY.values() if x.world == k), None)
        parts.append(le.description.format(value=f"{(v or le.value):g}") if le else k.replace("_", " "))
    return "; ".join(parts)


def summary(equipment: dict) -> list[str]:
    """Lines for the equipment screen: each set being worn, with what it gives now and what the next piece would add."""
    lines = []
    for material, n in sorted(counts(equipment).items(), key=lambda kv: -kv[1]):
        s = SETS.get(material)
        if not s or n < 1:
            continue
        name = items.MATERIALS[material].name
        earned = [need for need in THRESHOLDS if n >= need]
        if not earned and n < THRESHOLDS[0]:
            continue
        head = f"{name} set ({n} piece{'s' if n != 1 else ''})"
        lines.append(head)
        for need in THRESHOLDS:
            if NAMES[need] not in s:
                continue
            mark = "✓" if n >= need else " "
            lines.append(f"   {mark} {need} pieces: {describe(s[NAMES[need]])}")
    return lines

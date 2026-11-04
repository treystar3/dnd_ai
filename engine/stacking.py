"""(f504) The stacking recipes, declared: how the parts of one figure combine, in the order data/rules/stages.yaml stacking names
them. RECIPES names the function behind each recipe id and PARTS the parts it takes; engine/data_check.py holds the data to them both
ways. Each recipe is today's formula, read from where it stands (engine/combat.py raw_damage and mitigate, engine/pools.py maximum,
engine/combat.py resist_factor and element_factor, mechanics); combine(recipe, parts) gives the value and the parts it applied, in
order, so the fight and the window (engine/statsheet.py) can read one calculation.

Not yet wired (f504): the callers still carry their own lines; f506 makes them call combine, the stat sheets and the fixtures the
proof."""
from __future__ import annotations

from typing import Callable


def base_damage(parts: dict) -> tuple[float, list]:
    """A blow before armour: weapon + attribute + flat, then x move multiplier x (1 + percent / 100) x variance x magic."""
    base = parts["weapon"] + parts.get("attr_bonus", 0.0) + parts.get("flat", 0.0)
    value = base * parts.get("multiplier", 1.0) * (1 + parts.get("percent", 0.0) / 100) * parts.get("variance", 1.0) * parts.get("magic", 1.0)
    return value, [["base", base], ["percent", parts.get("percent", 0.0)], ["variance", parts.get("variance", 1.0)], ["magic", parts.get("magic", 1.0)]]


def mitigate(parts: dict) -> tuple[float, list]:
    """Gear defence after armour: x max(0.05, 1 - percent / 100), then - flat, never below a tenth of what came in."""
    before = parts["amount"]
    after = before * max(0.05, 1 - parts.get("percent", 0.0) / 100)
    cut_pct = before - after
    step = after
    after = max(before * 0.1, after - parts.get("flat", 0.0))
    return after, [["gear defence", cut_pct], ["flat defence", step - after]]


def pools(parts: dict) -> tuple[float, list]:
    """A pool's maximum: raw x (1 + percent) + flat, then hunger and fatigue (a percent penalty)."""
    total = parts["raw"] * (1 + parts.get("percent", 0.0)) + parts.get("flat", 0.0)
    needs = parts.get("needs", 0.0)
    if needs:
        total *= 1 + needs / 100
    return total, [["raw", parts["raw"]], ["percent", parts.get("percent", 0.0)], ["flat", parts.get("flat", 0.0)], ["needs", needs]]


def resistance(parts: dict) -> tuple[float, list]:
    """The share of a hit that gets through: the resistances summed and clamped (floor 0 for a kind of damage, -100 for an element,
    which may be a weakness; cap elements.yaml resist_cap), as 1 - the clamped percent / 100."""
    total = sum(parts.get("values") or [])
    clamped = max(parts.get("floor", 0), min(parts["cap"], total))
    return 1 - clamped / 100, [["sum", total], ["clamp", clamped]]


def mechanics(parts: dict) -> tuple[dict, list]:
    """Every mechanic active for a fighter: legendary gear, relic buffs and conditional passives add."""
    out: dict[str, float] = {}
    for source in parts.get("sources") or []:
        for k, v in source.items():
            out[k] = out.get(k, 0) + v
    return out, [["additive", len(parts.get("sources") or [])]]


RECIPES: dict[str, Callable[[dict], tuple]] = {"base_damage": base_damage, "mitigate": mitigate, "pools": pools,
                                               "resistance": resistance, "mechanics": mechanics}
PARTS: dict[str, tuple[str, ...]] = {"base_damage": ("flat", "percent"), "mitigate": ("percent", "flat"), "pools": ("percent", "flat", "needs"),
                                     "resistance": ("sum", "clamp"), "mechanics": ("additive",)}


def combine(recipe: str, parts: dict) -> tuple:
    """The value a recipe gives these parts, and the parts it applied in order."""
    return RECIPES[recipe](parts)

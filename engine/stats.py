"""Starting attribute rules. Values live in data/rules/progression.yaml."""

from pathlib import Path

import yaml

from core.models import Attributes

RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "progression.yaml").read_text(encoding="utf-8"))

STAT_NAMES = list(Attributes.model_fields)
BASE = int(RULES["starting_base"])
POINTS = int(RULES["starting_points"])
CAP = int(RULES["starting_cap"])
PRIORITY_TEMPLATE = list(RULES["priority_template"])
TOTAL = BASE * len(STAT_NAMES) + POINTS

_problems = []
if len(PRIORITY_TEMPLATE) != len(STAT_NAMES):
    _problems.append(f"priority_template needs {len(STAT_NAMES)} values")
if sum(PRIORITY_TEMPLATE) != TOTAL:
    _problems.append(f"priority_template adds up to {sum(PRIORITY_TEMPLATE)}, but the starting total is {TOTAL}")
if any(not BASE <= v <= CAP for v in PRIORITY_TEMPLATE):
    _problems.append(f"priority_template values must be between {BASE} and {CAP}")
if _problems:
    raise ValueError("progression.yaml: " + "; ".join(_problems))


def rules_text() -> str:
    return (
        f"Every attribute starts at {BASE}. You have {POINTS} points to add. "
        f"No attribute may go above {CAP} at the start. "
        f"The six attributes must total {TOTAL}."
    )


def check_allocation(values: dict[str, int]) -> str | None:
    low = [k for k in STAT_NAMES if values[k] < BASE]
    if low:
        return f"{', '.join(low)} cannot go below {BASE}."
    high = [k for k in STAT_NAMES if values[k] > CAP]
    if high:
        return f"{', '.join(high)} cannot go above {CAP} at the start."
    total = sum(values[k] for k in STAT_NAMES)
    if total < TOTAL:
        return f"{TOTAL - total} points are still unspent."
    if total > TOTAL:
        return f"that uses {total - TOTAL} more points than are available."
    return None


EXTREME = ("everything", "all of it", "all in", "max", "limit", "as high as", "as far", "as much as")


def wants_extreme(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in EXTREME)


def from_priorities(priorities: list[str], extreme: bool = False) -> dict[str, int]:
    order = list(dict.fromkeys(p for p in priorities if p in STAT_NAMES))
    order += [s for s in STAT_NAMES if s not in order]
    values = list(PRIORITY_TEMPLATE)
    if extreme and values[0] < CAP:           # 'as far past the limit as possible' means the cap, taking the points from the others
        extra = CAP - values[0]
        values[0] = CAP
        for i in range(len(values) - 1, 0, -1):
            take = min(extra, values[i] - BASE)
            values[i] -= take
            extra -= take
    return dict(zip(order, values))


def gear_attributes(c) -> dict[str, int]:
    """The attribute points a character's gear adds ({} if none)."""
    from engine import items
    out: dict[str, int] = {}
    for item in c.equipment.values():
        for e in items.effects(item):
            if e.flat and e.modifies in STAT_NAMES and e.trigger == "always":
                out[e.modifies] = out.get(e.modifies, 0) + e.magnitude
    return out


def effective(c, name: str, gear: dict | None = None) -> int:
    """An attribute with the points gear adds."""
    gear = gear_attributes(c) if gear is None else gear
    return getattr(c.attributes, name) + gear.get(name, 0)

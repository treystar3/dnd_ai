"""Elements: which kind of damage an attack carries, read from words (data/rules/elements.yaml)."""
import re
from pathlib import Path

import yaml

R = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "elements.yaml").read_text(encoding="utf-8"))
ELEMENTS = list(R["elements"])
CAP = R["resist_cap"]
_PATTERNS = {e: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + ")") for e, kws in R["elements"].items()}


WHEEL = list(R.get("wheel") or [])
BORROW = float(R.get("borrow_chance", 0))


def neighbors(element: str) -> list[str]:
    """The two elements beside this one on the wheel (f266) - the only ones it borrows effects from."""
    if element not in WHEEL:
        return []
    i = WHEEL.index(element)
    return [WHEEL[(i - 1) % len(WHEEL)], WHEEL[(i + 1) % len(WHEEL)]]


def of_text(text: str) -> str:
    """The element a piece of text describes ('' if none): the one it names most."""
    t = text.lower().replace("_", " ")
    best, top = "", 0
    for e, pat in _PATTERNS.items():
        n = len(pat.findall(t))
        if n > top:
            best, top = e, n
    return best


def of_creature(creature) -> str:
    name = f"{creature.id} {creature.name}".lower().replace("_", " ")
    for hint, e in R["creature_hints"].items():
        if hint in name:
            return e
    return of_text(f"{name} {' '.join(creature.attacks)}")

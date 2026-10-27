"""What a speaker can lay hands on, and how tense the moment is (f344). Pure assembly: no model calls, no printing.

The dialogue frames say what someone does as they speak. Left to itself a small model gives everyone one habit - a tester's Maren had a
hand on her sword hilt in ten frames of nineteen, because her only example gesture was the hilt and the sword her only prop. Instead of
policing the habit, the frame is shown what is really there: the speaker's own tools (data/rules/reach.yaml by trade), the place they
stand in, what they sell and keep in stock, what lies on the ground, what they carry. And it is told the moment: easy, or tense and why
(a stranger who may be a bandit, someone the watch wants, a captor and their prisoner, a fight). Hands then follow the world: the smith
works the iron, the clerk stamps a slip, Maren's hand stays near the hilt while she weighs a stranger and comes away once she knows them."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
R = yaml.safe_load((ROOT / "data" / "rules" / "reach.yaml").read_text(encoding="utf-8"))
EASY = "easy"


def within(role: str = "", place_type: str = "", carries: list[str] | None = None, wares: list[str] | None = None,
           ground: list[str] | None = None) -> list[str]:
    """The things this speaker can lay hands on now, most their own first, at most R['most']. Nothing repeated."""
    out: list[str] = []
    for group in (list(carries or ()), list(R["tools"].get(role, ())), list(wares or ())[:2], list(R["places"].get(place_type, ())),
                  list(ground or ())[:2]):
        for thing in group:
            thing = " ".join(str(thing).split())
            if thing and thing.lower() not in (x.lower() for x in out):
                out.append(thing)
    return out[:R["most"]]


def moment(role: str = "", trust: int | None = None, heat_tier: str = "", fight: bool = False, wary: str = "") -> str:
    """'easy', or 'tense - why'. `wary` is a reason the caller already knows (Maren weighing a stranger)."""
    T = R["tense"]
    if fight:
        return "tense - in the middle of a fight"
    if wary:
        return f"tense - {wary}"
    if role in T["roles"]:
        return "tense - a prisoner facing the one who holds them"
    if role in T["watch_roles"] and heat_tier in ("confront", "wanted"):
        return "tense - the watch wants this stranger, and this one is the watch"
    if trust is not None and trust < T["trust_below"]:
        return "tense - they distrust the stranger"
    return EASY


def problems(roles: set[str], place_types: set[str]) -> list[str]:
    """A trade or a place type in data/rules/reach.yaml that the world does not have, or a trade with nothing to hand."""
    bad = [f"reach.yaml tools: '{r}' is not a role" for r in R["tools"] if r not in roles]
    bad += [f"reach.yaml tools: the role '{r}' has nothing listed to hand" for r in sorted(roles) if not R["tools"].get(r)]
    bad += [f"reach.yaml places: '{t}' is no place's type" for t in R["places"] if t not in place_types]
    bad += [f"reach.yaml tense: '{r}' is not a role" for r in R["tense"]["roles"] + R["tense"]["watch_roles"] if r not in roles]
    if not isinstance(R.get("most"), int) or R["most"] < 1:
        bad.append("reach.yaml most: needs a whole number of at least 1")
    return bad

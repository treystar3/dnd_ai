"""(f499) What a fight remembers of itself between rounds, on the saved fight (pillar 1: a fight remembers the same in-process and after
a reload; decision 2): the player's quarry (one row a fight), who placed a withering affliction (one row an afflicted fighter), the last
heal (one row a fight). An ActiveEffect is a row of the fight's `effects` list (engine/combat.py Combat), written by the perks and the
heals and read back by them, so a mark is in the row the save holds, goes back with the row when a round rolls back, and goes with the
row when the fight ends. The list is capped at combat.yaml effects_keep: the oldest expired rows go first, then the oldest."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class EffectDef(BaseModel):
    """(f504) A kind of effect a fight carries between rounds, as data/rules/active_effects.yaml declares it: its family (one of
    FAMILIES), how it ends (EXPIRY), what a second landing does (STACKING), and for a status the combat.yaml row that holds its stat
    deltas. Frozen: a kind is read, never changed in play."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    family: str
    expiry: str
    stacking: str
    deltas: str = ""


_T = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "active_effects.yaml").read_text(encoding="utf-8"))
FAMILIES: tuple[str, ...] = tuple(_T["families"])
EXPIRY: tuple[str, ...] = tuple(_T["expiry"])
STACKING: tuple[str, ...] = tuple(_T["stacking"])
KINDS: dict[str, EffectDef] = {k: EffectDef(id=k, **v) for k, v in _T["kinds"].items()}


class ActiveEffect(BaseModel):
    id: str                      # one a kind for the fight (quarry, last_heal), or one a fighter (withering:<fighter id>)
    kind: str                    # quarry | withering | last_heal
    family: str = ""             # mark | affliction | heal
    source: str = ""             # the fighter who placed it
    target: str = ""             # the fighter it is on
    until: int = 0               # the last round it holds for; 0 while the fight lasts
    left: int = 0                # rounds left, for a kind that counts down
    charges: int = 0             # uses left, for a kind that spends
    value: float = 0.0           # what it carries (a heal's size)
    data: dict = {}


def keep() -> int:
    from engine import combat
    return int(combat.RULES.get("effects_keep", 64))


def expired(e: ActiveEffect, round_: int) -> bool:
    return bool(e.until) and round_ > e.until


def put(combat, e: ActiveEffect) -> ActiveEffect:
    """Keep this row on the fight, in place of the row with its id, and the list within its cap."""
    rows = [r for r in combat.effects if r.id != e.id]
    rows.append(e)
    combat.effects = cap(rows, combat.round)
    return e


def cap(rows: list, round_: int, limit: int | None = None) -> list:
    """At most `limit` rows: the oldest expired go first, then the oldest."""
    limit = keep() if limit is None else limit
    rows = list(rows)
    while len(rows) > limit:
        gone = next((r for r in rows if expired(r, round_)), rows[0])
        rows.remove(gone)
    return rows


def get(combat, kind: str, target: str = "") -> ActiveEffect | None:
    """The row of this kind (on this fighter, when one is named), or None."""
    for r in combat.effects:
        if r.kind == kind and (not target or r.target == target):
            return r
    return None


def drop(combat, kind: str, target: str = "") -> None:
    combat.effects = [r for r in combat.effects if not (r.kind == kind and (not target or r.target == target))]

"""(f394) The turn's record: what happened, as typed rows, in one place (BUILD_PLAN.md: KEEP and TELL).

The engine used to report each outcome twice, as text, to two readers who never compared notes: the player read the notes, the narrator
a loose description and the player's own words. A row here is what the engine did: `moved` to a part of a place, `found` a part,
`made` an addition to the world, `refused` an attempt it said no to, and the rest as later slices add them. The narrator is given the
turn's rows (told()); a night counts them (each turn row keeps this_turn()); the acceptance scenes count `made` (count()).

begin() opens a turn and end() closes it (the scene's turn does both); add() outside a turn still counts, and is told with the next."""
from __future__ import annotations

import collections

ROWS: list[dict] = []                         # this turn's
LAST: list[dict] = []                         # the last turn's, once it has ended (a night's harness reads it)
TOTALS: collections.Counter = collections.Counter()


def begin() -> None:
    ROWS.clear()


def end() -> list[dict]:
    out = list(ROWS)
    ROWS.clear()
    return out


def add(kind: str, **fields) -> dict:
    row = {"kind": kind, **fields}
    ROWS.append(row)
    TOTALS[kind] += 1
    return row


def this_turn() -> list[dict]:
    return list(ROWS)


def count(kind: str) -> int:
    return TOTALS[kind]


def told() -> list[str]:
    """The turn's rows as the narrator is given them: plain facts, the engine's, to tell and never contradict."""
    out = []
    for r in ROWS:
        if r.get("say"):
            out.append(r["say"])
    return out

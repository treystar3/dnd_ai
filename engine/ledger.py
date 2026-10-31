"""(f394) The turn's record: what happened, as typed rows, in one place (BUILD_PLAN.md: KEEP and TELL).

The engine used to report each outcome twice, as text, to two readers who never compared notes: the player read the notes, the narrator
a loose description and the player's own words. A row here is what the engine did: `moved` to a part of a place, `found` a part,
`made` an addition to the world, `refused` an attempt it said no to, `changed` a part made different by an attempt (f395), and the rest
as later slices add them. The narrator is given the
turn's rows (told()); a night counts them (each turn row keeps this_turn()); the acceptance scenes count `made` (count()).

begin() opens a turn and end() closes it (the scene's turn does both); add() outside a turn still counts, and is told with the next.

(f416) Every writer reads the same rows. A narrator is told each row once (told() marks what it hands over, so a second passage in the
turn does not tell it again); a person answering the player reads all of the turn's rows so far, told or not (decided()), so they never
answer a deal or a refusal the engine has already settled the other way. The kinds are declared below, so a row of a kind nobody declared
is a bug caught at once. Rows live one turn."""
from __future__ import annotations

import collections

KINDS = {                                     # what each row means; add() refuses any other kind
    "made": "an addition to the world, real from now on",
    "refused": "a step the game said no to: what did not happen, and why",
    "not_done": "steps the game did not get to this turn",
    "changed": "a part of the place made different by an attempt",
    "moved": "the player went to a part of the place",
    "found": "a part of the place, a clue, a cache or a resource found",
    "closed": "a way that is shut",
    "hurt": "the player hurt by the place",
    "end": "no way further in",
    "tended": "a companion saw to the player's wounds",
    "took": "a contract or request taken on",
    "gained": "a thing now in the player's pack",
    "left": "a thing left lying here, not taken",
    "paid": "coin the player paid out",
    "received": "coin paid to the player",
    "departed": "someone gone from the place",
    "worked": "work done for someone",
    "gathered": "herbs or materials gathered",
    "ended": "a matter brought to an end",
}
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
    if kind not in KINDS:
        raise ValueError(f"ledger row of an undeclared kind: {kind}")
    row = {"kind": kind, **fields}
    ROWS.append(row)
    TOTALS[kind] += 1
    return row


def this_turn() -> list[dict]:
    return list(ROWS)


def count(kind: str) -> int:
    return TOTALS[kind]


def told() -> list[str]:
    """The turn's rows as the narrator is given them: plain facts, the engine's, to tell and never contradict. Each is handed over once:
    (f416) a row told in one passage is not told again in the next."""
    out = []
    for r in ROWS:
        if r.get("say") and not r.get("told"):
            out.append(r["say"])
            r["told"] = True
    return out


def untold() -> list[str]:
    """(f416) What the turn did that no passage has told yet, without marking it."""
    return [r["say"] for r in ROWS if r.get("say") and not r.get("told")]


def decided() -> list[str]:
    """(f416) Everything the engine has settled this turn so far, told or not: what a person answering the player must not contradict."""
    return [r["say"] for r in ROWS if r.get("say")]

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
is a bug caught at once. Rows live one turn.

(f633) The turn's rows, the last turn's and the totals are the turn's registers (engine/actor.py Registers)."""
from __future__ import annotations

from engine import actor

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
    "carried": "a thing in the world the player carries in hand, no item of the pack",
    "left": "a thing left lying here, not taken",
    "paid": "coin the player paid out",
    "given": "coin or a thing the player handed to a companion",
    "received": "coin paid to the player",
    "departed": "someone gone from the place",
    "worked": "work done for someone",
    "gathered": "herbs or materials gathered",
    "ended": "a matter brought to an end",
}


def begin() -> None:
    actor.registers().rows.clear()


def end() -> list[dict]:
    """The turn is over: its rows become the last turn's (last()), and are returned."""
    mine = actor.registers()
    mine.last = list(mine.rows)
    mine.rows.clear()
    return mine.last


def last() -> list[dict]:
    """The last turn's rows, once it has ended: what the recorder writes after an input, and a night's harness reads. The list
    itself, a new one at each turn's end."""
    return actor.registers().last


def totals() -> dict[str, int]:
    """How many rows of each kind stand, over the campaign so far."""
    return dict(actor.registers().totals)


def _take_back(mine, rows) -> None:
    for r in rows:
        mine.totals[r["kind"]] -= 1
        if mine.totals[r["kind"]] <= 0:
            del mine.totals[r["kind"]]


def rollback() -> None:
    """(f455) The turn rolled back: its rows are taken back and the totals with them. The last turn's stay those of the last turn that
    stood, which is what the recorder writes after an input and the replayer compares."""
    mine = actor.registers()
    _take_back(mine, mine.rows)
    mine.rows.clear()


def add(kind: str, facts: dict | None = None, **fields) -> dict:
    """A row of the turn's record. (f462) `facts` are the labels a stand-in line is filled from when the row's telling cannot be written
    (engine/failures.py stood_lines: what, who, amount), never ids; and when an operation is open (engine/operation.py) the row carries
    its id and the operation keeps the row, so a rollback of that one operation takes back its rows alone (rollback_op)."""
    if kind not in KINDS:
        raise ValueError(f"ledger row of an undeclared kind: {kind}")
    row = {"kind": kind, **fields}
    if facts:
        row["facts"] = {k: str(v) for k, v in facts.items() if v not in (None, "")}
    from engine import operation
    op = operation.current()
    if op is not None:
        row["op"] = op.id
        op.rows.append(row)
    mine = actor.registers()
    mine.rows.append(row)
    mine.totals[kind] += 1
    return row


def rollback_op(op_id: str) -> None:
    """(f462) One operation rolled back: its rows and their totals go; the rest of the turn's stay."""
    mine = actor.registers()
    _take_back(mine, [r for r in mine.rows if r.get("op") == op_id])
    mine.rows[:] = [r for r in mine.rows if r.get("op") != op_id]


def this_turn() -> list[dict]:
    """The turn's rows so far, in order: the rows themselves in a list of the caller's own."""
    return list(actor.registers().rows)


def count(kind: str) -> int:
    return actor.registers().totals[kind]


def told(but: tuple[str, ...] = ()) -> list[str]:
    """The turn's rows as the narrator is given them: plain facts, the engine's, to tell and never contradict. Each is handed over once:
    (f416) a row told in one passage is not told again in the next. but: kinds the caller tells under heads of its own (the passage after
    a fight lists what was found and what was left), marked told and not returned."""
    out = []
    for r in actor.registers().rows:
        if r.get("say") and not r.get("told"):
            if r["kind"] not in but:
                out.append(r["say"])
            r["told"] = True
    return out


def untold() -> list[str]:
    """(f416) What the turn did that no passage has told yet, without marking it."""
    return [r["say"] for r in actor.registers().rows if r.get("say") and not r.get("told")]


def decided() -> list[str]:
    """(f416) Everything the engine has settled this turn so far, told or not: what a person answering the player must not contradict."""
    return [r["say"] for r in actor.registers().rows if r.get("say")]


actor.moved(__name__, {"ROWS": "ledger.this_turn()", "LAST": "ledger.last() (ledger.end() keeps it)", "TOTALS": "ledger.totals() or ledger.count(kind)"})

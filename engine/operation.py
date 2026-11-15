"""(f462) The operation: the unit the rebuild's Stage 3 commits. A typed line is one or more operations (f463: the understanding and the
first action, each later step, the pulse, the arrival, the tail; a pane command; a fight's round), and each is one all-or-nothing write
with its own record in the save, so what the player did is never undone because what came after it failed (Bundle C decision 1), and a
game closed between a commit and its telling can tell it at the next load (decision 8, f467).

This feature is the record alone, behaviour-neutral: nothing opens an operation yet (f463 does). storage/campaign.py keeps the record in
the kv rows `operations` (the last RETENTION["operations"] records and a revision every commit must have seen, so two writers can never
commit over each other: StaleOperation) and `presentation` (the lines of each operation not yet shown, cleared by mark_shown). Both are
outside the state digest (storage/statehash.py NOT_STATE_ROWS): the record describes the state's history and its telling, it is not the
state, and a replay compares it through the recording instead. The ids come from a stream of their own (engine/streams.py
new_id(stream="ops")), so drawing them moves no other die. (f633) The operation open now, what reached the page and the calls
made inside a transaction are the turn's registers (engine/actor.py Registers), read and written through the functions here."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from core import yamlio
from engine import actor as _actor
from engine import streams

_B = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8"))
RETENTION: dict = dict(_B.get("retention") or {})      # operations: records kept; deferred_turns: how long a deferred call waits (f469)
ID_DIGITS = 12


@dataclass
class Operation:
    id: str
    kind: str                       # what it is: line, action:<kind>, passage, round, aftermath, goddess, world, arrival, law, tail, command:<name>, world:open
    steps: int                      # the input it belongs to (CampaignMeta.steps)
    index: int                      # its place in the line, from 0
    revision_seen: int              # the record's revision when it opened; a commit over another revision is stale
    text: str = ""                  # the typed line, for the record
    rows: list = field(default_factory=list)       # the ledger rows it committed (engine/ledger.py add stamps them with its id)
    lines: list = field(default_factory=list)      # what it will show, held until it commits (f463) and kept until shown (f467)
    state: str = "open"             # open | committed | rolled_back
    held: list = field(default_factory=list, repr=False)   # (f463) the story calls held back (name, args, kwargs), released at commit; not kept
    failure: str = ""               # (f466) why it did not stand, for the turn log: the model's failure, or the game's own fault
    crashed: bool = False           # (f466) ...and which of the two
    void: bool = False              # (f470) nothing took the line inside it: ended without a record, nothing written, nothing shown
    actor: str = ""                 # (f629) the character whose entry opened it (engine/actor.py who); "" when none was bound
    did: list = field(default_factory=list)        # (f644) what it did, in the player's terms, said as it ran; kept for the line, not saved
    speech: bool = False            # (f644) it did not stand because someone's spoken words could not be written

    def record(self) -> dict:
        """What the save keeps of it: no lines (they are the presentation entry's) and no state (a record is a commit)."""
        return {"id": self.id, "kind": self.kind, "steps": self.steps, "index": self.index, "text": self.text, "rows": list(self.rows),
                "actor": self.actor}

    def presentation(self) -> list:
        """(f467) What it holds, as the calls the next load can make again through the installed bindings (scenes/world.py
        recover_unshown): [name, args, kwargs] for each story call, ["marker", [], {}] where a passage was to be told (a telling never
        written: the record's rows stand in for it). A legendary reveal is kept as a note naming the find. Plain JSON, nothing else."""
        import json
        out = []
        for name, a, k in self.held:
            if name in ("combat_state", "combat_panel"):           # (f497) the fight's pane: load re-shows it from the row (scenes/world.py enter)
                continue
            if name == "marker":
                out.append(["marker", [], {}])
            elif name == "legendary_reveal":
                from engine import items
                out.append(["note", [f"A legendary find: {items.display_name(a[0])}."], {}])
            else:
                out.append(json.loads(json.dumps([name, list(a), dict(k)], default=str)))
        return out


PRESENTED_KEEP = 400              # (f467) what reached the page is taken per input by the recorder; without one, the last few hundred are kept
TELLING = {"passage", "round", "aftermath", "goddess", "opening"}   # (f470) operations that are the call itself (the telling): not counted; (f498) the fight's opening


def note_legacy(task: str) -> None:
    """(f470) A model call made while an operation is open: the save waits on the model inside a transaction (the survey's smell; the
    plan's prepare-then-commit reads committed state before the call and commits after it). The telling operations are their one call
    and are not counted. What is left is named, once each, for the ratchet. (f520) Only a call on the operation's own thread: the people
    written behind the scenes at the same moment wait on no transaction of the turn's."""
    op, kept = current(), _actor.registers().legacy
    if op is not None and op.kind not in TELLING and task not in kept:
        kept.append(task)


def legacy() -> list[str]:
    """(f470) The tasks asked for while an operation held the save's transaction open, once each, in order: the residue
    prepare-then-commit moves out family by family (the ratchet of tools/sim/prepared_470_test.py only shrinks)."""
    return list(_actor.registers().legacy)


def present(op_id: str, how: str) -> None:
    """(f467) An operation's outcome reached the page: shown at its commit, told by a stand-in, or recovered at a load."""
    reached = _actor.registers().presented
    reached.append({"op": op_id, "how": how})
    del reached[:-PRESENTED_KEEP]


def presented() -> list[dict]:
    """(f467) What reached the page since it was last taken, in order: {"op": id, "how": shown | stand_in | recovered}."""
    return list(_actor.registers().presented)


def take_presented() -> list[dict]:
    """...and it is taken: the recorder writes it with each input and leaves none (engine/recording.py, tools/rerun.py)."""
    mine = _actor.registers()
    out, mine.presented = mine.presented, []
    return out


def begin(kind: str, steps: int, index: int, revision_seen: int, text: str = "", op_id: str = "") -> Operation:
    """Open an operation, the one open now, with an id drawn from the ops stream. (f466) Or with `op_id`, one the caller drew from that
    stream before, to look for its record first: the game's opening operation (scenes/world.py open_world) repeats its id at the same
    count of inputs, so an open after a stood one finds it committed and runs nothing."""
    mine = _actor.registers()
    if mine.operation is not None:
        raise RuntimeError(f"an operation is already open: {mine.operation.kind} {mine.operation.id}")
    op = Operation(op_id or streams.new_id(ID_DIGITS, stream="ops"), kind, steps, index, revision_seen, text, actor=_actor.who())
    mine.claim()                                    # (f633) the turn is the thread's that opened it
    mine.operation = op
    return op


def did(what: str) -> None:
    """(f644) The open operation did this, in the player's terms (a step's summary, what was handed in and paid): what a line that
    stood in part names, if this operation commits. Said outside any operation, it is said to nobody."""
    op = current()
    if op is not None and what:
        op.did.append(what)


def current() -> Operation | None:
    """The operation open now, on this thread. (f520) It belongs to the thread that plays the turn: a call made on another thread
    at the same moment (the people written behind the scenes) is no part of it, so it is not filed under it (the recorder's and the
    audit's op, the ledger's stamp) nor counted as waiting inside its transaction (note_legacy)."""
    mine = _actor.registers()
    return mine.operation if mine.mine() else None


def opened() -> Operation | None:
    """The operation open now, whichever thread asks: for the session's residue and a test, never for filing a call."""
    return _actor.registers().operation


def end(state: str) -> Operation | None:
    """Close the open operation as committed or rolled_back; None if none was open."""
    mine = _actor.registers()
    op, mine.operation = mine.operation, None
    mine.release()
    if op is not None:
        op.state = state
    return op


_actor.moved(__name__, {"CURRENT": "operation.current(), or operation.opened() from any thread", "PRESENTED": "operation.presented() or take_presented()",
                        "LEGACY": "operation.legacy()"})

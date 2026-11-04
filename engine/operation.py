"""(f462) The operation: the unit the rebuild's Stage 3 commits. A typed line is one or more operations (f463: the understanding and the
first action, each later step, the pulse, the arrival, the tail; a pane command; a fight's round), and each is one all-or-nothing write
with its own record in the save, so what the player did is never undone because what came after it failed (Bundle C decision 1), and a
game closed between a commit and its telling can tell it at the next load (decision 8, f467).

This feature is the record alone, behaviour-neutral: nothing opens an operation yet (f463 does). storage/campaign.py keeps the record in
the kv rows `operations` (the last RETENTION["operations"] records and a revision every commit must have seen, so two writers can never
commit over each other: StaleOperation) and `presentation` (the lines of each operation not yet shown, cleared by mark_shown). Both are
outside the state digest (storage/statehash.py NOT_STATE_ROWS): the record describes the state's history and its telling, it is not the
state, and a replay compares it through the recording instead. The ids come from a stream of their own (engine/streams.py
new_id(stream="ops")), so drawing them moves no other die. CURRENT is the operation open now, if any; the session owns it
(engine/session.py), as it owns the ledger's rows."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from engine import streams

_B = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8"))
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

    def record(self) -> dict:
        """What the save keeps of it: no lines (they are the presentation entry's) and no state (a record is a commit)."""
        return {"id": self.id, "kind": self.kind, "steps": self.steps, "index": self.index, "text": self.text, "rows": list(self.rows)}

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


CURRENT: Operation | None = None
PRESENTED: list = []              # (f467) what reached the page, in order: {"op": id, "how": shown | stand_in | recovered}; the recorder
PRESENTED_KEEP = 400              # writes it per input and clears it (engine/recording.py); without one it is kept to the last few hundred


LEGACY: list[str] = []            # (f470) the tasks the model was asked for while an operation held the save's transaction open: the
                                  # residue prepare-then-commit moves out family by family; the test's ratchet (prepared_470_test RECORDED) only shrinks
TELLING = {"passage", "round", "aftermath", "goddess", "opening"}   # (f470) operations that are the call itself (the telling): not counted; (f498) the fight's opening


def note_legacy(task: str) -> None:
    """(f470) A model call made while an operation is open: the save waits on the model inside a transaction (the survey's smell; the
    plan's prepare-then-commit reads committed state before the call and commits after it). The telling operations are their one call
    and are not counted. What is left is named, once each, for the ratchet."""
    op = CURRENT
    if op is not None and op.kind not in TELLING and task not in LEGACY:
        LEGACY.append(task)


def present(op_id: str, how: str) -> None:
    """(f467) An operation's outcome reached the page: shown at its commit, told by a stand-in, or recovered at a load."""
    PRESENTED.append({"op": op_id, "how": how})
    del PRESENTED[:-PRESENTED_KEEP]


def begin(kind: str, steps: int, index: int, revision_seen: int, text: str = "", op_id: str = "") -> Operation:
    """Open an operation, the one open now, with an id drawn from the ops stream. (f466) Or with `op_id`, one the caller drew from that
    stream before, to look for its record first: the game's opening operation (scenes/world.py open_world) repeats its id at the same
    count of inputs, so an open after a stood one finds it committed and runs nothing."""
    global CURRENT
    if CURRENT is not None:
        raise RuntimeError(f"an operation is already open: {CURRENT.kind} {CURRENT.id}")
    CURRENT = Operation(op_id or streams.new_id(ID_DIGITS, stream="ops"), kind, steps, index, revision_seen, text)
    return CURRENT


def current() -> Operation | None:
    return CURRENT


def end(state: str) -> Operation | None:
    """Close the open operation as committed or rolled_back; None if none was open."""
    global CURRENT
    op, CURRENT = CURRENT, None
    if op is not None:
        op.state = state
    return op


def reset() -> None:
    """(engine/session.py) A campaign opened or closed: no operation of another campaign's stays open, and nothing it showed is carried."""
    global CURRENT
    CURRENT = None
    PRESENTED.clear()
    LEGACY.clear()

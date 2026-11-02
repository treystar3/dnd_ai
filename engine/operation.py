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
    kind: str                       # what it is: action:<kind>, understanding, pulse, arrival, tail, command:<name>, round, world:open
    steps: int                      # the input it belongs to (CampaignMeta.steps)
    index: int                      # its place in the line, from 0
    revision_seen: int              # the record's revision when it opened; a commit over another revision is stale
    text: str = ""                  # the typed line, for the record
    rows: list = field(default_factory=list)       # the ledger rows it committed (engine/ledger.py add stamps them with its id)
    lines: list = field(default_factory=list)      # what it will show, held until it commits (f463) and kept until shown (f467)
    state: str = "open"             # open | committed | rolled_back
    held: list = field(default_factory=list, repr=False)   # (f463) the story calls held back (name, args, kwargs), released at commit; not kept

    def record(self) -> dict:
        """What the save keeps of it: no lines (they are the presentation entry's) and no state (a record is a commit)."""
        return {"id": self.id, "kind": self.kind, "steps": self.steps, "index": self.index, "text": self.text, "rows": list(self.rows)}


CURRENT: Operation | None = None


def begin(kind: str, steps: int, index: int, revision_seen: int, text: str = "") -> Operation:
    """Open an operation, the one open now, with an id drawn from the ops stream."""
    global CURRENT
    if CURRENT is not None:
        raise RuntimeError(f"an operation is already open: {CURRENT.kind} {CURRENT.id}")
    CURRENT = Operation(streams.new_id(ID_DIGITS, stream="ops"), kind, steps, index, revision_seen, text)
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
    """(engine/session.py) A campaign opened or closed: no operation of another campaign's stays open."""
    global CURRENT
    CURRENT = None

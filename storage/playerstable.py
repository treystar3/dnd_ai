"""(f638) Where a save keeps its characters' records (docs/design/13; docs/design/20_phase3_plan.md; multiplayer, GOALS.md checklist 8).

Until version 17 a save kept its one player as one row of the small table, under the key 'player'. The store's load, save, exists and raw text
(storage/campaign.py) reach that record through a port, and there are two: RowPlayers is that row, and TablePlayers is a table
with a row for each character, the first under the id the save's one character has always had. A row's json is the record as
the row would have written it, and the only thing read back; its place is read from it when it is written, for a query to find
who stands somewhere.

What a record is stays the store's: a hire's memories are rows of their own, and the clock is written with the player in one
transaction. A port only says where the record's text is kept.

(f640) A save's players are the table's from version 17. The row is what an older save is read from until its step, which is `adopt`.
"""
from __future__ import annotations

import json

from core.models import Character

KEY = "player"                                         # the row of the small table a save keeps its one player in
FIRST = Character.model_fields["id"].default           # the save's first character: the one that row has always held
TABLE = "players"
# no index: a save holds a party's worth of characters, and the key finds one
STATEMENTS = [f'CREATE TABLE IF NOT EXISTS "{TABLE}" (character_id TEXT PRIMARY KEY, place TEXT NOT NULL, json TEXT NOT NULL)']
DDL = ";\n".join(STATEMENTS) + ";\n"                   # one text for a new save and for the migration


def text_of(body: dict) -> str:
    """A record as it is stored: the same text over the row and over the table."""
    return json.dumps(body, ensure_ascii=False)


def place_of(body) -> str:
    """A row's place, read from its record: where the character stands, or "" for a record that does not say."""
    value = body.get("location") if isinstance(body, dict) else None
    return value if isinstance(value, str) else ""


class RowPlayers:
    """(f638) The one record a save holds, in the small table's row. It answers for the first character and has no other."""

    def __init__(self, store):
        self._store = store

    def text(self, who: str = FIRST) -> str | None:
        return self._store._kv_text(KEY) if who == FIRST else None

    def exists(self, who: str = FIRST) -> bool:
        return self.text(who) is not None

    def ids(self) -> list[str]:
        return [FIRST] if self.exists() else []

    def put(self, body: dict, who: str = FIRST) -> None:
        if who != FIRST:
            raise ValueError(f"this save keeps one character's record: there is no row for '{who}'")
        self._store._put(KEY, text_of(body))


class TablePlayers:
    """(f638) A row for each character. The same port as RowPlayers, answered the same for the first."""

    def __init__(self, store):
        self._store = store

    def text(self, who: str = FIRST) -> str | None:
        with self._store._lock:
            row = self._store._db.execute(f'SELECT json FROM "{TABLE}" WHERE character_id = ?', (who,)).fetchone()
        return row[0] if row else None

    def exists(self, who: str = FIRST) -> bool:
        return self.text(who) is not None

    def ids(self) -> list[str]:
        """The characters the save holds, in the order they were first saved."""
        with self._store._lock:
            return [r[0] for r in self._store._db.execute(f'SELECT character_id FROM "{TABLE}" ORDER BY rowid')]

    def put(self, body: dict, who: str = FIRST) -> None:
        with self._store._lock:
            self._store._db.execute(f'INSERT INTO "{TABLE}" (character_id, place, json) VALUES (?, ?, ?) '
                                    "ON CONFLICT(character_id) DO UPDATE SET place = excluded.place, json = excluded.json",
                                    (who, place_of(body), text_of(body)))


def ensure(store) -> None:
    """The table, made if it is not there."""
    for statement in STATEMENTS:
        store.execute(statement)


def adopt(store) -> TablePlayers:
    """The store's players are kept in the table from here on: it is made, and the record the row held is moved into it as it
    was, under the first character's id, and the row taken away. What the migration does to a save (v17), and how a test puts the
    table under a store. A save with no player is left with none. Where the table already holds the first character, the row
    is left where it is for the campaign's check to name: the table's record is the later one."""
    ensure(store)
    port = store._players if isinstance(store._players, TablePlayers) else TablePlayers(store)
    with store.transaction():
        text = store._kv_text(KEY)
        if text is not None and not port.exists(FIRST):
            try:
                place = place_of(json.loads(text))
            except ValueError:
                place = ""
            store._db.execute(f'INSERT INTO "{TABLE}" (character_id, place, json) VALUES (?, ?, ?)', (FIRST, place, text))
            store._drop(KEY)
    store._players = port
    return port


def problems(store) -> list[str]:
    """What is wrong in the players table, for the campaign's check (storage/invariants.py): a record that cannot be read, a place
    that is not what its record says, the old row left beside the table. Nothing, for a save without the table."""
    out = []
    with store._lock:
        if not store._db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).fetchone():
            return out
        if store._kv_text(KEY) is not None:
            out.append("the old row of the player's record is still there beside the table")
        for who, place, text in store._db.execute(f'SELECT character_id, place, json FROM "{TABLE}" ORDER BY rowid').fetchall():
            try:
                should = place_of(json.loads(text))
            except ValueError:
                out.append(f"{who}: the record cannot be read")
                continue
            if place != should:
                out.append(f"{who}: place is {place!r}, the record says {should!r}")
    return out

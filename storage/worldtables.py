"""(f637) The world's four lists in tables of their own (docs/design/05 step 6; docs/design/13; docs/design/20_phase3_plan.md).

Until version 17 the world's state was one JSON row, read and written whole (storage/worldrow.py). TableWorld answers the same seam with the
matters, the deeds, the news and the effects each kept as the rows of a table, in the order the list holds them. Every other key
stays in the row, with a marker where each list stood, so the keys load in their order. A row's json is the list's item as the
row would have written it, and the only thing read back; the columns beside it are read from it when it is written, for a query
to find rows by.

`save` means what it meant: the stored world is this dict. It keeps nothing between calls. Inside the caller's transaction it
reads what the tables hold, writes the rows that differ, and always writes the row of the other keys: a rollback takes all of it
back, and an operation that saved the world has written.

(f640) A save's world is the tables' from version 17. The row is what an older save is read from until its step, which is `adopt`.
"""
from __future__ import annotations

import difflib
import json

from core.models import Character
from storage import worldrow
from storage.worldrow import Loaded, effects_matching, threads_matching, deeds_matching, news_matching

KEY = worldrow.RowWorld.KEY
FIRST = Character.model_fields["id"].default            # the save's first character: whose a deed is that names nobody
TEXT, WHOLE = "TEXT", "INTEGER"

# table -> its columns, in order: (column, type, the item's field it is read from)
COLUMNS: dict[str, tuple] = {
    "threads": (("id", TEXT, "id"), ("status", TEXT, "status"), ("place", TEXT, "place")),
    "deeds": (("seq", WHOLE, "seq"), ("minute", WHOLE, "minute"), ("kind", TEXT, "kind"), ("actor", TEXT, "by"), ("place", TEXT, "place")),
    "news": (("minute", WHOLE, "minute"), ("origin", TEXT, "origin"), ("thread", TEXT, "thread")),
    "effects": (("kind", TEXT, "kind"), ("place", TEXT, "place"), ("until", WHOLE, "until"), ("thread", TEXT, "thread")),
}
LISTS = tuple(COLUMNS)
# what the narrow readers ask by (storage/worldrow.py): a matter's status, a deed's minute, an effect's kind and place while it lasts
INDEXES = {"threads_status": ("threads", ("status",)), "deeds_minute": ("deeds", ("minute",)), "effects_where": ("effects", ("kind", "place", "until"))}


def _ddl() -> list[str]:
    out = []
    for table, cols in COLUMNS.items():
        typed = ", ".join(f'"{c}" {t} NOT NULL' for c, t, _ in cols)
        out.append(f'CREATE TABLE IF NOT EXISTS "{table}" (ord INTEGER PRIMARY KEY, {typed}, json TEXT NOT NULL)')
    for name, (table, cols) in INDEXES.items():
        out.append(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ({", ".join(chr(34) + c + chr(34) for c in cols)})')
    return out


STATEMENTS = _ddl()
DDL = ";\n".join(STATEMENTS) + ";\n"                   # one text for a new save and for the migration


def marker(name: str) -> dict:
    """What the row holds where a list stood: the list is the rows of this table. (This very value saved under a list's key, in
    place of a list, would load as the table's rows. Nothing writes one.)"""
    return {"table": name}


def derive(table: str, item) -> tuple:
    """A row's columns, read from its item. A field the item lacks is the column's default ("" or 0); a deed that names nobody is
    the first character's."""
    out = []
    for column, kind, field in COLUMNS[table]:
        value = item.get(field) if isinstance(item, dict) else None
        if kind == WHOLE:
            out.append(int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value
                       and abs(value) != float("inf") else 0)
        else:
            out.append(value if isinstance(value, str) and value else (FIRST if column == "actor" else ""))
    return tuple(out)


def ensure(store) -> None:
    """The four tables and their indexes, made if they are not there."""
    for statement in STATEMENTS:
        store.execute(statement)


def adopt(store) -> "TableWorld":
    """The store's world is kept in the tables from here on: they are made, and the lists the row held are moved into them. What
    the migration does to a save (v17), and how a test puts the tables under a store. A save with no world row is left with none.
    For a store nothing holds a loaded world of: a copy the row loaded, saved after this, is noted as stale."""
    ensure(store)
    world = store._world if isinstance(store._world, TableWorld) else TableWorld(store)
    with store.transaction():
        state = world._state()
        if state is not None:
            world._write(state)
    store._world = world
    return world


def problems(store) -> list[str]:
    """What is wrong between the tables and the row, for the campaign's check (storage/invariants.py): a row whose json cannot be
    read, a column that is not what its json says, rows of a list the world does not hold. Nothing, for a save without the tables."""
    out = []
    with store._lock:
        have = {r[0] for r in store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not set(LISTS) <= have:
            return out
        text = store._kv_text(KEY)
        try:
            held = json.loads(text) if text else {}
        except ValueError:
            return ["the world's row cannot be read"]
        if not isinstance(held, dict):
            return ["the world's row is not a record"]
        for table, cols in COLUMNS.items():
            names = ", ".join(f'"{c}"' for c, _, _ in cols)
            found = store._db.execute(f'SELECT ord, {names}, json FROM "{table}" ORDER BY ord').fetchall()
            if found and held.get(table) != marker(table):
                out.append(f"table {table}: {len(found)} rows of a list the world's row does not point at")
            for r in found:
                try:
                    want = derive(table, json.loads(r[-1]))
                except ValueError:
                    out.append(f"table {table}, row {r[0]}: its json cannot be read")
                    continue
                for (column, _, _), got, should in zip(cols, r[1:-1], want):
                    if got != should:
                        out.append(f"table {table}, row {r[0]}: column {column} is {got!r}, its json says {should!r}")
    return out


class TableWorld:
    """(f637) The world's state with its four lists in tables. The same seam as RowWorld, answered the same."""

    KEY = KEY

    def __init__(self, store):
        self._store = store
        self.stale: list[dict] = []           # the saves the detector caught, as RowWorld keeps them
        self.written = 0                      # rows of the four tables written since this was made (a test's count)

    # ---- the whole state
    def _held(self) -> tuple[dict | None, dict[str, list[str]]]:
        """What is stored: the row as read (None when there is none), and the json of each list's rows, in order, for the lists
        the row points at."""
        with self._store._lock:
            text = self._store._kv_text(KEY)
            if not text:
                return None, {}
            row = json.loads(text)
            return row, {name: [r[0] for r in self._store._db.execute(f'SELECT json FROM "{name}" ORDER BY ord')]
                         for name in LISTS if name in row and row[name] == marker(name)}

    def _state(self) -> dict | None:
        """The world as stored, the lists read back into their places; None when there is no row."""
        state, lists = self._held()
        for name, found in lists.items():
            state[name] = json.loads("[" + ",".join(found) + "]")
        return state

    def _mark(self, held=None) -> str:
        """A digest of what is stored, for the detector: it changes when the row or any list's rows do."""
        row, lists = held or self._held()
        return worldrow._digest(None if row is None else json.dumps(row) + "".join(f"\n{name}\n" + "\n".join(found) for name, found in lists.items()))

    def load(self) -> dict:
        if not worldrow.WATCH_STALE:
            return self._state() or {}
        held = self._held()
        mark = self._mark(held)
        state, lists = held
        for name, found in lists.items():
            state[name] = json.loads("[" + ",".join(found) + "]")
        out = Loaded(state or {})
        out.came_from = mark
        return out

    def save(self, state: dict) -> None:
        made = self._texts(state)
        if worldrow.WATCH_STALE and isinstance(state, Loaded):
            if state.came_from and self._mark() != state.came_from:
                self.stale.append({"site": worldrow._site(), "turn": int(getattr(getattr(self._store, "meta", None), "turn", 0) or 0)})
        self._put(*made)
        if isinstance(state, Loaded):
            state.came_from = self._mark()                # saved: the stored world is now this copy's own

    def _texts(self, state: dict) -> tuple[str, dict[str, tuple[list, list[str]]]]:
        """The row's text, and each list's items with their json. All of it is made before anything is written, as the row's one
        text is: a world that cannot be written writes nothing, whoever catches the error."""
        row, lists = {}, {name: ([], []) for name in LISTS}
        for key, value in state.items():
            tabled = key in COLUMNS and isinstance(value, list)
            if tabled:
                lists[key] = (value, [json.dumps(x) for x in value])
            row[key] = marker(key) if tabled else value
        return json.dumps(row), lists

    def _write(self, state: dict) -> None:
        self._put(*self._texts(state))

    def _put(self, text: str, lists: dict) -> None:
        with self._store.transaction():                # the caller's, when one is open: the tables and the row stand or fall together
            for name, (items, new) in lists.items():
                self._rows(name, items, new)
            self._store._put(KEY, text)

    def _rows(self, table: str, items: list, new: list[str]) -> None:
        """The table holds these items, in this order (`new` is their json). Rows that stand as they are are left; what was taken
        out is deleted, what changed where it stood is updated, what is new goes after the last. Where an item has to go in before
        rows that stay, the rows from there on are written again."""
        db = self._store._db
        old = db.execute(f'SELECT ord, json FROM "{table}" ORDER BY ord').fetchall()
        was = [t for _, t in old]
        if was == new:
            return
        cols = "".join(f', "{c}"' for c, _, _ in COLUMNS[table])
        sets = ", ".join(f'"{c}" = ?' for c, _, _ in COLUMNS[table])
        top = [old[-1][0] if old else 0]

        def delete(i1: int, i2: int) -> None:
            if i2 > i1:
                db.execute(f'DELETE FROM "{table}" WHERE ord >= ? AND ord <= ?', (old[i1][0], old[i2 - 1][0]))
                self.written += i2 - i1

        def update(i: int, j: int) -> None:
            if was[i] != new[j]:
                db.execute(f'UPDATE "{table}" SET {sets}, json = ? WHERE ord = ?', (*derive(table, items[j]), new[j], old[i][0]))
                self.written += 1

        def insert(j: int) -> None:
            top[0] += 1
            db.execute(f'INSERT INTO "{table}" (ord{cols}, json) VALUES ({", ".join("?" * (len(COLUMNS[table]) + 2))})',
                       (top[0], *derive(table, items[j]), new[j]))
            self.written += 1

        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, was, new, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            if tag == "delete" or (tag == "replace" and i2 - i1 >= j2 - j1):
                for k in range(j2 - j1):
                    update(i1 + k, j1 + k)
                delete(i1 + (j2 - j1), i2)
                continue
            i2, j2 = len(was), len(new)                # new items before rows that stay: everything from here on, place by place
            shared = min(i2 - i1, j2 - j1)
            for k in range(shared):
                update(i1 + k, j1 + k)
            delete(i1 + shared, i2)
            for j in range(j1 + shared, j2):
                insert(j)
            break

    # ---- the narrow readers: each a filter over the whole state, as the row's are
    def effects_at(self, kind: str, place: str, now: int, good: str = "") -> list[dict]:
        return effects_matching(self.load(), now, kind, place, good)

    def threads(self, status: str | None = None) -> list[dict]:
        return threads_matching(self.load(), status)

    def deeds_since(self, minute: int, kinds=None) -> list[dict]:
        return deeds_matching(self.load(), minute, kinds)

    def news(self) -> list[dict]:
        return news_matching(self.load())

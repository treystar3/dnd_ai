"""The save's version, and how an older save is brought up to date.

The rules: a new database is created at the baseline schema (storage.campaign.SCHEMA_V1) and nothing else; every change to the schema or
to what a record means after that is a step here, and only here, so an old database is never half-shaped by the current schema before its
own steps run. PRAGMA user_version says which steps a database has had; open_or_create() runs the rest in order, each in its own
transaction, after taking a backup of the database as it was. A save from a newer build than this one is refused (SaveTooNew). Add a step
whenever a record changes shape or meaning (a new table, an index, a renamed field, a value that now means something else); a default on a
pydantic field covers a field that is merely new.

Each step is (version, description, function(store)). The function sees the store as it is and may read and write anything, including
DDL through store.execute()."""
from __future__ import annotations


def _v1_initial(store) -> None:
    """The first database layout. Nothing to change: records imported from the file layout are already in this shape."""


def _v2_memory_rows(store) -> None:
    """What people remember moves out of their records into npc_memory rows (a record carries only a window from then on), and the event
    journal table is created."""
    from storage.campaign import SCHEMA_V2
    from npc.models import NPC
    for stmt in [s.strip() for s in SCHEMA_V2.split(";") if s.strip()]:
        store.execute(stmt)
    rows = store._db.execute("SELECT id, json FROM npcs").fetchall()
    for i, j in rows:
        n = NPC.model_validate_json(j)
        for m in n.memories:
            m.id = None
        store.save_npc(n)


def _v3_battlefield(store) -> None:
    """Combat moved from range bands to the battlefield (zones, rows, engagement). A fight saved mid-round under the old model cannot
    be carried over, so it is discarded and the player resumes outside it; everything else is untouched."""
    store.save_combat(None)


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "one SQLite file per campaign, with an index over people", _v1_initial),
    (2, "memories as rows (npc_memory) with a window on the record; the event journal", _v2_memory_rows),
    (3, "combat on the battlefield (zones, rows, engagement); a fight in progress under range bands is discarded", _v3_battlefield),
]

CURRENT = MIGRATIONS[-1][0]


def run(store) -> list[str]:
    """Bring the save to the current version. Returns what was done, one line per step."""
    done = []
    have = store.version
    todo = [(v, w, s) for v, w, s in MIGRATIONS if v > have]
    if not todo:
        return done
    store.backup(f"v{have}")                              # as it was, in case a step commits a wrong transformation cleanly
    for version, what, step in todo:
        with store.transaction():
            step(store)
            store.set_version(version)
        done.append(f"save brought to v{version}: {what}")
    return done

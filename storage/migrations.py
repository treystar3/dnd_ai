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


def _v4_meravia(store) -> None:
    """The world was renamed: Rivia was a placeholder, and the world is Meravia. What the model wrote into a save under the old name -
    people's memories and moods, the journal, the narration kept for the recap, thread and news lines, the player's own record - is
    carried over to the new one, so nobody in an old campaign still speaks of a land that is no longer called that. Whole words only:
    'trivial' is not touched."""
    import re
    word, upper = re.compile(r"\bRivia\b"), re.compile(r"\bRIVIA\b")

    def fix(v):
        return upper.sub("MERAVIA", word.sub("Meravia", v)) if isinstance(v, str) and v else v
    for table, key, cols in (("kv", "key", ("json",)), ("places", "id", ("json",)), ("npcs", "id", ("json", "motive", "mood")),
                             ("npc_memory", "id", ("text",)), ("event_log", "seq", ("text", "data", "action"))):
        if not store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone():
            continue
        found = store._db.execute(f"SELECT {key}, {', '.join(cols)} FROM {table} WHERE "
                                  + " OR ".join(f"{c} LIKE '%rivia%'" for c in cols)).fetchall()
        for row in found:
            new = [fix(v) for v in row[1:]]
            if new != list(row[1:]):
                store.execute(f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)} WHERE {key} = ?", (*new, row[0]))


def _v5_lethoria(store) -> None:
    """The capital was renamed: Valecourt is Lethoria. Unlike the world's name (v4), the capital's name is also an id - the city and
    the places inside it (lethoria_guild, lethoria_palace...), the knowledge group of its people, its lore facts, a home there - so
    every text column of every table is carried over, ids and index columns included: where the player stands, where people live,
    what they know, whose memories are whose, the journal's actors and targets, what the model wrote. Whole words only; a prefix of
    an id ('valecourt_guild', 'home_valecourt') counts as a word."""
    import re
    rules = ((re.compile(r"(?<![A-Za-z])Valecourt(?![a-z])"), "Lethoria"), (re.compile(r"(?<![A-Za-z])valecourt(?![a-z])"), "lethoria"),
             (re.compile(r"VALECOURT"), "LETHORIA"))

    def fix(v):
        if not isinstance(v, str) or not v:
            return v
        for rx, to in rules:
            v = rx.sub(to, v)
        return v
    tables = [r[0] for r in store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        cols = [r[1] for r in store._db.execute(f"PRAGMA table_info({table})") if (r[2] or "").upper() == "TEXT"]
        if not cols:
            continue
        found = store._db.execute(f"SELECT rowid, {', '.join(cols)} FROM {table} WHERE "          # LIKE ignores case, so every form is found
                                  + " OR ".join(f"{c} LIKE '%valecourt%'" for c in cols)).fetchall()
        for row in found:
            new = [fix(v) for v in row[1:]]
            if new != list(row[1:]):
                store.execute(f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)} WHERE rowid = ?", (*new, row[0]))


def _v6_maren_voice(store) -> None:
    """(f374) Maren, once the lesson is over, is a person written by hand: her record takes her own personality, voice and rank and a
    speech profile with no drawn habits (engine/mentor.py own_voice), replacing the townsperson's voice kit an older build drew for her.
    A save where she is not yet a person of the world is untouched."""
    if not store.npc_exists("maren"):
        return
    from engine import mentor
    try:
        player = store.load_player()
    except Exception:
        player = None
    store.save_npc(mentor.own_voice(store.load_npc("maren"), player))


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "one SQLite file per campaign, with an index over people", _v1_initial),
    (2, "memories as rows (npc_memory) with a window on the record; the event journal", _v2_memory_rows),
    (3, "combat on the battlefield (zones, rows, engagement); a fight in progress under range bands is discarded", _v3_battlefield),
    (4, "the world renamed from Rivia to Meravia in everything the model wrote into the save", _v4_meravia),
    (5, "the capital renamed from Valecourt to Lethoria, its ids with it", _v5_lethoria),
    (6, "Maren after the lesson keeps the voice she was written with", _v6_maren_voice),
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

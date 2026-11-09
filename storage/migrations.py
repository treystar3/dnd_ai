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


def _v7_maren_moves_on(store) -> None:
    """(f382) Maren no longer waits at the guild hall once the lesson is over: she has left Parth on the capital's work. A save where she
    was made a person of the world by an older build (f374 to f381) has her taken out of the hall's residents and marked gone."""
    if not store.npc_exists("maren"):
        return
    from engine import mentor
    from world.loader import authored                 # (f451) the one parse of the written world, never a second
    npc = store.load_npc("maren")
    if npc.gone:
        return
    npc.gone = mentor.M["npc"]["gone"]
    store.save_npc(npc)
    minutes = getattr(store.meta, "minutes", 0) or 0
    mentor.moved_on(store, authored(), npc, minutes)


def _v8_hire_pronouns(store) -> None:
    """(f385) Every hire keeps she or he: the roster drew a gender with each name and never kept it, so the narrator called one hire she,
    he and they in one fight. An older save's hires get theirs back from their week's roster, drawn again (engine/party.py pronoun_of);
    a tamed companion gets one once."""
    try:
        player = store.load_player()
    except Exception:
        return
    from engine import party
    for m in player.party:
        party.pronoun_of(m, store.meta.seed, player.party_used)
    for c in player.character.companions:
        party.companion_pronoun(c)
    store.save_player(player)


def _v9_entities(store) -> None:
    """(f392) The registry. Nothing is moved into it: what it keeps is registered as it happens (engine/entities.py), and an older save
    simply starts with it empty."""
    from storage.campaign import SCHEMA_V3
    for stmt in [s.strip() for s in SCHEMA_V3.split(";") if s.strip()]:
        store.execute(stmt)


def typed_memory(store) -> None:
    """(f478) npc_memory's typed columns and their indexes: added by v10 to an older save, and made with a new one (storage/campaign.py)."""
    for col, ddl in (("subject", "TEXT NOT NULL DEFAULT ''"), ("source", "TEXT NOT NULL DEFAULT ''"), ("about", "TEXT NOT NULL DEFAULT ''"),
                     ("minute", "INTEGER NOT NULL DEFAULT -1"), ("times", "INTEGER NOT NULL DEFAULT 1"),
                     ("state", "TEXT NOT NULL DEFAULT ''")):                     # (f483) a knows row's: held, or told:<character ids>
        have = {r[1] for r in store._db.execute("PRAGMA table_info(npc_memory)").fetchall()}
        if col not in have:
            store._db.execute(f"ALTER TABLE npc_memory ADD COLUMN {col} {ddl}")
    store._db.execute("CREATE INDEX IF NOT EXISTS npc_memory_kind ON npc_memory (npc_id, kind, minute)")
    store._db.execute("CREATE INDEX IF NOT EXISTS npc_memory_subject ON npc_memory (npc_id, subject)")


def _v10_memory_kinds(store) -> None:
    """(f478) What people remember, typed: each row says what it is (experienced, witnessed, noticed, heard, told, own_life...), whom it
    is about (subject), who said it (source), what it is about (about, so a repeat counts up) and when to the minute. Old rows are typed
    the least-work way (GOALS.md S8): "(my own life) " rows become own_life with the prefix stripped (it was machinery in the text); a
    row the world wrote with no turn (turn -1) is about no one: an anchor's "I dealt with ... myself" is their own life, a disaster
    lived through is experienced; every other row was something the player did, experienced, about the player."""
    typed_memory(store)
    store.execute("UPDATE npc_memory SET kind = 'own_life', subject = '', text = substr(text, 15) WHERE text LIKE '(my own life) %'")
    store.execute("UPDATE npc_memory SET kind = 'own_life', subject = '' WHERE kind = 'event' AND turn = -1 AND text LIKE 'I dealt with %'")
    store.execute("UPDATE npc_memory SET kind = 'experienced', subject = '' WHERE kind = 'event' AND turn = -1")
    store.execute("UPDATE npc_memory SET kind = 'experienced', subject = 'player' WHERE kind = 'event'")


def _v11_hire_memories(store) -> None:
    """(f479) A hire's memories leave the player's record for rows under hire:<id>, typed as a townsperson's are: what they lived with
    the player experienced, a fact the player told them told (by the player), weight as importance, key as about, count as times. Each
    keeps its stamped day. The record then carries only the window the party reads, rebuilt from the rows when the player is loaded."""
    import json
    from engine import memory
    raw = store._kv_text("player")
    if not raw:
        return
    body = json.loads(raw)
    for m in body.get("party") or []:
        if not m.get("id"):
            continue
        for x in m.get("memories") or []:
            r = memory.hire_row(x)
            store._db.execute("INSERT INTO npc_memory (npc_id, day, turn, kind, importance, text, subject, source, about, minute, times) "
                              "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (f"hire:{m['id']}", r["day"], r["turn"], r["kind"], r["importance"],
                                                                         r["text"], r["subject"], r["source"], r["about"], r["minute"], r["times"]))
        m.pop("memories", None)
    store._db.execute("UPDATE kv SET json = ? WHERE key = 'player'", (json.dumps(body, ensure_ascii=False),))


def _v12_regard(store) -> None:
    """(f480) A person's view of the player becomes their view of one character, by id: trust, met, the name they were given and whether
    they know theirs, when they last spoke, the journal's note, Easy Company and who named them first leave the record's top level for
    regard["player"] (npc/models.py legacy_regard: only what differs from a new acquaintance's, so a person nobody met keeps none). The
    index columns are unchanged: with one character they hold that character's view."""
    import json
    from npc.models import legacy_regard
    for nid, raw in store._db.execute("SELECT id, json FROM npcs ORDER BY id").fetchall():
        body = json.loads(raw)
        moved = legacy_regard(body)
        if moved is not body:
            moved.setdefault("regard", {})                          # as save_npc writes it: every record carries its views, none or some
            store._db.execute("UPDATE npcs SET json = ? WHERE id = ?", (json.dumps(moved, ensure_ascii=False), nid))


def _v13_offers(store) -> None:
    """(f481) A person's standing work offer and request leave their record for the registry: each an offer (data/rules/lifecycles.yaml),
    from them to the one character there was then, still offered (an old work offer's hour is gone: GOALS.md S2, nothing ends by age; the
    world withdraws it for a reason on the next line if the day is over or the player has left the town). The ids are fixed by the person
    and the family, so the step is the same every time it runs."""
    import json
    from core.models import Entity
    for nid, raw in store._db.execute("SELECT id, json FROM npcs ORDER BY id").fetchall():
        body = json.loads(raw)
        work, ask = body.pop("work_offer", None), body.pop("quest_offer", None)
        for fam, terms, title in (("work", work, (work or {}).get("task", "")), ("request", ask, (ask or {}).get("title", ""))):
            if not terms:
                continue
            t = {k: v for k, v in dict(terms).items() if k != "until"}
            e = Entity(ref=f"obl:{nid}:{fam}", kind="offer", name=str(title)[:120], state="offered", since=0, owner="player", links={"npc": nid},
                       data={"family": fam, "with": "player", "title": str(title), "terms": t, "key": f"{fam}:{nid}"},
                       history=[[0, "", "offered", "brought forward from an older save"]])
            store._db.execute("INSERT OR REPLACE INTO entities (ref, kind, state, place, owner, deadline, json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (e.ref, e.kind, e.state, e.place, e.owner, 0, e.model_dump_json()))
        if work is not None or ask is not None or "work_offer" in raw or "quest_offer" in raw:
            store._db.execute("UPDATE npcs SET json = ? WHERE id = ?", (json.dumps(body, ensure_ascii=False), nid))


def _v14_knows(store) -> None:
    """(f483) What a person knows of a matter becomes their own: npc_memory gains its state column (typed_memory), and every clue held
    in a matter still open becomes a knows row of its holder's (about thread:<id>:<n>, from themselves, held, or told:player when its
    words were found), dated when the matter opened. A clue whose holder is gone from the save is left to the matter."""
    import json
    typed_memory(store)
    raw = store._kv_text("world_state")
    if not raw:
        return
    from engine import clock
    have = {r[0] for r in store._db.execute("SELECT id FROM npcs").fetchall()}
    for th in json.loads(raw).get("threads") or []:
        if th.get("status") != "active":
            continue
        t = int(th.get("opened", th.get("made", 0)) or 0)
        for i, c in enumerate(th.get("clues") or []):
            nid, about = c.get("npc") or "", f"thread:{th.get('id')}:{i}"
            if nid not in have or store._db.execute("SELECT 1 FROM npc_memory WHERE npc_id = ? AND kind = 'knows' AND about = ? AND forgotten = 0",
                                                    (nid, about)).fetchone():
                continue
            store._db.execute("INSERT INTO npc_memory (npc_id, day, turn, kind, importance, text, subject, source, about, minute, times, state) "
                              "VALUES (?, ?, -1, 'knows', 2, ?, '', 'self', ?, ?, 1, ?)",
                              (nid, clock.day(t), str(c.get("text", "")), about, t, "told:player" if c.get("found") else "held"))


def _v15_effect_rows(store) -> None:
    """(f507) A fight's statuses, buffs, curses and ground effects became rows of the fight's own record (engine/effects.py), and a
    fight row of another shape is refused rather than read in part. A fight saved mid-round under the old shape is let go of, as v3
    did, and a notice left that the next load tells once (failures.yaml fight_let_go): the fight is lost, never the game."""
    if store.load_combat() is not None:
        store.save_combat(None)
        store.leave_notice("fight_let_go")


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "one SQLite file per campaign, with an index over people", _v1_initial),
    (2, "memories as rows (npc_memory) with a window on the record; the event journal", _v2_memory_rows),
    (3, "combat on the battlefield (zones, rows, engagement); a fight in progress under range bands is discarded", _v3_battlefield),
    (4, "the world renamed from Rivia to Meravia in everything the model wrote into the save", _v4_meravia),
    (5, "the capital renamed from Valecourt to Lethoria, its ids with it", _v5_lethoria),
    (6, "Maren after the lesson keeps the voice she was written with", _v6_maren_voice),
    (7, "Maren leaves Parth once the lesson is over, on the capital's work", _v7_maren_moves_on),
    (8, "every hire keeps the pronoun they were drawn with", _v8_hire_pronouns),
    (9, "the registry of who someone is and what has become of them", _v9_entities),
    (10, "memories typed: what each is, whom it is about, who said it, what it is about, and when", _v10_memory_kinds),   # (f478)
    (11, "a hire's memories as rows of their own, the player's record carrying only the window", _v11_hire_memories),      # (f479)
    (12, "a person's view of the player kept as their view of one character, by id", _v12_regard),                          # (f480)
    (13, "work offered and requests made kept as offers that end for a reason", _v13_offers),                               # (f481)
    (14, "what a person knows of a matter kept as their own, past the matter's end", _v14_knows),                          # (f483)
    (15, "a fight's statuses, buffs, curses and ground as rows of its record; a fight saved under the old shape is let go", _v15_effect_rows),   # (f507)
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

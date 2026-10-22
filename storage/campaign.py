"""Campaign persistence. Everything generated during play is written here and becomes canon.

One SQLite file per campaign, saves/<campaign>/campaign.db:
    kv      the small blobs, one row each: campaign (name, seed, clock), player, world_state, dungeons, arcs, discoveries,
            legendaries, combat, story
    places  one row per place the player has touched: id, json
    npcs    one row per person: id, json, and beside the json the few fields the game queries (name, role, location, tier,
            met_player, gone, motive, trust, mood, away_until...), so finding "everyone the player has met who is not here" is one
            indexed query instead of reading every file

Every record body is JSON in a text column, so a save stays readable with any SQLite browser (or export_json() writes it out as
files). Each save call is its own transaction; transaction() groups several. The schema has a version (PRAGMA user_version) and
storage/migrations.py carries it forward; a save made by the older one-file-per-record layout is imported on first open and the
old files moved aside to legacy_json/.

The rest of the game only talks to CampaignStore."""

from __future__ import annotations

import json
import random
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from core.models import Item, Character
from npc.models import NPC, Memory

SAVES_DIR = Path("saves")
DB_NAME = "campaign.db"


class CampaignMeta(BaseModel):
    name: str
    seed: int
    day: int = 1
    turn: int = 0
    minutes: int = 0
    created: str


class PlaceState(BaseModel):
    id: str
    populated: bool = False
    roster: list[str] = []
    residents: list[str] = []
    first_visit_day: int | None = None
    marks: list[str] = []          # lasting changes the player made here (marked trees, a hidden cache...)
    ground: list[dict] = []        # items left here: {"item": Item data, "minute": when it was left}
    carcasses: list[dict] = []     # fallen creatures not yet skinned: {"creature", "level", "minute"}
    board: list[dict] = []         # guild contracts posted here
    extra_roles: dict[str, int] = {}  # people the world has brought here (arrivals), generated on the next visit
    hidden: list[dict] = []        # story objects the player went looking for here: {"name", "description", "worth", "taken"}
    locks: list[dict] = []         # locked rooms and containers here: {"id", "name", "quality", "owner", "state", "jam", "change_day"}
    bodies: list[dict] = []        # the fallen here, for Speak with a Corpse: {"creature", "name", "level", "category", "minute", "carried", "asked"}
    board_day: int = -1
    memory: list[dict] = []        # (f317) a town's memory of the matters that ended here: {"text", "minute"}; the truth layer gives it to every speaker


class PlayerState(BaseModel):
    character: Character
    location: str
    room: str = ""            # place id of a rented room
    room_until: int = -1      # game minute the rental ends
    stash: list[Item] = []    # the item box, reachable from any place with storage
    commissions: list[dict] = []   # gear ordered from crafters: {npc, npc_name, item, ready}
    guild_rank: str = ""           # "" until they join; then F, E, D, C, B, A or S
    guild_done: dict[str, int] = {}  # guild contracts completed, by letter
    quests: list[dict] = []        # contracts and personal requests taken on (see engine/quests.py)
    delve: dict | None = None      # inside a dungeon: {"dungeon", "floor", "chamber", "rest"}
    reputation: dict[str, int] = {}  # how each town regards the player, -100..100
    visited: list[str] = []        # places the player has been
    last_in: dict[str, int] = {}   # (f331) town id -> the game minute the player last left it, for "since you were last here"
    audiences: dict[str, int] = {}  # (f320) places whose door has been opened to the player: place -> game minute it shuts (engine/court.py)
    heard: list[str] = []          # places the player has heard of (named by someone, in a contract) without having been there
    free_room_day: int = -1        # Sing for Your Supper: a room is owed tonight
    outlaw_rep: int = 0            # how outlaws regard you (-100..100): what you do with those you beat
    prisoners: dict[str, dict] = {}  # captives you hold, by npc id: {"deal", "arc", "node", "tip", "asked"}
    homes: dict[str, dict] = {}    # houses bought, by town id: {"day", "upgrades": [...], "last_garden", "last_hearth"}
    relics_bought: list[str] = []  # named relics already bought (one of each exists)
    party: list[dict] = []         # hired adventurers with you: {"id", "name", "role", "level", "blurb", "arc"} (engine/party.py)
    party_mode: str = "with"       # "with" - they move and fight beside you; "hold" - they wait outside a camp and come when the alarm rings
    party_used: list[str] = []     # roster ids already hired or lost, so they do not reappear
    party_relations: dict = {}     # how two hires are with each other: "idA|idB" -> {"score", "dynamic", "day"} (engine/party.py)
    party_last_fight: dict = {}    # the last fight the party was in: {"minute", "won", "hard", "hurt": [names], "carried": [names]}
    titles: list[str] = []         # honorifics earned by ending campaigns and cataclysms
    mounts: list[dict] = []        # mounts owned: {"id", "name", "speed", "stamina"} (see data/rules/events.yaml)
    mount: str = ""                # id of the mount ridden, if any
    field: dict = {}               # field-ability state (scenes/field_actions.py): cd, camp, haste, edge, shadow, scouted, lit, shows
    heat: dict[str, dict] = {}     # how wanted you are, by town id: {"heat", "day"} (engine/law.py)
    standing: dict[str, dict] = {}   # how the groups of each town regard you, hidden: town -> group -> [value, day] (engine/standing.py)
    orenna: dict = {}                    # progress of the quest Orenna (engine/orenna.py)
    mentor: dict = {}                    # progress of the mentor's first contract (engine/mentor.py)
    trial: dict = {}                     # the trial of rank (scenes/trial_actions.py): pending rank, examiner, tries, wait_until, told_day
    standing_seen: dict[str, dict] = {}  # deed news already felt in far towns: news id -> town -> {group: change}
    confronted: dict[str, int] = {}  # town id -> the last day guards stopped you there
    road: dict | None = None       # stopped on the road: {"id", "from", "to", "place", "log", "text", "resume"}


@dataclass
class NPCRow:
    """The few fields of a person the game looks people up by, read straight from the index columns: no file, no validation. Enough
    to list, filter and name someone; load_npc() for the whole record."""
    id: str
    name: str
    epithet: str
    name_known_to_player: bool
    role: str
    location: str
    tier: str
    met_player: bool
    gone: str
    motive: str
    trust: int
    mood: str
    away_until: int
    heard_of: bool
    protected: bool

    def label(self) -> str:
        return self.name if self.name_known_to_player else (self.epithet or f"the {self.role.replace('_', ' ')}")


NPC_COLUMNS = ("name", "epithet", "name_known_to_player", "role", "location", "tier", "met_player", "gone", "motive", "trust", "mood",
               "away_until", "heard_of", "protected")


def _npc_index(npc: NPC) -> dict:
    return {"name": npc.name, "epithet": npc.epithet, "name_known_to_player": int(npc.name_known_to_player), "role": npc.role,
            "location": npc.location, "tier": npc.tier, "met_player": int(npc.met_player), "gone": npc.gone, "motive": npc.motive,
            "trust": npc.trust, "mood": npc.mood, "away_until": npc.away_until, "heard_of": int(bool(npc.heard_of)),
            "protected": int(npc.protected)}


class SaveTooNew(Exception):
    """The save was made by a newer build than this one: opening it here could misread or damage it."""


BACKUPS_KEPT = 3
JOURNAL_KEEP = 6000          # event_log rows kept: the oldest go once past this (the trail, not the state; checked every JOURNAL_CHECK rows)
JOURNAL_CHECK = 500
MEMORY_WINDOW = 24           # how many of a person's memories their record carries: every defining one (importance 3), then the newest
MEMORY_DEFINING = 3

SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS npc_memory (
    id INTEGER PRIMARY KEY, npc_id TEXT NOT NULL, day INTEGER NOT NULL, turn INTEGER NOT NULL DEFAULT -1,
    kind TEXT NOT NULL DEFAULT 'event', importance INTEGER NOT NULL DEFAULT 1, text TEXT NOT NULL, forgotten INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS npc_memory_who ON npc_memory (npc_id, day);
CREATE INDEX IF NOT EXISTS npc_memory_weight ON npc_memory (npc_id, importance);
CREATE TABLE IF NOT EXISTS event_log (
    seq INTEGER PRIMARY KEY, minute INTEGER NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL DEFAULT '', target TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL DEFAULT '', data TEXT NOT NULL DEFAULT '{}', action TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS event_log_actor ON event_log (actor, seq);
CREATE INDEX IF NOT EXISTS event_log_target ON event_log (target, seq);
"""

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS places (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS npcs (
    id TEXT PRIMARY KEY, json TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '', epithet TEXT NOT NULL DEFAULT '', name_known_to_player INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', tier TEXT NOT NULL DEFAULT 'background',
    met_player INTEGER NOT NULL DEFAULT 0, gone TEXT NOT NULL DEFAULT '', motive TEXT NOT NULL DEFAULT '',
    trust INTEGER NOT NULL DEFAULT 50, mood TEXT NOT NULL DEFAULT '', away_until INTEGER NOT NULL DEFAULT -1,
    heard_of INTEGER NOT NULL DEFAULT 0, protected INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS npcs_location ON npcs (location, gone);
CREATE INDEX IF NOT EXISTS npcs_met ON npcs (met_player, gone);
CREATE INDEX IF NOT EXISTS npcs_role ON npcs (role, gone);
"""


class CampaignStore:
    def __init__(self, root: Path, meta: CampaignMeta, db: sqlite3.Connection):
        self.root = root
        self.meta = meta
        self._db = db
        self._lock = threading.RLock()
        self._depth = 0

    # ---------- opening ----------

    @classmethod
    def open_or_create(cls, name: str, saves_dir: Path = SAVES_DIR) -> "CampaignStore":
        root = saves_dir / name
        root.mkdir(parents=True, exist_ok=True)
        path = root / DB_NAME
        fresh = not path.exists()
        db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)      # autocommit; transaction() groups writes
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        store = cls(root, CampaignMeta(name=name, seed=0, created=""), db)
        from storage import migrations
        if fresh:                                         # a new database is created whole at the current schema and marked current;
            db.executescript(SCHEMA_V1)                   # an older one is brought forward step by step below (storage/migrations.py)
            db.executescript(SCHEMA_V2)
            store.set_version(migrations.CURRENT)
            if (root / "campaign.json").exists():
                store._import_legacy()
        elif store.version > migrations.CURRENT:
            have = store.version
            db.close()
            raise SaveTooNew(f"This save was made by a newer version of the game (save v{have}, this build reads up to v{migrations.CURRENT}). "
                             "Update the game to play it.")
        row = store._kv("campaign")
        if row is None:
            store.meta = CampaignMeta(name=name, seed=random.SystemRandom().randrange(2**31), created=datetime.now(timezone.utc).isoformat())
            store.save_meta()
        else:
            store.meta = CampaignMeta.model_validate(row)
        migrations.run(store)                             # an older database is brought forward here, and only here (a backup is taken first)
        return store

    def backup(self, label: str = "") -> Path:
        """A copy of the whole database as it is now, under backups/; the oldest beyond BACKUPS_KEPT are dropped."""
        folder = self.root / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"campaign_{label or 'copy'}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.db"
        with self._lock:
            out = sqlite3.connect(dest)
            try:
                self._db.backup(out)
            finally:
                out.close()
        old = sorted(folder.glob("campaign_*.db"), key=lambda p: p.stat().st_mtime)
        for p in old[:-BACKUPS_KEPT]:
            p.unlink(missing_ok=True)
        return dest

    def close(self) -> None:
        with self._lock:
            self._db.close()

    @property
    def version(self) -> int:
        return int(self._db.execute("PRAGMA user_version").fetchone()[0])

    def set_version(self, v: int) -> None:
        self._db.execute(f"PRAGMA user_version = {int(v)}")

    def execute(self, sql: str, args: tuple = ()) -> None:
        """For migrations: a statement run on the database as it is (a new table, an index, a column)."""
        with self._lock:
            self._db.execute(sql, args)

    @contextmanager
    def transaction(self):
        """Group several saves into one all-or-nothing write (a whole turn, say). Nested use joins the outer one."""
        with self._lock:
            if self._depth == 0:
                self._db.execute("BEGIN")
            self._depth += 1
            try:
                yield
            except BaseException:
                self._depth -= 1
                if self._depth == 0:
                    self._db.execute("ROLLBACK")
                raise
            else:
                self._depth -= 1
                if self._depth == 0:
                    self._db.execute("COMMIT")

    # ---------- the small blobs ----------

    def _kv(self, key: str):
        with self._lock:
            row = self._db.execute("SELECT json FROM kv WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def _kv_text(self, key: str) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT json FROM kv WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def _put(self, key: str, text: str) -> None:
        with self._lock:
            self._db.execute("INSERT INTO kv (key, json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET json = excluded.json", (key, text))

    def _drop(self, key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM kv WHERE key = ?", (key,))

    def save_meta(self) -> None:
        self._put("campaign", self.meta.model_dump_json())

    def reload_meta(self) -> None:
        """The clock and turn count as the database has them: after a rollback, what the scene advanced in memory is taken back too."""
        text = self._kv_text("campaign")
        if text:
            self.meta = CampaignMeta.model_validate_json(text)

    def load_world_state(self) -> dict:
        return self._kv("world_state") or {}

    def save_world_state(self, state: dict) -> None:
        self._put("world_state", json.dumps(state))

    def load_dungeons(self) -> list[dict]:
        return self._kv("dungeons") or []

    def save_dungeons(self, dungeons: list[dict]) -> None:
        self._put("dungeons", json.dumps(dungeons))

    def load_arcs(self) -> dict:
        base = {"arcs": [], "last_end": -10 ** 9}
        got = self._kv("arcs")
        return {**base, **got} if got else base

    def save_arcs(self, data: dict) -> None:
        self._put("arcs", json.dumps(data))

    def load_discoveries(self) -> dict:
        base = {"places": [], "tracks": [], "leads": []}
        got = self._kv("discoveries")
        return {**base, **got} if got else base

    def save_discoveries(self, data: dict) -> None:
        self._put("discoveries", json.dumps(data))

    def player_exists(self) -> bool:
        return self._kv_text("player") is not None

    def load_player(self) -> PlayerState:
        return PlayerState.model_validate_json(self._kv_text("player") or "")

    def save_player(self, player: PlayerState) -> None:
        with self.transaction():                     # the clock and turn count live beside the player; one without the other lost the time on reload
            self._put("player", player.model_dump_json())
            self.save_meta()

    def legendary_names(self) -> list[str]:
        return self._kv("legendaries") or []

    def add_legendary_name(self, name: str) -> None:
        self._put("legendaries", json.dumps(self.legendary_names() + [name]))

    def save_combat(self, combat_json: str | None) -> None:
        if combat_json is None:
            self._drop("combat")
        else:
            self._put("combat", combat_json)

    def load_combat(self) -> str | None:
        return self._kv_text("combat")

    def save_story(self, recent: list[str], shown: dict) -> None:
        self._put("story", json.dumps({"recent": recent, "shown": shown}))

    def load_story(self) -> tuple[list[str], dict]:
        try:
            data = self._kv("story") or {}
            recent = [t for t in data.get("recent", []) if isinstance(t, str)]
            shown = data.get("shown", {})
            if isinstance(shown, str):
                shown = {"type": "narration", "text": shown}
            return recent, shown if isinstance(shown, dict) else {}
        except (ValueError, AttributeError):
            return [], {}

    # ---------- places ----------

    def load_place(self, place_id: str) -> PlaceState:
        with self._lock:
            row = self._db.execute("SELECT json FROM places WHERE id = ?", (place_id,)).fetchone()
        return PlaceState.model_validate_json(row[0]) if row else PlaceState(id=place_id)

    def save_place(self, state: PlaceState) -> None:
        with self._lock:
            self._db.execute("INSERT INTO places (id, json) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET json = excluded.json",
                             (state.id, state.model_dump_json()))

    def list_places(self) -> list[str]:
        with self._lock:
            return [r[0] for r in self._db.execute("SELECT id FROM places ORDER BY id")]

    # ---------- people ----------

    def npc_exists(self, npc_id: str) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM npcs WHERE id = ?", (npc_id,)).fetchone() is not None

    def load_npc(self, npc_id: str) -> NPC:
        with self._lock:
            row = self._db.execute("SELECT json FROM npcs WHERE id = ?", (npc_id,)).fetchone()
        if row is None:
            raise FileNotFoundError(f"no such npc: {npc_id}")
        npc = NPC.model_validate_json(row[0])
        self._attach_memories(npc)
        return npc

    def load_npcs(self, ids: list[str]) -> list[NPC]:
        """Several at once, in the order asked for; ids that do not exist are skipped."""
        ids = list(ids)
        if not ids:
            return []
        out = {}
        with self._lock:
            for k in range(0, len(ids), 500):
                chunk = ids[k:k + 500]
                for i, j in self._db.execute(f"SELECT id, json FROM npcs WHERE id IN ({','.join('?' * len(chunk))})", chunk):
                    out[i] = j
        npcs = [NPC.model_validate_json(out[i]) for i in ids if i in out]
        for n in npcs:
            self._attach_memories(n)
        return npcs

    def save_npc(self, npc: NPC) -> None:
        idx = _npc_index(npc)
        cols = ("id", "json") + NPC_COLUMNS
        sets = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
        with self._lock, self.transaction():
            self._db.execute(f"INSERT INTO npcs ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) ON CONFLICT(id) DO UPDATE SET {sets}",
                             (npc.id, npc.model_dump_json(exclude={"memories", "memory_total"})) + tuple(idx[c] for c in NPC_COLUMNS))
            for m in npc.memories:                        # a memory made this turn becomes a row; the ones already rows are left alone
                if m.id is None:
                    cur = self._db.execute("INSERT INTO npc_memory (npc_id, day, turn, kind, importance, text) VALUES (?, ?, ?, ?, ?, ?)",
                                           (npc.id, m.day, m.turn, m.kind, int(m.importance), m.text))
                    m.id = cur.lastrowid

    # ---------- what people remember: rows, with the record carrying a window ----------

    def _attach_memories(self, npc: NPC) -> None:
        npc.memories = self.npc_memories(npc.id)
        npc.memory_total = self.memory_count(npc.id)

    def npc_memories(self, npc_id: str, limit: int = MEMORY_WINDOW, min_importance: int = 1) -> list[Memory]:
        """What a person remembers, oldest first: every defining memory, then the newest of the rest up to the limit. Recency is not
        importance: a defining memory is never pushed out by routine ones."""
        with self._lock:
            rows = self._db.execute("SELECT id, day, turn, kind, importance, text FROM npc_memory WHERE npc_id = ? AND forgotten = 0 AND importance >= ? "
                                    "ORDER BY (importance >= ?) DESC, id DESC LIMIT ?", (npc_id, int(min_importance), MEMORY_DEFINING, int(limit))).fetchall()
        rows.sort(key=lambda r: r[0])
        return [Memory(id=r[0], day=r[1], turn=r[2], kind=r[3], importance=r[4], text=r[5]) for r in rows]

    def memory_count(self, npc_id: str) -> int:
        with self._lock:
            return int(self._db.execute("SELECT COUNT(*) FROM npc_memory WHERE npc_id = ? AND forgotten = 0", (npc_id,)).fetchone()[0])

    def forget_memory(self, memory_id: int) -> None:
        """Marked forgotten, never deleted: the history stays for the journal and for anyone debugging."""
        with self._lock:
            self._db.execute("UPDATE npc_memory SET forgotten = 1 WHERE id = ?", (int(memory_id),))

    # ---------- the event journal: what happened, in order, for anyone asking 'why does this person hate me?' ----------

    def journal(self, minute: int, kind: str, actor: str = "", target: str = "", text: str = "", data: dict | None = None, action: str = "") -> None:
        """One authoritative fact, appended. Not event sourcing: the game's state is still the rows above; this is the trail."""
        with self._lock:
            cur = self._db.execute("INSERT INTO event_log (minute, kind, actor, target, text, data, action) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                   (int(minute), kind, actor or "", target or "", text or "", json.dumps(data or {}), action or ""))
            if cur.lastrowid and cur.lastrowid % JOURNAL_CHECK == 0:
                self.journal_trim()

    def journal_trim(self, keep: int = JOURNAL_KEEP) -> int:
        """Drop the oldest journal rows past `keep`. Returns how many went."""
        with self._lock:
            row = self._db.execute("SELECT seq FROM event_log ORDER BY seq DESC LIMIT 1 OFFSET ?", (int(keep),)).fetchone()
            if not row:
                return 0
            return self._db.execute("DELETE FROM event_log WHERE seq <= ?", (row[0],)).rowcount

    def journal_tail(self, n: int = 30, actor: str = "", target: str = "", kind: str = "") -> list[dict]:
        """The most recent entries, oldest first, for one actor, target or kind when given."""
        where, args = [], []
        if actor:
            where.append("(actor = ? OR target = ?)"); args += [actor, actor]
        if target:
            where.append("target = ?"); args.append(target)
        if kind:
            where.append("kind = ?"); args.append(kind)
        sql = "SELECT seq, minute, kind, actor, target, text, data, action FROM event_log" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY seq DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(sql, args + [int(n)]).fetchall()
        return [{"seq": r[0], "minute": r[1], "kind": r[2], "actor": r[3], "target": r[4], "text": r[5], "data": json.loads(r[6] or "{}"), "action": r[7]}
                for r in reversed(rows)]

    def list_npcs(self) -> list[str]:
        """Every person's id. Prefer npc_rows() with a filter: it reads only the index."""
        with self._lock:
            return [r[0] for r in self._db.execute("SELECT id FROM npcs ORDER BY id")]

    def npc_rows(self, *, gone: bool | None = None, met_player: bool | None = None, location: str | list[str] | None = None,
                 role: str | list[str] | None = None, tier: str | None = None, not_tier: str | None = None, motive: bool | None = None,
                 min_trust: int | None = None, exclude: list[str] | tuple = (), heard_of: bool | None = None) -> list[NPCRow]:
        """The people matching a filter, from the index alone: no record is parsed. gone=False: still in the story; motive=True: has one;
        location and role take one value or several."""
        where, args = [], []
        if gone is not None:
            where.append("gone = ''" if not gone else "gone != ''")
        if met_player is not None:
            where.append("met_player = ?"); args.append(int(met_player))
        if heard_of is not None:
            where.append("heard_of = ?"); args.append(int(heard_of))
        if tier is not None:
            where.append("tier = ?"); args.append(tier)
        if not_tier is not None:
            where.append("tier != ?"); args.append(not_tier)
        if motive is not None:
            where.append("motive != ''" if motive else "motive = ''")
        if min_trust is not None:
            where.append("trust >= ?"); args.append(int(min_trust))
        for col, val in (("location", location), ("role", role)):
            if val is None:
                continue
            vals = [val] if isinstance(val, str) else list(val)
            if not vals:
                return []
            where.append(f"{col} IN ({','.join('?' * len(vals))})"); args.extend(vals)
        if exclude:
            ex = list(exclude)
            where.append(f"id NOT IN ({','.join('?' * len(ex))})"); args.extend(ex)
        sql = "SELECT id, " + ", ".join(NPC_COLUMNS) + " FROM npcs" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        out = []
        for r in rows:
            d = dict(zip(("id",) + NPC_COLUMNS, r))
            for b in ("name_known_to_player", "met_player", "heard_of", "protected"):
                d[b] = bool(d[b])
            out.append(NPCRow(**d))
        return out

    def npc_names(self) -> list[str]:
        with self._lock:
            return [r[0] for r in self._db.execute("SELECT name FROM npcs ORDER BY id")]

    def reindex_npcs(self) -> None:
        """Rebuild the index columns from every record (after a migration that changes what they mean)."""
        with self.transaction():
            for i, j in self._db.execute("SELECT id, json FROM npcs").fetchall():
                self.save_npc(NPC.model_validate_json(j))

    # ---------- the old layout: one file per record ----------

    def _import_legacy(self) -> None:
        """A save from before the database: every JSON file becomes a row, and the files move to legacy_json/ untouched."""
        root = self.root
        with self.transaction():
            meta = (root / "campaign.json").read_text(encoding="utf-8")
            self._put("campaign", CampaignMeta.model_validate_json(meta).model_dump_json())
            for key, fn in (("player", "player.json"), ("world_state", "world_state.json"), ("dungeons", "dungeons.json"), ("arcs", "arcs.json"),
                            ("discoveries", "discoveries.json"), ("legendaries", "legendaries.json"), ("combat", "combat.json"), ("story", "story.json")):
                p = root / fn
                if p.exists():
                    self._put(key, p.read_text(encoding="utf-8"))
            for p in sorted((root / "places").glob("*.json")) if (root / "places").exists() else []:
                self._db.execute("INSERT OR REPLACE INTO places (id, json) VALUES (?, ?)", (p.stem, p.read_text(encoding="utf-8")))
            for p in sorted((root / "npcs").glob("*.json")) if (root / "npcs").exists() else []:
                n = NPC.model_validate_json(p.read_text(encoding="utf-8"))
                for m in n.memories:
                    m.id = None                           # every memory of the old record becomes a row
                self.save_npc(n)
        legacy = root / "legacy_json"
        legacy.mkdir(exist_ok=True)
        for name in ("campaign.json", "player.json", "world_state.json", "dungeons.json", "arcs.json", "discoveries.json", "legendaries.json",
                     "combat.json", "story.json", "places", "npcs"):
            p = root / name
            if p.exists():
                p.replace(legacy / name)

    def export_json(self, folder: Path) -> None:
        """Write the whole campaign out as readable files (for a look, or a bug report). The database stays the save."""
        folder.mkdir(parents=True, exist_ok=True)
        for key, fn in (("campaign", "campaign.json"), ("player", "player.json"), ("world_state", "world_state.json"), ("dungeons", "dungeons.json"),
                        ("arcs", "arcs.json"), ("discoveries", "discoveries.json"), ("legendaries", "legendaries.json"), ("combat", "combat.json"),
                        ("story", "story.json")):
            t = self._kv_text(key)
            if t is not None:
                (folder / fn).write_text(json.dumps(json.loads(t), indent=2), encoding="utf-8")
        (folder / "places").mkdir(exist_ok=True)
        (folder / "npcs").mkdir(exist_ok=True)
        with self._lock:
            for i, j in self._db.execute("SELECT id, json FROM places"):
                (folder / "places" / f"{i}.json").write_text(json.dumps(json.loads(j), indent=2), encoding="utf-8")
            for i, j in self._db.execute("SELECT id, json FROM npcs").fetchall():
                body = json.loads(j)
                body["memories"] = [m.model_dump() for m in self.npc_memories(i, limit=10 ** 6)]
                (folder / "npcs" / f"{i}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
            (folder / "event_log.json").write_text(json.dumps(self.journal_tail(10 ** 6), indent=1), encoding="utf-8")

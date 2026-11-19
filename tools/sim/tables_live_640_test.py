"""(f640) The one migration: the world's lists and the player's record are kept in their tables (docs/design/20_phase3_plan.md).
Until here a save was version 16: the world one row, the player another. Held here:
- a new save is version 17, has the five tables, and its store reads and writes them: no row of the player is left in the small
  table, and the world's row holds a marker where each list stood;
- each save kept at version 16 opens at 17 with one backup taken, and the state it holds, read as version 16 held it
  (statehash.view), is the state it held before, table for table; its tables and indexes are a new save's;
- a save with rows of an older shape (news with no certainty, a matter with no place, a deed with no number) keeps each as written;
- a save with no world loads none; a save with no player has none;
- the older steps that read the player and the world still do: a save from before v6 gets Maren's voice, has her moved on with
  the town told (v7, the world), and its hires their pronouns (v8, the player), and ends in the tables;
- a save that cannot be migrated is refused in a line with no dash, its file as it was and closed, a copy in its backups;
- a save made by a newer build is still refused, and both refusals are one kind for the caller;
- the home page reads a save not yet opened and the same save once opened, and says the same of both;
- the export writes the player and the whole world;
- the state's fingerprint reads the five tables, a list's rows by where they stand; the view of an unknown version is refused;
- the replay takes --as-schema, and refuses a version it has no view of.
Run: python tools/sim/tables_live_640_test.py"""
import json
import shutil
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
sys.path.insert(0, "tools/sim")
sys.path.insert(0, "tools")
import rows_v16
from engine import crashlog, mentor
from engine.session import CampaignSession
from storage import invariants, migrations, playerstable, saves, statehash, worldrow, worldtables
from storage import campaign as cmod
from storage.campaign import DB_NAME, CampaignStore, SaveTooNew

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

KEPT = rows_v16.KEPT
LISTS = worldtables.LISTS
FIVE = set(LISTS) | {playerstable.TABLE}
OLD = ["kv", "places", "npcs", "npc_memory", "event_log", "entities"]
MADE = []


def folder(name: str) -> Path:
    MADE.append(name)
    shutil.rmtree(simlib.saves_path() / name, ignore_errors=True)
    return simlib.saves_path() / name


def copied(name: str, kept: str) -> Path:
    root = folder(name)
    root.mkdir(parents=True)
    shutil.copyfile(KEPT / kept, root / DB_NAME)
    return root / DB_NAME


class Raw:
    """A database read as it lies, for the fingerprint: no store, no step run."""
    def __init__(self, path):
        self._db, self._lock = sqlite3.connect(path), threading.RLock()


def raw_dump(path) -> dict:
    r = Raw(path)
    try:
        return statehash.dump(r)
    finally:
        r._db.close()


def schema(store) -> set:
    return {(r[0], r[1], r[2]) for r in store._db.execute("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}


def tables(store) -> set:
    return {r[0] for r in store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


# ---- a new save
check("the save's version is 17, and the step before it is 16", migrations.CURRENT == 17 and migrations.MIGRATIONS[-2][0] == 16, migrations.CURRENT)
folder("tables_640_new")
new = simlib.campaign("tables_640_new", seed=3, location="trading_square")
store = new.store
check("a new save is version 17 with the five tables, and its store reads and writes them", store.version == 17 and FIVE <= tables(store)
      and type(store._world) is worldtables.TableWorld and type(store._players) is playerstable.TablePlayers,
      (store.version, sorted(tables(store)), type(store._world).__name__, type(store._players).__name__))
st = store.load_world_state()
st.setdefault("news", []).append({"text": "A cart lost a wheel at the gate.", "place": "parth", "minute": 5, "origin": "pulse"})
st.setdefault("deeds", []).append({"seq": 1, "minute": 5, "kind": "found", "place": "parth", "by": "player"})
store.save_world_state(st)
held = json.loads(store._kv_text("world_state"))
check("its player is a row of the players table and no row of the small one", store._kv_text("player") is None and store.player_exists()
      and [r[0] for r in store._db.execute("SELECT character_id FROM players")] == ["player"])
check("its world's row holds a marker where each list stood, and the lists are rows", all(held[k] == worldtables.marker(k) for k in ("news", "deeds"))
      and store._db.execute("SELECT count(*) FROM news").fetchone()[0] == 1 and store.load_world_state()["news"][0]["text"].startswith("A cart"), held)
check("the campaign's check finds nothing wrong in it", [str(p) for p in invariants.validate_campaign(store, new.session.world)] == [],
      [str(p) for p in invariants.validate_campaign(store, new.session.world)][:3])
fresh_schema = schema(store)

# ---- the fingerprint
check("the state's fingerprint reads the five tables after the six", list(statehash.TABLES) == OLD + [playerstable.TABLE, *LISTS], list(statehash.TABLES))
d0 = statehash.digest(store)
st = store.load_world_state()
st["news"].insert(0, {"text": "Rain since dawn.", "place": "parth", "minute": 1, "origin": "pulse"})
store.save_world_state(st)
d1 = statehash.digest(store)
dumped = statehash.dump(store)
check("a list's rows are read by where they stand, and a row put in moves that table's mark and no other's",
      [r[0] for r in dumped["news"]] == [1, 2] and dumped["news"][0][-1]["text"] == "Rain since dawn."
      and [t for t in d0 if d0[t] != d1[t]] == ["news", "all"], ([r[0] for r in dumped["news"]], [t for t in d0 if d0[t] != d1[t]]))
p = store.load_player()
p.location = "guild_house"
store.save_player(p)
d2 = statehash.digest(store)
check("...and a player who moved moves the players' mark", "players" in [t for t in d1 if d1[t] != d2[t]], [t for t in d1 if d1[t] != d2[t]])
seen = statehash.view(statehash.dump(store), 16)
check("read as version 16 held it, the state is six tables, the player and the whole world back in the small one",
      list(seen) == OLD and [r[0] for r in seen["kv"]] == sorted(r[0] for r in seen["kv"])
      and dict((r[0], r[1]) for r in seen["kv"])["player"]["location"] == "guild_house"
      and dict((r[0], r[1]) for r in seen["kv"])["world_state"] == store.load_world_state(), list(seen))
try:
    statehash.view(statehash.dump(store), 15)
    refused = False
except ValueError:
    refused = True
check("...and a version there is no view of is refused", refused)
new.session.close()

# ---- the saves kept at version 16
for kept in sorted(p.name for p in KEPT.glob("*.db")):
    stem = Path(kept).stem
    path = copied(f"tables_640_{stem}", kept)
    before = raw_dump(path)
    listed = saves.summary(f"tables_640_{stem}")
    s = CampaignStore.open_or_create(f"tables_640_{stem}")
    backs = [b.name for b in (path.parent / "backups").glob("*.db")]
    after = statehash.view(statehash.dump(s), 16)
    check(f"{kept}: opens at 17 with one backup of it at 16, its store on the tables", s.version == 17 and len(backs) == 1 and "v16" in backs[0]
          and type(s._world) is worldtables.TableWorld and type(s._players) is playerstable.TablePlayers, (s.version, backs))
    check(f"{kept}: read as version 16 held it, its state is what it was, table for table", all(after[t] == before[t] for t in OLD),
          statehash.diff({t: before[t] for t in OLD}, after)[:3])
    check(f"{kept}: no row of the player is left behind, and the check finds nothing wrong", s._kv_text("player") is None
          and worldtables.problems(s) == [] and playerstable.problems(s) == [], (worldtables.problems(s)[:2], playerstable.problems(s)[:2]))
    check(f"{kept}: its tables and indexes are a new save's", schema(s) >= {x for x in fresh_schema if x[1] in FIVE or x[1] in worldtables.INDEXES}
          and {x[1] for x in schema(s)} == {x[1] for x in fresh_schema}, sorted({x[1] for x in schema(s)} ^ {x[1] for x in fresh_schema}))
    s.close()
    again = saves.summary(f"tables_640_{stem}")
    check(f"{kept}: the home page says the same of it before it is opened and after",
          listed["ready"] and {k: v for k, v in listed.items() if k != "played"} == {k: v for k, v in again.items() if k != "played"}
          and listed["character"], (listed, again))
    s = CampaignStore.open_or_create(f"tables_640_{stem}")
    check(f"{kept}: opened again, nothing more is done to it", s.version == 17 and len(list((path.parent / "backups").glob("*.db"))) == 1
          and statehash.view(statehash.dump(s), 16) == after)
    s.close()

# ---- rows of an older shape are kept as written
path = copied("tables_640_shapes", "stub_short.db")
old_world = {"seq": 0, "threads": [{"id": "t1", "title": "A quarrel over a well", "status": "active"}],
             "news": [{"text": "Élan the miller is ill.", "place": "parth", "minute": 3}],
             "deeds": [{"minute": 2, "kind": "start", "place": "parth"}], "effects": [], "history": [{"text": "It began.", "minute": 1}],
             "campaign": "", "odd": None}
db = sqlite3.connect(path)
db.execute("INSERT INTO kv (key, json) VALUES ('world_state', ?)", (json.dumps(old_world),))
db.commit(); db.close()
s = CampaignStore.open_or_create("tables_640_shapes")
got = s.load_world_state()
rows = {t: [json.loads(r[0]) for r in s._db.execute(f'SELECT json FROM "{t}" ORDER BY ord')] for t in LISTS}
check("rows of an older shape come through as they were written, their keys in their order", got == old_world and list(got) == list(old_world)
      and rows == {t: old_world[t] for t in LISTS}, worldtables.problems(s))
check("...their columns read from them, a field they lack the column's nothing, a deed with no doer the first character's",
      s._db.execute("SELECT id, status, place FROM threads").fetchall() == [("t1", "active", "")]
      and s._db.execute("SELECT seq, minute, kind, actor, place FROM deeds").fetchall() == [(0, 2, "start", "player", "parth")]
      and worldtables.problems(s) == [], s._db.execute("SELECT seq, minute, kind, actor, place FROM deeds").fetchall())
s.close()

# ---- no world, no player
path = copied("tables_640_bare", "stub_short.db")
db = sqlite3.connect(path)
db.execute("DELETE FROM kv WHERE key IN ('player', 'world_state')")
db.commit(); db.close()
s = CampaignStore.open_or_create("tables_640_bare")
check("a save with no world and no player opens at 17 with neither, and the tables empty", s.version == 17 and s.load_world_state() == {}
      and not s.player_exists() and s._kv_text("world_state") is None
      and all(s._db.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] == 0 for t in FIVE))
s.close()

# ---- the older steps still read the player and the world
old = rows_v16.opened("tables_640_older", "stub_party.db")
MADE.append("tables_640_older")
p = old.load_player()
npc = mentor.make_npc(p, old.meta.minutes, 1, "guild_house").model_copy(update={"gone": "", "voice": "a voice drawn for a townsperson"})
old.save_npc(npc)
hall = old.load_place("guild_house")
hall.residents.append("maren")
old.save_place(hall)
body = json.loads(old._kv_text("player"))
had = [m.pop("pronoun") for m in body["party"]]
old._put("player", json.dumps(body, ensure_ascii=False))
old.set_version(5)
old.close()
s = CampaignStore.open_or_create("tables_640_older")
maren = s.load_npc("maren")
check("a save from before v6 is brought to 17", s.version == 17 and type(s._world) is worldtables.TableWorld and s._kv_text("player") is None, s.version)
check("...Maren has the voice she was written with (v6, which reads the player)", maren.voice == mentor.M["npc"]["voice"], maren.voice)
check("...she has moved on and the town was told (v7, which writes the world), the news now a row",
      bool(maren.gone) and "maren" not in s.load_place("guild_house").residents
      and any("Maren Holt" in n["text"] for n in s.load_world_state().get("news", []))
      and any("Maren Holt" in r[0] for r in s._db.execute("SELECT json FROM news")), maren.gone)
check("...and every hire has their pronoun back (v8, which writes the player), in the table's record",
      len(had) == 3 and [m.get("pronoun") for m in json.loads(s.player_text())["party"]] == had, [m.get("pronoun") for m in json.loads(s.player_text())["party"]])
s.close()

# ---- a save that cannot be migrated
path = copied("tables_640_torn", "stub_party.db")
db = sqlite3.connect(path)
db.execute("UPDATE kv SET json = 'not a world' WHERE key = 'world_state'")
db.commit(); db.close()
was = raw_dump(path)
logged = len(crashlog.SESSION)
try:
    CampaignSession.open("tables_640_torn")
    line = None
except cmod.SaveNotMigrated as e:
    line = str(e)
entry = crashlog.SESSION[-1] if len(crashlog.SESSION) > logged else {}
check("...why its step failed is kept for the logs: the save, the step and the error under it", entry.get("save") == "tables_640_torn"
      and "v17" in entry.get("error", "") and "StepFailed" in entry.get("error", ""), entry)
check("a save that cannot be migrated is refused in a line, with no dash in it", bool(line) and not any(c in line for c in "-–—")
      and "new game" in (line or "").lower(), line)
check("...the two refusals are one kind for the caller, and the newer save's is still its own", issubclass(cmod.SaveNotMigrated, cmod.SaveRefused)
      and issubclass(SaveTooNew, cmod.SaveRefused) and not issubclass(cmod.SaveNotMigrated, SaveTooNew))
db = sqlite3.connect(path)
left = (db.execute("PRAGMA user_version").fetchone()[0], {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")})
db.close()
check("...its file is as it was, at 16 with no table made, and a copy is in its backups", left[0] == 16 and not left[1] & FIVE and raw_dump(path) == was
      and len(list((path.parent / "backups").glob("*v16*.db"))) == 1, left)
shutil.rmtree(path.parent)
check("...and it was closed: the folder can be taken away", not path.parent.exists())

# ---- a step that fails after another stood, and a failure that is no step's
def broke(store) -> None:
    store.execute("CREATE TABLE half_made (x)")
    raise RuntimeError("the step broke")

path = copied("tables_640_partway", "stub_party.db")
copied("tables_640_clean", "stub_party.db")
steps, current = migrations.MIGRATIONS, migrations.CURRENT
migrations.MIGRATIONS, migrations.CURRENT = steps + [(18, "a step that fails", broke)], 18
try:
    CampaignStore.open_or_create("tables_640_partway")
    line = cause = None
except cmod.SaveNotMigrated as e:
    line, cause = str(e), e.__cause__
finally:
    migrations.MIGRATIONS, migrations.CURRENT = steps, current
db = sqlite3.connect(path)
left = (db.execute("PRAGMA user_version").fetchone()[0], {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")})
db.close()
check("a step that fails after another stood is refused in the same line, the step and its error named under it", line == cmod.NOT_MIGRATED
      and isinstance(cause, migrations.StepFailed) and cause.version == 18 and isinstance(cause.__cause__, RuntimeError) and "the step broke" in str(cause), (line, cause))
check("...the save is left at the last step that stood: at 17 with its tables, nothing of the failed step, a copy from before the first in its backups",
      left[0] == 17 and FIVE <= left[1] and "half_made" not in left[1] and len(list((path.parent / "backups").glob("*v16*.db"))) == 1, left)
s, c = CampaignStore.open_or_create("tables_640_partway"), CampaignStore.open_or_create("tables_640_clean")
check("...and it opens afterwards as the save a clean migration makes", s.version == 17 and statehash.digest(s) == statehash.digest(c),
      statehash.diff(statehash.dump(c), statehash.dump(s))[:3])
s.close(); c.close()

path = copied("tables_640_nocopy", "stub_party.db")
was = raw_dump(path)
real = CampaignStore.backup
def full(self, label=""):
    raise OSError("no room for the copy")
CampaignStore.backup = full
try:
    CampaignStore.open_or_create("tables_640_nocopy")
    told = None
except Exception as e:
    told = e
finally:
    CampaignStore.backup = real
check("a copy that could not be taken is its own fault, never told as a save with a copy in its backups: no step run, the file as it was",
      isinstance(told, OSError) and not isinstance(told, cmod.SaveRefused) and raw_dump(path) == was, told)
shutil.rmtree(path.parent)
check("...and the file was closed", not path.parent.exists())

s = CampaignStore.open_or_create("tables_640_clean")
d = statehash.dump(s)
d["kv"] = d["kv"] + [[playerstable.KEY, {"stale": True}]]
v = [r for r in statehash.view(d, 16)["kv"] if r[0] == playerstable.KEY]
check("the view of 16 holds one player, the table's, whatever is left beside it in the small table",
      len(v) == 1 and v[0][1] == json.loads(s.player_text()), v)
s.close()
logged = len(crashlog.SESSION)
main_py = Path("main.py").read_text(encoding="utf-8")
check("the game's loop tells the player either refusal and goes back to the home page", "except SaveRefused" in main_py and "except SaveTooNew" not in main_py)

path = copied("tables_640_future", "stub_short.db")
s = CampaignStore.open_or_create("tables_640_future")
s.close()
real = migrations.CURRENT
migrations.CURRENT = 16
try:
    CampaignSession.open("tables_640_future")
    line = None
except SaveTooNew as e:
    line = str(e)
finally:
    migrations.CURRENT = real
check("a version 17 save is refused by a build that reads up to 16", bool(line) and "v17" in line and "v16" in line, line)
check("...and that is no fault: nothing is written to the logs for it", len(crashlog.SESSION) == logged, crashlog.SESSION[logged:])

# ---- the export
game = simlib.campaign("tables_640_new", seed=3, location="trading_square", fresh=False)
s = game.store
out = simlib.saves_path() / "tables_640_new" / "export"
s.export_json(out)
world_out = json.loads((out / "world_state.json").read_text(encoding="utf-8"))
player_out = json.loads((out / "player.json").read_text(encoding="utf-8"))
check("the export writes the player and the whole world, its lists in their places", player_out == json.loads(s.player_text())
      and world_out == s.load_world_state() and len(world_out["news"]) == 2 and player_out["location"] == "guild_house", list(world_out))
game.session.close()

# ---- the replay's view
import rerun
import inspect
check("the replay can read the state as an older version held it", "as_schema" in inspect.signature(rerun.replay).parameters)
done = subprocess.run([sys.executable, "tools/rerun.py", "--golden", "stub_short", "--as-schema", "15"], capture_output=True, text=True,
                      encoding="utf-8", errors="replace")
check("...and refuses a version it has no view of, before it plays anything", done.returncode == 2 and "15" in done.stdout + done.stderr
      and "16" in done.stdout + done.stderr, (done.returncode, (done.stdout + done.stderr)[-300:]))

for name in MADE:
    shutil.rmtree(simlib.saves_path(name), ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

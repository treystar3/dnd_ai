"""(f747) An old save whose player's record does not read is refused, never stepped past. The steps that read the player (v6, v8)
ask whether there is one and read it with no guard, so a record that does not read stops its step: the save is refused in the line
f640 wrote, left at the last step that stood with its copy in the backups, and why is kept for the logs. Held here:
- a save at v5 with Maren a person of the world and a record the game refuses: v6 stops, the save is left at v5, her drawn voice kept;
- the same save without her (a second step of the kind): v6 and v7 stand, v8 stops, the save is left at v7 with the copy from v5;
  its record mended, it opens at 17 and every hire has their pronoun back, so nothing was skipped for good;
- a save at v5 with no player at all still opens at 17, Maren's voice written (the case the old guards were for);
- no step of the migration catches every fault and goes on (a handler that raises again is no answer): run() is the one place that
  does, and it refuses the save.
Run: python tools/sim/old_player_row_747_test.py"""
import ast
import json
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
sys.path.insert(0, "tools/sim")
sys.path.insert(0, "tools")
import rows_v16
from engine import crashlog, mentor
from engine.session import CampaignSession
from storage import migrations, playerstable
from storage import campaign as cmod
from storage.campaign import DB_NAME, CampaignStore, PlayerState

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

MADE = []


def aged(name: str, maren: bool, record: str) -> tuple[list, str]:
    """A kept v16 save put back to v5, the hires' pronouns taken out (v8 gives them back); Maren a person of the world or not; its
    player's record whole ('whole'), whole JSON the game refuses ('torn': it stands nowhere), or gone ('none')."""
    MADE.append(name)
    old = rows_v16.opened(name, "stub_party.db")
    if maren:
        p = old.load_player()
        npc = mentor.make_npc(p, old.meta.minutes, 1, "guild_house").model_copy(update={"gone": "", "voice": "a voice drawn for a townsperson"})
        old.save_npc(npc)
        hall = old.load_place("guild_house")
        hall.residents.append("maren")
        old.save_place(hall)
    body = json.loads(old._kv_text("player"))
    had = [m.pop("pronoun") for m in body["party"]]
    where = body["location"]
    if record == "torn":
        body["location"] = None
    if record == "none":
        old._drop("player")
    else:
        old._put("player", json.dumps(body, ensure_ascii=False))
    old.set_version(5)
    old.close()
    return had, where


def opened(name: str):
    """The save opened as the game opens it: the session, or the line the player is told and the entry kept for the logs."""
    logged = len(crashlog.SESSION)
    try:
        session = CampaignSession.open(name)
        return session, None, None, []
    except cmod.SaveRefused as e:
        return None, e, e.__cause__, crashlog.SESSION[logged:]


def lying(name: str) -> dict:
    """The file as it lies after the try: its version, its tables, its player's row, Maren's voice, its copies."""
    path = simlib.saves_path(name, DB_NAME)
    db = sqlite3.connect(path)
    try:
        maren = db.execute("SELECT json FROM npcs WHERE id = 'maren'").fetchone()
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        row = (db.execute(f'SELECT json FROM "{playerstable.TABLE}" ORDER BY rowid').fetchone() if playerstable.TABLE in tables
               else db.execute("SELECT json FROM kv WHERE key = 'player'").fetchone())
        return {"version": db.execute("PRAGMA user_version").fetchone()[0], "tables": tables,
                "row": row[0] if row else None, "voice": json.loads(maren[0])["voice"] if maren else None,
                "copies": sorted(p.name for p in (path.parent / "backups").glob("*.db"))}
    finally:
        db.close()


# ---- the record the game refuses
_, where = aged("old_row_probe", maren=False, record="torn")
text = lying("old_row_probe")["row"]
try:
    PlayerState.model_validate_json(text)
    refused = False
except ValueError:
    refused = True
check("the record of the cases below is whole JSON that the game refuses: it stands nowhere", refused and json.loads(text)["location"] is None
      and bool(where), where)

# ---- v6: Maren a person of the world, the player's record refused
had, _ = aged("old_row_v6", maren=True, record="torn")
before = lying("old_row_v6")
session, refusal, cause, entries = opened("old_row_v6")
if session:
    session.close()
after = lying("old_row_v6")
check("with Maren a person of the world, a save whose record does not read is refused in the line the player reads, with no dash",
      refusal is not None and str(refusal) == cmod.NOT_MIGRATED and not any(c in str(refusal) for c in "-–—"),
      (refusal, after["version"]))
check("...the step that stopped is v6, which reads the player for her lines", isinstance(cause, migrations.StepFailed) and cause.version == 6,
      (type(cause).__name__, getattr(cause, "version", None), str(cause)[:200]))
check("...why is kept for the logs: the save, the step and the error under it",
      len(entries) == 1 and entries[0].get("save") == "old_row_v6" and "v6" in entries[0].get("error", "")
      and "ValidationError" in entries[0].get("error", ""), entries)
check("...the save is left at v5 as it was: her drawn voice, the record as written, no table made, one copy from v5",
      after["version"] == 5 and after["voice"] == "a voice drawn for a townsperson" and after["row"] == before["row"]
      and playerstable.TABLE not in after["tables"] and len(after["copies"]) == 1 and "_v5_" in after["copies"][0],
      {k: after[k] for k in ("version", "voice", "copies")})

# ---- v8: no Maren, so v6 and v7 stand and the hires' step is the one that reads the record
had, where = aged("old_row_v8", maren=False, record="torn")
before = lying("old_row_v8")
session, refusal, cause, entries = opened("old_row_v8")
if session:
    session.close()
after = lying("old_row_v8")
check("without her, the same record is refused in the same line", refusal is not None and str(refusal) == cmod.NOT_MIGRATED,
      (refusal, after["version"]))
check("...the step that stopped is v8, which gives the hires their pronouns", isinstance(cause, migrations.StepFailed) and cause.version == 8,
      (type(cause).__name__, getattr(cause, "version", None), str(cause)[:200]))
check("...and why is kept for the logs", len(entries) == 1 and entries[0].get("save") == "old_row_v8" and "v8" in entries[0].get("error", ""),
      entries)
check("...the save is left at v7, the last step that stood, its record as written and its copy the one from v5",
      after["version"] == 7 and after["row"] == before["row"] and playerstable.TABLE not in after["tables"]
      and len(after["copies"]) == 1 and "_v5_" in after["copies"][0], {k: after[k] for k in ("version", "copies")})
check("...no hire was given a pronoun by a step that stopped", [m.get("pronoun") for m in json.loads(after["row"])["party"]] == [None] * len(had),
      [m.get("pronoun") for m in json.loads(after["row"])["party"]])

body = json.loads(after["row"])
body["location"] = where
db = sqlite3.connect(simlib.saves_path("old_row_v8", DB_NAME))
db.execute("UPDATE kv SET json = ? WHERE key = 'player'", (json.dumps(body, ensure_ascii=False),))
db.commit(); db.close()
session, refusal, cause, entries = opened("old_row_v8")
mended = (session.store.version, [m.get("pronoun") for m in json.loads(session.store.player_text())["party"]]) if session else (None, None)
if session:
    session.close()
check("its record mended, the save opens at 17 and every hire has their pronoun back: the step was never skipped for good",
      session is not None and mended[0] == migrations.CURRENT and len(had) == 3 and mended[1] == had, (refusal, cause, mended, had))

# ---- no player at all: the case the old guards were for
aged("old_row_none", maren=True, record="none")
logged = len(crashlog.SESSION)
s = CampaignStore.open_or_create("old_row_none")
check("a save at v5 with no player at all still opens at 17, with no player and nothing for the logs",
      s.version == migrations.CURRENT and not s.player_exists() and len(crashlog.SESSION) == logged, (s.version, crashlog.SESSION[logged:]))
check("...and Maren has the voice she was written with (v6 with no player to read)", s.load_npc("maren").voice == mentor.M["npc"]["voice"],
      s.load_npc("maren").voice)
s.close()

# ---- the kind: no step of the migration takes a fault for an answer
tree = ast.parse(Path("storage/migrations.py").read_text(encoding="utf-8"))
broad = []
for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name != "run"):
    for h in (x for x in ast.walk(fn) if isinstance(x, ast.ExceptHandler)):
        names = [t for t in (h.type.elts if isinstance(h.type, ast.Tuple) else [h.type])] if h.type is not None else [None]
        goes_on = not (h.body and isinstance(h.body[-1], ast.Raise))
        if goes_on and any(t is None or (isinstance(t, ast.Name) and t.id in ("Exception", "BaseException")) for t in names):
            broad.append(f"{fn.name}:{h.lineno}")
steps = {s.__name__ for _, _, s in migrations.MIGRATIONS}
check("no step of the migration catches every fault and goes on: a step that fails is run()'s to refuse (StepFailed)", broad == [], broad)
check("...and the scan read every step", steps <= {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}, steps)

for name in MADE:
    shutil.rmtree(simlib.saves_path(name), ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

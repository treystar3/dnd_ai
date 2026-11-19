"""(f744) A save folder in the one-file-per-record layout from before the database (campaign.json, player.json, npcs/ and the
rest, no campaign.db) is refused by the store with one plain line and left as it was, never made a new database, marked current
and then read past the migration steps. Held here, in a saves folder of its own:
- the case that found it: an old-layout save is refused, no database is made in it, its files are as they were;
- the failed import: a folder holding a record this build cannot read is refused on the first open and on the second, and no
  new campaign is started over it;
- second cases of the kind (a folder of the old layout, no database): one without campaign.json, its player, world and people
  only, where a new campaign was started over the files; and a folder holding any one entry of that layout alone;
- and what still opens: a new folder, an empty one, a version 1 database brought forward by the steps (its memory typed, its
  player moved to its table), a database with a stray campaign.json beside it; a database save named main is still adopted
  and listed, and the home page lists no old-layout folder.
Run: python tools/sim/old_layout_744_test.py"""
import gc
import json
import random
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import campaign as cmod
from storage import migrations, saves
from storage.campaign import DB_NAME, SCHEMA_V1, CampaignMeta, CampaignStore, PlaceState, PlayerState
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

BASE = Path(tempfile.mkdtemp(prefix="old_layout_"))
cmod.SAVES_DIR = BASE                                        # nothing here can reach the real saves/
REFUSAL = getattr(cmod, "OldLayout", None)
DASHES = ("-", "‐", "‑", "‒", "–", "—", "―", "−")
LAYOUT = ("campaign.json", "player.json", "world_state.json", "dungeons.json", "arcs.json", "discoveries.json", "legendaries.json",
          "combat.json", "story.json", "places", "npcs")    # the old layout as its saves held it, written here, not read from the code
ch, _ = simlib.make_character("warrior", random.Random(1))


def snapshot(root: Path) -> dict:
    """Every file under a folder, with its bytes."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                out[p.relative_to(root).as_posix()] = p.read_bytes()
            except OSError:
                out[p.relative_to(root).as_posix()] = b"(held open)"
    return out


def open_it(name: str):
    """What the store does with the folder: ("opened", store), ("refused", error) or ("failed", error)."""
    try:
        return "opened", CampaignStore.open_or_create(name, saves_dir=BASE)
    except Exception as e:
        return ("refused" if REFUSAL is not None and isinstance(e, REFUSAL) else "failed"), e


def told(how, got) -> str:
    """What an open that did not refuse did, for the failure's line."""
    if how != "opened":
        return f"{how}: {type(got).__name__}: {got}"
    row = got._db.execute("SELECT kind, subject, text FROM npc_memory").fetchall()
    said = (f"opened at version {got.version} of {migrations.CURRENT}, seed {got.meta.seed}, turn {got.meta.turn}, "
            f"player: {got.load_player().location if got.player_exists() else None}, memory rows: {row}")
    got.close()
    return said


def plain(how, got, name) -> bool:
    line = str(got) if how == "refused" else ""
    return bool(line) and name in line and "\n" not in line and not any(d in line.replace(str(BASE), "") for d in DASHES)


def old_npc(npc_id: str, place: str) -> str:
    body = json.loads(NPC(id=npc_id, name="Old Tom", people="human", role="farmer", location=place).model_dump_json())
    body["memories"] = [{"day": 1, "turn": -1, "text": "(my own life) I walked the long road down to Parth."}]
    return json.dumps(body)


def left_alone(root: Path, before: dict) -> bool:
    gc.collect()                                             # a handle a failed open left
    return not (root / DB_NAME).exists() and not list(root.glob(DB_NAME + "-*")) and snapshot(root) == before


# ---- 1. the case that found it: an old-layout save, opened by name
old = BASE / "old_save"
(old / "npcs").mkdir(parents=True)
(old / "campaign.json").write_text(CampaignMeta(name="old_save", seed=5, turn=40, created="2026-10-12T10:00:00").model_dump_json(), encoding="utf-8")
(old / "player.json").write_text(PlayerState(character=ch, location="parth").model_dump_json(), encoding="utf-8")
(old / "npcs" / "n1.json").write_text(old_npc("n1", "parth"), encoding="utf-8")
before = snapshot(old)
how, got = open_it("old_save")
check("a save in the old file layout is refused by the store, not made current and read", how == "refused", told(how, got))
check("...in one plain line that names the folder, with no dash", plain(how, got, "old_save"), str(got))
check("...no database is made in it, and its files are as they were, none moved aside", left_alone(old, before),
      sorted(p.relative_to(old).as_posix() for p in old.rglob("*")))

# ---- 2. the failed import: a record this build cannot read, the folder opened twice
half = BASE / "half_read"
(half / "npcs").mkdir(parents=True)
(half / "campaign.json").write_text(CampaignMeta(name="half_read", seed=77, turn=40, created="2026-10-14T10:00:00").model_dump_json(), encoding="utf-8")
(half / "player.json").write_text(PlayerState(character=ch, location="parth").model_dump_json(), encoding="utf-8")
(half / "npcs" / "n1.json").write_text('{"id": "n1", "name": 5, "people": [], "role": {}}', encoding="utf-8")
before = snapshot(half)
first, got1 = open_it("half_read")
said1 = told(first, got1)
gc.collect()
second, got2 = open_it("half_read")
check("an old-layout save holding a record this build cannot read is refused on the first open", first == "refused", said1)
check("...and on the second: no new campaign is started over its files", second == "refused", told(second, got2))
check("...no database is left behind, and its files are as they were", left_alone(half, before),
      sorted(p.relative_to(half).as_posix() for p in half.rglob("*")))

# ---- 3. second case: an old-layout folder with no campaign.json, its player, world and people only
bare = BASE / "no_meta"
(bare / "npcs").mkdir(parents=True)
(bare / "places").mkdir()
(bare / "player.json").write_text(PlayerState(character=ch, location="parth").model_dump_json(), encoding="utf-8")
(bare / "world_state.json").write_text(json.dumps({"last": 5000, "threads": [], "news": []}), encoding="utf-8")
(bare / "npcs" / "n1.json").write_text(old_npc("n1", "parth"), encoding="utf-8")
(bare / "places" / "parth.json").write_text(PlaceState(id="parth", populated=True, residents=["n1"]).model_dump_json(), encoding="utf-8")
before = snapshot(bare)
how, got = open_it("no_meta")
check("second case: an old-layout folder with no campaign.json is refused too, where a new campaign was begun over its files",
      how == "refused", told(how, got))
check("...no database is made in it, and its files are as they were", left_alone(bare, before),
      sorted(p.relative_to(bare).as_posix() for p in bare.rglob("*")))

# ---- 4. second case: a folder holding any one entry of the old layout alone
alone = []
for entry in LAYOUT:
    name = "only_" + entry.replace(".json", "")
    root = BASE / name
    root.mkdir(parents=True)
    if entry.endswith(".json"):
        (root / entry).write_text("{}", encoding="utf-8")
    else:
        (root / entry).mkdir()
        (root / entry / "x1.json").write_text("{}", encoding="utf-8")
    before = snapshot(root)
    how, got = open_it(name)
    said = told(how, got)
    if how != "refused" or not left_alone(root, before):
        alone.append((entry, said))
check("a folder holding any one entry of the old layout, and no database, is refused and left as it was", not alone, alone)

# ---- 5. what still opens
how, got = open_it("new_game")
check("a new folder still makes a new campaign, at the current version, with no player",
      how == "opened" and got.version == migrations.CURRENT and got.meta.seed > 0 and not got.player_exists(), told(how, got) if how != "opened" else "")
if how == "opened":
    got.close()
(BASE / "empty_folder").mkdir()
how, got = open_it("empty_folder")
check("...and so does an empty folder that is already there", how == "opened" and got.version == migrations.CURRENT, told(how, got) if how != "opened" else "")
if how == "opened":
    got.close()

v1 = BASE / "v1_save"                                        # the same October records, in a version 1 database
v1.mkdir()
db = sqlite3.connect(v1 / DB_NAME)
db.executescript(SCHEMA_V1)
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (CampaignMeta(name="v1_save", seed=5, turn=40, created="x").model_dump_json(),))
db.execute("INSERT INTO kv (key, json) VALUES ('player', ?)", (PlayerState(character=ch, location="parth").model_dump_json(),))
db.execute("INSERT INTO npcs (id, json, name, role, location) VALUES (?, ?, ?, ?, ?)", ("n1", old_npc("n1", "parth"), "Old Tom", "farmer", "parth"))
db.execute("PRAGMA user_version = 1")
db.commit()
db.close()
how, got = open_it("v1_save")
moved = (got.version, got.meta.seed, got.load_player().location, got._kv_text("player"),
         got._db.execute("SELECT kind, subject, text FROM npc_memory WHERE npc_id = 'n1'").fetchall()) if how == "opened" else told(how, got)
if how == "opened":
    got.close()
check("a version 1 database of the same records is brought forward by the steps: its memory typed, its player moved to its table",
      how == "opened" and moved[0] == migrations.CURRENT and moved[1] == 5 and moved[2] == "parth" and moved[3] is None
      and [r[0] for r in moved[4]] == ["own_life"] and moved[4][0][2] == "I walked the long road down to Parth.", moved)

st = CampaignStore.open_or_create("db_and_json", saves_dir=BASE)  # a database save with a stray campaign.json beside it
seed = st.meta.seed
st.save_player(PlayerState(character=ch, location="parth"))
st.close()
(BASE / "db_and_json" / "campaign.json").write_text(CampaignMeta(name="db_and_json", seed=99, created="x").model_dump_json(), encoding="utf-8")
how, got = open_it("db_and_json")
check("a folder with a database opens as that database, whatever old file lies beside it",
      how == "opened" and got.meta.seed == seed and got.load_player().location == "parth"
      and (BASE / "db_and_json" / "campaign.json").exists() and not (BASE / "db_and_json" / "legacy_json").exists(),
      told(how, got) if how != "opened" else (got.meta.seed, seed))
if how == "opened":
    got.close()

st = CampaignStore.open_or_create("main", saves_dir=BASE)   # the old single save: a database, from before the save index
c, _ = simlib.make_character("warrior", random.Random(1))
c.name = "Horseguy55"
st.save_player(PlayerState(character=c, location="parth"))
st.close()
listed = {s["name"]: s for s in saves.list_saves(BASE)}
check("a database save named main is still adopted and listed, with its character",
      listed.get("main", {}).get("character") == "Horseguy55" and listed["main"]["ready"], sorted(listed))
check("...and the home page lists no old-layout folder, nor any other folder no game marked", sorted(listed) == ["main"], sorted(listed))

gc.collect()
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f638) The players table, built and proven, not yet used (docs/design/20_phase3_plan.md; docs/design/13; storage/playerstable.py).
A save keeps its one player's record as one row of the small table, under the key 'player'. TablePlayers keeps a row for each
character in a table of its own, the first under the id the save's one character has always had. Held here:
- nothing uses it yet: a save is version 16, has no players table, and its store's players are the row's;
- the store's load, save, exists and raw text go through the port, and over the row they are what they were;
- adopting a save moves the record into the table as it was, byte for byte, and takes the row away;
- for each save kept at version 16 (two of them with hires) the player loads the same from the table as from the row, saves the
  same text, and leaves every other table the same: a hire's memories stay rows;
- a row's place is read from its record when it is written;
- the player and the clock are one write: a fault between them leaves neither, and a transaction that failed leaves the row as it was;
- the table holds a row for each character, and the row's port refuses a second;
- the campaign's check names a place that is not what its record says, a record that cannot be read, and the old row left beside
  the table;
- the scene sees the pulse write the player over the table as over the row (f466), and an operation that wrote the player
  and did not stand gives the record back as it was;
- the seeded world script played over the row and over the table, a process each, holds the same world after every step, the
  same other tables, lines shown, operations and model calls, and the same player at the end.
Run: python tools/sim/players_638_test.py"""
import json
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
sys.path.insert(0, "tools/sim")
import world_script
import rows_v16
from core.models import Character
from engine import party as rules
from engine import pulse
from llm.gateway import LLMError
from storage import invariants, migrations, playerstable, statehash
from storage.campaign import DB_NAME, CampaignStore

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

FIRST = Character.model_fields["id"].default
KEPT = Path("data/replay/saves_v16")
MADE = []


def scratch(name: str, kept: str = "") -> CampaignStore:
    """(f640) A save as version 16 kept it, its player in the row: a new one put back, or a copy of one of the saves kept at
    that version with no later step run. The row's side of every comparison here, and what `adopt` is tried on."""
    MADE.append(name)
    return rows_v16.opened(name, kept)


def tables(store) -> set:
    return {r[0] for r in store._db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def held(store) -> list[tuple]:
    return [tuple(r) for r in store._db.execute("SELECT character_id, place, json FROM players ORDER BY rowid")]


def others(store) -> dict:
    """Every table but the player's own record: the small table without its 'player' row, and the rest whole."""
    d = statehash.dump(store)
    d["kv"] = [r for r in d["kv"] if r[0] != "player"]
    d.pop(playerstable.TABLE, None)                       # (f640) the fingerprint reads the players table: the record's other home
    return d


# ---- (f640) in use: a save has the table, and one put back is the row
plain = scratch("players_638_plain")
shutil.rmtree("saves/players_638_live", ignore_errors=True)
MADE.append("players_638_live")
live = CampaignStore.open_or_create("players_638_live")
check("a save is version 17 and its players are the table's; one put back is version 16, its players the row's, with no players table",
      migrations.CURRENT == 17 and live.version == 17 and type(live._players) is playerstable.TablePlayers and "players" in tables(live)
      and plain.version == 16 and type(plain._players) is playerstable.RowPlayers and "players" not in tables(plain),
      (type(live._players).__name__, type(plain._players).__name__, tables(plain)))
live.close()
check("a save with no player has none, by the store and by the port", not plain.player_exists() and plain.player_text() is None
      and plain._players.ids() == [] and not plain._players.exists(FIRST))
check("the first character's id is the one a character has by default", playerstable.FIRST == FIRST == "player")

# ---- over the row, the store's four are what they were
row = scratch("players_638_row", "stub_party.db")
text = row._kv_text("player")
check("over the row: the record's raw text is the row's, the player exists, and the port holds the one", row.player_text() == text and text
      and row.player_exists() and row._players.ids() == [FIRST] and row._players.text(FIRST) == text)
p = row.load_player()
row.save_player(p)
check("...and a player loaded and saved is written to the row, the same text", row._kv_text("player") == row.player_text() == text,
      world_script.first_difference(text, row._kv_text("player") or "{}"))

# ---- adopting a save
tab = scratch("players_638_tab", "stub_party.db")
port = playerstable.adopt(tab)
check("adopting a save makes the table and puts the store's players on it", "players" in tables(tab) and tab._players is port
      and type(port) is playerstable.TablePlayers, (tables(tab), type(tab._players).__name__))
check("...with the record moved in as it was, under the first character's id, its place beside it, and the old row gone",
      held(tab) == [(FIRST, json.loads(text)["location"], text)] and tab._kv_text("player") is None and tab.player_text() == text
      and tab.player_exists(), (held(tab)[0][:2] if held(tab) else None, tab._kv_text("player") is None))
again = playerstable.adopt(tab)
check("...and adopting it again changes nothing", again is port and tab._players is port and held(tab) == [(FIRST, json.loads(text)["location"], text)])
tab._put("player", text.replace(json.loads(text)["location"], "amaranth"))
playerstable.adopt(tab)
check("an old row that came back beside the table is not written over the table's record: it is left, and named",
      held(tab) == [(FIRST, json.loads(text)["location"], text)] and tab._kv_text("player") is not None and len(playerstable.problems(tab)) == 1,
      (held(tab)[0][1], playerstable.problems(tab)))
tab._drop("player")
bare = scratch("players_638_bare")
playerstable.adopt(bare)
check("a save with no player is adopted with no row, and has no player", held(bare) == [] and not bare.player_exists() and bare.player_text() is None
      and bare._players.ids() == [])
row.close(); tab.close()

# ---- the kept saves: the same player from the table as from the row
hires = 0
for kept in sorted(p.name for p in KEPT.glob("*.db")):
    stem = Path(kept).stem
    a, b = scratch(f"players_638_{stem}_row", kept), scratch(f"players_638_{stem}_tab", kept)
    was = a._kv_text("player")
    playerstable.adopt(b)
    pa, pb = a.load_player(), b.load_player()
    same = [pa.model_dump_json() == pb.model_dump_json() and b.player_text() == was]
    a.save_player(pa); b.save_player(pb)
    same.append(a.player_text() == b.player_text() == was and others(a) == others(b))
    for q in (pa, pb):                                    # the same day lived by both: a move, a coin, and a memory for each hire
        q.location = "kings_pass"
        q.character.coins += 5
        q.character.name = "Élodie of the Pass"
        for i, m in enumerate(q.party):
            rules.remember(m, 50 + i, f"We crossed the pass together, the {i + 1}th day out.", weight=2)
    a.save_player(pa); b.save_player(pb)
    same.append(a.player_text() == b.player_text() != was and others(a) == others(b) and held(b)[0][:2] == (FIRST, "kings_pass")
                and "Élodie" in b.player_text())           # a name is kept as it is written, not as escapes
    back = (a.load_player().model_dump_json(), b.load_player().model_dump_json())
    same.append(back[0] == back[1] and '"kings_pass"' in back[0])
    rows = [r for r in others(b)["npc_memory"] if "crossed the pass" in json.dumps(r)]
    carried = "crossed the pass" in (b.player_text() or "")
    hires += bool(pa.party)
    check(f"{kept}: the player loads the same from the table, saves the same text, and leaves every other table the same "
          f"({len(pa.party)} hires, their new memories {len(rows)} rows)", all(same) and len(rows) == len(pa.party) and not carried, (same, len(rows), carried))
    a.close(); b.close()
check("...two of the kept saves have hires", hires == 2, hires)

# ---- one write with the clock; a failed transaction
row, tab = scratch("players_638_row2", "stub_fight.db"), scratch("players_638_tab2", "stub_fight.db")
playerstable.adopt(tab)


def no_clock():
    raise OSError("the clock could not be written")


def fault_between(store) -> tuple:
    """A save whose clock cannot be written: the player's record and the clock, before and after."""
    before = (store.player_text(), store._kv_text("campaign"))
    q = store.load_player()
    q.character.coins += 99
    store.meta.minutes += 77
    store.save_meta = no_clock
    try:
        store.save_player(q)
        failed = False
    except OSError:
        failed = True
    del store.save_meta
    store.reload_meta()
    return failed, before == (store.player_text(), store._kv_text("campaign"))


check("a fault between the player and the clock leaves neither written, over the table as over the row",
      fault_between(tab) == fault_between(row) == (True, True), (fault_between(tab), fault_between(row)))


def rolled_back(store) -> tuple:
    before = store.player_text()
    try:
        with store.transaction():
            q = store.load_player()
            q.location = "amaranth"
            store.save_player(q)
            inside = store.player_text()
            raise RuntimeError("the operation did not stand")
    except RuntimeError:
        pass
    store.reload_meta()
    return inside != before, store.player_text() == before, store.load_player().location


check("a transaction that saved the player and failed leaves the record as it was, and it loads as it was",
      rolled_back(tab) == rolled_back(row) and rolled_back(tab)[:2] == (True, True), (rolled_back(tab), rolled_back(row)))

# ---- a row for each character
first = tab.player_text()
second = json.loads(first)
second["character"]["id"], second["character"]["name"], second["location"] = "second", "Second Traveller", "parth"
tab._players.put(second, "second")
check("the table holds a row for each character: a second beside the first, each under its id with its place",
      [r[:2] for r in held(tab)] == [(FIRST, json.loads(first)["location"]), ("second", "parth")] and tab._players.ids() == [FIRST, "second"]
      and tab._players.text("second") == json.dumps(second, ensure_ascii=False) and tab._players.exists("second") and not tab._players.exists("third")
      and tab._players.text("third") is None and tab.player_text("second") == tab._players.text("second") and tab.player_text("third") is None, held(tab))
check("...the first is untouched, and is still the player the store loads", tab.player_text() == first and tab.load_player().character.id == FIRST)
second["location"] = "amaranth"
tab._players.put(second, "second")
check("...and a second save of a character is the same row, its place moved", [r[:2] for r in held(tab)] == [(FIRST, json.loads(first)["location"]),
                                                                                                           ("second", "amaranth")], held(tab))
try:
    row._players.put(second, "second")
    refused = False
except ValueError:
    refused = True
check("the row holds one character and refuses a second; it has none by another id", refused and row._players.ids() == [FIRST]
      and row._players.text("second") is None and not row._players.exists("second") and row.player_text() == row._kv_text("player"))

# ---- the campaign's check
tab._db.execute("DELETE FROM players WHERE character_id = 'second'")
check("the campaign's check finds nothing wrong with a player in the table, nor with one in the row", playerstable.problems(tab) == []
      and playerstable.problems(row) == [] and playerstable.problems(plain) == []
      and not [x for x in invariants.validate_campaign(tab) if "players" in str(x)], playerstable.problems(tab))
tab._db.execute("UPDATE players SET place = 'nowhere'")
found = playerstable.problems(tab)
named = [str(x) for x in invariants.validate_campaign(tab) if found and found[0] in str(x)]
check("a place that is not what its record says is named, once, as the players'", len(found) == 1 and "place" in found[0] and "nowhere" in found[0]
      and named == [f"players: {found[0]}"] and named[0].count("players") == 1, (found, named))
tab.save_player(tab.load_player())
check("(a save puts it right)", playerstable.problems(tab) == [], playerstable.problems(tab))
tab._db.execute("INSERT INTO players (character_id, place, json) VALUES ('torn', '', 'not a record')")
tab._put("player", first)
found = playerstable.problems(tab)
check("...and so are a record that cannot be read, and the old row left beside the table", len(found) == 2 and any("torn" in x for x in found)
      and any("row" in x for x in found), found)
tab._db.execute("DELETE FROM players WHERE character_id = 'torn'")
tab._drop("player")
row.close(); tab.close()


# ---- the scene sees the pulse write the player (f466)
def pulse_writes(name: str, table: bool) -> tuple:
    g = simlib.campaign(name, seed=3, location="trading_square")
    MADE.append(name)
    if not table:
        rows_v16.player_to_row(g.store)                   # (f640) a save has the table: the row's side is put back
    ws = g.scene
    ws.enter("trading_square")
    had = ws.player.character.coins

    def wrote_the_player(store, *a, **k):
        q = store.load_player()
        q.character.coins += 7
        store.save_player(q)
        return {}

    real, pulse.catch_up = pulse.catch_up, wrote_the_player
    try:
        ws.run_pulse()
    finally:
        pulse.catch_up = real
    took = ws.player.character.coins - had
    ws.player.character.coins += 3                       # the scene's own copy, not yet saved, and a pulse that writes no player
    pulse.catch_up = lambda *a, **k: {}
    try:
        ws.run_pulse()
    finally:
        pulse.catch_up = real
    kept = ws.player.character.coins - had - took
    g.store.save_player(ws.player)
    before = (g.store.player_text(), ws.player.location, ws.player.character.coins)
    with ws.operation("test", "a step that writes the player and fails") as op:
        ws.player.location = "kings_pass"
        ws.player.character.coins += 100
        g.store.save_player(ws.player)
        wrote = g.store.player_text() != before[0]
        raise LLMError("the model failed")
    back = (wrote, op.state, (g.store.player_text(), ws.player.location, ws.player.character.coins) == before)
    out = (type(g.store._players).__name__, took, kept, back)
    g.session.close()
    return out


simlib.quiet_console()
seen = (pulse_writes("players_638_pulse_row", False), pulse_writes("players_638_pulse_tab", True))
check("when the pulse writes the player through the save, the scene takes the saved one; when it writes none, the scene keeps its own; "
      "over the table as over the row", [s[:3] for s in seen] == [("RowPlayers", 7, 3), ("TablePlayers", 7, 3)], seen)
check("an operation that wrote the player and did not stand is rolled back, and the scene's reload gives the record as it was",
      [s[3] for s in seen] == [(True, "rolled_back", True)] * 2, [s[3] for s in seen])

# ---- the seeded world script, over the row and over the table
with ThreadPoolExecutor(2) as pool:                      # each play in a process of its own (the stand-in model counts what it invents)
    a, b = pool.map(lambda args: world_script.run_apart(*args), (("players_638_play_row", world_script.SEED, ("--players", "row")),
                                                                 ("players_638_play_tab", world_script.SEED, ())))
MADE.extend(("players_638_play_row", "players_638_play_tab"))
check("the script was played over the row, and over the table", (a["players"], b["players"]) == ("RowPlayers", "TablePlayers"), (a.get("players"), b.get("players")))
check("...all of it, in both", all(a["cover"].values()) and a["cover"] == b["cover"] and len(a["steps"]) == len(b["steps"]) > 20, a["cover"])
apart = next((x[0] for x, y in zip(a["steps"], b["steps"]) if x != y), None)
check("the world is the same after every step", a["steps"] == b["steps"], apart)
check("every other table of the save holds the same", all(a["other"][t] == b["other"][t] for t in a["other"] if t not in ("kv", "all", playerstable.TABLE)) and len(a["other"]) >= 7,
      [t for t in a["other"] if a["other"][t] != b["other"][t]])
check("...and so does every other row of the small one", a["rest"] == b["rest"])
check("the player's record at the end is the same text", a["player"] == b["player"] and len(a["player"] or "") > 1000,
      world_script.first_difference(a["player"] or "{}", b["player"] or "{}"))
check("the same lines were shown", a["shown"] == b["shown"] and len(a["shown"]) > 5, (len(a["shown"]), len(b["shown"])))
check("the same operations stood, with the same outcomes, and the model was asked the same", a["ops"] == b["ops"] and len(a["ops"]) > 3
      and a["calls"] == b["calls"], (len(a["ops"]), len(b["ops"])))
check("the store was written at every step in both", a["wrote"] == b["wrote"] and all(a["wrote"]) and len(a["wrote"]) == len(a["steps"]))

plain.close(); bare.close()
for name in MADE:
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    Path(f"saves/{name}.world_script.json").unlink(missing_ok=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

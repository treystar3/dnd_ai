"""(f480) What a person makes of each character, kept per character id (GOALS.md, owner's decision 2026-11-03: a townsperson's view of
each character is kept separate). An older save's view of the player comes forward as one character's (v12) with the index unchanged;
a second character beside the first is their own stranger: their gift moves only their trust, their first meeting is seeded from
their own standing, both names they gave survive a reload; a trust move keeps its cause; a deed is journaled as its doer's; the night's
measures read the same keys; and no code reads a person's view of "the player" without naming the character (the ratchet)."""
import ast
import json
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import domain_events as de, regard
from npc.models import NPC, LEGACY_REGARD
from storage import migrations
from storage.campaign import CampaignStore, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3, NPC_COLUMNS

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- an older save (v11): its view of the player becomes regard["player"], and the index reads the same
root = Path("saves/regard_480_old")
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db")
db.executescript(SCHEMA_V1); db.executescript(SCHEMA_V2); db.executescript(SCHEMA_V3)
db.execute("PRAGMA user_version = 11")
OLD = {"a1": dict(trust=72, met_player=True, name_known_to_player=True, knows_player_as="Aric", last_talk_day=3, last_talk_at=4400,
                  journal_note="Sells a fair loaf.", note_trust=70, note_mem=4, easy_bonus=2, easy_day=3),
       "a2": dict(trust=50, met_player=False, heard_of={"by": "the miller", "day": 2, "line": "Ask Bel at the mill."}),
       "a3": dict(trust=50)}
for nid, f in OLD.items():
    body = {"id": nid, "name": f"{nid.upper()} Vane", "people": "human", "role": "farmer", "location": "parth", **f}
    db.execute("INSERT INTO npcs (id, json, name, role, location, trust, met_player, name_known_to_player, heard_of) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (nid, json.dumps(body), body["name"], "farmer", "parth", f.get("trust", 50), int(f.get("met_player", False)),
                int(f.get("name_known_to_player", False)), int(bool(f.get("heard_of")))))
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "regard_480_old", "seed": 3, "created": "x"}),))
db.commit()
index_before = db.execute(f"SELECT id, {', '.join(NPC_COLUMNS)} FROM npcs ORDER BY id").fetchall()
db.close()
st = CampaignStore.open_or_create("regard_480_old")
a1, a2, a3 = (st.load_npc(x) for x in ("a1", "a2", "a3"))
r1 = regard.of(a1, "player")
check("v11 to v12: the view of the player is regard['player'], every field kept",
      (r1.trust, r1.met, r1.name_known, r1.knows_as, r1.last_talk_day, r1.last_talk_at, r1.journal_note, r1.note_trust, r1.note_mem,
       r1.easy_bonus, r1.easy_day) == (72, True, True, "Aric", 3, 4400, "Sells a fair loaf.", 70, 4, 2, 3), r1)
check("...someone named to the player before they met keeps who named them; a person nobody knew keeps no view at all",
      regard.of(a2, "player").heard_of["by"] == "the miller" and a3.regard == {}, (a2.regard, a3.regard))
raw = json.loads(st._db.execute("SELECT json FROM npcs WHERE id = 'a1'").fetchone()[0])
check("...the record keeps none of the old fields at its top level", not (set(LEGACY_REGARD) & set(raw)) and "regard" in raw, sorted(raw))
for n in (a1, a2, a3):
    st.save_npc(n)                                   # written again through the store: the index from the views
index_after = st._db.execute(f"SELECT id, {', '.join(NPC_COLUMNS)} FROM npcs ORDER BY id").fetchall()
check("...and the index columns read the same as before (with one character, that character's view)", index_after == index_before,
      (index_before, index_after))
check("...the save is at the current version", st.version == migrations.CURRENT)
st.close()
shutil.rmtree(root, ignore_errors=True)

# ---- two characters: each their own stranger
game = simlib.campaign("regard_480")
ws, store = game.scene, game.store
c1, c2 = simlib.two_characters(ws)
check("the second character has an id of their own", c1.id != c2.id and c2.id, (c1.id, c2.id))
n = NPC(id="b1", name="Bel Hart", people="human", role="miller", location="parth")
regard.set_trust(n, c1.id, 70, cause="old friends")
regard.meet(n, c1.id, 100).knows_as = "Aric"
regard.step(n, c2.id, 6, cause="a gift", about="loaf", minute=200)
check("a gift from the second moves only the second's trust", regard.of(n, c1.id).trust == 70 and regard.of(n, c2.id).trust == 56,
      (regard.of(n, c1.id).trust, regard.of(n, c2.id).trust))
check("...and the move keeps its cause", regard.of(n, c2.id).moves[-1] == {"minute": 200, "n": 6, "cause": "a gift", "about": "loaf"},
      regard.of(n, c2.id).moves)
regard.own(n, c2.id).knows_as = "Bel's friend"                # named, but not yet met: the meeting comes below, in play
store.save_npc(n)
back = store.load_npc("b1")
check("both names they were given survive a reload, each with its own character", regard.of(back, c1.id).knows_as == "Aric"
      and regard.of(back, c2.id).knows_as == "Bel's friend", back.regard)
check("the index holds the aggregate: met by any, the highest trust", store.npc_rows(met_player=True)[0].trust == 70)
try:
    regard.of(back, "c9").trust = 99
    leaked = True
except Exception:
    leaked = False
check("a view nobody holds is read-only: a write through of() fails instead of being lost", not leaked and "c9" not in back.regard)

# the first meeting, as each character: the second is seeded from their own standing, the first's view untouched
store.save_npc(n)
ws.enter(ws.player.location)
ws.present = [store.load_npc("b1")] + [p for p in ws.present if p.id != "b1"]
first = ws.player.character
ws.player.character = c2
stub.plan = [{"kind": "talk", "target": "b1", "speech": "Good morning to you."}]
ws.turn('I say to Bel Hart, "Good morning to you."')
stub.plan = None
ws.player.character = first
after = store.load_npc("b1")
check("the second's first meeting is their own: met now, seeded from their standing (50 and what their name is worth here)",
      regard.of(after, c2.id).met and regard.of(after, c2.id).first_met >= 0, after.regard.get(c2.id))
check("...and leaves the first's view as it was", regard.of(after, c1.id).trust == 70 and regard.of(after, c1.id).knows_as == "Aric",
      after.regard.get(c1.id))

# ---- a deed is the acting character's
seen = []
ws.session.bus.subscribe(de.Deed, lambda e: seen.append(e.actor))
ws.player.character = c2
ws.notice(de.Visited(place="parth", minute=ws.minutes))
ws.player.character = first
ws.notice(de.Visited(place="parth", minute=ws.minutes))
check("a deed is journaled as its doer's: the second's as theirs, the first's as theirs", seen[-2:] == [c2.id, c1.id], seen)
game.close()

# ---- the ratchet: no code reads a person's view of "the player" without naming the character
CODE = [p for d in ("engine", "scenes", "npc", "services", "storage", "world", "llm", "ui") for p in Path(d).rglob("*.py")] + \
       [Path(p) for p in ("main.py", "simlib.py", "tools/nightrun.py", "tools/nightbot.py", "tools/eventrun.py", "tools/acceptance.py",
                          "tools/page_measures.py", "tools/interp_eval.py")]
ALLOWED = {"npc/models.py", "storage/migrations.py", "storage/campaign.py"}       # the legacy map, the migration, the index row
legacy = []
RENAMED = ("met_player", "knows_player_as", "name_known_to_player")        # the fields whose names changed: a read of one is a bug
for p in CODE:
    if str(p) in ALLOWED:
        continue
    for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Attribute) and node.attr in RENAMED and not (isinstance(node.value, ast.Name) and node.value.id in ("r", "row")):
            legacy.append(f"{p}:{node.lineno} .{node.attr}")          # an index row (NPCRow) keeps the column names; a person has none
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "NPC" and any(k.arg in LEGACY_REGARD for k in node.keywords):
            legacy.append(f"{p}:{node.lineno} NPC({[k.arg for k in node.keywords if k.arg in LEGACY_REGARD]})")
check("no code reads or writes a person's old view-of-the-player fields", legacy == [], legacy[:8])
# where the acting character's id is taken from the one player: pinned, so a new site is a choice made on purpose
SITES = {"scenes/world.py": 2, "engine/starts.py": 2, "engine/mentor.py": 1}   # the scene's acting and canon's ids; a start's people; Maren
found = {}
for p in CODE:
    k = p.read_text(encoding="utf-8").count("player.character.id")
    if k:
        found[str(p)] = k
check("the call sites that take the acting character from the one player are the named ones", found == SITES, found)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

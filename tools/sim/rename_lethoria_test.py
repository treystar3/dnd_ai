"""The capital is Lethoria (it was Valecourt): nothing in the game's own text still names it the old way, and an old save is carried
over - not only what the model wrote but the ids the save is built on: where the player stands, the capital's places and their
people, a home there, the standing kept per town, the knowledge group of its people, the journal's actors and targets."""
import json, random, re, shutil, subprocess, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import migrations
from storage.campaign import CampaignStore, PlayerState
from npc.models import NPC
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

OLD = "Valecourt"
# ---- 1. the game's own text
files = [f for f in subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
         if not f.startswith(("saves/", "logs/", "sim_out/")) and not f.endswith((".jpg", ".png", ".ico", ".woff2"))
         and f not in ("storage/migrations.py", "tools/sim/rename_lethoria_test.py")]      # the two that must name it: the step that renames, and this
left = []
for f in files:
    try:
        text = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        continue
    if OLD.lower() in text.lower():
        left.append(f)
check("no file of the game still names the capital the old way", not left, left)
world = load_world()
cap = world.places.get("lethoria")
check("the capital is Lethoria, and it is still the royal capital", cap and cap.name == "Lethoria" and cap.scale == "capital", cap)
check("its places came with it", all(p in world.places for p in ("lethoria_guild", "lethoria_palace", "lethoria_inn", "lethoria_temple")))

# ---- 2. an old save, written under the old name, is carried over when it is opened
o, oo = OLD, OLD.lower()
shutil.rmtree("saves/rename_lethoria_test", ignore_errors=True)
store = CampaignStore.open_or_create("rename_lethoria_test")
char, _ = simlib.make_character("warrior", random.Random(1))
char.class_summary = f"Sworn at {o}; the {o.upper()} oath."
pl = PlayerState(character=char, location=f"{oo}_guild")
pl.standing = {oo: {"nobility": [12, 3]}, "parth": {"guild": [3, 1]}}
pl.homes = {oo: {"day": 3, "upgrades": ["garden"]}}                     # a house bought in the capital
store.save_player(pl)
n = NPC(id="n1", name="Ser Aldo", people="human", role="royal_guard", location=f"{oo}_palace", knowledge_groups=[f"{oo}_locals", "guards"],
        mood=f"proud of {o}", motive=f"to rise at the court of {o}")
store.save_npc(n)
store.execute("INSERT INTO places (id, json) VALUES (?, ?)", (oo, json.dumps({"id": oo, "name": o, "populated": False})))
store.execute("INSERT INTO places (id, json) VALUES (?, ?)", (f"home_{oo}", json.dumps({"id": f"home_{oo}", "name": f"your house in {o}"})))
store.execute("INSERT INTO npc_memory (npc_id, day, text) VALUES (?, ?, ?)", ("n1", 1, f"The stranger came up the road to {o}'s gates."))
store.execute("INSERT INTO event_log (minute, kind, actor, target, text, data, action) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (5, "arrived", "player", oo, f"Arrived in {o}.", json.dumps({"place": f"{oo}_guild"}), f"I go to {o}"))
store.set_version(4)                     # as a save written before the rename was
store.close()

store = CampaignStore.open_or_create("rename_lethoria_test")
db = store._db
check("the old save is brought to the current version", store.version == migrations.CURRENT >= 5, store.version)
p2 = store.load_player()
check("the player stands in the capital's guild hall, under its new id", p2.location == "lethoria_guild", p2.location)
check("standing kept for the capital moved with it", "lethoria" in p2.standing and oo not in p2.standing and p2.standing["lethoria"] == {"nobility": [12, 3]}, p2.standing)
check("the player's own record says Lethoria, capitals and all", p2.character.class_summary == "Sworn at Lethoria; the LETHORIA oath.", p2.character.class_summary)
check("a house in the capital is still theirs", p2.homes == {"lethoria": {"day": 3, "upgrades": ["garden"]}}, p2.homes)
check("...and its place record is found under the house's new id", json.loads(db.execute("SELECT json FROM places WHERE id = 'home_lethoria'").fetchone()[0])["name"]
      == "your house in Lethoria")
hal = store.load_npc("n1")
check("the palace guard lives in the renamed palace and knows what its people know",
      hal.location == "lethoria_palace" and hal.knowledge_groups == ["lethoria_locals", "guards"], (hal.location, hal.knowledge_groups))
check("...and their mood and motive say Lethoria", hal.mood == "proud of Lethoria" and hal.motive == "to rise at the court of Lethoria", (hal.mood, hal.motive))
check("the index column people are found by moved too", db.execute("SELECT location FROM npcs WHERE id = 'n1'").fetchone()[0] == "lethoria_palace")
check("the capital's place record is found under its new id", db.execute("SELECT id FROM places WHERE id = 'lethoria'").fetchone() is not None
      and json.loads(db.execute("SELECT json FROM places WHERE id = 'lethoria'").fetchone()[0])["name"] == "Lethoria")
mem = db.execute("SELECT text FROM npc_memory WHERE npc_id = 'n1'").fetchone()[0]
check("what they remember says Lethoria", mem == "The stranger came up the road to Lethoria's gates.", mem)
ev = db.execute("SELECT target, text, data, action FROM event_log WHERE kind = 'arrived'").fetchone()
check("the journal's target, text, data and the player's line say Lethoria",
      ev == ("lethoria", "Arrived in Lethoria.", json.dumps({"place": "lethoria_guild"}), "I go to Lethoria"), ev)
leftover = [t for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            if db.execute(f"SELECT count(*) FROM {t} WHERE " + " OR ".join(f"{c} LIKE '%{oo}%'" for c in
               [r[1] for r in db.execute(f"PRAGMA table_info({t})") if (r[2] or '').upper() == 'TEXT'] or ["''"])).fetchone()[0]]
check("nothing anywhere in the save still names the old capital", not leftover, leftover)
check("a backup of the save as it was is kept", any((store.root / "backups").glob("campaign_v4_*.db")))
store.close()
shutil.rmtree("saves/rename_lethoria_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

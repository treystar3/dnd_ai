"""The world is Meravia (Rivia was a placeholder): nothing in the game's own text still says Rivia, and an old save is carried over -
what the model wrote under the old name (memories, moods, the journal, narration, news) says Meravia, and 'trivial' is untouched."""
import random, re, shutil, sqlite3, subprocess, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import migrations
from storage.campaign import CampaignStore, PlayerState
from npc.models import NPC
from llm import prompts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- 1. the game's own text
files = [f for f in subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
         if not f.startswith(("saves/", "logs/", "sim_out/")) and not f.endswith((".jpg", ".png", ".ico")) and "rename_meravia_test" not in f
         and f != "storage/migrations.py"]
left = []
for f in files:
    try:
        text = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        continue
    if re.search(r"\bRivia\b|\bRIVIA\b", text):
        left.append(f)
check("no file of the game still names the world Rivia", not left, left)
check("every speaker is told the world is Meravia", "THE WORLD (Meravia)" in prompts.WORLD_RULES)

# ---- 2. an old save, written under the old name, is carried over when it is opened
shutil.rmtree("saves/rename_meravia_test", ignore_errors=True)
store = CampaignStore.open_or_create("rename_meravia_test")
char, _ = simlib.make_character("warrior", random.Random(1))
char.class_summary = "A wanderer of Rivia, and the trivial worries of RIVIA's roads."
store.save_player(PlayerState(character=char, location="parth"))
n = NPC(id="n1", name="Hal", people="human", role="baker", location="parth", mood="homesick for old Rivia", motive="to see all of Rivia")
store.save_npc(n)
store.execute("INSERT INTO npc_memory (npc_id, day, text) VALUES (?, ?, ?)", ("n1", 1, "The stranger said Rivia was wide, a trivial thing."))
store.execute("INSERT INTO event_log (minute, kind, text, action) VALUES (?, ?, ?, ?)", (5, "said", "A tale of Rivia.", "I talk about Rivia"))
store.set_version(3)                     # as a save written before the rename was
store.close()
store = CampaignStore.open_or_create("rename_meravia_test")
check("the old save is brought to the current version", store.version == migrations.CURRENT, store.version)
pl = store.load_player().character.class_summary
check("the player's own record says Meravia, and 'trivial' stays trivial", pl == "A wanderer of Meravia, and the trivial worries of MERAVIA's roads.", pl)
hal = store.load_npc("n1")
check("a person's mood and motive say Meravia", hal.mood == "homesick for old Meravia" and hal.motive == "to see all of Meravia", (hal.mood, hal.motive))
db = store._db
mem = db.execute("SELECT text FROM npc_memory WHERE npc_id = 'n1'").fetchone()[0]
check("what they remember says Meravia", mem == "The stranger said Meravia was wide, a trivial thing.", mem)
ev = db.execute("SELECT text, action FROM event_log WHERE kind = 'said'").fetchone()
check("the journal says Meravia", ev == ("A tale of Meravia.", "I talk about Meravia"), ev)
row = db.execute("SELECT motive FROM npcs WHERE id = 'n1'").fetchone()[0]
check("...and so does the index column the record is found by", row == "to see all of Meravia", row)
check("a backup of the save as it was is kept", any((store.root / "backups").glob("campaign_v3_*.db")))
store.close()
shutil.rmtree("saves/rename_meravia_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)

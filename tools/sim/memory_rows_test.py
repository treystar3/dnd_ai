"""What people remember lives in rows (npc_memory), the record carrying only a window: every defining memory, then the newest. A v1 save
is migrated into rows with nothing lost; the journal records authoritative facts in order and answers 'why does this person hate me?'."""
import json, random, shutil, sqlite3, sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from storage import migrations
from storage.campaign import CampaignStore, PlayerState, MEMORY_WINDOW, SCHEMA_V1
from npc.models import NPC, Memory
from engine import canon
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

root = Path("saves/memrows"); shutil.rmtree(root, ignore_errors=True)
st = CampaignStore.open_or_create("memrows")
n = NPC(id="n1", name="Alric Vane", people="human", role="merchant", location="parth")
for d in range(1, 41):
    n.memories.append(Memory(day=d, turn=d, text=f"The stranger bought bread on day {d}."))
n.memories.insert(3, Memory(day=4, turn=4, text="The stranger stole my purse.", importance=3))
st.save_npc(n)
check("saving a person makes a row of every new memory, and marks them saved", st.memory_count("n1") == 41 and all(m.id is not None for m in n.memories))
raw = json.loads(st._db.execute("SELECT json FROM npcs WHERE id='n1'").fetchone()[0])
check("...the record itself carries no memories (bounded), the table does", "memories" not in raw)
got = st.load_npc("n1")
check("loading gives a window: at most MEMORY_WINDOW, oldest first", len(got.memories) == MEMORY_WINDOW and [m.day for m in got.memories] == sorted(m.day for m in got.memories), len(got.memories))
check("...the defining memory (the theft, day 4) survives in the window though 36 routine ones came after it", any("stole my purse" in m.text for m in got.memories))
check("...and the window ends with the newest routine ones", got.memories[-1].text.endswith("day 40."))
check("...the total is known without loading them all", got.memory_total == 41)
got.memories.append(Memory(day=41, turn=41, text="The stranger came back and paid for the bread."))
st.save_npc(got)
check("saving again adds only the new one; the old rows are untouched", st.memory_count("n1") == 42)
st.forget_memory(got.memories[-1].id)
check("a forgotten memory leaves the window but stays as history", st.memory_count("n1") == 41 and not any("came back" in m.text for m in st.load_npc("n1").memories)
      and st._db.execute("SELECT COUNT(*) FROM npc_memory WHERE npc_id='n1'").fetchone()[0] == 42)
st.close(); shutil.rmtree(root)

# ---- a v1 database (memories inside the record) comes forward with nothing lost, and a backup taken
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db"); db.executescript(SCHEMA_V1); db.execute("PRAGMA user_version = 1")
old = NPC(id="n2", name="Old Save", people="human", role="farmer", location="parth", memories=[Memory(day=1, turn=1, text="An old memory."), Memory(day=2, turn=2, text="Another.")])
db.execute("INSERT INTO npcs (id, json, name, role, location) VALUES (?, ?, ?, ?, ?)", ("n2", old.model_dump_json(), "Old Save", "farmer", "parth"))
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "memrows", "seed": 3, "created": "x"}),))
db.commit(); db.close()
st = CampaignStore.open_or_create("memrows")
check("a v1 save is migrated: its memories are rows now, in order", st.version == migrations.CURRENT and [m.text for m in st.load_npc("n2").memories] == ["An old memory.", "Another."])
check("...and a backup of the v1 database was taken first", list((root / "backups").glob("campaign_v1_*.db")) != [])

# ---- the journal
st.journal(100, "trust", "player", "n2", "Old Save's trust moved -5 to 45", {"step": -5})
st.journal(200, "deed_reaction", "player", "h1", "Bram minded running from a fight", {"deed": "flee"})
st.journal(300, "trust", "player", "n2", "Old Save's trust moved -8 to 37", {"step": -8})
tail = st.journal_tail(10, actor="n2")
check("the journal answers for one person, oldest first", [r["text"][-2:] for r in tail] == ["45", "37"] and all(r["target"] == "n2" for r in tail), tail)
check("...and for a kind", len(st.journal_tail(10, kind="deed_reaction")) == 1)
# through the engine's hook, as the game writes it
canon.JOURNAL = lambda kind, actor, target, text, data: st.journal(400, kind, actor, target, text, data, "I run")
from engine import quirks
m = {"id": "h1", "name": "Bram Voss", "bond": 20, "memories": [], "quirks": {"likes": "harvest", "dislikes": "flee", "reacted": {}, "deeds_seen": {}}}
quirks.roll(m, random.Random(1)); m["quirks"].update(likes="harvest", dislikes="flee", reacted={})
quirks.react(m, "flee", "disapprove", 3)
last = st.journal_tail(1)[-1]
check("a deed reaction is journaled with what the player typed as the action", last["kind"] == "deed_reaction" and last["data"]["deed"] == "flee" and last["action"] == "I run", last)
canon.JOURNAL = None
st.export_json(root / "export")
check("an export carries every memory and the journal", json.loads((root / "export" / "event_log.json").read_text()) != [] and (root / "export" / "npcs" / "n2.json").exists())
st.close(); shutil.rmtree(root, ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

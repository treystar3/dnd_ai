"""(f478) What people remember, typed. Every memory row says what it is, whom it is about, who it came from and what it is about; each
kind is held to its cap (data/rules/memory.yaml) with defining rows going last; the same thing again counts up on its row; a deed's line
keeps a slot for the one who did it, read as "the stranger"; an older save's rows are typed on the way in (v10) the least-work way; and
the clue holders of a matter are written in one order whatever the process's hash seed."""
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
from engine import memory
from npc.models import NPC, Memory
from storage import migrations
from storage.campaign import CampaignStore, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("memory_rows_478")
store = game.session.store
n = NPC(id="m478", name="Hob Marl", people="human", role="farmer", location="parth", traits=[], trust=50)
store.save_npc(n)

# ---- a thousand memories: every kind within its cap, the defining ones last to go
for i in range(1000):
    n = store.load_npc("m478")
    kind = ("experienced", "witnessed", "noticed", "heard", "own_life")[i % 5]
    memory.keep(n, f"Thing {i} happened.", day=1 + i // 10, turn=i, kind=kind, subject="" if kind in ("noticed", "own_life", "heard") else "player",
                importance=3 if i % 50 == 0 else 1, minute=i)
    store.save_npc(n)
counts = {k: len(simlib.remembered(store, "m478", kind=k)) for k in ("experienced", "witnessed", "noticed", "heard", "own_life")}
check("a thousand memories leave each kind at its cap", all(counts[k] == memory.cap("m478", k) for k in counts), counts)
exp = simlib.remembered(store, "m478", kind="experienced")
check("...the defining ones kept first within it, the newest of the rest after", sum(r["importance"] == 3 for r in exp) == 20
      and max(r["turn"] for r in exp) == 995, (sum(r["importance"] == 3 for r in exp), max(r["turn"] for r in exp)))
check("...and the window still carries every defining memory first", sum(m.importance == 3 for m in store.load_npc("m478").memories) >= 20)

# ---- the same thing again counts up; a deed's slot; an unknown kind refused
simlib.reset_person(store, "m478")
n = store.load_npc("m478")
for _ in range(3):
    memory.keep(n, "Sold {them} a sack of seed.", day=2, turn=5, kind="experienced", about="deed:sold:seed", minute=3000)
store.save_npc(n)
rows = simlib.remembered(store, "m478", about="seed")
check("the same deed three times is one row, counted three times", len(rows) == 1, rows)
with store._lock:
    times = store._db.execute("SELECT times, source FROM npc_memory WHERE npc_id = 'm478'").fetchall()
check("...its count and its source (seen first hand)", times == [(3, "self")], times)
check("a deed's line keeps a slot for the one who did it, read as the stranger", store.load_npc("m478").memories[-1].text == "Sold the stranger a sack of seed."
      and memory.render("{them} laid hands on me.") == "The stranger laid hands on me.", store.load_npc("m478").memories[-1].text)
try:
    memory.keep(n, "x", day=1, turn=1, kind="gossip")
    refused = False
except ValueError:
    refused = True
check("a kind of memory nobody knows is refused", refused)
check("the caps are checked at startup", memory.problems() == [] and any("no such kind" in p for p in (memory._CAPS.__setitem__("townsfolk", {"gossip": 3}) or memory.problems())),
      memory.problems())
memory._CAPS = None
game.close()

# ---- an older save comes forward typed (v10), the least-work way
root = Path("saves/memory_rows_478_old")
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db")
db.executescript(SCHEMA_V1); db.executescript(SCHEMA_V2); db.executescript(SCHEMA_V3)
db.execute("PRAGMA user_version = 9")
old = NPC(id="o1", name="Old Hand", people="human", role="smith", location="parth")
db.execute("INSERT INTO npcs (id, json, name, role, location) VALUES (?, ?, ?, ?, ?)", ("o1", old.model_dump_json(exclude={"memories"}), "Old Hand", "smith", "parth"))
for day, turn, text in ((1, 3, "Sold the stranger a hammer."), (2, -1, "(my own life) Married in the spring."),
                        (3, -1, "I dealt with the bridge quarrel myself, in the end."), (4, -1, "The fire took half the street.")):
    db.execute("INSERT INTO npc_memory (npc_id, day, turn, text) VALUES (?, ?, ?, ?)", ("o1", day, turn, text))   # defaults, as an old save has them
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "memory_rows_478_old", "seed": 3, "created": "x"}),))
db.commit(); db.close()
st = CampaignStore.open_or_create("memory_rows_478_old")
got = {r["text"]: (r["kind"], r["subject"]) for r in simlib.remembered(st, "o1")}
check("v9 to v10: a dealing with the player is experienced, about the player", got.get("Sold the stranger a hammer.") == ("experienced", "player"), got)
check("...their own life loses its prefix and is own_life, about no one", got.get("Married in the spring.") == ("own_life", ""), got)
check("...an anchor's settling is their own life, and a disaster lived through is experienced, about no one",
      got.get("I dealt with the bridge quarrel myself, in the end.") == ("own_life", "") and got.get("The fire took half the street.") == ("experienced", ""), got)
check("...and the save is at the current version", st.version == migrations.CURRENT)
st.close()
shutil.rmtree(root, ignore_errors=True)

# ---- a matter's clue holders are written in one order, whatever the hash seed
code = r'''
import sys, json; sys.path.insert(0, "."); sys.path.insert(0, "tools")
import simlib; simlib.install(simlib.Stub("warrior", 2))
from engine import matters
from npc.models import NPC
game = simlib.campaign("memory_rows_478_seed")
store, world = game.session.store, game.session.world
for nid in ("zed", "amy", "kit", "bob"):
    store.save_npc(NPC(id=nid, name=nid.title() + " Vale", people="human", role="farmer", location="parth"))
th = {"title": "The Missing Ewes", "place": "parth", "clues": [{"npc": x} for x in ("zed", "amy", "kit")], "sender": "bob"}
matters.remember(store, world, th, "settled", "Edrin", 5000, 7)
with store._lock:
    print(json.dumps([r[0] for r in store._db.execute("SELECT npc_id FROM npc_memory WHERE kind = 'heard' ORDER BY id").fetchall()]))
game.close()
'''
outs = []
for seed in ("1", "2"):
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"})
    outs.append(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
check("a matter's holders hear of its end in one order under any hash seed", outs[0] == outs[1] == json.dumps(["amy", "bob", "kit", "zed"]), outs)
shutil.rmtree("saves/memory_rows_478_seed", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

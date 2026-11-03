"""(f479) A hire's memories on the same record as a townsperson's: rows under hire:<id>, typed (what they lived with the player is
experienced, a fact the player told them is told), every one kept as a row while the hire's record carries the window of eight the party
always read; the same key updates its row, the same meaning counts up; a dismissed hire's rows stay; an older save's hire memories come
forward (v11) and read the same; and Maren's log of what was said keeps one cap, from data."""
import json
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
from engine import memory, mentor
from engine import party as rules
from storage import migrations
from storage.campaign import CampaignStore, PlayerState, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


def hire(hid: str, name: str) -> dict:
    return {"id": hid, "name": name, "role": "fighter", "level": 3, "memories": []}


game = simlib.campaign("hire_rows_479")
store = game.session.store
p = store.load_player()
p.party = [hire("h1", "Ghak Skurz")]
A = "ash birch cedar dune elm fern gorse heath iris juniper kelp larch moss nettle oak pine quince reed sedge thorn umber vetch willow yarrow zinnia alder bramble clover dock esker".split()
B = "anvil barrel candle drum ember flute gate hammer ink jug kettle lantern mill needle oar pail quill rope saddle tent urn vial wheel yoke zither axe bell cart dagger easel".split()
LINES = [f"{A[i].title()} {B[i]} memory, number{i}." for i in range(30)]       # words of its own each: thirty different memories
for i in range(30):
    rules.remember(p.party[0], 1 + i, LINES[i], weight=1 + (i % 3 == 0))
store.save_player(p)
rows = memory.records(store, "hire:h1")
check("a hire's thirty memories are all rows, the ninth and the thirtieth among them", len(rows) == 30
      and any(LINES[8] == r["text"] for r in rows) and any(LINES[29] == r["text"] for r in rows), len(rows))
check("...typed: what they lived with the player is experienced, about the player, seen first hand",
      all(r["kind"] == "experienced" and r["subject"] == "player" and r["source"] == "self" for r in rows), rows[:1])
raw = json.loads(store._kv_text("player"))
check("the player's record carries none of a hire's memories", all("memories" not in m for m in raw["party"]), list(raw["party"][0]))
back = store.load_player()
check("...and a reload gives the hire the window of eight the party always read", len(back.party[0]["memories"]) == memory.HIRE_WINDOW
      and all("text" in x and "day" in x and "weight" in x for x in back.party[0]["memories"]), back.party[0]["memories"][:1])

m = back.party[0]
rules.remember(m, 40, "The player told me their sister lives in the capital.", weight=2, key="sister", kind="fact")
store.save_player(back)
rules.remember(m, 41, "The player told me their sister lives by the sea now.", weight=2, key="sister", kind="fact")
store.save_player(back)
told = [r for r in memory.records(store, "hire:h1") if r["kind"] == "told"]
check("a fact the player told them is told, by the player, and the same key updates its row in place",
      len(told) == 1 and told[0]["source"] == "player" and "by the sea" in told[0]["text"] and told[0]["about"] == "sister", told)
again = store.load_player()
rules.remember(again.party[0], 42, LINES[29])
store.save_player(again)
same = [r for r in memory.records(store, "hire:h1") if r["text"] == LINES[29]]
check("...and the same thing again counts up on its row", len(same) == 1 and same[0]["times"] == 2, same)

gone = store.load_player()
gone.party = []
store.save_player(gone)
check("a dismissed hire's rows stay", len(memory.records(store, "hire:h1")) == 31)
game.close()

# ---- an older save (v10) with three hires of eight memories each comes forward and reads the same
root = Path("saves/hire_rows_479_old")
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db")
db.executescript(SCHEMA_V1); db.executescript(SCHEMA_V2); db.executescript(SCHEMA_V3)
db.execute("PRAGMA user_version = 9")
char, _ = simlib.make_character("warrior", __import__("random").Random(3))
old = PlayerState(character=char, location="parth")
for k, name in enumerate(("Ann Ash", "Bo Birch", "Cy Cole")):
    h = hire(f"o{k}", name)
    for i in range(8):
        h["memories"].append({"day": 3 + i, "text": f"{name.split()[0]} remembers the {i}th camp, by the {['ford', 'mill', 'oak'][k]}.",
                              "weight": 1 + (i % 2), "count": 1 + (i == 5), "kind": "fact" if i == 7 else "event", **({"key": f"k{i}"} if i == 3 else {})})
    old.party.append(h)
before = [rules.pick_memories(h, "", day=10) + rules.pick_memories(h, "the 6th camp by the mill", day=10) for h in old.party]
db.execute("INSERT INTO kv (key, json) VALUES ('player', ?)", (old.model_dump_json(),))
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "hire_rows_479_old", "seed": 3, "created": "x"}),))
db.commit(); db.close()
st = CampaignStore.open_or_create("hire_rows_479_old")
now = st.load_player()
after = [rules.pick_memories(h, "", day=10) + rules.pick_memories(h, "the 6th camp by the mill", day=10) for h in now.party]
check("v11: three hires' eight memories each become rows, and read back the same lines", st.version == migrations.CURRENT
      and all(len(memory.records(st, f"hire:o{k}")) == 8 for k in range(3)) and before == after, (before[1], after[1]))
check("...the told one told, the counted one counted, the keyed one keyed", [r["kind"] for r in memory.records(st, "hire:o0")].count("told") == 1
      and any(r["times"] == 2 for r in memory.records(st, "hire:o0")) and any(r["about"] == "k3" for r in memory.records(st, "hire:o0")))
check("...and the player's record no longer carries them", all("memories" not in m for m in json.loads(st._kv_text("player"))["party"]))
st.close()
shutil.rmtree(root, ignore_errors=True)

# ---- Maren's log: one cap, from data
pl = PlayerState(character=char, location="parth")
for i in range(40):
    mentor.remember_chat(pl, f"question {i}", f"answer {i}")
n_chat = len(pl.mentor["chat"])
for i in range(40):
    mentor.remember_said(pl, f"line {i}")
check("Maren keeps one cap on what was said, whichever way it was added", n_chat == len(pl.mentor["chat"]) == memory.caps()["maren"]["chat"],
      (n_chat, len(pl.mentor["chat"])))
check("the hires' caps are checked at startup with the townsfolk's", memory.problems() == [] and memory.cap("hire:x", "experienced") == 60
      and memory.cap("someone", "experienced") == 40)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

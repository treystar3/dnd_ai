"""(f483, part 2 of 2) Where people go and what they know, held fast (Bundle D G2, G5): a habit, once settled, stays when the town gains
an inn and then a square, on a person's record and on the index rows alike; someone whose town had nowhere to go takes the first place
added and keeps it when another comes; a person knows by the circles they were raised among and the place they live now, read from where
they are; a clue held is a knows row of the holder's, from themselves, written wherever they become its holder, said once (told:<who>),
and still theirs after the matter is over and gone from the record, a clue to nothing then; and an older save's open matters come
forward as rows (v14)."""
import ast
import json
import random
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 9)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import circumstance, clock, matters, memory, pulse, retrieval, routines
from npc.models import NPC
from world.loader import Place

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("circumstances_483b", minutes=2000)
ws, store, world = game.scene, game.store, game.world
seed = store.meta.seed

# ---- a habit, once settled, stays when the town gains an inn and then a square: records and index rows alike
for i, (nm, role) in enumerate([("Ada Kell", "farmer"), ("Bram Coyle", "smith"), ("Cass Wyn", "farmer"), ("Dov Pell", "miller"), ("Ena Moss", "baker"),
                                ("Fen Rudd", "farmer"), ("Gil Hart", "hunter"), ("Hal Bree", "farmer"), ("Ivo Lunt", "chandler"), ("Jory Tamm", "farmer"),
                                ("Kit Abel", "shepherd"), ("Lenn Shaw", "farmer")]):
    store.save_npc(NPC(id=f"p{i}", name=nm, people="human", role=role, location="parth"))
rows = retrieval.people_in_town(store, world, "parth")
recs = store.load_npcs([r.id for r in rows])
before = {r.id: routines.routine_for(world, seed, r) for r in rows}
before_rec = {n.id: routines.routine_for(world, seed, n) for n in recs}
held = {k: v for k, v in before.items() if v}
check("the town's people have their habits to begin with (the case is not empty)", len(held) >= 3, len(held))
region = world.places["parth"].region
world.add_place(Place(id="lantern_inn", name="The New Lantern", type="inn", region=region, parent="parth"))
mid = {r.id: routines.routine_for(world, seed, r) for r in rows}
world.add_place(Place(id="new_square", name="Cooper's Square", type="square", region=region, parent="parth"))
after = {r.id: routines.routine_for(world, seed, r) for r in retrieval.people_in_town(store, world, "parth")}
after_rec = {n.id: routines.routine_for(world, seed, n) for n in store.load_npcs([r.id for r in rows])}
check("an added inn and then an added square move no one's habit, on the index rows", before == mid == after,
      [k for k in before if before[k] != after.get(k)])
check("...and on the records", before_rec == after_rec and all(before_rec[k] == before[k] for k in before))
who, r0 = next(iter(held.items()))
minute = next(m for m in range(0, 1440, 30) if clock.period(m) == r0["when"])
check("...and the place they go still finds them there in their hour (visitor_ids)", who in routines.visitor_ids(store, world, seed, r0["place"], minute))

# ---- someone whose town had nowhere to go takes the first place added, and keeps it when another comes
def drawn(i):
    return random.Random(f"{seed}:routine:{i}").random() < routines.chance("farmer")
nid = next(f"cairn{i}" for i in range(200) if drawn(f"cairn{i}"))
store.save_npc(NPC(id=nid, name="Wenn Hollin", people="human", role="farmer", location="cairnholt"))
row = next(r for r in store.npc_rows(location=["cairnholt"]) if r.id == nid)
r_none = routines.routine_for(world, seed, row)
cregion = world.places["cairnholt"].region
world.add_place(Place(id="cairn_inn", name="The Cairn's Ease", type="inn", region=cregion, parent="cairnholt"))
r_first = routines.routine_for(world, seed, row)
world.add_place(Place(id="cairn_square", name="Stone Square", type="square", region=cregion, parent="cairnholt"))
world.add_place(Place(id="cairn_inn2", name="The Second Cup", type="inn", region=cregion, parent="cairnholt"))
r_later = routines.routine_for(world, seed, next(r for r in store.npc_rows(location=["cairnholt"]) if r.id == nid))
r_rec = routines.routine_for(world, seed, store.load_npc(nid))
check("a person with nowhere to go has no habit, then takes the first place added", r_none is None and r_first and r_first["place"] == "cairn_inn",
      (r_none, r_first))
check("...and keeps it when a square and another inn are added, record and row alike", r_later == r_first == r_rec, (r_later, r_rec))
m2 = next(m for m in range(0, 1440, 30) if clock.period(m) == r_first["when"])
check("...and is found there in their hour", nid in routines.visitor_ids(store, world, seed, "cairn_inn", m2))

# ---- what a person knows by: the circles they were raised among, and where they live now
moved = NPC(id="fled1", name="Tamsin Rook", people="human", role="farmer", location="cairnholt", knowledge_groups=["everyone", "parth_locals"])
store.save_npc(moved)
g = circumstance.groups(world, moved)
check("someone raised in Parth who lives in Cairnholt knows by both", {"parth_locals", world.locals_group("cairnholt")} <= g and "everyone" in g, g)
state = store.load_world_state()
pulse.add_news(state, "The Cairnholt well has gone sour.", "cairnholt", 2000, [world.locals_group("cairnholt")])
store.save_world_state(state)
heard = pulse.news_for(store, world, store.load_npc("fled1"), 2010)
check("...and hears the news of where they live now", any("well has gone sour" in h for h in heard), heard)
check("...while what they were raised among stays as it was set", store.load_npc("fled1").knowledge_groups == ["everyone", "parth_locals"])

# ---- a clue held is a knows row of the holder's, from themselves, said once, and theirs past the matter's end
holder = recs[0]
th = {"id": "k1", "title": "The Silent Bell", "place": "parth", "status": "active", "groups": ["everyone"], "sender": "", "opened": 2000,
      "clues": [{"text": "The bell-rope was cut, not frayed.", "holder": holder.id, "npc": "", "found": False}], "times": [2000, 2600]}
state = store.load_world_state(); state.setdefault("threads", []).append(th); state.setdefault("history", [])
matters._bind_holders(store, world, th)
store.save_world_state(state)
kn = [r for r in memory.records(store, holder.id) if r["kind"] == "knows" and r["about"] == "thread:k1:0"]
check("the holder of a clue keeps it as a knows row, in its words, from themselves, held", len(kn) == 1 and kn[0]["text"] == "The bell-rope was cut, not frayed."
      and kn[0]["source"] == "self" and kn[0]["state"] == "held" and kn[0]["minute"] == 2000, kn)
matters._bind_holders(store, world, th)
check("...once, however often the holder is bound", len([r for r in memory.records(store, holder.id) if r["about"] == "thread:k1:0"]) == 1)
check("...and that row is what they are given to know", [f.id for f in matters.clue_facts(store, world, store.load_npc(holder.id))] == ["clue:k1:0"])
found = matters.mark_found(ws, store.load_npc(holder.id), ["clue:k1:0"])
kn = [r for r in memory.records(store, holder.id) if r["about"] == "thread:k1:0"]
check("when they say it, it is found, and their row says to whom", found and kn[0]["state"] == f"told:{ws.acting}"
      and matters.clue_facts(store, world, store.load_npc(holder.id)) == [], kn)

smith = next((n for n in recs[1:] if n.role == "smith"), recs[1])
th2 = {"id": "k2", "title": "The Cold Forge", "place": "parth", "status": "active", "groups": ["everyone"], "sender": "", "opened": 2000,
       "clues": [{"text": "Someone has been taking coal at night.", "holder": smith.role, "npc": "", "found": False}], "times": [2000, 2600]}
state = store.load_world_state(); state["threads"].append(th2); store.save_world_state(state)
matters.bind_for(store, world, store.load_npc(smith.id))
check("a clue written for a role becomes the first of that role's own row when they are met", any(r["about"] == "thread:k2:0" and r["state"] == "held"
      for r in memory.records(store, smith.id)), [r["about"] for r in memory.records(store, smith.id)])
state = store.load_world_state()
t2 = next(x for x in state["threads"] if x["id"] == "k2")
pulse.end_thread(store, state, t2, "resolved", "The Cold Forge - settled.", 2600)
for j in range(pulse.FINISHED_KEPT + 1):                      # thirty-one more matters end after it: it is trimmed from the record
    x = {"id": f"z{j}", "title": f"Matter {j}", "place": "parth", "status": "active", "groups": ["everyone"], "sender": "", "clues": [], "times": [2700, 2700 + j]}
    state["threads"].append(x)
    pulse.end_thread(store, state, x, "resolved", f"Matter {j} - settled.", 2700 + j)
store.save_world_state(state)
gone = all(x["id"] != "k2" for x in store.load_world_state()["threads"])
still = [r for r in memory.records(store, smith.id) if r["about"] == "thread:k2:0"]
check("what they knew of a matter outlives it and its trim from the record", gone and len(still) == 1 and still[0]["text"] == "Someone has been taking coal at night.",
      (gone, still))
check("...a clue to nothing now", all(not f.id.startswith("clue:k2") for f in matters.clue_facts(store, world, store.load_npc(smith.id))))

# ---- the fence: every place a clue's holder is bound writes the holder's row
unheld = []
for f in ("engine/matters.py", "engine/stakes.py"):
    for fn in ast.walk(ast.parse(Path(f).read_text(encoding="utf-8"))):
        if not isinstance(fn, ast.FunctionDef):
            continue
        binds = [n for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Subscript) and getattr(t.slice, "value", None) == "npc"
                                                                                for t in n.targets)]
        calls = {getattr(n.func, "attr", getattr(n.func, "id", "")) for n in ast.walk(fn) if isinstance(n, ast.Call)}
        if binds and "hold" not in calls:
            unheld.append(f"{f}:{fn.name}")
check("every place a clue's holder is bound writes their row (matters, stakes)", unheld == [], unheld)
game.close()
shutil.rmtree("saves/circumstances_483b", ignore_errors=True)

# ---- an older save: the clues held in its open matters come forward as rows (v14)
from storage.campaign import CampaignStore, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3
from storage import migrations
root = Path("saves/circumstances_483b_old")
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db")
db.executescript(SCHEMA_V1); db.executescript(SCHEMA_V2); db.executescript(SCHEMA_V3)
for col, ddl in (("subject", "TEXT NOT NULL DEFAULT ''"), ("source", "TEXT NOT NULL DEFAULT ''"), ("about", "TEXT NOT NULL DEFAULT ''"),
                 ("minute", "INTEGER NOT NULL DEFAULT -1"), ("times", "INTEGER NOT NULL DEFAULT 1")):
    db.execute(f"ALTER TABLE npc_memory ADD COLUMN {col} {ddl}")
db.execute("PRAGMA user_version = 13")
for i, name in (("v1", "Ada Moor"), ("v2", "Bel Hask")):
    db.execute("INSERT INTO npcs (id, json, name, role, location) VALUES (?, ?, ?, ?, ?)",
               (i, json.dumps({"id": i, "name": name, "people": "human", "role": "farmer", "location": "parth", "regard": {}}), name, "farmer", "parth"))
ws_old = {"threads": [{"id": "o1", "title": "Open", "status": "active", "opened": 1440 * 3, "clues": [
              {"text": "The ford was moved.", "holder": "", "npc": "v1", "found": False}, {"text": "A cart went by at dusk.", "holder": "", "npc": "v2", "found": True},
              {"text": "Nobody holds this.", "holder": "smith", "npc": "", "found": False}, {"text": "Gone with them.", "holder": "", "npc": "gone9", "found": False}]},
                      {"id": "o2", "title": "Over", "status": "resolved", "clues": [{"text": "Too late.", "holder": "", "npc": "v1", "found": False}]}]}
db.execute("INSERT INTO kv (key, json) VALUES ('world_state', ?)", (json.dumps(ws_old),))
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "circumstances_483b_old", "seed": 3, "created": "x"}),))
db.commit(); db.close()
st = CampaignStore.open_or_create("circumstances_483b_old")
r1 = [r for r in memory.records(st, "v1") if r["kind"] == "knows"]
r2 = [r for r in memory.records(st, "v2") if r["kind"] == "knows"]
check("v13 to v14: a clue held in an open matter is its holder's row, held, dated when the matter opened", [(r["about"], r["state"], r["text"], r["day"]) for r in r1]
      == [("thread:o1:0", "held", "The ford was moved.", clock.day(1440 * 3))], r1)
check("...one already said is told; none for a clue nobody holds, a holder gone from the save, or a matter over", [(r["about"], r["state"]) for r in r2]
      == [("thread:o1:1", "told:player")] and st._db.execute("SELECT COUNT(*) FROM npc_memory WHERE kind = 'knows'").fetchone()[0] == 2
      and st.version == migrations.CURRENT == 15)                       # (f507) v15 lets a saved fight go; a save without one is untouched by it
st.close()
shutil.rmtree(root, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f481, part 1 of 2) Offers and obligations that end for a reason (GOALS.md S2: nothing ends by age; the owner's answers of 2026-11-03 to
Bundle D's questions 1 and 2). Work offered and requests made are offers in the registry, contracts held are obligations; read through
the store after a reload: a contract stands through thirty defining memories and ninety days; a work offer stands past the old six hours
while its holder is at work, and is withdrawn at the end of their day, or when other work is offered in its place, with a reason from
data; a request left without a yes is let go when a new conversation opens, and the next one is recorded; a contract walked away from
is broken, with how; an ended row is kept for the measures and then removed, its memory staying; a move its lifecycle does not allow is
refused; an older save's standing offers come forward (v13); and the night reads what is owed and what closed, with the reason."""
import json
import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import entities, memory, obligations
from llm.contracts import WorkOffer
from npc.models import NPC
from scenes.work_actions import offer_open
from storage import migrations
from storage.campaign import CampaignStore, SCHEMA_V1, SCHEMA_V2, SCHEMA_V3

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("obligations_481", minutes=600)
ws, store = game.scene, game.store
ws.enter(ws.player.location)
here = ws.player.location
n = NPC(id="w1", name="Tam Reed", people="human", role="farmer", location=here)
store.save_npc(n)
hours = ws.world.roles["farmer"].hours

# ---- a contract stands through thirty defining memories and ninety days
c = obligations.open_(store, "contract", "w1", ws.acting, "Clear the north field", ws.minutes, terms={"quest": "q9"}, key="q9")
for i in range(30):
    m = store.load_npc("w1")
    memory.keep(m, f"A hard day, number {i}, with its own words {i * 7}.", day=1 + i, turn=i, kind="experienced", importance=3, minute=600 + i)
    store.save_npc(m)
store.meta.minutes += 90 * 1440
store.save_meta()
game.close()
game = simlib.campaign("obligations_481", fresh=False)
ws, store = game.scene, game.store
held = obligations.find(store, "q9")
check("a contract stands through thirty defining memories and ninety days, still active after a reload",
      held is not None and held.state == "active" and held.data["with"] == ws.acting and held.links == {"npc": "w1"}, held)

# ---- a contract walked away from is broken, with how
obligations.close(store, held, "broken", "abandoned", ws.minutes)
again = store.load_entity(held.ref)
check("...walked away from, it is broken, with how, in data's words", again.state == "broken"
      and again.history[-1][3] in obligations.family("contract")["reasons"]["broken"]["abandoned"] and again.owner == "" and again.data["with"] == ws.acting,
      again.history[-1])
try:
    obligations.close(store, again, "fulfilled", "handed_in", ws.minutes)
    refused = False
except ValueError:
    refused = True
check("a move its lifecycle does not allow is refused (a broken contract is never then fulfilled)", refused)

# ---- a work offer: stands past the old six hours while they work, withdrawn at the end of their day for a reason
day0 = (ws.minutes // 1440) * 1440
start = next(m for m in range(day0, day0 + 1440, 30) if __import__("engine.clock", fromlist=["x"]).in_hours(m, hours))
store.meta.minutes = start; store.save_meta()
tam = store.load_npc("w1")
ws.present = [tam]
ws.record_work_offer(WorkOffer(task="mend the gate", minutes=60, pay=20), tam)
check("an offer of work is an offer in the registry, from them to the character", offer_open(store, tam, ws.acting) is not None
      and obligations.current(store, "work", "w1", ws.acting).data["terms"]["task"] == "mend the gate")
from engine import clock
late = start
while clock.in_hours(late + 30, hours) and late - start < 12 * 60:
    late += 30
store.meta.minutes = late; store.save_meta()
obligations.lapse(ws)
check("...it stands while they are at work, past the six hours an offer used to last", offer_open(store, tam, ws.acting) is not None
      or late - start < 6 * 60, (start, late))
ws.record_work_offer(WorkOffer(task="carry the sacks", minutes=60, pay=20), tam)
firsts = [e for e in store.find_entities(kind="offer") if e.data.get("family") == "work" and e.data["terms"]["task"] == "mend the gate"]
check("a second offer withdraws the first, with that reason", firsts and firsts[0].state == "withdrawn"
      and firsts[0].history[-1][3] in obligations.family("work")["reasons"]["withdrawn"]["other_work"], [e.history for e in firsts])
store.meta.minutes = late + 120; store.save_meta()
while clock.in_hours(store.meta.minutes, hours):
    store.meta.minutes += 30
store.save_meta()
obligations.lapse(ws)
gone = [e for e in store.find_entities(kind="offer") if e.data["terms"].get("task") == "carry the sacks"]
check("...and the second is withdrawn when their working day is over, for that reason, not by any clock of its own",
      gone and gone[0].state == "withdrawn" and gone[0].history[-1][3] in obligations.family("work")["reasons"]["withdrawn"]["day_over"],
      [e.history for e in gone])

# ---- a request left without a yes is let go when a new conversation opens; the next one is recorded
obligations.open_(store, "request", "w1", ws.acting, "Find my lost ewe", ws.minutes, terms={"id": "r1", "title": "Find my lost ewe", "letter": "F"})
check("a request waits on a yes", ws.request_of(store.load_npc("w1")) is not None)
store.meta.minutes += 60; store.save_meta()
ws.present = [store.load_npc("w1")]
ws.convo = []
stub.plan = [{"kind": "talk", "target": "w1", "speech": "Good day."}]
ws.turn('I say to Tam Reed, "Good day."')
stub.plan = None
asked = [e for e in store.find_entities(kind="offer") if e.data.get("family") == "request"]
check("...a new conversation without a yes lets it go, with the reason, and leaves Tam the memory of asking",
      asked and asked[0].state == "released" and asked[0].history[-1][3] in obligations.family("request")["reasons"]["released"]["no_answer"]
      and simlib.remembered(store, "w1", about="lost ewe"), [e.history for e in asked])
obligations.open_(store, "request", "w1", ws.acting, "Mend the well rope", ws.minutes, terms={"id": "r2", "title": "Mend the well rope", "letter": "F"})
check("...and the next request is recorded", (ws.request_of(store.load_npc("w1")) or {}).get("title") == "Mend the well rope")

# ---- the night reads what is owed and what closed, with the reason
owed = obligations.for_state(store, ws.acting, [{"id": "q1", "kind": "hunt", "issuer": "", "title": "Wolves"}])
check("what is owed reads under the ids the measures always read", {o["id"] for o in owed} >= {"q1", "request:w1"}
      and next(o for o in owed if o["id"] == "request:w1")["state"] == "offered", owed)
closed = obligations.closed_since(store, 0)
check("...and what closed, each with its reason", {c["id"] for c in closed} >= {"q9", "work:w1", "request:w1"} and all(c["reason"] for c in closed), closed)

# ---- an ended row is kept for the measures, then removed; its memory stays
store.meta.minutes += (obligations.rules()["keep_days"] + 1) * 1440; store.save_meta()
removed = obligations.trim(store, store.meta.minutes)
check("ended rows past their keeping are removed, the open one kept, and the memory of the ended request stays",
      removed >= 3 and [e.data["title"] for e in obligations.open_ones(store)] == ["Mend the well rope"]
      and simlib.remembered(store, "w1", about="lost ewe"), (removed, [e.data["title"] for e in obligations.open_ones(store)]))
game.close()
shutil.rmtree("saves/obligations_481", ignore_errors=True)

# ---- an older save's standing offers come forward (v13)
root = Path("saves/obligations_481_old")
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)
db = sqlite3.connect(root / "campaign.db")
db.executescript(SCHEMA_V1); db.executescript(SCHEMA_V2); db.executescript(SCHEMA_V3)
db.execute("CREATE TABLE IF NOT EXISTS entities (ref TEXT PRIMARY KEY, kind TEXT, state TEXT, place TEXT, owner TEXT, deadline INTEGER, json TEXT)")
db.execute("PRAGMA user_version = 12")
body = {"id": "o1", "name": "Ola Fenn", "people": "human", "role": "farmer", "location": "parth", "regard": {},
        "work_offer": {"task": "stack the hay", "pay": 12, "minutes": 60, "until": 5}, "quest_offer": {"id": "rq", "title": "Bring back my dog", "letter": "F"}}
db.execute("INSERT INTO npcs (id, json, name, role, location) VALUES (?, ?, ?, ?, ?)", ("o1", json.dumps(body), "Ola Fenn", "farmer", "parth"))
db.execute("INSERT INTO kv (key, json) VALUES ('campaign', ?)", (json.dumps({"name": "obligations_481_old", "seed": 3, "created": "x"}),))
db.commit(); db.close()
st = CampaignStore.open_or_create("obligations_481_old")
w, r = obligations.current(st, "work", "o1", "player"), obligations.current(st, "request", "o1", "player")
check("v12 to v13: a standing work offer and a request are offers, still offered (the old hour gone), terms kept",
      w is not None and w.data["terms"] == {"task": "stack the hay", "pay": 12, "minutes": 60} and r is not None and r.data["terms"]["title"] == "Bring back my dog",
      (w, r))
raw = json.loads(st._db.execute("SELECT json FROM npcs WHERE id = 'o1'").fetchone()[0])
check("...the record carries neither any more, and the save is at the current version", "work_offer" not in raw and "quest_offer" not in raw
      and st.version == migrations.CURRENT)
st.close()
shutil.rmtree(root, ignore_errors=True)
check("the families' reasons and memories name final states, and are checked at startup", obligations.problems() == [] and entities.problems() == [])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

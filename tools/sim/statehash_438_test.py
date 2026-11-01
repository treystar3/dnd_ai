"""(f438) A fingerprint of a campaign's whole state, and of the game it was played on. The rebuild replays recorded sessions through the
real turn and checks the state after every line (tools/rerun.py); that needs one canonical reading of a save, the same however its rows
came to be written, a way to name where two saves part, and a hash of the rules and content a recording was made with."""
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 38))
from npc.models import NPC
from storage import statehash
from storage.campaign import CampaignStore

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

PEOPLE = [NPC(id=f"h{i}", name=f"Person {i}", people="human", role="farmer", location="parth", tier="known") for i in range(6)]

def save(name, order):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    store = CampaignStore.open_or_create(name)
    store.meta.seed = 38; store.meta.minutes = 600; store.save_meta()
    with store.transaction():
        for n in order:
            store.save_npc(n)
        store.save_dungeons([{"id": "d1", "place": "greywood", "entrance": "greywood_cave", "made": 0, "cleared": [0, 0]}])
    return store

a = save("statehash_438_a", PEOPLE)
b = save("statehash_438_b", list(reversed(PEOPLE)))
da, db = statehash.digest(a), statehash.digest(b)
check("the same state gives the same hash, whatever order its rows were written in, and whatever the save is called", da == db,
      {k: (da[k][:8], db[k][:8]) for k in da if da[k] != db[k]})
n = b.load_npc("h3"); n.mood = "furious"; b.save_npc(n)
dc = statehash.digest(b)
check("a changed person changes the people's hash and the whole, and nothing else", {k for k in da if da[k] != dc[k]} == {"npcs", "all"},
      {k for k in da if da[k] != dc[k]})
where = statehash.diff(statehash.dump(a), statehash.dump(b))
check("...and the difference is named: the table, the person and the field", where and where[0].startswith("npcs h3:") and "mood" in where[0], where)
check("a save matches itself", statehash.diff(statehash.dump(a), statehash.dump(a)) == [])
a.close(); b.close()

# ---- the game a recording was made on
tmp = Path(tempfile.mkdtemp(prefix="datahash_"))
shutil.copytree("data", tmp / "data")
before = statehash.data_hash(tmp)
check("the data hash reads the same files the same way", before == statehash.data_hash(tmp) and before == statehash.data_hash())
f = tmp / "data" / "rules" / "weather.yaml"
f.write_text(f.read_text(encoding="utf-8") + "\n# a changed rule\n", encoding="utf-8")
check("...and changes when a rule file changes", statehash.data_hash(tmp) != before)
changed = statehash.data_hash(tmp)
(tmp / "data" / "replay" / "a_new_case.yaml").write_text("x: 1\n", encoding="utf-8")
check("...but not when only the recordings and test cases kept in data/replay change", statehash.data_hash(tmp) == changed)
shutil.rmtree(tmp, ignore_errors=True)

for s in ("statehash_438_a", "statehash_438_b"):
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

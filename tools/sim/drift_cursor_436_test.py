"""(f436) Drift looks at the living a chunk at a time, round robin (engine/drift.py people). Each pass read every id in the save from the
index to take forty of them, so the cost of a pass grew with the campaign. Now a pass reads only its page, along the primary key, after
the last person it looked at; it wraps to the start, never takes anyone twice in a pass, skips the gone, and an old save's cursor (a
position, a number) starts again from the beginning."""
import math, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 36))
from engine import drift, pulse
from npc.models import NPC
from storage.campaign import CampaignStore
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
SIZE = pulse.P["drift"]["people_per_pass"]

def save_with(name, n):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    store = CampaignStore.open_or_create(name)
    with store.transaction():
        for i in range(n):
            store.save_npc(NPC(id=f"p{i:04d}", name=f"Person {i}", people="human", role="farmer", location="parth", tier="known"))
    return store

for n in (60, 600):
    store = save_with(f"drift_cursor_436_{n}", n)
    pages = []
    real_after, real_rows = store.npc_ids_after, store.npc_rows
    store.npc_ids_after = lambda after, limit: pages.append(real_after(after, limit)) or pages[-1]
    store.npc_rows = lambda *a, **k: (_ for _ in ()).throw(AssertionError("drift read the whole index"))
    state, seen, repeats = {}, [], 0
    for _ in range(math.ceil(n / SIZE)):
        pages.clear()
        drift.people(store, world, state, 10 ** 7, random.Random(1))
        chunk = [i for p in pages for i in p]
        repeats += len(chunk) - len(set(chunk))
        check(f"{n} people: a pass reads no more than its page of {SIZE}", len(chunk) <= SIZE, len(chunk))
        seen += chunk
    store.npc_rows = real_rows
    check(f"{n} people: the whole index is never read by a pass", True)
    check(f"{n} people: everyone is looked at within {math.ceil(n / SIZE)} passes", len(set(seen)) == n, n - len(set(seen)))
    check(f"{n} people: no one twice in one pass", repeats == 0, repeats)
    store.npc_ids_after = real_after
    store.close()

# ---- the edges: a wrap, the gone, a small town, an old cursor
store = save_with("drift_cursor_436_edge", 50)
state = {"drift_cursor": "p0045"}
chunk = drift.next_people(store, state, SIZE)
check("a pass near the end wraps to the start", chunk[:4] == ["p0046", "p0047", "p0048", "p0049"] and chunk[4] == "p0000" and len(chunk) == SIZE,
      chunk[:6])
check("...and the cursor is the last one looked at", state["drift_cursor"] == chunk[-1])
npc = store.load_npc("p0047"); npc.gone = "moved away"; store.save_npc(npc)
check("someone gone is passed over", "p0047" not in drift.next_people(store, {"drift_cursor": "p0045"}, SIZE))
small = drift.next_people(store, {"drift_cursor": "p0010"}, 500)
check("fewer people than a pass: each once", len(small) == len(set(small)) == 49, len(small))
old = {"drift_cursor": 17}
check("an old save's numbered cursor starts again from the beginning", drift.next_people(store, old, 3) == ["p0000", "p0001", "p0002"]
      and old["drift_cursor"] == "p0002", old)
check("an empty town gives an empty pass", drift.next_people(save_with("drift_cursor_436_none", 0), {}, SIZE) == [])
store.close()

for s in ("60", "600", "edge", "none"):
    shutil.rmtree(f"saves/drift_cursor_436_{s}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

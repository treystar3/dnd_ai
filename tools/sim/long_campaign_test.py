"""A campaign far bigger than any real one yet - 5,000 people, 1,000 of them met, a memory table in the tens of thousands, a long journal -
and the operations a turn depends on timed against it. The point is not the numbers themselves but catching the day an indexed query
quietly turns back into 'read everyone': each check bounds both the time and how many whole records were parsed."""
import random, shutil, sys, time
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
from storage.campaign import CampaignStore, PlayerState, PlaceState
from storage import invariants
from npc.models import NPC, Memory
from world.loader import load_world
from engine import retrieval, candidates as C, mapview
import npc.models as nm
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

parsed = {"n": 0}
_v = NPC.model_validate_json
NPC.model_validate_json = classmethod(lambda cls, *a, **k: (parsed.__setitem__("n", parsed["n"] + 1), _v(*a, **k))[1])
def timed(label, fn, max_s, max_parsed=None):
    parsed["n"] = 0
    t = time.perf_counter(); out = fn(); dt = time.perf_counter() - t
    ok = dt <= max_s and (max_parsed is None or parsed["n"] <= max_parsed)
    check(f"{label}: {dt * 1000:.0f} ms, {parsed['n']} records parsed (limits {max_s * 1000:.0f} ms, {max_parsed if max_parsed is not None else 'any'})", ok)
    return out

root = Path("saves/longrun"); shutil.rmtree(root, ignore_errors=True)
world = load_world()
places = [p for p in world.places.values() if p.type != "road"]
roles = list(world.roles)
rng = random.Random(5)
t0 = time.perf_counter()
st = CampaignStore.open_or_create("longrun")
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
first = ["Aldric", "Brenna", "Cael", "Dunstan", "Elowen", "Fenric", "Gisela", "Hob", "Ilse", "Jory", "Kestrel", "Lio", "Maud", "Nolan", "Orla", "Piran"]
last = ["Vane", "Ashcombe", "Tallow", "Greaves", "Mire", "Fell", "Quill", "Harrow", "Pell", "Stroud", "Wren", "Coyle"]
with st.transaction():
    residents = {}
    for i in range(5000):
        p = rng.choice(places)
        n = NPC(id=f"x{i}", name=f"{rng.choice(first)} {rng.choice(last)} {i}", people="human", role=rng.choice(roles), location=p.id,
                tier="known" if i % 5 == 0 else "background", met_player=i < 1000, name_known_to_player=i < 600, trust=rng.randint(20, 80),
                motive="wants something" if i % 50 == 0 else "", gone="left" if i % 9 == 0 else "")
        n.memories = [Memory(day=d, turn=d, text=f"The stranger did a thing on day {d}.", importance=3 if d % 10 == 0 else 1) for d in range(1, (30 if i < 200 else 2))]
        st.save_npc(n)
        residents.setdefault(p.id, []).append(n.id)
    for pid, ids in residents.items():
        st.save_place(PlaceState(id=pid, populated=True, residents=ids[:40]))
    for k in range(20000):
        st.journal(k * 10, "trust", "player", f"x{k % 1000}", "trust moved", {"step": 1})
print(f"     fixture built in {time.perf_counter() - t0:.1f}s: 5,000 people, {st._db.execute('select count(*) from npc_memory').fetchone()[0]} memories, 20,000 journal rows")
st.close()

timed("open the campaign", lambda: CampaignStore.open_or_create("longrun"), 0.5, 0)
st = CampaignStore.open_or_create("longrun")
timed("load the player", st.load_player, 0.1, 0)
rows = timed("everyone met who is not here (the interpreter's distant people)", lambda: retrieval.met_elsewhere(st, ["x1", "x2"]), 0.15, 0)
check("...is the right set, from the index alone", len(rows) == 998)
timed("who is named in a line of speech", lambda: retrieval.named_in(st, "Ask Elowen Quill 3 about the ford, and Aldric too."), 0.25, 0)
got = timed("who is in this town (the pulse's place context)", lambda: retrieval.people_in_town(st, world, "parth"), 0.1, 0)
check("...finds only this town's people", got and all(mapview.top_of(world, r.location) == "parth" for r in got), len(got))
timed("one person's whole record, with their memory window", lambda: st.load_npc("x7"), 0.05, 1)
timed("the interpreter's candidate places for a line", lambda: C.places(world, "parth", "walk to the market and find Aldric"), 0.1, 0)
timed("the interpreter's candidate people for a line", lambda: C.people_elsewhere(rows, "find Aldric Vane"), 0.3, 0)
def one_turn():
    with st.transaction():
        p = st.load_player(); p.character.coins += 1; st.save_player(p)
        n = st.load_npc("x3"); n.memories.append(Memory(day=99, turn=99, text="A new memory.")); st.save_npc(n)
        st.journal(5, "trust", "player", "x3", "moved", {})
timed("one ordinary turn's writes, as one transaction", one_turn, 0.1, 1)
timed("the journal for one person out of 20,000 rows", lambda: st.journal_tail(25, actor="x5"), 0.05, 0)
probs = timed("validate the whole campaign", lambda: invariants.validate_campaign(st, world), 3.0, 0)
check("...and it is sound", probs == [], probs[:3])
timed("a backup of the whole database", lambda: st.backup("test"), 3.0, 0)
size = (root / "campaign.db").stat().st_size / 1e6
print(f"     database {size:.1f} MB")
st.close(); shutil.rmtree(root, ignore_errors=True)
NPC.model_validate_json = _v
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

"""Engine-picked names: no repeated first name in a save, same seed gives the same names, every people has a pool, gender is stored."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from npc import names, life
from storage.campaign import CampaignStore
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
P = names.pools()
check("every people has a pool", all(p in P and len(P[p]["male"]) >= 10 and len(P[p]["female"]) >= 10 and P[p]["family"] for p in world.peoples))
check("a pool has no duplicates", all(len(set(v)) == len(v) for p in P.values() for v in p.values()))

def run(name, seed):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    st = CampaignStore.open_or_create(name)
    st.meta.seed = seed; st.save_meta()
    out = []
    for pid in list(world.places)[:40]:
        if world.places[pid].residents and world.peoples_at(pid):
            out += life.populate_place(st, world, pid, load_traits())
    return out
a = run("names_a", 7); b = run("names_b", 7); c = run("names_c", 8)
check("a save fills many places", len(a) > 40, len(a))
firsts = [n.name.split()[0].lower() for n in a]
check("no first name repeats in a save", len(set(firsts)) == len(firsts), [f for f in set(firsts) if firsts.count(f) > 1])
check("no full name repeats", len({n.name for n in a}) == len(a))
check("same seed, same names", [n.name for n in a] == [n.name for n in b])
check("different seed, different names", [n.name for n in a] != [n.name for n in c])
check("gender is stored", all(n.gender in ("male", "female") for n in a))
check("the mentor's first name is not given to anyone", all(f != "maren" for f in firsts))
rng = random.Random(1); taken = []
for _ in range(400):
    nm, g = names.pick("orc", taken, rng); taken.append(nm)
check("a small pool runs dry without repeating a full name", len(set(taken)) == len(taken))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

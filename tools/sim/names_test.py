"""Engine-built names for residents: no repeated first name in a save, same seed gives the same names, every people can be named,
gender is stored. The names themselves are built from each people's sounds (name_sounds_test.py); there is no list of names."""
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
check("every people of the world can be named, first and family", all(len(names.pick(p, [], random.Random(p))[0].split()) == 2 for p in world.peoples))
check("no list of names is left: residents are built from sounds", not (names._DATA / "names.yaml").exists())

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
check("400 orcs in a row: no first name twice, no full name twice", len({names.first_of(n) for n in taken}) == 400 and len(set(taken)) == 400,
      (len({names.first_of(n) for n in taken}), len(set(taken))))
# hires and trial examiners are named the same way: built from their people's sounds, never from a list (data/rules/party.yaml has none)
from engine import party
import yaml
check("the guild keeps no name lists any more", "names" not in yaml.safe_load(open("data/rules/party.yaml", encoding="utf-8")))
for people in ("human", "dwarf", "halfling", "elf", "orc", "dragonborn", "goliath", "genasi", "gnome", "half_elf"):
    hr = random.Random(people)
    built = [party.hire_name(people, hr) for _ in range(30)]
    ok = all(len(n.split()) == 2 and names.acceptable(n.split()[0], names._rules(people, "male")) or names.acceptable(n.split()[0], names._rules(people, "female"))
             for n in built)
    check(f"a {people} hire's name is built from the people's sounds, first and family", ok and len(set(built)) >= 25, built[:5])
check("the same roll gives the same hire name", party.hire_name("dwarf", random.Random(3)) == party.hire_name("dwarf", random.Random(3)))
roster = party.roster(5, "guild_house", 3, 20, 500, [])
check("a hall's roster is named that way too", all(len(m["name"].split()) == 2 for m in roster), [m["name"] for m in roster])
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

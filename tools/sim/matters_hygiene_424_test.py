"""(f424) Matters, hygiene and the tools. A matter the player ended was not marked touched, so the journal never showed it; a kill path
with nothing spawned was met by the same creature killed anywhere; building a hunt contract made and saved a roster for every wild place
it looked at, and asked to 'Hunt 1 wolves'; French 'leur' passed the foreign-word guard; a carriage return joined two words; a resource
found in a part of a place showed no 'Gathered' line; and the stub gave every ability the description 'd'."""
import pathlib, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 14))
from engine import events, guard, hygiene, quests
from llm.contracts import QuestOffer
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- kills count where the matter is
path = {"kind": "kill", "target": "wolf"}
thread = {"made": 0}
state = {"deeds": [{"kind": "kill", "minute": 10, "place": "frostholm_wastes", "creature": "wolf"}]}
check("a wolf killed far away does not end this matter's wolves", not events.path_met(path, state, thread, near={"greywood", "parth"}))
state["deeds"].append({"kind": "kill", "minute": 20, "place": "greywood", "creature": "wolf"})
check("...one killed in its own wild does", events.path_met(path, state, thread, near={"greywood", "parth"}))
check("...and with no place known, any kill counts, as before", events.path_met(path, {"deeds": state["deeds"][:1]}, thread))
src = pathlib.Path("engine/events.py").read_text(encoding="utf-8")
check("a matter the player ends is marked touched, so the journal shows it", 'th["touched"] = True' in src[src.index("def finish("):src.index("def finish(") + 2500])

# ---- a hunt contract builds no rosters it does not need
shutil.rmtree("saves/matters_hygiene_424_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("matters_hygiene_424_test")
store.meta.seed = 14; store.meta.minutes = 600; store.save_meta()
wild = [p.id for p in world.places.values() if p.danger]
before = sum(1 for pid in wild if store.load_place(pid).roster)
q = quests.map_offer(world, store, QuestOffer(kind="hunt", what="wolf", count=1), "x", "Tam", 600)
after = sum(1 for pid in wild if store.load_place(pid).roster)
check("a hunt contract is made", q is not None and q["creature"], q)
check("...building at most the roster of the place it is for", after - before <= 1, (before, after, len(wild)))
check("...and a count of one is said in the singular", q is not None and q["title"].startswith("Hunt 1 ") and not q["title"].split(" in ")[0].endswith("s"),
      q["title"] if q else "")
store.close()
shutil.rmtree("saves/matters_hygiene_424_test", ignore_errors=True)

# ---- hygiene
check("French 'leur' is a foreign word the guard sends back", "leur" in guard.WORDS)
check("a carriage return is a space, not two words run together", hygiene.clean("the\rgate opens") == "the gate opens")
check("...and a Windows line end is a line end", hygiene.clean("one\r\ntwo") == "one\ntwo")

# ---- a part's resource, and the stub's abilities
psrc = pathlib.Path("scenes/part_actions.py").read_text(encoding="utf-8")
check("a resource found in a part of a place shows its 'Gathered' line", 'console.ledger(f"Gathered: {inventory.label(item)}.")' in psrc)
char, _ = simlib.make_character("mage", random.Random(1))
check("the stub's abilities have descriptions a reader can see", all(len(a.description.split()) >= 3 for a in char.actives), [a.description for a in char.actives][:3])
csrc = pathlib.Path("scenes/combat_scene.py").read_text(encoding="utf-8")
check("...and a description of a word or two is not shown as how an ability looks", 'len((a.description or "").split()) >= 3' in csrc)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

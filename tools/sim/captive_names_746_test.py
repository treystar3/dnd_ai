"""(f746) A captive is named for their people, apart from every name in the save, from a source that cannot run dry (found by the
audit, people-3 and aged-save-5: a captive taken in a fight was named from the sixteen names of data/rules/arcs.yaml prisoner.names
less those already in the save, and from the seventeenth captive the list was empty and every captive after took a name an earlier
person had; the name was one pool for every people and both genders, and make_prisoner rolled the captive's gender afterwards). Each
captive's people is decided where the fight makes them (the people their kind names, else the place's), and their name and gender
are built by npc/names.pick for that people, apart from every name in the save and from the captives named before them in the same
fight, on a die of the fight's own for the captive's place in it, so the tip die keeps its own draws. Cases: twenty captives, one a
fight, in one save; two taken in one fight; a save in which every name of the old list is already someone's first name; a captive of
the place's people (a dwarf in Ironvein) and one whose kind names their people (an orc warband chief), each named for their own
people and gender; the same fight named the same; the tip die the same whatever names are free; the list gone from the data.
Run: python tools/sim/captive_names_746_test.py"""
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import combat as C
from engine import data_check, entities, streams
from engine.arcs import A
from npc import names
from npc.models import NPC
from scenes import combat_scene as cs
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


OLD = ["Dorn", "Kell", "Marek", "Sorin", "Vask", "Tobren", "Hale", "Garrick", "Brannoc", "Ferrow", "Jessk", "Orlen", "Ruddick", "Skarn",
       "Teague", "Wynn"]                                   # the list captives were named from before
room = {}


def of_people(people, gender, full):
    """Whether a full name is one the people's sounds build for that gender: a first name of theirs and a family name of theirs."""
    if (people, gender) not in room:
        room[(people, gender)] = (names.possible(people, gender), names.possible(people, "family"))
    first, _, family = full.partition(" ")
    return first in room[(people, gender)][0] and family in room[(people, gender)][1]


def foe(world, i, creature="bandit", level=3):
    """One who yielded, as captives() reads them."""
    return types.SimpleNamespace(category=world.bestiary[creature].category, name=f"{creature.replace('_', ' ')} {i + 1}", level=level,
                                 creature=creature, id=f"e{i}")


def here(ws):
    """The id of the place the acting character stands in, where the fight is."""
    return ws.player_of(ws.acting).location


def take(ws, svc, serial, foes):
    """The fight service names the captives of one fight and the scene makes them: [(the record, the person)]."""
    out = []
    for cap in svc.captives(types.SimpleNamespace(serial=serial), foes, here(ws)):
        out.append((cap, ws.make_prisoner(cap.name, "", tip=cap.tip, named=False, kind=cap.kind, fighter=cap)))
    return out


def apart(store, npc):
    """Nobody else in the save has this person's full name or first name."""
    every = store.npc_names()
    return (sum(1 for n in every if n.strip().lower() == npc.name.strip().lower()) == 1
            and sum(1 for n in every if names.first_of(n) == names.first_of(npc.name)) == 1)


def told(npc, store):
    """The person, the registry and the name agree: the person's gender is the one the name was built for, and the registry's pronoun
    and people are the person's."""
    row = store.load_entity(f"captive:{npc.id}")
    return (row is not None and of_people(npc.people, npc.gender, npc.name) and row.pronoun == entities.GENDER[npc.gender]
            and row.people == npc.people)


# ---- the case that found it: twenty captives, one a fight, in one save, each let go (their rows stay)
NAME = "captive_names"
g = simlib.campaign(NAME, cls="warrior", seed=5, location="parth")
ws, store, world = g.scene, g.store, g.scene.world
svc = cs.service_of(ws)
made = []
for i in range(20):
    for cap, npc in take(ws, svc, 500 + i, [foe(world, i)]):
        made.append(npc)
        ws.settle_prisoner(npc, "release", "I let them go.")
given = [n.name for n in made]
check("(twenty captives taken, one a fight, and let go)", len(made) == 20, given)
check("twenty captives in one save take twenty names: no full name twice", len(set(given)) == 20, given)
check("...and no first name twice", len({names.first_of(n) for n in given}) == 20, given)
check("...each apart from every other name in the save, the dead and gone among them", all(apart(store, n) for n in made),
      [n.name for n in made if not apart(store, n)])
check("...none of them a name off the old list of sixteen", not any(n.name.split()[0] in OLD for n in made), given)
check("...each named for their people and gender, the registry telling the same", all(told(n, store) for n in made),
      [(n.name, n.people, n.gender) for n in made if not told(n, store)])

# ---- two taken in one fight, through the fight scene
foes = [C.fighter_from_creature(world.bestiary["bandit"], 3, "normal", f"t{i}", name=f"bandit {i + 1}") for i in range(2)]
for e in foes:
    e.hp, e.surrendered = 1, True
sc = cs.CombatScene(ws, C.Combat(fighters=[C.fighter_from_character(ws.player.character)] + foes, place="parth"), "bandit")
before = set(ws.escorted())
taken = sc.take_prisoners(foes)
pair = [store.load_npc(i) for i in ws.escorted() if i not in before]
check("(two who yielded in one fight are both taken)", len(taken) == 2 and len(pair) == 2, (taken, ws.escorted()))
check("two captives of one fight take two names, apart from each other and from the save",
      len(pair) == 2 and names.first_of(pair[0].name) != names.first_of(pair[1].name) and all(apart(store, n) for n in pair),
      [n.name for n in pair])
check("...each named for their people and gender", len(pair) == 2 and all(told(n, store) for n in pair),
      [(n.name, n.people, n.gender) for n in pair])
for n in pair:
    ws.settle_prisoner(n, "release", "I let them go.")
_keyed = streams.keyed
streams.keyed = lambda purpose, *a, **k: _keyed(purpose, "one die") if purpose == "captive_name" else _keyed(purpose, *a, **k)
try:
    same = [c.name for c in svc.captives(types.SimpleNamespace(serial=778), [foe(world, 0), foe(world, 1)], here(ws))]
finally:
    streams.keyed = _keyed
check("...and with both drawn on one die, the second is still named apart from the first",
      len(same) == 2 and names.first_of(same[0]) != names.first_of(same[1]), same)
again = [c.name for c in svc.captives(types.SimpleNamespace(serial=777), [foe(world, 0), foe(world, 1)], here(ws))]
check("the same fight on the same save names its captives the same", again == [c.name for c in svc.captives(
    types.SimpleNamespace(serial=777), [foe(world, 0), foe(world, 1)], here(ws))] and len(again) == 2, again)
store.close()
saves.drop(NAME)

# ---- a second save: the tip die, whatever names are free; then every old name already someone's first name
NAME2 = "captive_names_b"
g2 = simlib.campaign(NAME2, cls="warrior", seed=7, location="parth")
ws2, store2 = g2.scene, g2.store
svc2 = cs.service_of(ws2)


def tips():
    """The tip die of thirty fights, two who yielded in each, as captives() rolls it."""
    return [c.tip for s in range(900, 930) for c in svc2.captives(types.SimpleNamespace(serial=s), [foe(world, 0), foe(world, 1)],
                                                                   here(ws2))]


free = tips()
for i, nm in enumerate(OLD[:9]):
    store2.save_npc(NPC(id=f"held_{i}", name=f"{nm} Vell", people="human", role="farmer", location="parth"))
some = tips()
for i, nm in enumerate(OLD[9:]):
    store2.save_npc(NPC(id=f"held_{i + 9}", name=f"{nm} Vell", people="human", role="farmer", location="parth"))
none = tips()
check("(sixty tip dice rolled, some true and some false)", len(free) == 60 and 0 < sum(free) < 60, free)
check("the tip die of a fight is the same whatever names are free: with nine of the old names held, and with all sixteen",
      free == some == none, [i for i, (a, b, c) in enumerate(zip(free, some, none)) if not a == b == c])

check("(every name of the old list is someone's first name in the save)",
      {names.first_of(n) for n in store2.npc_names()} >= {n.lower() for n in OLD})
cap, npc = (take(ws2, svc2, 1000, [foe(world, 0)]) or [(None, None)])[0]
check("on that save a captive takes a name of their own, not one off the old list", npc is not None and npc.name.split()[0] not in OLD,
      getattr(npc, "name", None))
check("...apart from every name in the save, and named for their people and gender", npc is not None and apart(store2, npc)
      and told(npc, store2), (getattr(npc, "name", None), getattr(npc, "people", None), getattr(npc, "gender", None)))
if npc is not None:
    ws2.settle_prisoner(npc, "release", "I let them go.")

# ---- of another people: the place's (a bandit taken in Ironvein, a dwarf city), and the one their kind names (an orc warband chief)
ws2.enter("ironvein")
peoples = world.peoples_at("ironvein")
check("(Ironvein's people are dwarves, the most of them)", max(peoples, key=peoples.get) == "dwarf", peoples)
dwarf = (take(ws2, svc2, 1100, [foe(world, 0)]) or [(None, None)])[0][1]
check("a bandit taken in Ironvein is a dwarf, named from a dwarf's sounds for their gender",
      dwarf is not None and dwarf.people == "dwarf" and told(dwarf, store2) and apart(store2, dwarf),
      (getattr(dwarf, "name", None), getattr(dwarf, "people", None), getattr(dwarf, "gender", None)))
orc = (take(ws2, svc2, 1200, [foe(world, 1, "orc_warband_chief", 8)]) or [(None, None)])[0][1]
check("an orc warband chief taken there is an orc, named from an orc's sounds for their gender",
      orc is not None and orc.people == "orc" and told(orc, store2) and apart(store2, orc),
      (getattr(orc, "name", None), getattr(orc, "people", None), getattr(orc, "gender", None)))
store2.close()
saves.drop(NAME2)

# ---- the list is gone from the data, and its startup check with it
check("arcs.yaml prisoner holds no list of names", "names" not in A["prisoner"], A["prisoner"].get("names"))
check("...and the startup check that held the list is gone with it", not hasattr(data_check, "captive_names_problems"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

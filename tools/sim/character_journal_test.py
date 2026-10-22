"""Character pane + buttons spend one point at a time; the journal puts this town and the last town first and is searchable (data side)."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3); simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from ui import console
from ui.gui.bridge import is_view, HIDDEN

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
shutil.rmtree("saves/cj_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("cj_test"); store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1)); char.unspent_points = 2
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("parth")
c = ws.player.character
console.note = lambda m: None
check("#attradd is hidden and #character is a view", "#attradd" in HIDDEN and is_view("#character"))
str0 = c.attributes.strength
ws.command("#attradd strength")
check("one click spends one point", c.attributes.strength == str0 + 1 and c.unspent_points == 1, (str0, c.attributes.strength, c.unspent_points))
ws.command("#attradd dexterity"); ws.command("#attradd dexterity")
check("clicks stop when the points run out", c.unspent_points == 0 and c.attributes.dexterity == simlib.make_character("warrior", random.Random(1))[0].attributes.dexterity + 1)
ws.command("#attradd bogus")
# journal ordering
for n in ws.present: n.met_player = True; n.name_known_to_player = True; store.save_npc(n)
ws.enter("eldervale")
for n in ws.present: n.met_player = True; n.name_known_to_player = True; store.save_npc(n)
ws.enter("parth")
d = ws.journal_data()
towns = [g["town"] for g in d["groups"]]
check("this town comes first and is tagged", towns and d["groups"][0]["tag"] == "here" and towns[0] == "Parth", towns)
check("the last town comes next", len(towns) > 1 and d["groups"][1]["tag"] == "last visited" and towns[1] == "Eldervale", towns)
check("people are sorted by name inside a town", all([p["name"].lower() for p in g["people"]] == sorted(p["name"].lower() for p in g["people"]) for g in d["groups"]))
check("facts and history come with it", isinstance(d["facts"], list) and isinstance(d["history"], list))
ws.present[0].name_known_to_player = False; store.save_npc(ws.present[0])
d2 = ws.journal_data()
names = {x["name"] for g in d2["groups"] for x in g["people"]}
check("only people you know by name are listed", ws.present[0].name not in names, names)
check("each has a one-sentence line", all(x["line"].strip() for g in d2["groups"] for x in g["people"]))
n = ws.store.load_npc(ws.present[1].id); n.journal_note = "A kept note."; store.save_npc(n)
check("a written note is reused", any(x["line"] == "A kept note." for g in ws.journal_data()["groups"] for x in g["people"]))
from npc.models import Memory
m = ws.store.load_npc(ws.present[2].id); m.name_known_to_player = True; m.journal_note = ""
check("a named person with no note is due one", ws.note_due(m))
m.journal_note = "A note."; m.note_trust, m.note_mem = m.trust, len(m.memories)
check("a fresh note is not due again", not ws.note_due(m))
m.trust = min(100, m.trust + 20) if m.trust < 80 else m.trust - 20
check("a big change of heart makes it due", ws.note_due(m))
m.trust = m.note_trust; m.memories += [Memory(day=1, turn=1, text="a"), Memory(day=1, turn=2, text="b")]
store.save_npc(m); m = store.load_npc(m.id)                       # memories are rows: the count the note is judged by is read on load
check("new memories make it due", ws.note_due(m))
m.name_known_to_player = False
check("an unnamed person is never due", not ws.note_due(m))
print("FAILED" if bad else "ALL PASS", bad); sys.exit(1 if bad else 0)

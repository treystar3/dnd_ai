"""Journal: people named aloud by someone you talk to are noted as heard of, until you meet them."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
uc.note = lambda *a, **k: None
uc.panel = lambda name, data: False
from npc.life import note_mentions, populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/journal_heard_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("journal_heard_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
town = next(p for p in world.places.values() if not p.danger)
store.save_player(PlayerState(character=char, location=town.id))
cat = load_traits()
for p in world.places.values():
    if not p.parent and not p.danger:
        try: populate_place(store, world, p.id, cat)
        except Exception: pass
npcs = [store.load_npc(i) for i in store.list_npcs()]
speaker, other = next((a, b) for a in npcs for b in npcs if a.id != b.id and len(b.name.split()) >= 2)
speaker.name_known_to_player = True; store.save_npc(speaker)
added = note_mentions(speaker, f"That would be {other.name}. He keeps the records. Ask him.", store)
other = store.load_npc(other.id)
check("a named person is noted as heard of", added == [other.name] and other.heard_of.get("by") == speaker.name, (added, other.heard_of))
check("the line is the sentence that named them", other.name in other.heard_of["line"] and "Ask him" not in other.heard_of["line"], other.heard_of)
check("nobody is noted twice", note_mentions(speaker, f"{other.name} again", store) == [])
check("an empty speech notes no one", note_mentions(speaker, "", store) == [])
ws = WorldScene(store, world, cat, store.load_player())
d = ws.journal_data()
check("the journal lists them under heard of", any(x["name"] == other.name and x["by"] == speaker.name for x in d["heard"]), d["heard"])
check("and not among people met", all(x["name"] != other.name for g in d["groups"] for x in g["people"]))
other.met_player = True; other.name_known_to_player = True; store.save_npc(other)
d = ws.journal_data()
check("meeting them moves them out of heard of", all(x["name"] != other.name for x in d["heard"]) and any(x["name"] == other.name for g in d["groups"] for x in g["people"]))
shutil.rmtree("saves/journal_heard_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

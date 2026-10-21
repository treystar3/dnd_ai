"""Guild people know the guild's real rules and where the player stands."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
uc.note = lambda *a, **k: None
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/guild_knowledge_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("guild_knowledge_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 1400; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
store.save_player(PlayerState(character=char, location="guild_house"))
cat = load_traits()
for pid in ("guild_house", "parth"):
    populate_place(store, world, pid, cat)
ws = WorldScene(store, world, cat, store.load_player())
npcs = {n.role: n for n in (store.load_npc(i) for i in store.list_npcs())}
clerk = npcs["guild_clerk"]
text = " ".join(ws.guild_knowledge(clerk))
check("the clerk knows rank E needs level 10 and 4 contracts", "Rank E: you must be level 10 and have finished 4 guild contracts" in text, text[:400])
check("the clerk lists every rank up to S", all(f"Rank {l}:" in text for l in "EDCBAS"))
check("the clerk knows the joining fee", "joining costs" in text)
check("a stranger who has not joined is called that", "has not joined" in text)
ws.player.guild_rank = "F"; ws.player.guild_done = {"F": 1}
text = " ".join(ws.guild_knowledge(clerk))
check("a member's progress is spelled out", "rank F member" in text and "3 more to go" in text and "levels to go" in text, text[-300:])
ws.player.character.level = 12; ws.player.guild_done = {"F": 4}
text = " ".join(ws.guild_knowledge(clerk))
check("met requirements say met", text.count("(met)") == 2, text[-250:])
other = next((n for r, n in npcs.items() if r not in ws.GUILD_ROLES), None)
check("a non-guild person knows none of it", other is not None and ws.guild_knowledge(other) == [])
contractor = next((n for r, n in npcs.items() if r == "guild_contractor"), None)
if contractor:
    t = " ".join(ws.guild_knowledge(contractor))
    check("a contractor knows the rules but not your register", "Rank E:" in t and "The stranger" not in t)
shutil.rmtree("saves/guild_knowledge_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

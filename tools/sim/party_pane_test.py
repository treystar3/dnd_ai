"""The party pane: companions with their stats and a rename, hired adventurers listed but not renamable."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
NOTES, PANELS = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.panel = lambda name, data: (PANELS.append((name, data)) or True)
from core.models import Companion
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/party_pane_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("party_pane_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
char.level = 20
town = next(p for p in world.places.values() if not p.danger)
store.save_player(PlayerState(character=char, location=town.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character
ws.command("#party")
check("no companions, no party: a plain note", not PANELS or PANELS[-1][1]["companions"] == [], PANELS)

c.companions.append(Companion(id="rib", name="Skittering Ribcage", kind="undead", role="rogue", level=20, description="A twitching skeleton.", source="Skeletal Scout", tier="light"))
c.companions.append(Companion(id="sent", name="Iron-Willed Sentinel", kind="undead", role="guardian", level=20, description="A hulking skeleton.", source="Gravebound", tier="moderate"))
ws.player.party = [{"id": "h1", "name": "Brann Ashford", "role": "fighter", "level": 9, "fee": 0}]
PANELS.clear(); ws.command("#party")
name, d = PANELS[-1]
check("the party panel carries companions and adventurers", name == "party" and len(d["companions"]) == 2 and len(d["adventurers"]) == 1, d)
r = {x["id"]: x for x in d["companions"]}
check("stats are shown", all(r[k][f] > 0 for k in r for f in ("hp", "damage")) and r["sent"]["hp"] > r["rib"]["hp"], r)
check("role notes are shown", "bleeds" in r["rib"]["note"] and "sturdy" in r["sent"]["note"])
check("state is Ready", r["rib"]["state"] == "Ready" and r["rib"]["ok"])

NOTES.clear(); ws.command("#compname rib Bones")
check("renaming from the pane", c.companions[0].name == "Bones" and any("now called Bones" in n for n in NOTES), NOTES)
check("the panel is refreshed", PANELS[-1][1]["companions"][0]["name"] == "Bones")
check("it is saved", store.load_player().character.companions[0].name == "Bones")
NOTES.clear(); ws.command("#compname sent Bones")
check("names must be unique", c.companions[1].name == "Iron-Willed Sentinel" and any("already called" in n for n in NOTES), NOTES)
NOTES.clear(); ws.command("#compname sent Brann Ashford")
check("a name cannot match a hired adventurer", c.companions[1].name == "Iron-Willed Sentinel", NOTES)
NOTES.clear(); ws.command("#compname sent " + "x" * 30)
check("names are 24 characters at most", c.companions[1].name == "Iron-Willed Sentinel")
NOTES.clear(); ws.command("#compname sent <b>Hax</b>")
check("odd characters are refused", c.companions[1].name == "Iron-Willed Sentinel")
NOTES.clear(); ws.command("#name Iron = Stonewall")
check("renaming from the keyboard", c.companions[1].name == "Stonewall", NOTES)
NOTES.clear(); ws.command("#compname h1 Fred")
check("hired adventurers cannot be renamed", ws.player.party[0]["name"] == "Brann Ashford" and any("no such companion" in n for n in NOTES), NOTES)
c.companions[0].fallen = True; c.companions[0].recover_at = ws.minutes + 120
PANELS.clear(); ws.command("#party")
check("a fallen companion shows when it returns", "Fallen" in PANELS[-1][1]["companions"][0]["state"] and not PANELS[-1][1]["companions"][0]["ok"], PANELS[-1][1]["companions"][0])
uc.panel = lambda name, data: False
NOTES.clear(); ws.command("#party")
check("the terminal prints companions as text", any("Stonewall" in n and "health" in n for n in NOTES), NOTES)
print("\nFAILED:" if bad else "\nALL PASS", bad or "")
sys.exit(1 if bad else 0)

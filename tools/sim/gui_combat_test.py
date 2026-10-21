"""A whole fight through the window's bridge: the combat pane gets its data, the narration gets hoverable figures, and the
pinned view stays out of the way until the fight ends."""
import sys, random, shutil, json
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from types import SimpleNamespace as NS
stub.bot = NS(combat_choice=lambda: {"kind": "attack", "target": "e0"})
import re as _re
stub.a_Narration = lambda u, k: {"text": "The fight rages on. " + " Steel flashes. ".join(_re.findall(r"\[h\d+\]", u))}
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from scenes import combat_scene as cs
from npc.traits import load_traits
from engine import combat
from ui import console
from ui.gui.bridge import Bridge

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

shutil.rmtree("saves/gui_combat_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("gui_combat_test")
store.meta.seed = 6; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(3))
char.level = 8
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
b = Bridge(); b.install(); b.pinned = "#character"
foes = [combat.fighter_from_creature(world.bestiary["wolf"], 4, "normal", f"e{i}", name=f"wolf {i + 1}") for i in range(2)]
scene = cs.CombatScene.begin(ws, world.bestiary["wolf"], foes, "A pack of")
ws.combat = scene
evs = lambda: [e for _, e in b.log]
check("the fight opens the pane", any(e["k"] == "combat" for e in evs()))
check("pane is not also printed as text", not any(e["k"] == "text" and "⸢" in e.get("text", "") for e in evs()))
check("fight owns the side pane", b.in_combat is True)
b.dirty = True
for _ in range(8):
    if ws.combat is None:
        break
    scene.turn("I attack the first wolf")
combats = [e for e in evs() if e["k"] == "combat"]
check("a pane update after each round", len(combats) >= 2, len(combats))
d = combats[-1]["data"]
check("pane data carries enemies, you, abilities and blows", {"enemies", "you", "moves", "hits", "round"} <= set(d))
texts = "".join(e["text"] for e in evs() if e["k"] == "text" and e["pane"] == "main")
check("narration carries hoverable figures", "⟦" in texts and "damage)" in texts or "(miss)" in texts, texts[-300:])
ids = {h["id"] for e in combats for h in e["data"]["hits"]}
import re
used = set(re.findall(r"⟦([^|⟧]+)\|", texts))
check("every token points at a recorded blow", used and used <= ids, (used - ids))
check("no raw tags left in the text", "[h" not in texts)
check("no numbers line under the narration in the window", "⚔" not in texts)
if ws.combat is None:
    check("the pane is released when the fight ends", any(e["k"] == "combat_end" for e in evs()) and b.in_combat is False)
    b.dirty = True
    check("pinned view comes back afterwards", b.ask(main=True) == "#character")
b.uninstall()
print("\nFAILED: " + ", ".join(bad) if bad else "\nall ok", file=sys.__stdout__)
sys.exit(1 if bad else 0)

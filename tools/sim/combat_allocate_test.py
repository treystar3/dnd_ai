"""Spending attribute points in the middle of a fight keeps the fighter and the character in step."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
uc.note = lambda *a, **k: None
from engine import combat, pools
from scenes import combat_scene as cs
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/combat_allocate_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("combat_allocate_test")
store.meta.seed = 6; store.save_meta()
char, _ = simlib.make_character("mage", random.Random(3))
char.level = 8; char.unspent_points = 5
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
foes = [combat.fighter_from_creature(world.bestiary["wolf"], 4, "normal", "e0", name="wolf")]
scene = cs.CombatScene.begin(ws, world.bestiary["wolf"], foes, "A")
ws.combat = scene
p = scene.fight.player
c = ws.player.character
p.mana = p.max_mana * 0.4; scene.sync_player()
old_top, old_mana, old_ward = p.max_mana, p.mana, p.ward
attr = c.casting_attribute or "intelligence"
ws.attribute_click(attr)
ws.attribute_click("wisdom")
check("the fighter's mana maximum matches the character's", p.max_mana == pools.maximum(c, "mana") and p.max_mana > old_top, (p.max_mana, old_top))
check("the mana gained is added to current mana", p.mana > old_mana and abs(p.mana - (old_mana + (p.max_mana - old_top))) < 1, (p.mana, old_mana))
check("the character's mana equals the fight's", abs(c.mana - p.mana) < 0.01, (c.mana, p.mana))
check("wisdom raises the fighter's ward", p.ward > old_ward, (p.ward, old_ward))
check("current mana never exceeds the maximum", p.mana <= p.max_mana)
shutil.rmtree("saves/combat_allocate_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

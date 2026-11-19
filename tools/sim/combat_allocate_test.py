"""Spending attribute points in the middle of a fight keeps the fighter and the character in step. (f760) The points go through
play() as the pane sends them, and the fighter is read from the fight's row and again after the next typed line, never only from
the one in memory at once."""
import sys
from types import SimpleNamespace as NS
sys.path.insert(0, ".")
import config
import simlib
stub = simlib.Stub("mage", 5)
simlib.install(stub)
stub.bot = NS(combat_choice=lambda: {"kind": "attack", "target": "e0"})
simlib.quiet_console()
import ui.console as uc
for _n in ("note", "out", "status_block", "combat_state", "combat_panel", "show_header", "show_player_block"):
    if hasattr(uc, _n):
        uc.put(_n, lambda *a, **k: None)
from engine import combat, pools
from scenes import combat_scene as cs
from services.fight import FightService
from storage import saves

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "combat_allocate_test"
g = simlib.campaign(NAME, cls="mage", seed=6, char_seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = str(simlib.saves_path(NAME, "turns.jsonl"))
config.CRASH_LOG_PATH = str(simlib.saves_path(NAME, "crash.log"))
ws.enter("parth")
c = ws.player.character
c.level = 8; c.unspent_points = 5
store.save_player(ws.player)
world = g.world
foes = [combat.fighter_from_creature(world.bestiary["wolf"], 4, "normal", "e0", name="wolf")]
foes[0].hp = foes[0].max_hp = 5000
scene = cs.CombatScene.begin(ws, world.bestiary["wolf"], foes, "A")
ws.combat = scene
p = scene.fight.player
p.mana = p.max_mana * 0.4; scene.sync_player()
store.save_combat(scene.to_json())
old_top, old_mana, old_ward = p.max_mana, p.mana, p.ward
attr = c.casting_attribute or "intelligence"
ws.play(f"#attradd {attr}")
ws.play("#attradd wisdom")
c = ws.player.character
p = FightService.resume(store.load_combat())[0].player       # the fighter as the row keeps it
check("the fighter's mana maximum matches the character's", p.max_mana == pools.maximum(c, "mana") and p.max_mana > old_top, (p.max_mana, old_top))
check("the mana gained is added to current mana", p.mana > old_mana and abs(p.mana - (old_mana + (p.max_mana - old_top))) < 1, (p.mana, old_mana))
check("the character's mana equals the fight's", abs(c.mana - p.mana) < 0.01, (c.mana, p.mana))
check("wisdom raises the fighter's ward", p.ward > old_ward, (p.ward, old_ward))
check("current mana never exceeds the maximum", p.mana <= p.max_mana)
ws.play("I attack the wolf.")
p = ws.combat.fight.player
check("after the next typed line the fighter keeps the character's maximum and ward",
      p.max_mana == pools.maximum(c, "mana") and p.ward > old_ward, (p.max_mana, pools.maximum(c, "mana"), p.ward, old_ward))
g.close()
saves.drop(NAME)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

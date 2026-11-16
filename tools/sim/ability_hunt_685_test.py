"""(f685) A fighting ability aimed at a creature that lives here, with none in view, goes looking for it and opens the fight with it
(found in the second blind play: docs/play/2026-11-16_blind_play_journal.md). A search found signs, the passage showed the awakened
tree itself, and `I cast Twin Flare at the awakened tree.` was refused: "Twin Flare is a fighting technique - save it for a fight."
An attack named the same way already went looking (f449, hunt_named); the ability path never did. And `Twin Flare at the ogre.`
with no ogre about was read as an attack on a companion's id, which named nothing hunt_named could find.
Held here: a damaging ability at a creature of the place's roster searches for it as a search does, and when it is found the fight
begins with that ability as the first blow; a buff with nothing hostile in view is still told to wait for a fight; the words of the
line are read for the creature when the reading's target names none of them.
Run: python tools/sim/ability_hunt_685_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("mage", 6)
simlib.install(stub)
simlib.quiet_console()
from engine import combat, encounters
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("ability_hunt_685", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
c = ws.player.character
hits = [a for a in c.actives if a.context.value == "combat" and a.effect.value == "damage"]
buffs = [a for a in c.actives if a.context.value == "combat" and a.effect.value == "buff"]
check("(the character has a damaging fighting ability)", bool(hits), [a.name for a in c.actives])
wolf = ws.world.bestiary["wolf"]
real_roll = encounters.roll
encounters.roll = lambda *a, **k: (wolf, [combat.fighter_from_creature(wolf, 2, "normal", "e1", "wolf")])
said = []
ws.refuse = lambda say, *a, **k: said.append(say)
first = []
from scenes.combat_scene import CombatScene
real_turn = CombatScene.turn
CombatScene.turn = lambda self, text, forced=None, **k: first.append(getattr(forced, "ability", None)) or real_turn(self, text, forced=forced, **k)

ab = hits[0]
ws.combat, ws.wildlife = None, None
ws.on_ability(A(kind="ability", ability=ab.id, target="wolf"), f"I cast {ab.name} at the wolf.")
check("a damaging ability at a creature of this place, none in view, goes looking and the fight begins",
      ws.combat is not None and not said, (said, ws.combat))
check("...with that ability as the first blow", first[:1] == [ab.id], first)

g2 = simlib.campaign("ability_hunt_685b", seed=5, location="greywood")          # a fresh scene: the first fight is still on
ws2 = g2.scene
ws2.enter("greywood")
ws2.refuse = lambda say, *a, **k: said.append(say)
first.clear(); said.clear()
ws2.on_ability(A(kind="ability", ability=ab.id, target="hire:0-0"), f"{ab.name} at the wolf.")
check("the line's words are read for the creature when the reading's target names none", ws2.combat is not None and not said, said)

g3 = simlib.campaign("ability_hunt_685c", seed=5, location="greywood")
ws3 = g3.scene
ws3.enter("greywood")
ws3.on_attack(A(kind="attack", target="hire:0-0"), "Twin Flare at the wolf.")
check("an attack read as aimed at a companion, for a creature the line names, hunts the creature", ws3.combat is not None)

roster = ["panther", "giant_wasp", "bandit", "awakened_tree", "wolf"]
check("whole words name a creature: 'the awakened tree' is the tree", ws3.creature_named(roster, "Twin Flare at the awakened tree.") == ["awakened_tree"],
      ws3.creature_named(roster, "Twin Flare at the awakened tree."))
check("...and 'the wolves' the wolf", ws3.creature_named(roster, "I strike at the wolves") == ["wolf"])
check("a part of a word names none: 'the', 'and', 'was', 'has' are no panther, bandit, wasp or hawk",
      ws3.creature_named(roster, "Twin Flare at the ogre, and it was what it has been.") == [],
      ws3.creature_named(roster, "Twin Flare at the ogre, and it was what it has been."))
check("with no target read, the line's words are read whole too: 'at the griffon' is no saber-toothed tiger",
      ws3.hunt_named(A(kind="ability", ability=ab.id), "I cast Twin Flare at the griffon.") is False or
      "griffon" in " ".join(ws3.creature_named(encounters.ensure_roster(ws3.store, ws3.world, "greywood"), "at the griffon")))
sought = []
encounters.roll = lambda store, world, place, chance, rng, seek="", **k: sought.append(seek) or (wolf, [combat.fighter_from_creature(wolf, 2, "normal", "e1", "wolf")])
g4 = simlib.campaign("ability_hunt_685d", seed=5, location="greywood")
ws4 = g4.scene
ws4.enter("greywood")
from npc.models import NPC
ws4.store.save_npc(NPC(id="m685", name="Osric Vane", people="human", role="merchant", location="greywood"))
ws4.present = [ws4.store.load_npc("m685")] + ws4.present
ws4.on_attack(A(kind="attack", target="m685"), "I attack the merchant and the wolf.")
check("an attack aimed at a person here hunts nothing, whatever else the line names", ws4.combat is None and not sought, sought)
ws4.on_ability(A(kind="ability", ability=ab.id, target="hire:0-0"), f"{ab.name} at the wolf.")
check("the hunt seeks the creature the line names, not the first one about", sought[:1] == ["Wolf"] or sought[:1] == [wolf.name], sought)

if buffs:
    ws.combat, ws.wildlife = None, None
    said.clear()
    ws.on_ability(A(kind="ability", ability=buffs[0].id), f"I cast {buffs[0].name}.")
    check("a buff with nothing hostile about is still told to wait for a fight", ws.combat is None and said, said)
encounters.roll = real_roll
CombatScene.turn = real_turn
import shutil; shutil.rmtree("saves/ability_hunt_685", ignore_errors=True); shutil.rmtree("saves/ability_hunt_685b", ignore_errors=True); shutil.rmtree("saves/ability_hunt_685c", ignore_errors=True); shutil.rmtree("saves/ability_hunt_685d", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

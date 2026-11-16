"""(f663) A foe who yields: who yields is settled before the round's passage is written, among those standing when the round began,
and a foe who yields or runs mid-fight is said to the player (docs/design/21_play_faults_plan.md, D1; found in play:
docs/play/2026-11-15_play_findings.md 2.6 and 2.8). A fanatic was told felled like a log, then yielded, then was both bound and dead:
the prisoner was picked among the dead after the round's passage was written. Two bandits who yielded vanished from the foes' list
with no line.
Held here: in the round that wins, the one who yields is chosen before the round is told, from those standing when it began, never
one dead before it, and the round's telling is handed their yielding; the win does not choose again; a foe who yields or runs
mid-fight is a line the player reads.
Run: python tools/sim/yield_settled_663_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 8))
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(m))
for fn in ("narrate", "ledger"):
    uc.put(fn, lambda *a, **k: None)
from engine import battlefield, behaviors, combat, told
from engine.arcs import A as ARCS
from llm.contracts import CombatIntent
from scenes import combat_scene as cs

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("yield_settled_663_test", seed=9, location="trading_square")
ws, world = g.scene, g.scene.world
ARCS["prisoner"].update(chance=1.0, min_chance=1.0, max_chance=1.0)          # every won fight against outlaws leaves one who yields


def scene():
    me = combat.fighter_from_character(ws.player.character)
    early = combat.fighter_from_creature(world.bestiary["bandit"], 9, "normal", "e0", "the old bandit")
    last = combat.fighter_from_creature(world.bestiary["bandit"], 3, "normal", "e1", "the young bandit")
    fight = combat.Combat(fighters=[me, early, last], place="trading_square")
    for e in (early, last):
        battlefield.engage(fight, e, fight.player)
    early.hp = 0                                     # fell in an earlier round, and was told dead then
    last.hp = 1
    fight.round = 3
    sc = cs.CombatScene(ws, fight, "bandit")
    ws.combat = sc
    return sc, fight, early, last


sc, f, early, last = scene()
TOLD = []
sc.narrate_round = lambda text: TOLD.append(list(f.story))
sc.finish = lambda: None
sc.interpret = lambda text: CombatIntent(kind="attack", target="e1")
for _ in range(30):                                  # until a blow lands: the one standing has 1 health each round
    if f.over:
        break
    last.hp = 1
    sc.turn("I cut the young bandit down.")
check("the round wins", f.over == "victory", f.over)
check("2.6: the one who yields is one standing when the round began, never one dead before it",
      last.alive and last.surrendered and not early.alive, (last.hp, last.surrendered, early.hp, early.surrendered))
check("...and the round's telling is handed their yielding before it is written",
      TOLD and any("young bandit" in s.lower() and "yields" in s for s in TOLD[-1]), TOLD[-1:])
yielded_before = [e.id for e in f.fighters if e.alive and e.surrendered]
sc.service.yields(f, allowed=True)
sc.yield_settled = True
check("the win does not choose again", [e.id for e in f.fighters if e.alive and e.surrendered] == yielded_before)

sc, f, early, last = scene()
early.hp = early.max_hp
f.told = []
behaviors._break(f, early, True)
behaviors._break(f, last, False)
said = " ".join(f.told)
check("2.8: a foe who yields mid-fight is said to the player", "the old bandit" in said.lower() and "yield" in said.lower(), f.told)
check("...and one who runs", "the young bandit" in said.lower() and any(w in said.lower() for w in ("runs", "flees")), f.told)
shutil.rmtree("saves/yield_settled_663_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

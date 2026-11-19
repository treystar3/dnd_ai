"""(f668) What the narrator is told of a foe's stance stands on a state the engine holds, or is not told (docs/design/21_play_faults_plan.md,
D6; found in play: docs/play/2026-11-15_play_findings.md 2.11, a centaur and a ghost spoke and waited for an answer, then "cannot be
reasoned with"; backing away was told while the fight went on). The narrator was told "It holds its ground and warns the player off -
they could still back away" for every territorial foe, whatever the fight held.
Held here: a warning off offers a way back only when every foe starts far off and flight is open; otherwise the fight is told as on;
a foe the rules will not let be reasoned with (its category, its family) is told not to speak or wait for an answer, and one that can
be talked to is told nothing of it; parley's refusal and the telling read the one rule.
Run: python tools/sim/stance_held_668_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
simlib.quiet_console()
from engine import combat, parley
from scenes.combat_scene import CombatScene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


world = simlib.campaign("stance_held_668_test", seed=5, location="greywood").scene.world


def foe(kind, far):
    e = combat.fighter_from_creature(world.bestiary[kind], 5, "normal", "e0", kind, "far" if far else "engaged")
    e.starts_far = far
    return e


mute = next(k for k, c in world.bestiary.items() if not parley.speaks(combat.fighter_from_creature(c, 3, "normal", "x", k)))
talker = "bandit"
check("(a foe that cannot be reasoned with, and one that can)", not parley.speaks(foe(mute, True)) and parley.speaks(foe(talker, True)), mute)
told = CombatScene.stance_told("territorial", [foe(talker, True)], can_flee=True)
check("a warning off, every foe far and flight open: the way back is offered", "back away" in told, told)
told = CombatScene.stance_told("territorial", [foe(talker, False)], can_flee=True)
check("2.11: a foe close at hand: no way back is offered, the fight is told as on", "back away" not in told and "already on" in told, told)
told = CombatScene.stance_told("territorial", [foe(talker, True)], can_flee=False)
check("...nor when flight is shut (a duel, the first fight)", "back away" not in told, told)
told = CombatScene.stance_told("territorial", [foe(mute, True)], can_flee=True)
check("2.11: a foe that cannot be reasoned with is told not to speak or wait for an answer", "words will not reach it" in told, told)
told = CombatScene.stance_told("aggressive", [foe(talker, False)], can_flee=True)
check("...and one that can be talked to is told nothing of it", "words will not reach" not in told, told)
check("parley's refusal reads the same rule", (parley.why_not(foe(mute, True)) or "").endswith("only understands the fight.")
      and parley.why_not(foe(talker, True)) is None)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

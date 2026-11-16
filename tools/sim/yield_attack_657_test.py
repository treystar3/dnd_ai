"""(f657) A foe who has yielded and is then attacked, in any words or by any ability of the player's, is attacked: finished, as
"finish it" finishes them (docs/design/21_play_faults_plan.md, B2; found in play: docs/play/2026-11-15_play_findings.md 2.7, a centaur
yielded and "Twin Hammer Strike on the centaur." got "While you turn to other things, the centaur slips away"). The kill words were a
short list; a plain attack or an ability's name let the foe go. Held here: the attack verbs the action table declares, the common
words of a blow, and the name of any damaging ability the acting character holds, each finish the foe; mercy and a negated blow still
spare; a line about something else (a heal, a camp struck) still lets them slip away.
Run: python tools/sim/yield_attack_657_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
simlib.quiet_console()
from core.models import Effect
from engine import combat, loadout

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("yield_attack_657_test", seed=4, location="greywood")
ws, world = g.scene, g.scene.world
c = ws.player_of(ws.acting).character
blows = [a.name for a in loadout.prepared(c) if a.effect == Effect.DAMAGE]
others = [a.name for a in loadout.prepared(c) if a.effect != Effect.DAMAGE]
check("(the warrior holds a damaging ability)", bool(blows), [a.name for a in loadout.prepared(c)])


def outcome(line):
    e = combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", "e9", "the wolf", "engaged")
    e.hp, e.fled, e.surrendered = 3, True, True
    ws.held_yield = [e]
    took = ws.yield_intercept(line)
    return "killed" if e.hp <= 0 else ("spared" if took else "slipped")


blow = blows[0] if blows else "Brutal Strike"
for line in tuple(f"{b} on the wolf." for b in blows) + (f"I use {blow} on it", "I attack the wolf", "I strike it", "I hit the wolf with my axe",
             "I swing at the wolf", "I bring my hammer down on its skull", "I shoot it", "finish it"):
    check(f"an attack on a yielded foe finishes it: {line!r}", outcome(line) == "killed", outcome(line))
for line in ("I let it go", "don't attack it", "I lower my axe and spare it", "I won't strike it down"):
    check(f"mercy, or a blow said not to be struck, spares it: {line!r}", outcome(line) == "spared", outcome(line))
for line in ["I look around the trees", "We strike camp and move on", "I heal myself"] + [f"I use {n} on myself" for n in others[:1]]:
    check(f"a line about something else lets it slip away: {line!r}", outcome(line) == "slipped", outcome(line))
shutil.rmtree("saves/yield_attack_657_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

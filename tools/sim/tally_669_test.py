"""(f669) A contract's tally counts what the contract is about wherever it was done, and two contracts do not count the same things
(docs/design/21_play_faults_plan.md, D7; found in play: docs/play/2026-11-15_play_findings.md 5.9: a yielded centaur gave XP but no
tally; a boar in the dungeon did not count; two gather contracts were both "ready" on the same leaves).
Held here: a foe taken alive counts as one killed; a kill in a part of the contract's land, or in the dungeon beneath it, counts;
one somewhere else does not; for gathering, a contract taken earlier has what it needs first, and the second counts only what is
left, for every kind that counts the pack (goods and materials); a contract that counts its own progress is as before.
Run: python tools/sim/tally_669_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
simlib.quiet_console()
from engine import combat, dungeons, inventory as inv, quests

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("tally_669_test", seed=5, location="greywood")
ws, world = g.scene, g.scene.world
land = "greywood"


def boar(i=0):
    return combat.fighter_from_creature(world.bestiary["wolf"], 3, "normal", f"b{i}", "wolf")


def hunt():
    q = quests._quest("hunt", "F", "Hunt 3 wolves", ws.minutes, place=land, creature="wolf", count=3)
    ws.player.quests = [q]
    return q


q = hunt()
ws.tally_foes([boar()])
check("5.9: a foe taken alive counts as one killed", q["progress"] == 1, q["progress"])
q = hunt()
d = {"place": land, "entrance": "t669_warren", "name": "The Test Warren", "theme": "cave"}
world.add_place(dungeons.entrance_place(d, world))
ws.player.location = "t669_warren"
ws.record_kills([boar()])
check("...a kill in the dungeon beneath the contract's land counts", q["progress"] == 1, q["progress"])
sub = next((p.id for p in world.places.values() if p.parent == land), None)
if sub:
    q = hunt()
    ws.player.location = sub
    ws.record_kills([boar()])
    check("...as does one in a part of that land", q["progress"] == 1, (sub, q["progress"]))
q = hunt()
ws.player.location = "trading_square"
ws.record_kills([boar()])
check("...and one somewhere else does not", q["progress"] == 0, q["progress"])

leaves = "silverleaf" if "silverleaf" in inv.GOODS else next(iter(inv.GOODS))
a = quests._quest("gather", "F", "Bring 3 leaves", ws.minutes, good=leaves, count=3)
b = quests._quest("gather", "F", "Bring 3 more leaves", ws.minutes, good=leaves, count=3)
mine = [a, b]
pack = [inv.make_good(leaves, 4)]
check("5.9: two gather contracts: the earlier has what it needs first", quests.done(a, pack, mine) and quests.held(a, pack, mine) == 4)
check("...and the second counts only what is left", not quests.done(b, pack, mine) and quests.held(b, pack, mine) == 1, quests.held(b, pack, mine))
pack = [inv.make_good(leaves, 6)]
check("...with enough for both, both are ready", quests.done(a, pack, mine) and quests.done(b, pack, mine))
check("...one alone counts the whole pack, as before", quests.held(b, [inv.make_good(leaves, 4)]) == 4)
h = hunt()
h["progress"] = 2
check("a contract that counts its own progress is as before", quests.held(h, pack, [a, h]) == 2)
shutil.rmtree("saves/tally_669_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f569) An improvised control meets the same contest an ability's does (engine/combat.py contest): the target's wisdom resists it,
each control already landed on it this fight wears the next one down a step, and a boss starts a step down. To foul a foe (disable):
resisted, it shakes it off; half-taken, slowed a round; taken, slowed two. To drive one back (force_move): resisted, it holds its
ground; half-taken, it is driven out of position but keeps its feet; taken, it is also knocked prone. The count of controls on the
target rises only when a status lands."""
import random, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 69))
from engine import checks, combat, combat_improv
from world.loader import authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = authored()

class Die(random.Random):
    """The fight's dice with every uniform draw fixed: 99 is a clean take, 0 a clean resist."""
    def __init__(self, at):
        super().__init__(1); self.at = at
    def uniform(self, a, b):
        return self.at

def fight(boss=False, wisdom=None):
    char, _ = simlib.make_character("warrior", random.Random(2))
    me = combat.fighter_from_character(char)
    troll = combat.fighter_from_creature(world.bestiary["troll"], 3, "normal", "e1", name="the troll")
    if wisdom is not None:
        troll.attrs["wisdom"] = wisdom
    troll.boss = {"lr": 0} if boss else {}                     # a boss with no legendary resistance left: the contest alone
    return combat.Combat(fighters=[me, troll], place="greywood"), me, troll

real_roll = checks.roll
checks.roll = lambda odds, *a, **k: ("success", 1)                 # the check made: only the contest decides
try:
    # ---- fouling a foe, graded and worn down
    f, me, t = fight()
    seen = []
    for _ in range(3):
        before = t.counters.get("controlled", 0)
        n = len(f.story)
        combat_improv.resolve(f, me, t, "I tangle its legs in the net", Die(99), "disable")
        seen.append((" ".join(f.story[n:]), t.counters.get("controlled", 0) - before))
    check("a clean take fouls it for two rounds and counts as a control", "fouled and slowed" in seen[0][0] and "briefly" not in seen[0][0]
          and seen[0][1] == 1, seen[0])
    check("...the second is worn down a step: slowed, but briefly", "fouled and slowed" in seen[1][0] and "briefly" in seen[1][0]
          and seen[1][1] == 1, seen[1])
    check("...the third is shaken off, and does not count", "shakes it off" in seen[2][0] and seen[2][1] == 0, seen[2])

    f, me, t = fight(boss=True)
    n = len(f.story)
    combat_improv.resolve(f, me, t, "I tangle its legs in the net", Die(99), "disable")
    check("a boss starts a step down: a clean take only half-takes", "briefly" in " ".join(f.story[n:]), f.story[n:])

    f, me, t = fight()
    n = len(f.story)
    combat_improv.resolve(f, me, t, "I tangle its legs in the net", Die(0), "disable")
    check("a resisted fouling is shaken off and lands nothing", "shakes it off" in " ".join(f.story[n:])
          and not t.counters.get("controlled") and not "slowed" in t.statuses, f.story[n:])

    # ---- driving one back
    f, me, t = fight()
    combat_improv.resolve(f, me, t, "I shove it back", Die(99), "force_move")
    check("a clean shove drives it out of position and knocks it prone, a control", "driven" in " ".join(f.story)
          and "prone" in t.statuses and "exposed" in t.position_tags and t.counters.get("controlled") == 1, (f.story, t.position_tags))
    f, me, t = fight(boss=True)
    combat_improv.resolve(f, me, t, "I shove it back", Die(99), "force_move")
    check("a half-taken shove moves it but it keeps its feet, and is no control", "driven" in " ".join(f.story)
          and not "prone" in t.statuses and "exposed" in t.position_tags and not t.counters.get("controlled"), f.story)
    f, me, t = fight()
    combat_improv.resolve(f, me, t, "I shove it back", Die(0), "force_move")
    check("a resisted shove: it holds its ground", "holds its ground" in " ".join(f.story) and "exposed" not in t.position_tags
          and not "prone" in t.statuses, f.story)

    # ---- the counter rises only when a status lands
    f, me, t = fight()
    real_add = combat_improv.add_status
    combat_improv.add_status = lambda *a, **k: False                  # something turns the status aside (a ward, an immunity)
    try:
        combat_improv.resolve(f, me, t, "I tangle its legs in the net", Die(99), "disable")
        combat_improv.resolve(f, me, t, "I shove it back", Die(99), "force_move")
    finally:
        combat_improv.add_status = real_add
    check("a control turned aside is not counted", not t.counters.get("controlled"), t.counters)

    # ---- wisdom resists, on the fight's own dice
    def resisted(wisdom):
        n = 0
        for s in range(200):
            f, me, t = fight(wisdom=wisdom)
            combat_improv.resolve(f, me, t, "I tangle its legs in the net", random.Random(s), "disable")
            n += "shakes it off" in " ".join(f.story)
        return n
    dull, wise = resisted(3), resisted(40)
    check("a wise target shakes off far more foulings than a dull one", wise > dull + 30, (dull, wise))
finally:
    checks.roll = real_roll

src = open("engine/combat_improv.py", encoding="utf-8").read()
check("both controls go through combat.contest", src.count("contest(") >= 2)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

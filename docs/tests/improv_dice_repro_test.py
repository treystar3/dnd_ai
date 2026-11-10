"""REPRO (advisor review): a combat improvisation must roll on the fight's own dice.

services/fight.py hands combat_improv.resolve() the fight's dice (self.dice) as `rng`, but resolve() calls checks.roll(odds) without it,
so the roll is drawn from the global "checks" stream instead (engine/streams.py). The Bundle E decisions keep a fight's dice its own
(consistent across a reload; the odds simulation leaves no trace). Expected to FAIL on 06b393c; passes once resolve() passes rng."""
import random, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import engine.checks as checks
from engine import combat_improv

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

class _Stop(Exception):
    pass

seen = {}
_roll = checks.roll
def spy(odds, rng=None, c=None):
    seen["rng"] = rng
    raise _Stop()
checks.roll = spy

class P:                                   # only what resolve() reads before it rolls
    attrs = {"dexterity": 14, "intelligence": 12}
    name = "you"; side = "player"
class F:
    log = []; story = []

dice = random.Random(1234)
try:
    combat_improv.resolve(F(), P(), None, "I throw sand in its eyes", dice, "distract")
except _Stop:
    pass
finally:
    checks.roll = _roll

check("the improvisation's roll is made on the fight's dice it was handed", seen.get("rng") is dice,
      f"rolled on {seen.get('rng')!r} (None = the global 'checks' stream)")
print("FAILED:" if bad else "all ok", ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f503) The fence around the fight service (tools/purity.py check_fight): services/fight.py imports none of scenes, ui, llm.gateway,
llm.embed or the clock; writes nothing to the console; prints nothing; rolls no die outside the streams; and declares its dependencies
once (DEPENDS: store, bus, party, streams, and nothing else). The fence catches each of those planted; the DICE fence (f501) covers the
service as the fight module it is; the write-path scan reads services/ and catches a planted spatial write there."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import purity

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

check("the fight service passes its fence", purity.check_fight() == [], purity.check_fight())
check("...and the DICE fence names it, and it passes", "services/fight.py" in purity.DICE and not [p for p in purity.check_dice() if "services/fight.py" in p],
      [p for p in purity.check_dice() if "services/fight.py" in p])

planted = '''
import time
from scenes import combat_scene
from ui import console
from llm import embed
from llm.gateway import generate
from engine import streams
import random
DEPENDS = ("store", "bus", "party", "streams", "world")
def act(fight):
    console.note("a line")
    print("a line")
    r = random.Random(1)
    x = random.random()
    ok = streams.keyed("retreat", "f1", "ab12", 1)
'''
found = purity.fight_problems_in(planted, "services/planted.py")
for what in ("imports time", "imports scenes", "imports ui", "imports llm.embed", "imports llm.gateway", "writes to the console", "prints",
             "makes its own Random", "rolls random.random", "DEPENDS names"):
    check(f"the fence catches a service that {what}", any(what in f for f in found), found)
check("...and nothing else in it", len(found) == 10, found)

clean = '''
from engine import combat, streams
from engine.domain_events import FightBegun, current
DEPENDS = ("store", "bus", "party", "streams")
class FightService:
    def begin(self, spec):
        r = streams.get("combat")
        k = streams.keyed("yield", "ab12")
        return combat.Combat(fighters=[])
'''
check("a service that keeps to its dependencies passes", purity.fight_problems_in(clean, "services/clean.py") == [],
      purity.fight_problems_in(clean, "services/clean.py"))
check("a service with no DEPENDS is caught", any("DEPENDS" in f for f in purity.fight_problems_in("x = 1\n", "services/none.py")))

# ---- the write-path rule reads services/ (tools/sim/battlefield_test.py runs it over the tree; here, a planted write)
check("the write-path scan reads the services", "services" in purity.WRITE_SCAN_DIRS, purity.WRITE_SCAN_DIRS)
caught = purity.spatial_writes_in("def place(f):\n    f.zone_id = 'z1'\n    f.row = 'front'\n", "services/planted.py")
check("...and catches a spatial write planted there", len(caught) == 2 and all("services/planted.py" in c for c in caught), caught)
check("...while the law itself may write", purity.spatial_writes_in("f.zone_id = 'z1'\n", "engine/battlefield.py") == [])
check("the scan over the tree finds nothing", purity.spatial_writes() == [], purity.spatial_writes())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

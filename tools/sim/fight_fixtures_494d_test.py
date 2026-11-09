"""(f494) The fight fixtures, shard 3 of 4 (tools/sim/fight_fixtures.py): every fight of the shard, played through the scene under the
stub, gives the numbers recorded before Bundle E's rewrite: each round's blows with their explanation, the log, each fighter's resources,
statuses, strengths, buffs and place, and what was won. A moved number names its case, its first path and the keys that moved."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import fight_fixtures

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

fight_fixtures.shard_test(3, check)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

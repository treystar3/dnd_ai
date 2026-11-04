"""(f494) Fixtures of today's fight numbers, recorded before Bundle E's rewrite (decision 10): shard 0 of the fights (the other three are
fight_fixtures_494b/c/d_test.py) plays to its recorded numbers; the stat sheets of every stub class at levels 1, 10 and 25 are as
recorded; the grid covers every creature family, every combat mechanic, every status and every boss phase; a number changed on purpose
is caught and named by its round and key; the same fights give the same numbers whatever Python's hash seed; and the fixtures sit
outside the data hash, so recording them re-blesses nothing."""
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import fight_fixtures as ff

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- shard 0 plays to its numbers
ff.shard_test(0, check)

# ---- the sheets
kept = ff._read(ff.OUT / "sheets.json.gz")
now = ff._norm(ff.sheets())
check("every stub class's stat sheet at levels 1, 10 and 25 is as recorded", kept["sheets"] == now,
      ff.first_difference(kept["sheets"], now))
check("...one sheet for each", len(now) == len(ff._classes()) * len(ff.LEVELS), len(now))

# ---- what the grid covers
from core import rules
from engine import combat
cov = ff.kept_coverage()
fams = ff.families()
check("the grid meets every creature family", fams <= set(cov.get("families", ())), sorted(fams - set(cov.get("families", ()))))
check("...gives every combat mechanic the engine runs", set(rules.ENGINE_COMBAT_MECHANICS) <= set(cov.get("mechanics_given", ())),
      sorted(set(rules.ENGINE_COMBAT_MECHANICS) - set(cov.get("mechanics_given", ())))[:8])
check("...lays on every status", set(combat.RULES["statuses"]) <= set(cov.get("statuses", ())),
      sorted(set(combat.RULES["statuses"]) - set(cov.get("statuses", ()))))
phases = {p.split(":")[1] for p in cov.get("boss_phases", ())}
check("...brings a boss through every phase it has (fresh, bloodied, its last stand)", {"0", "1", "3"} <= phases, sorted(phases))
check("...and plays every stub class", set(ff._classes()) <= set(cov.get("classes", ())))

# ---- a number changed on purpose is caught and named
one = next(c["id"] for c in ff.cases() if ff.shard_of(c) == 0)
keep = combat.RULES["damage"]["attribute_bonus"]
combat.RULES["damage"]["attribute_bonus"] = keep * 1.25
try:
    records, _ = ff.play(0, only={one})
finally:
    combat.RULES["damage"]["attribute_bonus"] = keep
moved = ff.compare(0, records, only={one})
check("a changed damage number is caught, named by the case, the round and the key", moved and moved[0].startswith(one)
      and ".rounds[" in moved[0] and "keys moved:" in moved[0], moved[:1])

# ---- the same numbers whatever the hash seed
two = [c["id"] for c in ff.cases() if ff.shard_of(c) == 0][:2]
code = ("import sys; sys.path[:0] = ['.', 'tools', 'tools/sim']; import fight_fixtures as ff; "
        f"r, _ = ff.play(0, only={set(two)!r}); lines = ff.compare(0, r, only={set(two)!r}); "
        "print('MOVED' if [l for l in lines if not l.startswith('warning')] else 'SAME')")
out = subprocess.run([sys.executable, "-c", code], env=dict(os.environ, PYTHONHASHSEED="4242"), capture_output=True, text=True,
                     timeout=300)
check("the same fights give the same numbers under another hash seed", out.stdout.strip().endswith("SAME"),
      (out.stdout[-300:], out.stderr[-300:]))

# ---- outside the data hash
from storage import statehash
check("the fixtures are not part of the game's data (no re-bless for recording them)",
      not str(ff.OUT.relative_to(ff.ROOT)).startswith("data"), ff.OUT)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

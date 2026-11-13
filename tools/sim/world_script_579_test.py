"""(f579) The seeded world script (tools/sim/world_script.py) plays the same world twice, and covers what it says it covers. Two plays
from one seed, in saves of different names and a process each, hold the same world after every step, as text; every part of its coverage is met (a matter
ended by the player and its settled deed, news folded, capped and a deed's tale kept, an effect lifted and dropped, finished matters,
deeds and history at their caps, a rolled-back operation); and the world's four lists are all in use at the end. The storage features
of the foundations bundle run this script over old storage and new: a script that stopped covering a case would hollow that proof, so
the coverage is checked here by name.
Run: python tools/sim/world_script_579_test.py"""
import json
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
sys.path.insert(0, "tools/sim")
import world_script
from concurrent.futures import ThreadPoolExecutor

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

class Play:
    def __init__(self, d):
        self.steps, self.cover, self.other, self.calls = [tuple(x) for x in d["steps"]], d["cover"], d["other"], d.get("calls")

with ThreadPoolExecutor(2) as pool:                      # each play in a process of its own (the stand-in model counts what it invents)
    a, b = (Play(d) for d in pool.map(world_script.run_apart, ("world_script_579_a", "world_script_579_b")))

for what, met in a.cover.items():
    check(f"the script covers: {what}", met)
check("...fifteen things in all, none dropped from the script", len(a.cover) == 15, sorted(a.cover))   # (f605) an act
check("the two plays took the same steps", [l for l, _ in a.steps] == [l for l, _ in b.steps] and len(a.steps) >= 25, len(a.steps))
first = next((l for (l, x), (_, y) in zip(a.steps, b.steps) if x != y), None)
check("after every step the two plays hold the same world, as text", first is None, first)
check("...and every other table of the save, by its digest", a.other == b.other, [k for k in a.other if a.other[k] != b.other.get(k)])
check("(f605) the two plays made the same model calls, kind by kind (world_script_605_test pins them)", a.calls and a.calls == b.calls,
      (a.calls, b.calls))
end = json.loads(a.steps[-1][1])
check("the four lists the storage move takes are all in use at the end", all(end.get(k) for k in ("threads", "deeds", "news", "effects")),
      {k: len(end.get(k) or []) for k in ("threads", "deeds", "news", "effects")})
check("...beside the keys that stay in the row", all(k in end for k in ("last", "seq", "history", "cooldowns")), sorted(end))
changed = sum(1 for (_, x), (_, y) in zip(a.steps, a.steps[1:]) if x != y)
check("nearly every step changed the world (a script of quiet steps proves little)", changed >= len(a.steps) - 4, (changed, len(a.steps)))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

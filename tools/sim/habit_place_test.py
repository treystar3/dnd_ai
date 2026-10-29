"""(f379) A companion's habit happens only where it can: walking into the Greywood, "Urrok touches the doorframe on the way in, for luck"
had no door to touch. A habit says where it needs (quirks.yaml where: building, open_air); without it, anywhere."""
import random, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import quirks
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def hire(habit):
    return {"id": "h1", "name": "Urrok Ghagh", "gender": "male", "quirks": {"habit": habit}}

def shown(habit, place_type):
    return quirks.habit_line(hire(habit), "arrival", random.Random(1), place_type=place_type)

check("the doorframe is touched on the way into a building", "doorframe" in shown("doorframe", "inn") and "doorframe" in shown("doorframe", "guild"))
check("...never walking into a forest, onto a road, into a town's streets or down a dungeon",
      not any(shown("doorframe", t) for t in ("forest", "road", "town", "square", "dungeon")))
check("the sky is read in the open, never inside a building or under the ground", "sky" in shown("checks_sky", "forest")
      and not shown("checks_sky", "inn") and not shown("checks_sky", "dungeon") and not shown("checks_sky", "underground"))
check("a habit that needs no place happens anywhere", bool(shown("counts_coin", "forest")) and bool(shown("counts_coin", "inn")))
check("with no place given, nothing is held back", "doorframe" in shown("doorframe", ""))
check("every habit's where is one the engine knows", all(s.get("where", "") in ("", "building", "open_air") for s in quirks.Q["habits"].values()))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

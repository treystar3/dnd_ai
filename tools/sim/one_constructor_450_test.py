"""(f450) One constructor of the runtime, and the count of the others only falls. The suite opened its campaigns by hand in over a hundred
files (a store, a world, a character, a WorldScene), and eight tools did the same their own way: every one is a second constructor of the
runtime, and a change to the runtime's shape (the rebuild's Bundle B) is an edit to every one of them. simlib.campaign() is the one way
now, and this ratchet counts the files under tools/ that still build a WorldScene or parse the world themselves: a new one fails it, and a
file moved onto the helper must be taken off the count, so the list never silently stops shrinking (the shape of fresh_world_434_test's
fence). Bundle B's f457 moves the tools; the tests move as they are touched."""
import pathlib, sys
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

ME = pathlib.Path(__file__).resolve()
SCENE, WORLD = "WorldScene" + "(", "load_world" + "()"          # spelt apart, so this file counts neither itself nor the helper's test
RECORDED = {"tests building a WorldScene": 124, "tools building a WorldScene": 8, "tests parsing the world": 154, "tools parsing the world": 16}

def files(folder: str, pattern: str, tests: bool) -> list[str]:
    out = []
    for p in sorted(pathlib.Path(folder).glob("*_test.py" if tests else "*.py")):
        if p.resolve() == ME or p.name.endswith("_450_test.py"):
            continue
        if pattern in p.read_text(encoding="utf-8"):
            out.append(p.as_posix())
    return out

found = {"tests building a WorldScene": files("tools/sim", SCENE, True), "tools building a WorldScene": files("tools", SCENE, False),
         "tests parsing the world": files("tools/sim", WORLD, True), "tools parsing the world": files("tools", WORLD, False)}
counts = {k: len(v) for k, v in found.items()}
over = {k: (counts[k], RECORDED[k]) for k in RECORDED if counts[k] > RECORDED[k]}
check("no new file builds the runtime its own way (open a campaign with simlib.campaign)", not over,
      {k: v for k, v in over.items()} | {"new": [f for k in over for f in found[k][-3:]]})
under = {k: (counts[k], RECORDED[k]) for k in RECORDED if counts[k] < RECORDED[k]}
check("...and the ratchet is kept tight: a file moved onto the helper is taken off the count", not under, under)
for k in RECORDED:
    print(f"     {k}: {counts[k]}")
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

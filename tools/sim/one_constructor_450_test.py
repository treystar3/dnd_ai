"""(f450) One constructor of the runtime, and the count of the others only falls. The suite opened its campaigns by hand in over a hundred
files (a store, a world, a character, a WorldScene), and eight tools did the same their own way: every one is a second constructor of the
runtime, and a change to the runtime's shape (the rebuild's Bundle B) is an edit to every one of them. simlib.campaign() is the one way
now, and this ratchet counts the files under tools/ that still build a WorldScene or parse the world themselves: a new one fails it, and a
file moved onto the helper must be taken off the count, so the list never silently stops shrinking (the shape of fresh_world_434_test's
fence). Bundle B's f457 moves the tools; the tests move as they are touched."""
import ast, pathlib, sys
sys.path.insert(0, ".")

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

ME = pathlib.Path(__file__).resolve()
RECORDED = {"tests building a WorldScene": 124, "tools building a WorldScene": 5, "tests parsing the world": 154, "tools parsing the world": 14}
# (f453) rerun.py moved onto the session; session_453_test builds one scene the old way on purpose, the proof that such a scene adopts a session

def calls(tree: ast.AST, name: str) -> bool:
    """Whether the file calls `name(...)` anywhere: a call, not a mention in a string (the fences quote these names in source checks)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == name) or (isinstance(f, ast.Attribute) and f.attr == name):
                return True
    return False

def files(folder: str, name: str, tests: bool) -> list[str]:
    out = []
    for p in sorted(pathlib.Path(folder).glob("*_test.py" if tests else "*.py")):
        if p.resolve() == ME or p.name.endswith("_450_test.py"):
            continue
        if calls(ast.parse(p.read_text(encoding="utf-8")), name):
            out.append(p.as_posix())
    return out

found = {"tests building a WorldScene": files("tools/sim", "WorldScene", True), "tools building a WorldScene": files("tools", "WorldScene", False),
         "tests parsing the world": files("tools/sim", "load_world", True), "tools parsing the world": files("tools", "load_world", False)}
counts = {k: len(v) for k, v in found.items()}
over = {k: (counts[k], RECORDED[k]) for k in RECORDED if counts[k] > RECORDED[k]}
check("no new file builds the runtime its own way (open a campaign with simlib.campaign)", not over, over)
under = {k: (counts[k], RECORDED[k]) for k in RECORDED if counts[k] < RECORDED[k]}
check("...and the ratchet is kept tight: a file moved onto the helper is taken off the count", not under, under)
for k in RECORDED:
    print(f"     {k}: {counts[k]}")
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

"""(f581) The dice are an object. engine/streams.py's named streams, their key and its snapshot live on a Streams; the module's functions
(begin, reset, get, new_id, key, keyed, snapshot, restore) are those of one DEFAULT, the process's own, which alone seeds the global
random module. So today's play is today's play (stream_key_579_test passes unchanged), and a second set of dice can exist beside it
without moving it: what a second player's character rolls on in multiplayer M1, where its id enters the key. Whatever holds a stream
across inputs (the scene's dice, the fight's, the spells') holds the default's and is reseeded with it; those holders are listed here and
the list only shrinks, since each must take its dice from the acting character before a second set can serve it.
Run: python tools/sim/stream_object_581_test.py"""
import ast
import random
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import streams

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def same(r, seed, n=5):
    want = random.Random(seed)
    return [r.random() for _ in range(n)] == [want.random() for _ in range(n)]

# ---- the module's functions are the default's
streams.reset()
streams.begin(7, 3, "look")
D = streams.DEFAULT
check("the module's dice are one object, the process's own", isinstance(D, streams.Streams) and streams.get("obj581") is D.get("obj581")
      and streams.key() == D.key() == "7:3:look")
check("...its functions the default's: an id, a keyed die, a snapshot", streams.snapshot() == D.snapshot()
      and same(streams.keyed("brief", "n1"), "7:3:look:keyed:brief:n1::0") and same(D.keyed("brief", "n1"), "7:3:look:keyed:brief:n1::0"))

# ---- a second set of dice beside it
streams.begin(7, 3, "look")
held = streams.get("obj581")
before = (streams.snapshot(), random.getstate())
other = streams.Streams()
check("a new set of dice starts unseeded", other.key() == "unseeded" and same(other.get("obj581"), "unseeded:obj581"))
other.begin(7, 3, "look")
check("with the same key it draws what the default draws", other.key() == "7:3:look" and same(other.get("obj581"), "7:3:look:obj581")
      and other.new_id() == format(random.Random("7:3:look:ids").getrandbits(32), "08x"))
other.get("another").random()
other.keyed("pick").random()
other.begin(9, 1, "something else")
other.reset()
check("...and nothing it does moves the default: its key, its streams, or the global random module",
      (streams.snapshot(), random.getstate()) == before and streams.key() == "7:3:look" and other.get("obj581") is not held)
other.begin(7, 4, "wait")
snap = other.snapshot()
first = [other.get("obj581").random(), other.new_id()]
other.restore(snap)
check("it keeps and restores its own state", [other.get("obj581").random(), other.new_id()] == first and random.getstate() == before[1])
other.begin(7, 5, "wait")
try:
    other.restore(snap)
    refused = False
except RuntimeError:
    refused = True
check("...and refuses a snapshot from before it was reseeded", refused)
try:
    D.restore(snap)
    crossed = False
except RuntimeError:
    crossed = True
check("...as the default refuses one taken under another key", crossed)
streams.begin(7, 5, "wait")
mine = streams.snapshot()
try:
    D.restore(other.snapshot())                          # the same key, another set's states
    crossed = False
except RuntimeError:
    crossed = True
check("...and one of another set even under the same key: a second set moves nothing of the first through its snapshot either",
      crossed and streams.snapshot() == mine)
import copy
check("a copy of a set of dice is that set (a copied holder never rolls a second process's dice)",
      copy.copy(D) is D and copy.deepcopy(D) is D and copy.deepcopy(streams.get) == streams.get and copy.deepcopy(other) is other)

# ---- the default alone is the process's
streams.begin(7, 6, "look")
check("the default seeds the global random module with its key", same(random, "7:6:look:global"))
check("STRICT is the process's, on the module as before", streams.STRICT in (True, False) and not hasattr(D, "STRICT"))
check("a fixed die belongs to no set of dice", same(streams.fixed("roster", 12), "roster:12") and not hasattr(D, "fixed"))

# ---- who holds a stream across inputs: listed, and the lists only shrink
# KEPT: a stream put on a module or an object (reseeded with the default; it must come from the acting character before a second set
# of dice can serve it). HANDED: one passed straight into a call, whose callee may keep it: the fight service keeps the fight's for its
# life (services/fight.py self.dice, built per use by scenes/combat_scene.py fight_service). A stream drawn where it is asked for (a
# local name, `(rng or streams.get(..)).random()`) is held by nobody and is not listed.
KEPT = {("engine/spellcraft.py", "spells"), ("scenes/combat_scene.py", "combat"), ("scenes/world.py", "scene")}
HANDED = {("engine/combat.py", "combat"), ("engine/events.py", "events"), ("scenes/combat_scene.py", "combat"),
          ("scenes/training_actions.py", "lessons")}
kept, handed, second = set(), set(), []
for d in ("engine", "scenes", "services", "npc", "world", "storage", "character", "core", "llm", "ui"):
    for path in sorted(Path(d).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Streams" or \
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "Streams":
                if path.as_posix() != "engine/streams.py":
                    second.append(f"{path.as_posix()}:{node.lineno}")
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get"):
                continue
            v = node.func.value
            if not ((isinstance(v, ast.Name) and v.id == "streams") or (isinstance(v, ast.Attribute) and v.attr == "DEFAULT")):
                continue
            name = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "?"
            up = parent[node]
            while isinstance(up, ast.BoolOp):                # `given or streams.get(..)`
                up = parent[up]
            if isinstance(up, ast.keyword):
                up = parent[up]
            if isinstance(up, ast.Call):                     # passed straight into a call
                handed.add((path.as_posix(), name))
            elif isinstance(up, (ast.Assign, ast.AnnAssign)):
                target = up.targets[0] if isinstance(up, ast.Assign) else up.target
                if isinstance(target, ast.Attribute) or isinstance(parent[up], (ast.Module, ast.ClassDef)):
                    kept.add((path.as_posix(), name))
check("a stream kept on a module, a class or an object is one of the recorded holders", kept <= KEPT, sorted(kept - KEPT))
check("...a stream passed straight into a call is one of the recorded hand-offs", handed <= HANDED, sorted(handed - HANDED))
check("...and one that is gone is taken off its list (they only shrink)", KEPT <= kept and HANDED <= handed,
      (sorted(KEPT - kept), sorted(HANDED - handed)))
check("no game code makes a set of dice of its own yet: the process has the one", not second and D._process
      and not streams.Streams()._process, second)

# ---- a line tried again meets the same dice
g = simlib.campaign("stream_581", seed=5, location="trading_square")
ws = g.scene
ws.enter("trading_square")
seen, failing = [], [True]


def reading(u, k):
    seen.append((streams.key(), ws.rng.getstate(), streams.get("ids").getstate()))
    if failing[0]:
        raise RuntimeError("the model could not read the line")
    return {"actions": [{"kind": "look"}]}


stub.a_ActionPlan = reading
first_line = ws.turn("look at the well")
first_tries = list(seen)
seen.clear()
failing[0] = False
second_line = ws.turn("look at the well")
check("(the first line's reading failed every try and the line was not taken; the second was)", first_line is False
      and second_line is not False and len(first_tries) >= 2 and len(seen) == 1, (first_line, second_line, len(first_tries), len(seen)))
check("a line tried again after it was not taken meets the dice it met the first time: the key, the scene's dice, the ids",
      len(seen) == 1 and seen[0] == first_tries[0], (seen[0][0] if seen else None, first_tries[0][0] if first_tries else None))
check("the scene's dice are the default's 'scene' stream, held across the lines", ws.rng is streams.DEFAULT.get("scene"))
g.session.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

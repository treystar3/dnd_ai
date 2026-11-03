"""(f476) The fence around Bundle D's pure modules (tools/purity.py): every one that exists is clean, and the fence catches what it is
for: a module reaching the save, a scene, the model, the clock or a uuid; dice from anywhere but its own keyed stream; an order taken
from a set's iteration or an object's id(). And the keyed stream itself: the same input and purpose draw the same, a different purpose
or speaker draws otherwise, and drawing it moves no stream the game rolls."""
import subprocess
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import purity
from engine import streams

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

check("every pure module that exists passes the fence", purity.check_all() == [], purity.check_all())
planted = '''
import random
from storage import campaign
from engine import streams
def pick(names):
    for n in set(names):
        yield n
    order = sorted(names, key=id)
    x = random.choice(names)
    r = random.Random(1)
    d = streams.get("scene")
'''
found = purity.problems_in(planted, "planted.py")
for what in ("imports storage", "iterates a set unsorted", "orders by id()", "rolls random.choice", "makes its own Random", "draws streams.get"):
    check(f"the fence catches a module that {what}", any(what in f for f in found), found)
clean = '''
from engine import streams
def pick(names, speaker):
    r = streams.keyed("brief", speaker)
    return r.choice(sorted(set(names)))
'''
check("...and lets a module drawing its own keyed stream over a sorted set through", purity.problems_in(clean, "clean.py") == [], purity.problems_in(clean, "clean.py"))
check("...and a time or uuid import is refused too", any("imports time" in f for f in purity.problems_in("import time\n", "t.py"))
      and any("imports uuid" in f for f in purity.problems_in("import uuid\n", "u.py")) and any("imports llm.gateway" in f for f in purity.problems_in("from llm import gateway\n", "g.py")))

streams.begin(41, 3, "I talk to the farmer")
scene = streams.get("scene")
before = scene.getstate()
a = [streams.keyed("brief", "farmer", "c1", 0).random() for _ in range(2)]
check("a keyed draw is the same for the same input, purpose, speaker, conversation and count", a[0] == a[1], a)
check("...different for another purpose or speaker", streams.keyed("reply", "farmer", "c1", 0).random() != a[0] and streams.keyed("brief", "smith", "c1", 0).random() != a[0])
check("...and drawing it moves no stream the game rolls", scene.getstate() == before)
streams.begin(41, 4, "I talk to the farmer")
check("...while the next input draws otherwise", streams.keyed("brief", "farmer", "c1", 0).random() != a[0])
code = "import sys; sys.path.insert(0, '.'); from engine import streams; streams.begin(41, 3, 'I talk to the farmer'); print(streams.keyed('brief', 'farmer', 'c1', 0).random())"
outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={"PYTHONHASHSEED": s, "PATH": "/usr/bin:/bin"}).stdout.strip() for s in ("1", "2")}
check("...and the same in two processes under different hash seeds", len(outs) == 1 and str(a[0]) in outs, outs)
streams.reset()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

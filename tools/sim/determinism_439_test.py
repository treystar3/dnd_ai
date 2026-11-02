"""(f439) Every turn decided by the save, its seed and what was typed. The same save played with the same lines in two separate processes
(each with its own PYTHONHASHSEED, so nothing may lean on Python's per-process string hashing) must end in the same state and show the
same words, after a session of walks, talk, fights and road stops the night bot chooses, a pane command, and a turn the model failed
that was rolled back and tried again. And the source keeps it so: no unseeded generator, no roll of the global random module, no draw
from the machine's own entropy outside character creation, and no uuid, in the game's code."""
import ast, json, os, pathlib, random, shutil, subprocess, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 39))

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

CHILD = r'''
import hashlib, json, random, sys, types
sys.path.insert(0, "."); sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 39)
simlib.install(stub)
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append(f"{_fn}:{a[0] if a else ''}"))
uc.dialogue = lambda before, speaker, speech, after="", *a, **k: SHOWN.append(f"dialogue:{speaker}:{speech}")
uc.panel = lambda name, data: False
from engine import streams
streams.STRICT = True
from llm import gateway
from storage import statehash
import nightbot

game = simlib.campaign(sys.argv[1], fresh=False)        # (f450) the suite's one way to open a campaign: this one copied into place
store, ws = game.store, game.scene
bot = nightbot.Bot(ws, ws.world, random.Random(39), stub=stub, persona="wanderer")
stub.bot = bot
FAIL = {"on": False}
real = gateway._client
def chat(**k):
    if FAIL["on"] and k["format"].get("title") == "ActionPlan":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat)
N, AFTER = int(sys.argv[2]), []
state = {"n": 0}
def ask(*a, main=False, **k):
    if not main:
        return "yes"
    if state["n"]:
        AFTER.append(statehash.digest(store)["all"][:12])
    state["n"] += 1
    FAIL["on"] = state["n"] == 6                        # the sixth line's turn fails and rolls back; the seventh says it again
    if state["n"] > N:
        return "quit"
    if state["n"] == 4:
        return "#stats"
    if state["n"] == 7:
        return AFTER and LAST["text"]
    text, kind = bot.decide()
    LAST["text"] = text
    return text
LAST = {"text": "I look around."}
uc.ask = ask
ws.run()
print("RESULT " + json.dumps({"all": statehash.digest(store)["all"], "after": AFTER, "steps": store.meta.steps, "turn": store.meta.turn,
                              "shown": hashlib.sha256("\n".join(SHOWN).encode()).hexdigest(), "lines": len(SHOWN)}))
'''

# ---- one save, played twice in two processes
for s in ("det439_base", "det439_a", "det439_b"):
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
simlib.campaign("det439_base", seed=39, turn=1, minutes=480).close()      # (f450) the suite's one way to open a campaign
for s in ("det439_a", "det439_b"):
    shutil.copytree("saves/det439_base", f"saves/{s}")
script = pathlib.Path("saves/det439_child.py")
script.write_text(CHILD, encoding="utf-8")
runs = {}
for name, hseed in (("det439_a", "1"), ("det439_b", "2")):
    out = subprocess.run([sys.executable, str(script), name, "40"], capture_output=True, text=True, timeout=900,
                         env={**os.environ, "PYTHONHASHSEED": hseed})
    line = next((l for l in out.stdout.splitlines() if l.startswith("RESULT ")), "")
    runs[name] = json.loads(line[7:]) if line else {"error": (out.stderr or out.stdout)[-1500:]}
a, b = runs["det439_a"], runs["det439_b"]
check("both sessions ran to the end", "all" in a and "all" in b, {k: v.get("error", "")[-600:] for k, v in runs.items() if "error" in v})
if "all" in a and "all" in b:
    check("a session of 40 inputs took them all, a rolled-back one included", a["steps"] >= 38 and a["turn"] > 20, (a["steps"], a["turn"]))
    first = next((i for i, (x, y) in enumerate(zip(a["after"], b["after"])) if x != y), None)
    check("the same save and the same lines end in the same state, in two processes", a["all"] == b["all"],
          f"they part after input {first + 1 if first is not None else '?'}")
    check("...after every input, not only at the end", a["after"] == b["after"], first)
    check("...and the player was shown the same words", a["shown"] == b["shown"] and a["lines"] == b["lines"], (a["lines"], b["lines"]))
for s in ("det439_base", "det439_a", "det439_b"):
    shutil.rmtree(f"saves/{s}", ignore_errors=True)
script.unlink(missing_ok=True)

# ---- the source keeps it so
RAND = {"random", "_r", "_random"}
FNS = {"random", "choice", "choices", "randint", "uniform", "shuffle", "sample", "randrange", "gauss", "triangular", "betavariate",
       "getrandbits", "seed"}
ENTROPY_OK = {"engine/ability_slots.py", "engine/ability_traits.py", "engine/field.py", "engine/lessons.py"}   # defaults kept for creation
UNSEEDED_OK = {"engine/look.py": 1}                         # the look rolled at character creation
SEED_OK = {"engine/streams.py"}                             # the one place the global module is seeded, as a bridge
found = []
for d in ("engine", "scenes", "npc", "services"):
    for p in sorted(pathlib.Path(d).rglob("*.py")):
        rel = p.as_posix()
        unseeded = 0
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id in RAND:
                if node.func.attr == "Random" and not node.args and not node.keywords:
                    unseeded += 1
                elif node.func.attr in FNS and rel not in SEED_OK:
                    found.append(f"{rel}:{node.lineno} rolls the global random module ({node.func.attr})")
            if isinstance(node, ast.Attribute) and node.attr == "SystemRandom" and rel not in ENTROPY_OK:
                found.append(f"{rel}:{node.lineno} draws from the machine's entropy")
            if isinstance(node, ast.Attribute) and node.attr in ("uuid4", "uuid1"):
                found.append(f"{rel}:{node.lineno} makes a uuid (use streams.new_id)")
            if isinstance(node, ast.BoolOp) and any(isinstance(v, ast.Name) and v.id == "random" for v in node.values):
                found.append(f"{rel}:{node.lineno} falls back to the global random module")
            if isinstance(node, ast.Call) and any(isinstance(x, ast.Name) and x.id == "random" for x in node.args):
                found.append(f"{rel}:{node.lineno} passes the random module as dice")
        if unseeded > UNSEEDED_OK.get(rel, 0):
            found.append(f"{rel}: {unseeded} unseeded random.Random()")
check("no unseeded generator, global roll, entropy draw or uuid in the game's code (use engine/streams.py)", not found, found[:8])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

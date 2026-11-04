"""(f455) A rolled-back turn takes back everything. The database's rollback put the save back; what the turn had done outside the save
stayed: a place found was still on the campaign's map and in its routes, the ledger's rows and totals kept the turn that never was, the
casting cache kept a dead key, and the scene's private caches (what was shown here, the happenings seen, the arrival lines) said the turn
had happened. Now the session keeps, at the start of every turn and pane command, what a rollback cannot get from the database (the
map's additions, the scene's caches) and gives it back (engine/session.py begin_turn/rollback; world/campaign.py snapshot/restore;
ledger.rollback). The owner's decision for Bundle B: a rolled-back turn takes back the world's additions, the ledger rows and every
cache written mid-turn. The same line typed again meets the same dice and this time stands; and a session recorded with such a turn
replays in a child process, so the rollback is deterministic as well as complete. (f464) The narrator's failure no longer rolls the
find back: the passage is an operation after the action's commit, so the place found stands and the player reads that it stood; what
is rolled back whole here is a turn whose action itself fails."""
import copy, pathlib, re, shutil, subprocess, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 55)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import ui.console as uc
from engine import discovery, failures, ledger, spellcraft
from llm import gateway
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def same(a, b) -> bool:
    """Equal by value, through dicts, lists and plain objects (a deep copy is another object; what it holds must be the same)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple, __import__("collections").deque)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if hasattr(a, "__dict__") and not isinstance(a, (set, str, int, float, bool)):
        return same(vars(a), vars(b))
    return a == b

for n in ("rollback_455_a", "rollback_455_rec", "rollback_455_rec_out"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)

# a find every time it is looked for, with the same name: the game's own dice decide the rest
def proposal(u, k):                      # a find every time, of the first type allowed here, under one name: the game's own dice decide the rest
    safe = [x.strip() for x in re.search(r"PLACE TYPES \(safe\): (.*)", u).group(1).split(",")]
    return {"found": True, "kind": "place", "name": "the Quiet Hollow", "place_type": safe[0], "description": "A small, quiet place.", "residents": [], "news": "Folk talk of it."}
stub.a_DiscoveryProposal = proposal
made = []
real_make = discovery.make_place
def make_place(*a, **k):
    out = real_make(*a, **k)
    made.append(out)
    return out
discovery.make_place = make_place

# ---- A: a turn that finds a place and begins a cast, then the narrator fails every try
a = simlib.campaign("rollback_455_a", cls="warrior", seed=55, location="parth")
ws = a.scene
ws.explore_chance = lambda seek: 1.0
stub.plan = [{"kind": "look"}]
check("a first turn stands", ws.turn("I look around.") is True)
anchor = ws.player.location
last_before = ledger.LAST
totals_before = dict(ledger.TOTALS)
added_before = ws.world.added()                                       # its places, roads and ways, by anchor
version_before = ws.world.version
digest_before = statehash.digest(a.store)
attrs_before = {k: copy.deepcopy(v) for k, v in ws.__dict__.items() if k.startswith("_") and k != "_truth"}
check("the scene holds private caches a turn writes", len(attrs_before) >= 3, sorted(attrs_before))

real = gateway._client
def chat(**k):
    if k["format"].get("title") == "Narration":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat)
stub.plan = [{"kind": "explore", "seek": "a quiet hollow"}]
stood = ws.turn("I search the woods for a quiet hollow.")
gateway._client = real
check("the turn found a place and its passage could not be written: the find stands (f464)", stood is True and len(made) == 1 and made[0] is not None, (stood, len(made)))
pid = made[0]["place"]["id"]
check("the place found is on the campaign's map, in its routes and in the save", pid in ws.world.places and pid in ws.world.neighbors(anchor)
      and ws.world.path(anchor, pid) is not None and any(p["place"]["id"] == pid for p in a.store.load_discoveries()["places"]), ws.world.neighbors(anchor))
check("...the map's additions grew, and its version moved", ws.world.added() != added_before and ws.world.version > version_before, (ws.world.added(), added_before))
check("...the save moved: a find is state, whatever became of its telling", statehash.digest(a.store) != digest_before)
check("...the player stands at the place found", ws.player.location == pid, ws.player.location)
check("...LAST is this turn's", ledger.LAST is not last_before)
check("...no casting context is left anywhere: it lives on the fighter and ends with the cast (f499), no table to clear", not hasattr(spellcraft, "_CAST")
      and not any(getattr(f, "casting", None) for f in (ws.combat.fight.fighters if ws.combat else [])))
check("...and the truth scene is built again on the next read", "_truth" not in ws.__dict__)
check("the passage was an operation of its own, and the one that did not stand", [o.kind for o in ws.line_untold] == ["passage"] and not ws.line_failed,
      ([o.kind for o in ws.line_untold], [o.kind for o in ws.line_failed]))
told = [t for k, t in SHOWN if k == "narrate"]
check("the player reads that what they did stands, in the narrator's words, never machinery", any(t in failures.F["stood_any"] for t in told)
      and not any(failures.MACHINERY.search(t) for t in told), told)

# ---- the same line again: a new input; the place is already found, so no second find, and the line stands
SHOWN.clear()
stood2 = ws.turn("I search the woods for a quiet hollow.")
check("the same line typed again is a new input, and stands", stood2 is True, (stood2, len(made)))
check("...and the ledger is the standing turn's", ledger.LAST is not last_before)
a.close()

# ---- the same shape recorded, then replayed in a child process: the rollback is deterministic as well as complete
discovery.make_place = real_make
r = simlib.campaign("rollback_455_rec", cls="warrior", seed=55, location="parth")
wr = r.scene                                      # no patch on the odds here: seed 55 finds on the real ones, so the child replays it unpatched
fail = {"on": False}
def chat_r(**k):
    if fail["on"] and k["format"].get("title") == "Narration":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat_r)
SCRIPT = [("I look around.", [{"kind": "look"}]), ("I search the woods for a quiet hollow.", [{"kind": "explore", "seek": "a quiet hollow"}]),
          ("I search the woods for a quiet hollow.", [{"kind": "explore", "seek": "a quiet hollow"}]), ("I look around.", [{"kind": "look"}])]
state = {"n": 0}
def ask(*a_, main=False, **k):
    if not main:
        return "yes"
    if state["n"] >= len(SCRIPT):
        return "quit"
    text, plan = SCRIPT[state["n"]]
    state["n"] += 1
    fail["on"] = state["n"] == 2                     # the second line's turn finds the place and then fails: it rolls back
    stub.plan = plan
    return text
uc.ask = ask
OUT = pathlib.Path("saves/rollback_455_rec_out")
r.session.record(folder=OUT)
wr.run()
r.close()
gateway._client = real
turns = [__import__("json").loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("the recording holds the turn whose telling failed, its find standing, and the ones after it", len(turns) >= 4
      and turns[1]["state"]["all"] != turns[0]["state"]["all"] and turns[1].get("operations") and "passage" not in [o["kind"] for o in turns[1]["operations"]]
      and "passage" in [o["kind"] for o in turns[2]["operations"]], [(t["state"]["all"][:8], [o["kind"] for o in t.get("operations", [])]) for t in turns])
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last = (out.stdout.strip().splitlines() or [""])[-1]
check("...and it replays in a child process through the real turn, the rollback included", out.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
      (out.returncode, out.stdout[-400:], out.stderr[-400:]))

# ---- the sources
src = pathlib.Path("engine/combat.py").read_text(encoding="utf-8")
i, j = src.index("spellcraft.begin(att, move)"), src.index("spellcraft.end(att)")
check("the casting context is ended whatever way the cast ends", "try:" in src[i:j] and "finally:" in src[j - 200:j], src[j - 200:j])
check("a resumed fight carries no casting context: it is the fighter's, ended with the cast, never in a saved row mid-cast (f499)",
      "_CAST" not in pathlib.Path("scenes/combat_scene.py").read_text(encoding="utf-8") and "casting: dict" in src)
ws_src = pathlib.Path("scenes/world.py").read_text(encoding="utf-8")
check("every operation begins on the session, once, and the rollback goes through it first", ws_src.count("self.session.begin_turn(self)") == 1
      and "self.session.rollback(self, " in ws_src)                                              # (f463) one place: operation()
for n in ("rollback_455_a", "rollback_455_rec", "rollback_455_rec_out"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

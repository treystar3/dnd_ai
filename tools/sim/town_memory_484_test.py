"""(f484) What a town remembers (Bundle D G3): one writer of a town's memory, its rows typed and undated, each kind with its own term and
cap in data, so thirty moments never push out what was settled within its month; past the month a settled matter is one lasting mark; a
moment is filed at its end even when the player has walked out of it, and each person who was there keeps it as their own, at
importance 1; a thousand rows leave the caps and the last costs no more than the first; SETTLED LATELY lists settlements, never a
moment; and the world's history and the moments seen are held to their caps at every append."""
import ast
import random
import shutil
import sys
import time
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 9)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import matters, moments, pulse, town_memory
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("town_memory_484", minutes=2000)
ws, store, world = game.scene, game.store, game.world
K = town_memory.kinds()

# ---- thirty moments never push out a settlement within its month
th = {"id": "s1", "title": "The Missing Ewes", "place": "parth", "clues": [], "sender": ""}
matters.remember(store, world, th, "settled", "Arwen", 2000, 1)
for i in range(30):
    town_memory.file(store, world, "parth", "moment", f"The night of the {i}th song", 2100 + i * 60)
rows = store.load_place("parth").memory
check("a settled matter is filed typed, its words undated, with its mark to come", any(r.get("kind") == "settled" and r["text"] == "The Missing Ewes: settled by Arwen"
      and r.get("mark") == "The Missing Ewes, settled by Arwen" and r["keep_until"] == 2000 + K["settled"]["days"] * 1440 for r in rows), rows[:2])
check("thirty moments later the settlement is still remembered", "The Missing Ewes: settled by Arwen" in town_memory.lines(store, world, "parth", 2100 + 30 * 60))
check("...and the moments are held to their own cap", sum(1 for r in rows if r.get("kind") == "moment") == K["moment"]["cap"])

# ---- after the month it is one lasting mark
later = 2000 + (K["settled"]["days"] + 1) * 1440
town_memory.sweep(store, world, "parth", later)
town_memory.sweep(store, world, "parth", later + 1440)
ps = store.load_place("parth")
check("past its month the detail goes and one lasting mark stays", ps.marks.count("The Missing Ewes, settled by Arwen") == 1
      and not any(r.get("kind") == "settled" for r in ps.memory) and "The Missing Ewes: settled by Arwen" not in town_memory.lines(store, world, "parth", later), ps.marks)
check("...the moments' shorter term over, they are gone too", not any(r.get("kind") == "moment" for r in ps.memory))

# ---- a moment walked out of is filed at its end, and those present keep it
spec = next(s for s in moments.M["shapes"] if s["id"] == "performer")
ws.player.location = "tilted_plough"                       # an inn in a town that keeps a memory (a field has none)
for i, nm in enumerate(["Ada Kell", "Bram Coyle", "Cass Wyn"]):
    store.save_npc(NPC(id=f"m{i}", name=nm, people="human", role="farmer", location=ws.player.location))
ws.present = [store.load_npc(f"m{i}") for i in range(3)]
m = moments.start(ws, spec, random.Random(5), use_model=False)
here = ws.player.location
check("the moment knows who was there when it began", m.get("present") == ["m0", "m1", "m2"], m.get("present"))
away = next(p for p in world.places if p != here and not world.places[p].danger and pulse.town_of(world, p) != pulse.town_of(world, here))
ws.player.location = away
store.meta.minutes = m["until"] + 5
moments.tick(ws)
st = store.load_place(here)
words = spec["written"]["memory"]
check("walked out of, the moment ends at its time all the same", not st.moment, st.moment)
check("...and is filed in its town's memory, a moment's row", any(r.get("kind") == "moment" and r["text"].lower().startswith(words.lower()[:20])
      for r in store.load_place(pulse.town_of(world, here)).memory), store.load_place(pulse.town_of(world, here)).memory)
kept = [[r for r in simlib.remembered(store, f"m{i}", kind="experienced") if "I was there for" in r["text"]] for i in range(3)]
check("each person who was there keeps it as their own, at importance 1", all(len(k) == 1 and k[0]["importance"] == 1 for k in kept), kept)
ws.player.location = here

# ---- a thousand rows leave the caps, and the last costs no more than the first
def burst(n0):
    t0 = time.perf_counter()
    for i in range(100):
        town_memory.file(store, world, "parth", "note", f"Note {n0 + i}", 900000 + n0 + i)
    return time.perf_counter() - t0
first = burst(0)
for b in range(1, 9):
    burst(b * 100)
last = burst(900)
mem = store.load_place("parth").memory
check("a thousand rows leave every kind within its cap", sum(1 for r in mem if r.get("kind") == "note") == K["note"]["cap"]
      and len(mem) <= sum(v["cap"] for k, v in K.items() if not k.startswith("_")), len(mem))
check("...and the last hundred cost no more than the first", last < first * 3 + 0.05, (first, last))

# ---- SETTLED LATELY lists settlements, never a moment
t = 3_000_000
matters.remember(store, world, {"id": "s2", "title": "The Cold Forge", "place": "parth", "clues": [], "sender": ""}, "settled", "Arwen", t, 2)
town_memory.file(store, world, "parth", "moment", "The brawl that ended with the watch dragging two men out", t + 10)
state = store.load_world_state() or pulse.empty_state(t)
ctx = pulse.context_for_place(store, world, ws.catalog, state, world.places["parth"], t + 20)
line = next((x for x in ctx.splitlines() if "SETTLED LATELY" in x), "")
check("SETTLED LATELY holds what was settled and no moment", "The Cold Forge" in line and "brawl" not in line, line)
check("...while the town's people still bring the moment up", any("brawl" in x for x in town_memory.lines(store, world, "parth", t + 20)))

# ---- the world's history and the moments seen held at every append; one writer for each, and for the town's memory
state = pulse.empty_state(0)
for i in range(pulse.P["history_keep"] + 50):
    pulse.add_history(state, f"line {i}", "parth", i)
check("the world's history is held to its cap at every append", len(state["history"]) == pulse.P["history_keep"] and state["history"][-1]["text"].endswith(str(pulse.P["history_keep"] + 49)))
loose = []
for d in ("engine", "scenes", "npc", "services"):
    for p in Path(d).rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and any(isinstance(x, ast.Attribute) and x.attr == "memory" for x in node.targets) and p.as_posix() != "engine/town_memory.py":
                loose.append(f"{p}:{node.lineno}")
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "append" and isinstance(node.func.value, ast.Subscript) \
                    and getattr(node.func.value.slice, "value", None) == "history" and p.as_posix() != "engine/pulse.py":
                loose.append(f"{p}:{node.lineno} history")
check("the town's memory and the world's history each have one writer", loose == [], loose)
check("the moments seen are capped in data", "seen_keep" in moments.M and "seen_keep" in Path("engine/moments.py").read_text())
game.close()
shutil.rmtree("saves/town_memory_484", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

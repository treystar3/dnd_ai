"""What the action interpreter is shown (engine/candidates.py): places by tier (named, this town, the ways out, the nearest of a kind,
the neighbours' insides, by meaning), never the whole world; people elsewhere only when named or close; a catalogue only when the
words are about it or name something in it. No model: the stub stands in, and the meaning check falls back to shared words."""
import sys, time
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from world.loader import load_world
from storage.campaign import NPCRow
from engine import candidates as C, mapview
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

w = load_world()
total = len(w.places)
names = lambda ps: [n for _, n in ps]
ids = lambda ps: [i for i, _ in ps]

ps = C.places(w, "parth", "look around")
check("from a hub town the interpreter sees a bounded list, not the world", 0 < len(ps) <= C.I["most_places"] < total, (len(ps), total))
check("...this town's own places come first", all(mapview.top_of(w, i) == "parth" for i in ids(ps)[:5]), names(ps)[:5])
check("...and never the place the player stands in", "parth" not in ids(ps))
ps = C.places(w, "parth", "travel to Riverhaven")
check("a far place the words name is in, first, with its town's places", ids(ps)[0] == "riverhaven" and "riverhaven_guild" in ids(ps)[:10] or names(ps)[0] == "Riverhaven", names(ps)[:3])
ps = C.places(w, "south_fields", "walk to the market")
check("from the fields, the neighbouring town and what is inside it are offered", "parth" in ids(ps) and any(mapview.top_of(w, i) == "parth" and i != "parth" for i in ids(ps)), names(ps))
ps = C.places(w, "south_fields", "go to the smithy")
check("'the smithy': the nearest few of that kind, wherever they are", sum(1 for i in ids(ps) if w.places[i].type == "smithy") >= 2 and len(ps) < 15, names(ps))
ps = C.places(w, "parth", "I want to go back to the Blackpine inn in Eldervale")
check("a town named in passing brings its inns and halls", "eldervale" in ids(ps) and sum(1 for i in ids(ps) if mapview.top_of(w, i) == "eldervale") >= 3, names(ps)[:8])
t = time.perf_counter()
for k in range(50):
    C.places(w, "parth", "walk over to the trading square and look at the stalls")
check("choosing the places is cheap", (time.perf_counter() - t) / 50 < 0.02, f"{(time.perf_counter() - t) / 50 * 1000:.1f} ms")

rows = [NPCRow("a1", "Odo Brant", "the clerk", True, "guild_clerk", "parth_guild", "known", True, "", "", 50, "", -1, False, False),
        NPCRow("a2", "Mira Tallow", "", False, "baker", "parth_market", "background", True, "", "", 50, "", -1, False, False),
        NPCRow("a3", "Hal Greaves", "", True, "smith", "riverhaven", "known", True, "", "", 50, "", -1, False, False)]
check("people elsewhere: nobody is listed for words that name nobody", C.people_elsewhere(rows, "look around") == [])
got = C.people_elsewhere(rows, "go and find Odo at the guild")
check("...the one the words name is", [r.id for r in got] == ["a1"], [r.id for r in got])
got = C.people_elsewhere(rows, "ask the baker about bread")
check("...a role word finds them too", [r.id for r in got] == ["a2"], [r.id for r in got])

wares = ["bread from a2: a loaf - two copper", "ale from a2: a mug - one copper", "rope from a4: ten fathoms", "lamp oil from a4", "a whetstone from a4"]
check("a catalogue the words are not about is left out", C.catalogue("I pick up a rock", "wares", wares, 4) == [])
check("...one the words name something in comes in whole", C.catalogue("buy some rope", "wares", wares, 4) == wares)
check("...a short one always comes in", C.catalogue("I pick up a rock", "wares", wares[:3], 4) == wares[:3])
check("...'buying' is judged by meaning against the sentence for that kind (by shared words without the helper model)",
      C.catalogue("I would like to buy something for sale here", "wares", wares, 4) == wares)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)

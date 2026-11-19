"""(f704) A climb made for the view shows what is really there to see (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). "I climb up onto the standing wall to get a view across the marsh." worked, but the view held
nothing the game knows: no landmark, no way on. A height looked out from is the explorer's oldest move.
Held here: a climb that works, whose words look out (improv.yaml effects.climb changes vantage: view_words), from open ground (from),
out of a delve, by day, makes out the nearest places that can be seen from outside (seen: never under the ground) within its walk, the
ones not heard of first, each with its direction and its walk; those are on the map now and the passage is told them; a climb with no
wish to look, one at night, one from indoors, and one that failed show nothing; a plain-yes climb keeps its "It works" line (f703).
Run: python tools/sim/vantage_704_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import clock, world_improv as wi

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("vantage_704", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
real_read = wi.read_effect
wi.read_effect = lambda words: "climb"
spec = next((c for c in wi.W["effects"]["climb"].get("changes") or [] if c.get("kind") == "vantage"), {})
check("(the climb's vantage is declared in improv.yaml)", bool(spec) and spec.get("minutes") and spec.get("most") and spec.get("from"), spec)
while clock.is_dark(ws.minutes):
    ws.store.meta.minutes += 60
day = ws.minutes
UP = "I climb the tallest pine to get a view over the forest"


def look(words=UP, degree="success", minutes=None):
    ws.store.meta.minutes = minutes if minutes is not None else day
    ws.player.heard, ws.player.visited = [], ["greywood"]
    return wi.land(ws, words, degree)


told = look()
heard = set(ws.player.heard)
seen_types = set(spec.get("seen") or ())
check("a climb for the view, by day, puts places that can be seen on the map", heard and all(ws.world.places[p].type in seen_types for p in heard), heard)
check("...never a place under the ground", not any(ws.world.places[p].type == "underground" for p in heard), heard)
names = [ws.world.places[pid].name for pid in heard]
check("...and the passage is told each with its direction and walk", told and all(n in told[-1] for n in names) and "to the " in told[-1], told)
told = look("I climb over the fence to get away from the boar")
check("a climb with no wish to look shows nothing", not ws.player.heard and not any("make out" in t for t in told), (ws.player.heard, told))
night = day
while not clock.is_dark(night):
    night += 60
told = look(minutes=night)
check("...nor one in the dark", not ws.player.heard, ws.player.heard)
told = look(degree="failure")
check("...nor a climb that failed", not ws.player.heard, ws.player.heard)
inn = next(pid for pid, p in ws.world.places.items() if p.type == "inn")
ws.player.location = inn
told = look()
check("...nor one from indoors", not ws.player.heard, ws.player.heard)
ws.player.location = "greywood"
wi.read_effect = real_read
g.close()
shutil.rmtree("saves/vantage_704", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

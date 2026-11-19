"""(f708) A line naming a real place of the world as where to go is a step, never a reply to the hire who spoke last (found in the
third blind play, 2026-11-16: docs/play/2026-11-16_blind_play_journal.md). Morm asked what we expected to find; "Start the trek to
Ironvein." went to him as chat ("intercept: hire took the line"), the party talked of leaving, and nobody moved. The followup's own
command list did not hold "start" or "trek", and no list of verbs can hold every way of saying it.
Held here: after a hire speaks, a line that is not a question and names a place of the world other than here after to / toward /
for / into, in any wording (named to the hire or not), falls to the reader; a question about a place, and replies with no place in them, stay theirs.
Run: python tools/sim/hire_goes_708_test.py"""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import mapview

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("hire_goes_708", seed=3, turn=4, location="trading_square")
ws, store, world = g.scene, g.store, g.scene.world
ws.enter("trading_square")
ws.player.party = [{"id": "h1", "name": "Morm Wooddale", "role": "priest", "level": 3, "permanent": True, "temper": ["dry"], "blurb": "a priest"}]
ws.player.party_mode = "with"
far = next(p for pid, p in world.places.items() if p.type == "town" and pid != "parth" and pid != ws.player.location)


def after_morm(line):
    ws._hire_last = ("Morm Wooddale", store.meta.turn - 1)
    return ws.hire_followup(line)


for line in (f"Start the trek to {far.name}.", f"Time we made for {far.name}", f"On toward {far.name}, then.",
             f"Back to {far.name}.", f"The long road for {far.name} it is.", f"Back to {far.name}'s gate."):
    check(f"a step, not chat for the hire: {line!r}", after_morm(line) is None)
for line in (f"What do you know of {far.name}?", "tell me more", "fair enough", "I think we press on soon enough, friend",
             "To be honest, I am tired.", "Thanks for the great help", "Yes, for the grey one", "Not for the water, no",
             "for the first time in years", "I owe it to the royal guard", "it belongs to the hollow folk",
             f"Here's to {world.places[mapview.top_of(world, ws.player.location)].name}!"):
    check(f"...still theirs: {line!r}", after_morm(line) is not None)
here_top = mapview.top_of(world, ws.player.location)
part = next(p for pid, p in world.places.items() if p.type != "road" and mapview.top_of(world, pid) not in (pid, here_top)
            and not p.name.lower().removeprefix("the ").startswith(world.places[mapview.top_of(world, pid)].name.lower()))
check(f"a part of another town is not walked to by its name alone ({part.name!r})", after_morm(f"For {part.name}, then.") is not None)
town_part = next(p for pid, p in world.places.items() if mapview.top_of(world, pid) not in (pid, here_top)
                 and p.name.lower().removeprefix("the ").startswith(world.places[mapview.top_of(world, pid)].name.lower()))
check(f"...while one whose name opens with its town's is that town, walked to ({town_part.name!r})", after_morm(f"For {town_part.name}, then.") is None)

ws._hire_last = None
store.meta.turn += 1
for line, gone in ((f"Morm, start the trek to {far.name}.", True), (f"Morm, let's head to {far.name}.", True),
                   ("Morm, how are your feet holding up?", False)):
    check(f"named: {line!r} is {'a step' if gone else 'theirs'}", (ws.hire_wants_talk(line) is None) == gone)

from scenes import world_prompts as wp
seen = {}
real = wp.interpret_request
def spy(*a, **k):
    seen["last"] = a[6]
    raise RuntimeError("enough")
wp.interpret_request = spy
ws._hire_last = ("Morm Wooddale", store.meta.turn - 1)
ws.hire_people = lambda: [("hire:0-0", "Morm Wooddale", "a priest", "standing by")]
try:
    ws.interpret("I've been to the far towns before.", "")
except Exception:
    pass
wp.interpret_request = real
check("a line that falls through after a hire spoke is read with that hire as the one last spoken to", seen.get("last") == "hire:0-0", seen)
g.close()
shutil.rmtree("saves/hire_goes_708", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

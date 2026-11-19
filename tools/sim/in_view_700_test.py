"""(f700) A creature the game holds in view is told to every passage while it stays (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). In the Grey Mountains, after `I follow the hoof prints.` the game held an elite pegasus in
view, but the passage showed only tracks and a tuft of hair; the pegasus was told once, in the sighting's own passage, and every later
passage's people were told without it (people_view leaves wildlife out). And a search that found nothing handed the narrator the
creature's name with "fresh signs of" it, and passages showed the creature itself (the awakened tree).
Held here: while a creature is in view, every passage's request carries it, plainly named, as IN VIEW; with none in view there is no
such line; a search that finds nothing says the creature itself is not here and is not seen.
Run: python tools/sim/in_view_700_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import combat, encounters
from llm.contracts import ActionIntent as A, Narration
import scenes.world as W

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("in_view_700", seed=5, location="greywood")
ws = g.scene
ws.enter("greywood")
asked = []
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: (asked.append((task, request)), Narration(text="The wind moves the grass."))[1] \
    if task == "narrate" else real_fresh(task, system, request, *a, **k)
wolf = ws.world.bestiary["wolf"]
ws.wildlife = (wolf, [combat.fighter_from_creature(wolf, 3, "elite", "e1", "wolf (elite)", "near")])
asked.clear()
ws.narrate("The player looks around.", "I look around.")
req = asked[-1][1] if asked else ""
check("a creature in view is told to a later passage, plainly named", "IN VIEW" in req and "wolf" in req.split("IN VIEW", 1)[-1][:120]
      and "(elite)" not in req, req[:600])
ws.wildlife_at = ws.minutes
ws.advance(30)
check("half an hour on, it is still in view", ws.wildlife is not None)
ws.advance(40)
check("past the window kept in data (combat.yaml in_view_minutes), it has moved on", ws.wildlife is None, ws.wildlife)
asked.clear()
ws.narrate("The player looks around.", "I look around.")
check("...and the next passage is told nothing in view", asked and "IN VIEW" not in asked[-1][1])
ws.wildlife, ws.wildlife_at = (wolf, [combat.fighter_from_creature(wolf, 3, "normal", "e1", "wolf", "near")]), ws.minutes
ws.on_wait(A(kind="wait", wait_until="dawn", summary="sleep"), "I sleep until dawn.")
check("a night's sleep outlasts it: nothing is in view on waking", ws.wildlife is None)
from scenes import world_prompts as wp
place = ws.place
check("a dialogue frame is told the creature in view too",
      "IN VIEW" in wp.dialogue_request("noon", place, [], "the smith", "", "", "", False, "hi", "hello", "", False, [], in_view=["wolf"]))
check("...and an exchange among the party", "IN VIEW" in wp.exchange_request("noon", place, ["Pae"], [], "a", "b", [], "", in_view=["wolf"]))
ws.wildlife = None
asked.clear()
ws.narrate("The player looks around.", "I look around.")
check("with none in view, there is no such line", asked and "IN VIEW" not in asked[-1][1])
real_roll = encounters.roll
encounters.roll = lambda *a, **k: None
asked.clear()
ws.on_search(A(kind="search", seek="wolf"), "I search for wolves.")
encounters.roll = real_roll
miss = asked[-1][1] if asked else ""
check("a search that finds nothing says the creature itself is not here and is not seen", "itself is not here and is not seen" in miss, miss[-500:])
W.fresh = real_fresh
g.close()
shutil.rmtree("saves/in_view_700", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

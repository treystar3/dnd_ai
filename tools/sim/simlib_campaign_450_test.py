"""(f450) simlib.campaign(): the suite's one way to open a campaign (the owner's decision for Bundle B: a shared helper lands first, and
WorldScene(store, world, catalog, player) keeps working through it, so a change to the runtime's shape is a change to the helper's inside
and never to a hundred tests). Two games open in one process are two campaigns: their own stores, worlds and players; the scene is built
on the helper's own; close() closes the store and leaves no background work of that save behind. The four tests that already opened a
campaign the Stage 0 way are on the helper, and the stale copy of simlib under tools/sim is gone: every test imports the one at the root."""
import pathlib, random, sqlite3, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 50)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from npc import backfill

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

a = simlib.campaign("simlib_campaign_450_a", seed=50, minutes=600)
b = simlib.campaign("simlib_campaign_450_b", cls="mage", seed=51, minutes=720, turn=3, location="trading_square")
check("two campaigns opened in one process are two: their own stores, worlds and players",
      a.store is not b.store and a.world is not b.world and a.player is not b.player
      and a.store.meta.seed == 50 and b.store.meta.seed == 51 and b.store.meta.minutes == 720 and b.store.meta.turn == 3, (a.store.meta.seed, b.store.meta.seed))
check("...standing where the world starts, or where the test says", a.player.location == a.world.start_location and b.player.location == "trading_square",
      (a.player.location, b.player.location))
check("...as the class asked for, with Maren kept away", a.player.character.custom_class != b.player.character.custom_class
      and a.player.mentor.get("never") is True, (a.player.character.custom_class, b.player.character.custom_class))
ws_a, ws_b = a.scene, b.scene
check("the scene is built on the helper's own store, world and player, once", ws_a.store is a.store and ws_a.world is a.world and ws_a.player is a.player
      and a.scene is ws_a and ws_b.store is b.store)
stub.plan = [{"kind": "look"}]
check("...and plays a turn", ws_a.turn("I look around.") is True and ws_b.turn("I look around.") is True and a.store.meta.steps == 1 and b.store.meta.steps == 1,
      (a.store.meta.steps, b.store.meta.steps))
a.close()
try:
    a.store.load_player()
    closed = False
except sqlite3.ProgrammingError:
    closed = True
check("close() closes the store", closed)
check("...and leaves no background work of that save pending", not backfill.pending(store=a.store))
check("...while the other campaign plays on", ws_b.turn("I look around again.") is True and b.store.meta.steps == 2)
b.close()

again = simlib.campaign("simlib_campaign_450_b", fresh=False)
check("fresh=False opens a save as it stands: the same character, the clock where it was left", again.player.character.name == b.player.character.name
      and again.store.meta.steps == 2 and again.store.meta.seed == 51, (again.store.meta.steps, again.store.meta.seed))
again.close()
same = simlib.campaign("simlib_campaign_450_c", seed=7), simlib.campaign("simlib_campaign_450_d", seed=7)
check("the same seed makes the same character", same[0].player.character.attributes == same[1].player.character.attributes
      and [x.name for x in same[0].player.character.actives] == [x.name for x in same[1].player.character.actives])
for g in same:
    g.close()
for n in ("a", "b", "c", "d"):
    import shutil
    shutil.rmtree(f"saves/simlib_campaign_450_{n}", ignore_errors=True)

# ---- the four tests already on the Stage 0 seam are on the helper, and the stale simlib is gone
SCENE = "WorldScene" + "("
moved = ["outage_line_437_test.py", "recorder_440_test.py", "hazard_ruled_447_test.py", "determinism_439_test.py"]
for t in moved:
    src = pathlib.Path("tools/sim", t).read_text(encoding="utf-8")
    check(f"{t} opens its campaign through the helper and no other way", "simlib.campaign(" in src and "campaign_world" not in src and SCENE not in src)
check("the stale copy of simlib under tools/sim is gone: every test imports the one at the root", not pathlib.Path("tools/sim/simlib.py").exists()
      and pathlib.Path(simlib.__file__).resolve().parent == pathlib.Path(".").resolve())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)

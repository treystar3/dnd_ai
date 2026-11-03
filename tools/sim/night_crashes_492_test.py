"""(f492) Two faults the baseline night (pod night 20261103_0520) stopped on, each rolled back twelve turns running until the run ended:
- a walk on from a road stop met a new stop, the old stop was tidied away (f423, f426), and the line "or back to ..." then named the
  stop just tidied, KeyError, every time the player tried to go on;
- the understanding read what lies on the ground, and the read saved the place to drop what had lain too long, a write outside any
  operation with the fence armed (f470), WriteOutsideOperation, every time the player searched there.
The night called both "the model stopped answering": a fault of the game's own is named as one now, in each run's own crash.log."""
import inspect
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("summoner", 15))
shown = simlib.quiet_console()
import scenes.road_actions as ra
from engine import inventory as inv, matters, roads
from storage.campaign import WriteOutsideOperation

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("night_crashes_492", cls="summoner", seed=15, location="parth")
ws, world, store = game.scene, game.world, game.store
ws.enter("parth")

# ---- a walk on from a stop meets a new stop: the line names the new stop's own ends, real places
first = roads.make_stop(world, "parth", "riverhaven", 0.5, 120, "x", "", "Wolves")
ws.player.road = first
ws.ensure_road_place()
ws.enter(first["id"])
kinds, hostile = dict(ra.R["kinds"]), ra.R["hostile"]
ra.R["kinds"], ra.R["hostile"] = {"meeting": 1}, 0
real_matter = matters.road_matter
matters.road_matter = lambda *a, **k: None
shown.clear()
try:
    out = ws.road_event([first["id"], "riverhaven"], first["id"], "riverhaven", 60, 0.5, "I walk on.", [], walked=30)
    err = None
except KeyError as e:
    out, err = None, e
finally:
    ra.R["kinds"], ra.R["hostile"] = kinds, hostile
    matters.road_matter = real_matter
note = next((t for k, t in shown if k == "note" and t.startswith("You stop here")), "")
check("a walk on from a road stop that meets a new stop raises nothing, and stops", err is None and out == "stopped", (out, repr(err)))
check("...the old stop is tidied away and the player stands at the new one", first["id"] not in world.places
      and ws.player.road and ws.player.road["id"] != first["id"] and ws.player.location == ws.player.road["id"], ws.player.location)
check("...and the line names the new stop's own ends, the towns, never the stop just tidied",
      note == f"You stop here, on the road. Onward to {world.places['riverhaven'].name}, or back to {world.places['parth'].name}.", note)
ws.leave_road("parth")
ws.enter("parth")

# ---- what lies here is read, never written: with the fence armed and no operation open, asking is no fault
import random
from engine import loot
old_item, new_item = loot.make_drop(1, "common", random.Random(1)), loot.make_drop(1, "common", random.Random(2))
state = store.load_place("parth")
state.ground = [{"item": old_item.model_dump(), "minute": ws.minutes - 4 * 1440}, {"item": new_item.model_dump(), "minute": ws.minutes - 60}]
store.save_place(state)
store.arm(True)
try:
    seen, err = ws.ground_here(), None
except WriteOutsideOperation as e:
    seen, err = [], e
store.arm(False)
check("what lies here is read with the fence armed and no operation open, and nothing is written", err is None, repr(err))
check("...what has lain too long is left out of the answer", [i.uid for i in seen] == [new_item.uid], [i.uid for i in seen])
check("...and stays in the row until the ground is next written", len(store.load_place("parth").ground) == 2)
state = store.load_place("parth")
inv.leave_on_ground(state, loot.make_drop(1, "common", random.Random(3)), ws.minutes)
check("leaving something on the ground drops what has lain too long", len(state.ground) == 2
      and old_item.uid not in [g["item"]["uid"] for g in state.ground], [g["item"]["uid"] for g in state.ground])
game.close()
shutil.rmtree("saves/night_crashes_492", ignore_errors=True)

# ---- the night names a fault of the game's own as one, in the run's own crash.log
import nightrun
out = Path("saves/night_crashes_492_run")
shutil.rmtree(out, ignore_errors=True)
out.mkdir(parents=True)
run = nightrun.Run(out, 1, 0, live=False)
run.hesitations, run.crash_streak = 12, 12
said = [run.done()]
run.crash_streak = 5
said.append(run.done())
run.crash_streak = 0
said.append(run.done())
for f in (run.turn_file, run.transcript, run.errors):
    f.close()
check("twelve turns the game failed on its own fault are named as that, not as the model",
      said[0] == "the game failed 12 turns in a row on its own fault (crash.log)", said[0])
check("...a mix says how many were the game's, and the model's own silence keeps its words",
      "5 of them the game's own fault" in said[1] and said[2] == "the model stopped answering (12 turns failed in a row)", said[1:])
check("...and each run keeps its faults in its own folder", 'config.CRASH_LOG_PATH = str(out / "crash.log")' in inspect.getsource(nightrun.main))
shutil.rmtree(out, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

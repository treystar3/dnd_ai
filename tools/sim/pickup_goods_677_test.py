"""(f677) Taking up one of the game's own goods that does not lie here is refused by the engine, never told as done (found in the second
blind play: docs/play/2026-11-16_blind_play_journal.md). After the bear hides were given to the clerk, `I take the bear hides back
from Emlily's counter` was narrated as done ("You lift the thick skins from Emlily's counter") while nothing came into the pack: a
pick-up that finds no item went to the scenery passage, which leaves it to the model whether such a thing "would plausibly be here".
Held here: a good or a raw material named and not lying here is refused, nothing narrated as taken; one lying here is taken as
before; an ordinary bit of the place (a stone) still goes to the scenery passage.
Run: python tools/sim/pickup_goods_677_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import inventory as inv, ledger
from llm.contracts import ActionIntent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("pickup_goods_677_test", seed=3, minutes=900)
ws, store = g.scene, g.store
told = []
ws.narrate = lambda what, text="", *a, **k: told.append(what)


def pick(thing):
    told.clear()
    before = len([r for r in ledger.this_turn() if r.get("kind") == "refused"])
    ws.on_pick_up(ActionIntent(kind="pick_up", item=thing), f"I pick up the {thing}.")
    return len([r for r in ledger.this_turn() if r.get("kind") == "refused"]) > before


for thing in ("bear hides", "silverleaf"):
    n = len(ws.pack)
    refused = pick(thing)
    check(f"'{thing}' not lying here: refused, nothing narrated as taken, nothing in the pack", refused and not told and len(ws.pack) == n,
          (refused, told, len(ws.pack)))

said = []
ws.refuse = lambda say, *a, **k: said.append(say)
pick("the bear hides")
check("(f680) the refusal names the good in its own words, never the line's", said and "bear hide " in said[-1] + " " and "the bear hides" not in said[-1]
      and "hides lies" not in said[-1], said)
del ws.refuse
state = store.load_place(ws.player.location)
inv.leave_on_ground(state, inv.make_good("silverleaf", 2), ws.minutes)
store.save_place(state)
refused = pick("silverleaf")
check("one lying here is taken as before", not refused and inv.count_of(ws.pack, "silverleaf") == 2, (refused, inv.count_of(ws.pack, "silverleaf")))
refused = pick("smooth stone")
check("an ordinary bit of the place still goes to the scenery passage", not refused and told, (refused, told))
shutil.rmtree("saves/pickup_goods_677_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

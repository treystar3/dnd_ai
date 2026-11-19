"""(f656) A room bought by a line that says the player sleeps is slept in (docs/design/21_play_faults_plan.md, B2; found in play:
docs/play/2026-11-15_play_findings.md 4.9, "I pay the 52 copper for a room and we sleep until morning" paid and did not sleep). The buy
kind claims "sleep" and "rest" (a room is bought to sleep in), so the reading gives one buy and the sleep is lost; "I sleep at the inn"
paid for a room and never slept either. Held here: when the plan has no wait of its own, the room bought is slept in, until the time
the line names or, at night, until morning; a room bought with no sleep said is only bought, and a wait the reading gave is not doubled.
Run: python tools/sim/room_sleep_656_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from engine import clock, pools
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("room_sleep_656_test", seed=8, location="trading_square")
ws = g.scene
ws.enter("tilted_plough")
ws.player.character.coins = 10 ** 4
keeper = next((n for n in ws.present if n.role == "innkeeper"), None)
check("(the inn at Parth has its keeper)", keeper is not None)


def evening():
    """The clock to the next evening, the player hurt, no room held."""
    ws.advance(clock.minutes_until(ws.minutes, "evening"))
    ws.player.room, ws.player.room_until = "", 0
    c = ws.player.character
    c.health = pools.maximum(c, "health") * 0.4


def buy(text, plan_more=()):
    step = A(kind="buy", target=keeper.id, ware="room")
    ws.plan_now = [step, *plan_more]
    before, coins = ws.minutes, ws.player.character.coins
    ws.on_buy(step, text)
    c = ws.player.character
    return {"paid": coins - ws.player.character.coins, "waited": ws.minutes - before, "period": clock.period(ws.minutes),
            "health": round(pools.current(c, "health") / pools.maximum(c, "health"), 2)}


if keeper:
    evening()
    got = buy("I pay the 52 copper for a room and we sleep until morning")
    check("the journal's line: the room is paid for and slept in, until morning, and the player wakes rested",
          got["paid"] > 0 and got["period"] == "morning" and got["health"] == 1.0, got)
    evening()
    got = buy("I sleep at the inn tonight")
    check("'I sleep at the inn' read as the room: the room is slept in", got["paid"] > 0 and got["waited"] >= 360 and got["health"] == 1.0, got)
    evening()
    got = buy("I rent a room and turn in for the night, till dawn")
    check("...until the time the line names", got["paid"] > 0 and got["period"] == "dawn", got)
    evening()
    got = buy("I rent a room for the night")
    check("a room bought with no sleep said is only bought: no time passes, the player is not rested",
          got["paid"] > 0 and got["waited"] < 60 and got["health"] < 1.0, got)
    evening()
    got = buy("I rent a room and sleep until morning", (A(kind="wait", wait_until="morning"),))
    check("a wait the reading gave is its own step: the room does not sleep it as well", got["paid"] > 0 and got["waited"] < 60, got)
shutil.rmtree("saves/room_sleep_656_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

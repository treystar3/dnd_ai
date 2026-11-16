"""(f695) A sleep that asks for a room takes one, and the rest's passage is told where the sleeper slept (found in the second blind
play: docs/play/2026-11-16_blind_play_journal.md). At Ironvein, "We take rooms at the inn and sleep until morning." was read as a walk
to the inn and a sleep; no room was bought, the game said "You rested, but not as you would in a bed", and the passage said "You settle
into bed alongside your companions". f656 made a room bought with words of sleep slept in; the other way round was missing, and the
narrator was never told there was no bed.
Held here: a sleep whose line asks for a room (improv.yaml room_words), where rooms are sold and none is held, buys the room first and
the sleep is a full night's; with no room asked for, or no coin, it is a rest with no bed, and the passage is told so; a room already
held is slept in and not bought again; "bed down by the fire" asks for no room.
Run: python tools/sim/room_sleep_695_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import clock, pools
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "room_sleep_695"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="tilted_plough")
ws, store = g.scene, g.store
ws.enter("tilted_plough")
SAID = []
ws.narrate = lambda event, text="", *a, **k: SAID.append(event)
seller = next((n for n in ws.present if any(w.kind == "room" for w in ws.wares_of(n))), None)
check("(someone here lets rooms)", seller is not None, [(n.id, n.role) for n in ws.present])
M0 = store.meta.minutes


def sleep(line, coins=500, room=False):
    store.meta.minutes = M0
    c = ws.player.character
    c.coins = coins
    c.health = 1
    ws.player.room, ws.player.room_until = ("tilted_plough", M0 + 2000) if room else ("", 0)
    SAID.clear()
    ws.on_wait(A(kind="wait", wait_until="dawn", summary="sleep until morning"), line)
    return c, " ".join(SAID)


c, said = sleep("We take rooms at the inn and sleep until morning.")
check("a sleep that asks for a room takes one: paid, and the room is held", c.coins < 500 and ws.player.room == "tilted_plough", (c.coins, ws.player.room))
check("...and the passage is told they slept in their room", "room" in said.lower() and "no bed" not in said.lower(), said[:300])
c, said = sleep("I get a bed for the night and sleep.")
check("'a bed for the night' asks for a room too", c.coins < 500 and ws.player.room == "tilted_plough", c.coins)
c, said = sleep("We sleep until morning.")
check("a sleep that asks for no room buys none", c.coins == 500 and ws.player.room != "tilted_plough", (c.coins, ws.player.room))
check("...and the passage is told there was no bed", "no bed" in said.lower(), said[:300])
c, said = sleep("I bed down by the fire until morning.")
check("'bed down by the fire' asks for no room", c.coins == 500, c.coins)
for line in ("I sleep on a bench in the common room until morning.", "I cannot afford a room, so I sleep in the stable until morning.",
             "I make room by the hearth and sleep until morning.", "I sleep on a bed of straw in the stable until morning.",
             "The rooms upstairs are full, so I sleep by the fire until morning.", "I don't want a room; I sleep by the fire until morning."):
    c, said = sleep(line)
    check(f"a room or bed named but not asked for buys none: '{line}'", c.coins == 500, c.coins)
c, said = sleep("We take rooms at the inn and sleep until morning.")
check("the room taken is kept in the turn's record under its rule's name", any(r.get("rule") == "room_for_sleep" for r in (ws.repairs or [])),
      ws.repairs)
c, said = sleep("We sleep until morning.")
check("a sleep with no room is told so, with nothing invented around it", "no bed" in said.lower() and "bench" not in said.lower(), said[:300])
c, said = sleep("We take rooms and sleep until morning.", coins=0)
check("with no coin for it, no room: a rest with no bed, told so", ws.player.room != "tilted_plough" and "no bed" in said.lower(), said[:300])
c, said = sleep("We take rooms and sleep until morning.", room=True)
check("a room already held is slept in and not bought again", c.coins == 500 and "room" in said.lower(), (c.coins, said[:200]))

g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f730) A room already held is no refusal (found by the live gate's script, 17 November: with a room taken at the Tilted
Plough, "I sleep until morning." was read as taking a room and waiting until morning; the game answered "You already have a room
here until mid-morning tomorrow. No charge." as a refusal, the steps after it were dropped, and nobody slept). Asking for what
is already theirs is not something the game says no to: they are told it is theirs at no charge, and the rest of the line goes
on. A sleep after it is slept, in the room; a word with the innkeeper after it is had; a line of the room alone costs nothing
and passes no time. The room they hold is looked at before any price or purse: an empty purse does not stop them sleeping in
it. The same holds for another thing of the kind, a house already owned where one is asked for.
Run: python tools/sim/room_held_730_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
import ui.console as uc
from engine import ledger
from engine import property as prop

bad = []
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(str(m)))


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = "room_held_730"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="tilted_plough")
ws, store = g.scene, g.store
ws.enter("tilted_plough")
seller = next((n for n in ws.present if any(w.kind == "room" for w in ws.wares_of(n))), None)
check("(someone here lets rooms)", seller is not None, [(n.id, n.role) for n in ws.present])
BUY = {"kind": "buy", "target": seller.id, "ware": "room", "summary": "taking a room for the night"}
TALKS, REFUSED = [], []
uc.put("dialogue", lambda before, who, speech, after="": TALKS.append((who, speech)))
uc.put("say", lambda t, s="": TALKS.append((s, t)))


def play(line, plan, room=True, coins=500, held=None):
    """One typed line through the real turn, the room held or not: (minutes passed, coins spent, the notes shown). REFUSED: what
    the turn's record says the game said no to."""
    c = ws.player.character
    c.coins = coins
    ws.player.room, ws.player.room_until = ("tilted_plough", ws.minutes + 2000) if room else ("", 0)
    if held:                                                     # (where, how long from now)
        ws.player.room, ws.player.room_until = held[0], ws.minutes + held[1]
    store.save_player(ws.player)
    NOTES.clear()
    TALKS.clear()
    before = ws.minutes
    stub.plan = [dict(p) for p in plan]
    ws.turn(line)
    REFUSED[:] = [r for r in ledger.last() if r.get("kind") == "refused"]
    return ws.minutes - before, coins - ws.player.character.coins, list(NOTES)


WAIT = {"kind": "wait", "wait_until": "morning", "summary": "sleeping until morning"}
passed, spent, notes = play("I take a room for the night, then ask the innkeeper how the roads are.",
                            [BUY, {"kind": "talk", "target": seller.id, "speech": "How are the roads?", "summary": "asking about the roads"}])
check("a word with the innkeeper after it is had: the room they hold does not stop the line",
      any(speech for who, speech in TALKS if "innkeeper" in str(who).lower()) and spent == 0 and passed < 360 and not REFUSED, (TALKS, notes, REFUSED))

passed, spent, notes = play("I sleep until morning.", [BUY, WAIT])
check("with a room already theirs, a line read as taking a room and sleeping is slept: hours pass", passed >= 360, (passed, notes))
check("...nothing is charged, and they are told the room is theirs already", spent == 0 and any("already have a room" in n for n in notes), (spent, notes))
check("...and the turn's record has nothing the game said no to", not REFUSED, REFUSED)

from engine import clock
ws.player.free_room_day = clock.day(ws.minutes)
passed, spent, notes = play("I take a room for the night.", [BUY])
check("nothing is quoted for what is theirs: a free night they have earned is not offered for the room they hold",
      any("already have a room" in n for n in notes) and not any("yours tonight" in n for n in notes), notes)
ws.player.free_room_day = -1

passed, spent, notes = play("I take a room for the night and sleep until morning.", [BUY])
check("read as the room alone, the words of sleep are still slept in the room they hold (f656's rule, for a room already theirs)", passed >= 360 and spent == 0, (passed, spent, notes))

passed, spent, notes = play("I take a room for the night.", [BUY])
check("a line of the room alone costs nothing, tells them it is theirs and is no refusal", spent == 0 and any("already have a room" in n for n in notes) and not REFUSED,
      (spent, notes, REFUSED))

passed, spent, notes = play("I sleep until morning.", [BUY, WAIT], coins=0)
check("with an empty purse the room they hold is still slept in: nothing is quoted, nothing is unaffordable",
      passed >= 360 and not REFUSED and not any("afford" in n.lower() for n in notes), (passed, notes, REFUSED))

passed, spent, notes = play("I sleep until morning.", [BUY, WAIT], room=False)
check("with no room held the same line pays for one, once, and sleeps (as before)", spent > 0 and passed >= 360 and not any("already have a room" in n for n in notes), (passed, spent, notes))

passed, spent, notes = play("I take a room for the night.", [BUY], held=("guild_house", 2000))
check("a room held somewhere else is not a room here: one is paid for", spent > 0 and not any("already have a room" in n for n in notes), (spent, notes))

passed, spent, notes = play("I take a room for the night.", [BUY], held=("tilted_plough", -10))
check("a room whose night is over is theirs no longer: one is paid for", spent > 0 and not any("already have a room" in n for n in notes), (spent, notes))

passed, spent, notes = play("I take two rooms for the night and sleep until morning.", [dict(BUY, count=2), WAIT], room=False)
check("a step the game does say no to still stops the steps that rest on it: two rooms are refused and nobody sleeps",
      spent == 0 and passed < 360 and len(REFUSED) == 1, (passed, spent, notes, REFUSED))

# ---- another case of the kind: a house already theirs
town = "cinderhold"
store.meta.minutes = (ws.minutes // 1440 + 1) * 1440 + 4 * 60          # noon: the land agent is at work
ws.enter(town)
agent = next((n for n in ws.present if n.role == prop.P["agent_role"]), None)
check("(a land agent is at work here)", agent is not None, [(n.id, n.role) for n in ws.present])
ws.player.homes[town] = {"day": 0, "upgrades": [], "last_garden": -1, "last_hearth": -1}
ws.ensure_homes()
HOUSE = {"kind": "buy", "target": agent.id, "ware": "a house", "summary": "buying a house"}
passed, spent, notes = play("I buy a house here, then ask the land agent how the city fares.",
                            [HOUSE, {"kind": "talk", "target": agent.id, "speech": "How does the city fare?", "summary": "asking how the city fares"}], room=False)
check("a house already theirs: they are told so, nothing is paid and it is no refusal", spent == 0 and any("already own a house" in n for n in notes) and not REFUSED,
      (spent, notes, REFUSED))
check("...and the word with the land agent after it is had", bool(TALKS), (TALKS, notes))
del ws.player.homes[town]
ws.enter("parth")
ws.player.homes["parth"] = {"day": 0, "upgrades": [], "last_garden": -1, "last_hearth": -1}
ws.ensure_homes()
passed, spent, notes = play("I buy a house here.", [dict(HOUSE, target="")], room=False)
check("where no house is sold, one they own there is still theirs: told so before any word of what is for sale",
      any("already own a house" in n for n in notes) and not any("for sale" in n for n in notes) and not REFUSED, (notes, REFUSED))
del ws.player.homes["parth"]
passed, spent, notes = play("I buy a house here.", [dict(HOUSE, target="")], room=False)
check("with no house of theirs there, the game still says no houses are sold (as before)", any("for sale" in n for n in notes) and len(REFUSED) == 1, (notes, REFUSED))

g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f666) An act of the party that happens at a hall needs the hall and its clerk, as hiring does (docs/design/21_play_faults_plan.md,
D4; found in play: docs/play/2026-11-15_play_findings.md 2.3, "promote Kennard" in a monster den at night was done and told with a
guild representative, a counter and a clerk). Held here: every party act the table marks as the hall's (promote, hire) is refused
away from a guild hall, or at one with no clerk there, with a line that says where it is done, and nothing is paid or raised; at a
hall with its clerk the promotion is made as before.
Run: python tools/sim/hall_acts_666_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 8))
import ui.console as uc
NOTES = []
uc.put("note", lambda m, *a, **k: NOTES.append(m))
for fn in ("narrate", "ledger"):
    uc.put(fn, lambda *a, **k: None)
from engine import clock, told
from llm.contracts import PartyIntent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("hall_acts_666_test", seed=8, location="trading_square")
ws = g.scene
ws.player.guild_rank = "C"
ws.player.character.coins = 10 ** 6
member = {"id": "k1", "name": "Kennard Holt", "role": "fighter", "rank": "F", "level": 3, "permanent": True, "joined": 0, "fee": 100,
          "capped": True, "bond": 40, "fights_since": 9}                     # ready to be put forward
ws.player.party = [dict(member)]
ws.party_read = lambda text, offered: PartyIntent(kind="promote", target="Kennard")
check("the table marks the hall's acts", set(ws.AT_HALL) >= {"promote", "hire"})


def promote_at(place, morning=True):
    if morning:
        ws.advance(clock.minutes_until(ws.minutes, "morning"))
    ws.enter(place)
    ws.player.party = [dict(member)]
    NOTES.clear()
    coins = ws.player.character.coins
    took = ws.party_turn("promote Kennard")
    return took, ws.player.party[0]["rank"], coins - ws.player.character.coins


wild = next(p.id for p in ws.world.places.values() if p.type not in ("road", "dungeon", "city", "town", "village", "guild") and not p.parent and p.danger)
took, rank, paid = promote_at(wild)
said = " ".join(NOTES)
check("2.3: away from a hall the promotion is refused: no rank, no coin, and a line says where it is done",
      took and rank == "F" and paid == 0 and "hall" in said and "clerk" in said, (took, rank, paid, NOTES))
took, rank, paid = promote_at("guild_house")
check("...at a hall with its clerk it is made", ws.clerk_here() is not None and rank != "F" and paid > 0, (ws.clerk_here(), rank, paid, NOTES))
ws.advance(clock.minutes_until(ws.minutes, "deep night"))
took, rank, paid = promote_at("guild_house", morning=False)
check("...at a hall with no clerk there it waits", ws.clerk_here() is None and rank == "F" and paid == 0, (ws.clerk_here(), rank, paid, NOTES))
shutil.rmtree("saves/hall_acts_666_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

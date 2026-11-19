"""(f660) Coin and goods change hands only when the line asked for it (docs/design/21_play_faults_plan.md, B4; found in play:
docs/play/2026-11-15_play_findings.md 6.2 and 6.3). Asking the chandler what he sells was read as a haggle, which bought a bandage at
"25% off"; three silver handed to the guild clerk was taken as a gift, and joining then took three more.
Held here: a haggle whose line only asks (a question, no word of buying) is a word with the seller, and nothing is bought; a haggle
that says it buys still buys at the price it won. Coin handed to someone who takes coin for a deed with a price (the clerk, the guild's
joining fee) pays for that deed when it meets the price or the words name it, and is refused, kept in the purse, when it falls short
or names nothing that person sells; words of a gift or a bribe are still a gift or a bribe; once the deed is done, coin is a gift again.
Run: python tools/sim/coin_asked_660_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import ui.console as uc
NOTES = []
for fn in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    uc.put(fn, lambda *a, **k: None)
uc.put("note", lambda m, *a, **k: NOTES.append(m))
uc.put("panel", lambda name, data: False)
from llm.contracts import ActionIntent as A
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("coin_asked_660_test", seed=8, location="trading_square")
ws = g.scene
c = ws.player.character
ws.enter("tilted_plough")
keeper = next((n for n in ws.present if n.role == "innkeeper"), None)
check("(the inn has its keeper)", keeper is not None)
import random as _r
ws.rng = _r.Random(1)
ws.resolve = lambda *a, **k: "strong success"                 # every persuasion lands: what is bought is the line's to say


def haggle(line, ware="meal"):
    c.coins = 10 ** 4
    c.hunger = getattr(c, "hunger", 0)
    ws.on_haggle(A(kind="haggle", target=keeper.id, ware=ware), line)
    return {"spent": 10 ** 4 - c.coins}


got = haggle("What do you serve here, and how much for a meal?")
check("6.2: asking what is sold is no purchase: no coin spent", got == {"spent": 0}, got)
got = haggle("Do you have anything cheaper than that meal?")
check("...nor is asking after a cheaper one", got == {"spent": 0}, got)
got = haggle("I haggle him down on a hot meal and buy it")
check("a haggle that says it buys still buys", got["spent"] > 0, got)
got = haggle("Could you knock a copper off? I'll take the meal.")
check("...and so does one that asks, then says it takes it", got["spent"] > 0, got)


def pay(line, amount_words="three silver"):
    before = c.coins
    ws.pay_with_coins(A(kind="give", target=clerk.id, item=amount_words), line, clerk)
    return before - c.coins


from engine import clock
ws.advance(clock.minutes_until(ws.minutes, "morning"))
ws.enter("guild_house")
clerk = ws.clerk_here()
check("(the guild house has its clerk)", clerk is not None)
ws.player.guild_rank = ""
c.coins = 10 ** 4
NOTES.clear()
paid = pay("I hand the clerk three silver")
check("6.3: three silver to the clerk, not yet a member, is the joining fee: paid once, and the player is a member",
      paid == 300 and ws.player.guild_rank == "F", (paid, ws.player.guild_rank, NOTES))
ws.player.guild_rank = ""
c.coins = 10 ** 4
NOTES.clear()
paid = pay("Here is a silver for the fee", "a silver")
check("coin short of the fee, though said to be for it, is refused and kept: not a gift, not a member",
      paid == 0 and ws.player.guild_rank == "" and NOTES, (paid, ws.player.guild_rank, NOTES))
NOTES.clear()
paid = pay("I slide two silver across to the clerk", "two silver")
check("coin that meets nothing the clerk takes coin for is refused and kept, and the player told what it would pay for",
      paid == 0 and NOTES and "3 silver" in " ".join(NOTES).replace("three silver", "3 silver"), (paid, NOTES))
paid = pay("Two silver for your trouble, keep it", "two silver")
check("words of a gift are a gift", paid == 200 and ws.player.guild_rank == "", paid)
ws.player.guild_rank = "F"
paid = pay("I hand the clerk three silver")
check("once a member, there is no fee: coin to the clerk is a gift as before", paid == 300, paid)
shutil.rmtree("saves/coin_asked_660_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

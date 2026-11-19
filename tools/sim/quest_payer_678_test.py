"""(f678) The Quests pane says who pays a contract (found in the second blind play: docs/play/2026-11-16_blind_play_journal.md). A
guild contract posted on the board for the smith read "for Ulard Heygate", so the hides were taken to the smith, though the guild's
clerk pays it; the person a posting is for only asked for it.
Held here: a guild contract with a person behind it reads "for the guild, asked by" them; a guild contract with none reads "for the
guild"; a personal request reads "for" its person, as before; a reason stays after it.
Run: python tools/sim/quest_payer_678_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from engine import quests

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("quest_payer_678_test", seed=3, minutes=900)
ws = g.scene
a = quests._quest("gather", "F", "Bring 4 bear hide", ws.minutes, good="salt", count=4)
a.update(guild=True, issuer="ulard", issuer_name="Ulard Heygate", reason="the forge needs leather")
b = quests._quest("gather", "F", "Bring 3 salt", ws.minutes, good="salt", count=3)
b.update(guild=True, issuer="guild", issuer_name="the guild")
c = quests._quest("gather", "F", "Bring 2 salt", ws.minutes, good="salt", count=2)
c.update(guild=False, issuer="bors", issuer_name="Bors Hale")
ws.player.quests = [a, b, c]
rows = {r["title"]: r["for"] for r in ws.quest_rows()}
check("a guild contract with a person behind it: for the guild, asked by them, with its reason",
      rows["Bring 4 bear hide"] == "for the guild, asked by Ulard Heygate: the forge needs leather", rows)
check("a guild contract with no one behind it: for the guild", rows["Bring 3 salt"] == "for the guild", rows)
check("a personal request: for its person, as before", rows["Bring 2 salt"] == "for Bors Hale", rows)
shutil.rmtree("saves/quest_payer_678_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

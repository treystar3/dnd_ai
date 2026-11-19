"""(f673) A board refresh that falls due inside an operation is posted without asking the model for its stakes (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md, "THE CAUSE of the undone hand-overs"). A hand-over to a contract's person was undone again
and again: "operation action:give crashed and rolled back: Drift: board_stakes: the request at this point differs from the one asked".
The person's reply reads the town's truth view, whose board facet posted the day's new board, asking the model for each posting's
stakes inside the give; the give then changed what that request reads, and its re-run was thrown away as drift (the f470 rule: model
calls before an operation's writes, never inside).
Held here: inside an operation a due board is posted with no model call (the issuers chosen, the stakes not asked); a refresh read
outside any operation still asks them.
Run: python tools/sim/board_inside_673_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 2))
simlib.quiet_console()
from engine import clock, operation, stakes

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("board_inside_673_test", seed=7, location="guild_house")
ws, store = g.scene, g.store
ws.player.guild_rank = "F"
ws.advance(clock.minutes_until(ws.minutes, "morning"))
ws.enter("guild_house")
first = ws.ensure_board()
day0 = store.load_place("guild_house").board_day
check("(the board is posted)", day0 >= 0 and first, day0)
ASKED = []
real = stakes.plan
stakes.plan = lambda ws_, hall, new, ask=True: (ASKED.append(ask), real(ws_, hall, new, ask=ask))[1]
ws.advance(clock.MINUTES_PER_DAY * 3)                                  # the board falls due
with ws.operation("action:give", "I give the hides to the smith", world=True):
    inside = ws.ensure_board()
    posted = store.load_place("guild_house")
    check("inside an operation a due board is posted, its stakes not asked of the model",
          ASKED == [False] and posted.board_day > day0 and inside, (ASKED, posted.board_day))
check("(the operation stood down cleanly)", operation.current() is None)
ws.advance(clock.MINUTES_PER_DAY * 3)
ASKED.clear()
ws.ensure_board()
check("a refresh read outside any operation still asks them", ASKED == [True], ASKED)
stakes.plan = real
q = {"id": "q1", "kind": "hunt", "issuer": None, "letter": "F", "title": "Hunt 3 wolves"}
from engine import stakes as st
st.plan(ws, "guild_house", [q], ask=False)
check("without asking, a posting still gets the one who asked for it when the town has one, and no model is called",
      "more_wanted" not in q, q)
shutil.rmtree("saves/board_inside_673_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

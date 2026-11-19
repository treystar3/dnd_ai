"""(f683) A social act the player names for their own line rolls its check (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). `I try to persuade Fipen, appealing to his love of secrets: "..."` and `I go back to the
watchman and try to persuade him: "..."` were read as plain talk with no check: an arc's contact opens only to a won check or to
trust it takes a dozen talks to reach, so the clue stayed shut.
Held here: persuade, threaten and deceive said of the player's own act put that check on the talk; a word only inside what they say
aloud ("I'll never persuade you, will I?") does not; a check the reading already put there is kept and not doubled; a line with no
such act is left as it was.
Run: python tools/sim/social_check_683_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import ActionIntent as A

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("social_check_683_test", seed=3, minutes=900)
ws = g.scene


def checks_of(text, plan=None):
    plan = plan or [A(kind="talk", target="n1", speech="...")]
    ws.social_check(text, plan)
    return plan[0].checks


check("'I try to persuade Fipen: ...' rolls persuasion",
      checks_of('I try to persuade Fipen, appealing to his love of secrets: "Help me set the records right."') == ["persuasion"])
check("'I threaten the guard' rolls intimidation", checks_of("I threaten the guard until he talks.") == ["intimidation"])
check("'I bluff my way past' rolls deception", checks_of('I bluff: "The captain sent me."') == ["deception"])
check("a word only in what is said aloud rolls nothing", checks_of('"I could never persuade you, could I?" I ask the clerk.') == [])
check("a check already read is kept, not doubled", checks_of("I try to persuade her.", [A(kind="talk", target="n1", checks=["persuasion"])])
      == ["persuasion"])
check("a line with no such act is left as it was", checks_of("I ask the clerk about the board.") == [])
plan = [A(kind="move", destination="x"), A(kind="talk", target="n1")]
ws.social_check("We walk over and I try to convince the guard to let us pass.", plan)
check("the talk of the line gets it, not the walk", plan[0].checks == [] and plan[1].checks == ["persuasion"], [p.checks for p in plan])
import shutil; shutil.rmtree("saves/social_check_683_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

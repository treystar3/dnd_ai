"""(f674) A line that speaks to a companion and, in a sentence of its own, does something of the player's is the player's deed too: the
companion intercept leaves it to the reading (found in the second blind play: docs/play/2026-11-16_blind_play_journal.md,
'"Pae, hold it off!" I cast Chilling Touch at the bear.' was taken whole as talk to Pae, no spell cast, and Pae said "Bear fell").
f654 looked for the player's own part only inside the sentence spoken to the companion. Held here: a sentence said to no one that
starts with what the player does ("I cast", "We walk") or names one of their abilities sends the line to the reading; a sentence that
only tags the speech ("I ask") does not; and f654's cases stand.
Run: python tools/sim/hire_beside_674_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
from tools import interp_eval

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


cases = {c["name"]: c for c in interp_eval.load_cases()}
NAMES = ["a_companion_told_then_the_players_own_spell_is_the_spell", "a_companion_asked_with_a_speech_tag_is_theirs",
         "a_companion_told_then_a_walk_of_the_party_is_the_walk", "a_companion_asked_how_they_are_is_theirs",
         "a_companion_called_alone_is_theirs", "a_companion_called_with_the_players_own_deed_is_the_deed", "hire_asked_by_name",
         "an_order_to_a_hire_by_name", "a_quoted_line_to_a_hire"]
check("the corpus holds the cases", all(n in cases for n in NAMES), [n for n in NAMES if n not in cases])
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="hire_beside_674")
check("each line goes to the companion, or to the reading when the player does something of their own beside it", not out["wrong"], out["wrong"])
shutil.rmtree("saves/hire_beside_674", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

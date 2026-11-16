"""(f667) A thing handed over that settles a matter is handed over before the person speaks about it (docs/design/21_play_faults_plan.md,
D5; found in play: docs/play/2026-11-15_play_findings.md 2.9: the priestess refused the receipt, the game printed "delivered", and she
then said it was delivered earlier; the same with the watch captain). The deal-first repair (f417) left a give the reading wrote with
no one named where it stood, after the words. Held here: a deal with no one named, in a line that speaks to one person, is with them
and goes before the words; beside two people spoken to it stays where it is; a deal named to the one spoken to goes first as before.
Run: python tools/sim/deal_first_667_test.py"""
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
NAMES = ["a_thing_handed_over_to_the_one_spoken_to_goes_before_the_words", "a_thing_handed_over_with_no_one_named_beside_two_spoken_to_stays"]
check("the corpus holds the cases", all(n in cases for n in NAMES))
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="deal_first_667")
check("2.9: the thing goes before the words to the one spoken to, and stays put beside two", not out["wrong"], out["wrong"])
named = dict(cases[NAMES[0]], name="named", plan=[{"kind": "talk", "target": "p1", "speech": "Done."}, {"kind": "give", "target": "p1", "item": "receipt"}])
out = interp_eval.evaluate([named], quiet=True, save="deal_first_667")
check("...and a give named to them goes first as before", not out["wrong"], out["wrong"])
import shutil
shutil.rmtree("saves/deal_first_667", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f654) The hire and exit intercepts take a line by who it speaks to and what the player does, not by a name or a road anywhere in it
(docs/design/21_play_faults_plan.md, B2; found in play: docs/play/2026-11-15_play_findings.md 4.7, and by B0's corpus). "Raerei is still
white as a sheet. We sit under the pines for two hours" was talk to Raerei and the rest was lost; "Here, take this healing draught,
Bram" was talk and nothing was given; "I nod and tell the guard the road north is clear" left town by the north road. Held here: the
hire intercept takes a line spoken to a companion (or their name alone), and leaves to the reading one that only names them, hands
them a thing from the pack, or carries the player's own deed; the exit intercept reads only the player's own deeds, never words told
to someone, so "I ask the guard whether the King's Road south is safe" stays, while "I tell the innkeeper goodbye and head out the
north gate" leaves.
Run: python tools/sim/intercept_words_654_test.py"""
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
NAMES = ["a_thing_handed_to_a_companion_by_name_is_given", "telling_of_the_road_north_is_not_leaving_by_it",
         "a_companion_named_resting_with_the_party_is_a_wait", "goodbye_said_then_a_gate_taken_is_the_way_out", "a_road_asked_of_is_not_taken",
         "a_companion_spoken_of_beside_a_meal_bought_is_not_their_talk", "a_companion_asked_how_they_are_is_theirs",
         "a_companion_called_with_the_players_own_deed_is_the_deed", "hire_asked_by_name", "an_order_to_a_hire_by_name", "a_quoted_line_to_a_hire",
         "a_road_by_name_is_the_way_out", "a_gate_by_direction_is_the_way_out", "road_question_is_talk", "question_after_a_hire_spoke_goes_on", "a_companion_called_alone_is_theirs",
         "a_bandage_handed_to_a_companion_spoken_to_is_given", "a_companion_asked_of_their_healing_is_theirs"]
check("the corpus holds the cases of this class", all(n in cases for n in NAMES), [n for n in NAMES if n not in cases])
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="intercept_words_654")
check("each line goes to the companion it speaks to, or out by the road it takes, and no further", not out["wrong"] and not out["owed"], out)
check("...and the three cases B0 owed to this are no longer marked owed", not any(cases[n].get("owed") for n in NAMES[:3] if n in cases))
shutil.rmtree("saves/intercept_words_654", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

"""(f653) A talk or an act is read as a pastime, a bargain, a lesson, a job or a prayer by its own words, never by a deed it tells of or
a word elsewhere in the line (docs/design/21_play_faults_plan.md, B2; found in play: docs/play/2026-11-15_play_findings.md 4.2, and by
B0's corpus). "I kneel and jam the pressure plates" was a prayer, "kneel" anywhere in the line making one; "I tell Hollis I lost a game
of dice last night" was a gamble. Held here: a talk's own words are its speech and summary, and the part of the typed line that says it when the line is one deed;
a request is read clause by clause, and a clause that tells of a deed (last night, used to, lost, won, played) asks nothing, while a
request beside it still asks ("I lost last time, deal me in again"); kneeling alone is no prayer, a shrine or an altar knelt at is, and
a prayer is read from the act's own words, so a prayer whispered beside prying a chest open leaves the prying as it is.
Run: python tools/sim/talk_deed_653_test.py"""
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
NAMES = ["dice_lost_last_night_is_talk", "kneeling_to_jam_a_plate_is_no_prayer", "kneeling_to_jam_a_plate_said_so_is_no_prayer",
         "a_haggler_told_of_is_talk", "dice_asked_for_tonight_is_gamble", "kneeling_to_bind_a_wound_is_no_prayer", "kneeling_to_pray_is_a_prayer",
         "a_prayer_said_beside_another_deed_is_not_that_deed", "prayer_is_pray", "a_candle_lit_read_as_other_is_pray",
         "a_hand_of_cards_read_as_talk_is_gamble", "beating_down_a_price_read_as_talk", "asking_to_be_taught_read_as_talk_is_train",
         "taking_the_job_read_as_talk_is_work", "a_question_about_another_inns_prices_is_not_a_haggle", "a_word_after_a_game_is_still_a_word",
         "a_loss_told_beside_a_new_hand_asked_is_gamble", "wont_you_deal_me_in_is_gamble", "a_spear_once_trained_with_beside_a_lesson_asked_is_train",
         "a_game_asked_for_in_the_line_with_a_short_speech_is_gamble", "a_price_called_too_dear_in_the_line_is_haggle",
         "kneeling_at_the_altar_with_a_short_summary_is_a_prayer", "kneeling_before_a_shrine_is_a_prayer", "a_summary_telling_of_a_loss_beside_a_new_hand_asked_is_gamble"]
check("the corpus holds the cases of this class", all(n in cases for n in NAMES), [n for n in NAMES if n not in cases])
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="talk_deed_653")
check("each talk and act is read by its own words: told of, kneeling, a prayer beside, and as before", not out["wrong"] and not out["owed"], out)
check("...and the three cases B0 owed to this are no longer marked owed", not any(cases[n].get("owed") for n in NAMES[:3] if n in cases))
shutil.rmtree("saves/talk_deed_653", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

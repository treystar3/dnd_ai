"""(f652) A walk is rewritten by its own words, never by a word elsewhere in the line (docs/design/21_play_faults_plan.md, B2; found in
play: docs/play/2026-11-15_play_findings.md 4.1 and 4.5). "...point out the wires to Kennard, and go on to the next chamber" left the
dungeon, the "out" of "point out" read as climbing out; "the stairs" at a dungeon's mouth was a look. A walk's own words are its
destination, its summary, and the part of the typed line that says it (the part naming where, else one with a verb of going; the
whole line only when no part does). Held here, on the journal's line (with the model's summary echoing it or not) and lines it did
not hold: "out" counts only as a way out ("get out", "out of"), never "point out"; in a delve or at its mouth, on to the next chamber,
deeper or down the stairs is the delve, before any way out; in a delve, a way out is the way out though only the line says it;
a walk to somewhere new is a walk though the line names a room; a room, upstairs or the fire said in the walk is a look; a roof is a
climb.
Run: python tools/sim/deed_words_652_test.py"""
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
NAMES = ["pointing_out_the_wires_does_not_leave_the_dungeon", "going_on_to_the_next_chamber_is_the_delve",
         "a_tripwire_pointed_out_does_not_leave_the_dungeon", "climbing_out_said_in_the_walk_still_leaves",
         "climbing_out_read_as_a_move_is_leave_dungeon", "a_walk_back_to_a_chamber_stays_in_the_dungeon",
         "a_room_named_beside_a_walk_out_is_no_look", "going_up_to_the_room_is_still_a_look", "upstairs_read_as_a_move_is_look",
         "our_rooms_at_the_inn_is_not_a_journey", "a_roof_read_as_a_destination_is_a_climb",
         "turning_in_said_in_the_walk_is_a_look", "getting_out_said_only_in_the_line_leaves", "climbing_out_toward_town_leaves",
         "the_wires_with_an_echoing_summary_go_on", "out_of_this_chamber_to_the_next_goes_on", "the_stairs_down_at_the_mouth_is_the_delve",
         "going_deeper_at_the_mouth_is_the_delve", "upstairs_to_sleep_said_only_in_the_line_is_a_look", "sitting_by_the_fire_is_a_look",
         "checking_out_the_carvings_does_not_leave", "a_torch_held_out_on_a_walk_does_not_leave", "a_way_out_promised_beside_a_walk_does_not_leave"]
check("the corpus holds the cases of this class", all(n in cases for n in NAMES), [n for n in NAMES if n not in cases])
out = interp_eval.evaluate([cases[n] for n in NAMES if n in cases], quiet=True, save="deed_words_652")
check("every walk is read by its own words: out, on, within, a roof", not out["wrong"] and not out["owed"], out)
check("...and the journal's line, owed by B0, is no longer marked owed", not cases["pointing_out_the_wires_does_not_leave_the_dungeon"].get("owed"))
shutil.rmtree("saves/deed_words_652", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)

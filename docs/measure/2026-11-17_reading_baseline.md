# The reader on the real model: first baseline

Date: 2026-11-17. Commit ad6f7e0 (f716). Command: `python tools/interp_eval.py --live` over data/replay/interp_cases.yaml.
Model server: llama-server (cuda) on an RTX 4070 Ti SUPER, class minimum, 16384 tokens a slot. One run, about twenty minutes.
This is the first time the corpus's live result has been written down. The suite runs the same corpus offline, where the model's
reading is each case's own stored plan.

| | Right | Of | Share |
|---|---|---|---|
| Offline (what the suite checks) | 252 | 252 | 100% |
| Live (the model reads every line) | 216 | 252 | 86% |

No case went unread, and no intercept took a line that was not its own or missed one that was.

## What it means

- The offline figure says the repairs do what they were written to do. It says nothing about the model.
- The live figure is on the lines the repairs were written against, so it is the best case. Lines nobody has typed yet will do worse.
- The repairs changed the model's reading about 120 times in 252 lines (narrated_talk 37, talk_to_deed 14, deal_then_word 13,
  move_elsewhere 10, name_the_target 9, drop_restatements 7, the rest under 6 each). The model's first reading is put right by
  rule on nearly half the corpus.

## The 36 wrong

- **21 are one line read as two steps:** a spoken step and a deed made from the same words, or a look beside a walk
  (`ran ['talk', 'move'], not ['move']`). This is the class the review's "each step names the words it covers" would stop: two
  steps cannot claim the same words.
- The rest are the wrong kind (a wound bound read as talk, sitting by the fire read as other, a pluck read as forage), the wrong
  person of two (g1 for g2), or an order (give before talk).

By kind, where any were wrong: talk 36/43, other 14/20, move 9/13, give 14/16, buy 10/12, gamble 8/10, look 8/10, delve 5/8,
commission 0/2, ability 7/8, accept_quest 3/4, harvest 2/3, sell 5/6, train 2/3, wait 5/6. Every other kind was right in full.

## The wrong cases

a_goodbye_that_carries_a_question_is_still_read, a_word_then_a_sale_settles_the_sale_first, a_gift_said_so_stays_a_gift,
asking_the_smith_to_forge_is_commission, taking_the_first_contract, the_material_given_beside_the_commission_is_dropped,
a_hand_of_cards_read_as_talk_is_gamble, arrows_asked_for_do_not_buy_a_bow, a_nod_read_as_words_is_a_gesture,
kneeling_to_jam_a_plate_is_no_prayer, kneeling_to_jam_a_plate_said_so_is_no_prayer,
pointing_out_the_wires_does_not_leave_the_dungeon, going_to_watch_the_fishing_boats_is_a_walk, a_look_the_line_asked_for_stays,
a_companion_named_resting_with_the_party_is_a_wait, quoted_words_are_kept_as_said,
asking_a_friend_about_the_guard_stays_with_the_friend, of_two_guards_the_one_already_talking_is_spoken_to,
a_tripwire_pointed_out_does_not_leave_the_dungeon, a_room_named_beside_a_walk_out_is_no_look,
turning_in_said_in_the_walk_is_a_look, the_wires_with_an_echoing_summary_go_on, sitting_by_the_fire_is_a_look,
checking_out_the_carvings_does_not_leave, a_way_out_promised_beside_a_walk_does_not_leave, dice_asked_for_tonight_is_gamble,
kneeling_to_bind_a_wound_is_no_prayer, a_prayer_said_beside_another_deed_is_not_that_deed,
a_spear_once_trained_with_beside_a_lesson_asked_is_train, a_companion_spoken_of_beside_a_meal_bought_is_not_their_talk,
a_companion_called_with_the_players_own_deed_is_the_deed, a_bandage_handed_to_a_companion_spoken_to_is_given,
a_thing_handed_over_with_no_one_named_beside_two_spoken_to_stays, persuade_said_of_the_act_rolls_the_check,
plucking_a_fresh_kill_is_the_harvest, an_ability_read_as_words_to_a_companion_is_the_ability.

One run only: the model's reading varies a little from run to run, so a case or two either way is noise.

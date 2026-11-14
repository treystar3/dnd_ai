# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 16 | 8.4 | 11.3 | 5.1 | 7.0 | 6.2 | 7.2 | 3 | 0 |
| talk | 10 | 3.9 | 8.4 | 3.9 | 8.4 | 4.0 | 5.0 | 1 | 0 |
| search | 10 | 3.0 | 4.2 | 3.1 | 4.2 | 3.9 | 3.2 | 0 | 0 |
| leave | 9 | 4.1 | 7.5 | 3.6 | 4.1 | 5.1 | 4.5 | 2 | 0 |
| fight | 9 | 4.3 | 5.1 | 2.6 | 4.3 | 3.2 | 4.5 | 1 | 0 |
| board | 3 | 4.9 | 5.0 | 4.9 | 5.0 | 6.0 | 4.7 | 1 | 0 |
| look | 2 | 3.3 | 3.4 | 3.3 | 3.4 | 5.0 | 3.3 | 0 | 0 |
| hire | 1 | 3.7 | 3.7 | 3.7 | 3.7 | 4.0 | 2.5 | 0 | 0 |

60 turns in 5.2 minutes; 97% of it in the model; 203 embedding calls taking 1.0 s; 3 calls on background threads.
The budget: 7 optional calls deferred and 9 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 19.2 s and p90 39.0 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 14.0 s, talk, 4 calls, at the Riverhaven guild hall: "Good enough. Now, tell me: what kind of trouble has been brewing in th"
- 11.8 s, move, 10 calls, at the trading square: "I signal to the crew and start heading toward Willowmead."
- 11.3 s, move, 8 calls, at the Willowmead wetlands: "We're done here. Let's head back to the Adventurers' Guild House."
- 11.0 s, move, 10 calls, at Willowmead: "I turn toward the south and tell the crew we're heading for Riverhaven"
- 10.6 s, move, 8 calls, at Riverhaven: "I head north toward the Willowmead wetlands, looking for something wor"

Lines by what read them: interpret 51, combat 9

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 58 of 60 (97%) |
| Lines the model wrote | 48 (template 12; model failed 0, 20 s) |
| Lines picking up the passage before | 24 of 60 (40%); in talk 5 of 10 (50%) |
| Contracts taken / finished | 3 / 1 |
| Situations met / followed / ended by the player | 3 / 1 / 1 |
| Goals finished / given up | 8 / 1 (contract 1/1, find 1/0, follow 1/0, go 2/0, hunt 1/0, report 1/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 9 |
| Waits | 0 of 60 (0%) |
| Places visited | 11 |

Turns by goal: idle 19, fight 9, board 7, hunt 6, follow 6, contract 3, report 3, cont 2, go 2, revisit 2, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 6 (id 2, script 2, escape 1, broken 1) |
| Machinery mended at the screen | 1482 (dash 1464, stage 2, wrap 16) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("part of that stood: adjusting grip on blade and scanning the perimeter") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1, ruled 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 22.2 |
| Parts made different by an attempt (blocked, lit, cleared...) | 1 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Dynn Brookby in narrate 1) |
| Companion sentences naming another people | 1 (Calsa Hoyle in narrate 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 31 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '? Yes') |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 1 of 60 |
| Matters the player ended: pursued / by accident | 1 / 0 |
| Fights won / for +0 XP / XP median and most | 5 / 1 / 4 and 48 |
| Fight turns with a foe 10+ levels above the player | 0 of 9, the widest -7 |
| Marks shown from acts (Remembered here) | 1 |
| Captives escaped / handed over or let go | 0 / 0 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | none met again |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 2 / 0 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 3 / 0 (e.g. turn 55 the ink-stained clerk contract_taken; turn 55 the ink-stained clerk contract_done) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 11 | 0 | 0 | 1.4 | 57.8 | 569 | 281 | 2428 | 215.9 | 0 | 225 |
| narrate | 40 | 6 | 6 | 1.9 | 2.6 | 2461 | 190 | 5122 | 136.6 | 0 | 90 |
| npc_conversation | 17 | 2 | 3 | 1.7 | 3.1 | 5137 | 135 | 6638 | 137.7 | 0 | 41 |
| interpret_action | 55 | 0 | 0 | 0.6 | 0.9 | 4152 | 67 | 10710 | 251.3 | 0 | 36 |
| combat_narrate | 11 | 0 | 0 | 2.1 | 2.3 | 2756 | 195 | 4886 | 133.1 | 0 | 21 |
| player_line | 48 | 10 | 10 | 0.4 | 0.4 | 542 | 22 | 2897 | 138.7 | 0 | 20 |
| dialogue_frame | 19 | 0 | 0 | 1.0 | 1.2 | 2325 | 56 | 4170 | 134.7 | 0 | 19 |
| exchange | 8 | 0 | 0 | 1.4 | 1.8 | 2823 | 101 | 4670 | 164.2 | 0 | 11 |
| combat_aftermath | 7 | 0 | 0 | 1.6 | 1.7 | 1859 | 174 | 4529 | 171.9 | 0 | 11 |
| combat_opening | 5 | 0 | 0 | 1.8 | 2.0 | 1673 | 189 | 3715 | 136.8 | 0 | 9 |
| hire_chat | 9 | 0 | 0 | 0.8 | 1.0 | 2430 | 57 | 4511 | 190.8 | 0 | 8 |
| audit_compare | 30 | 0 | 0 | 0.2 | 0.3 | 219 | 36 | 2360 | 265.0 | 0 | 7 |
| road_event | 3 | 0 | 0 | 2.3 | 2.4 | 1762 | 323 | 3999 | 179.7 | 0 | 7 |
| audit_meaning | 30 | 0 | 0 | 0.2 | 0.2 | 160 | 20 | 1930 | 157.6 | 0 | 7 |
| board_stakes | 3 | 0 | 0 | 2.3 | 2.6 | 1147 | 413 | 3452 | 214.8 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.7 | 819 | 269 | 3523 | 186.0 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.3 | 4.3 | 1050 | 924 | 3125 | 231.5 | 0 | 4 |
| combat_interpret | 9 | 0 | 0 | 0.5 | 0.5 | 956 | 34 | 3087 | 295.0 | 0 | 4 |
| npc_profile | 5 | 0 | 0 | 0.7 | 0.9 | 493 | 99 | 3172 | 171.3 | 0 | 4 |
| moment | 2 | 0 | 0 | 1.6 | 2.0 | 1365 | 247 | 3592 | 173.1 | 0 | 4 |
| ruling | 4 | 0 | 0 | 0.7 | 1.1 | 1220 | 70 | 4563 | 204.5 | 0 | 3 |
| overheard | 7 | 0 | 0 | 0.2 | 0.2 | 283 | 16 | 1956 | 308.5 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.3 | 0.4 | 951 | 4 | 3251 | 205.1 | 0 | 1 |
| clarify | 1 | 0 | 0 | 0.3 | 0.3 | 262 | 31 | 2519 | 174.2 | 0 | 0 |
| work_offer_read | 1 | 0 | 0 | 0.2 | 0.2 | 100 | 19 | 1053 | 163.8 | 0 | 0 |

349 attempts for 331 calls, 9.1 minutes in the model in all.

## Fights

14 rounds with a fight call; 2.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 9 | 0.5 | 0.5 | 0 |
| combat_opening | 5 | 1.8 | 2.0 | 0 |
| combat_narrate | 11 | 2.1 | 2.7 | 0 |
| combat_aftermath | 7 | 1.6 | 1.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 17 | 88% | 20109 | 21401 | 22054 | 72 | 6% |
| npc_profile | 5 | 100% | 1988 | 2553 | 2553 | 923 | 0% |
| dialogue_frame | 19 | 100% | 9792 | 10752 | 11468 | 4720 | 6% |
| work_offer_read | 1 | 100% | 351 | 351 | 351 | 102 | 0% |
| hire_chat | 9 | 100% | 9848 | 12544 | 12544 | 1844 | 6% |
| canon_extract | 2 | 100% | 3339 | 4439 | 4439 | 707 | 0% |
| exchange | 8 | 100% | 12063 | 13436 | 13436 | 67 | 0% |
| overheard | 7 | 100% | 1115 | 1175 | 1175 | 221 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 17 | 88% | 95% | -7 | 21401 | 36345 | 36500 | 22054 | 6% |
| npc_profile | 5 | 100% | 100% | +0 | 2553 | 2774 | 3000 | 2553 | 0% |
| dialogue_frame | 19 | 100% | 86% | +14 | 10752 | 10715 | 11000 | 11468 | 6% |
| work_offer_read | 1 | 100% | 100% | +0 | 351 | 780 | 1000 | 351 | 0% |
| hire_chat | 9 | 100% | 98% | +2 | 12544 | 16275 | 16500 | 12544 | 6% |
| canon_extract | 2 | 100% | 100% | +0 | 4439 | 3998 | 4000 | 4439 | 0% |
| exchange | 8 | 100% | 90% | +10 | 13436 | 15039 | 15500 | 13436 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1175 | 1326 | 1500 | 1175 | 0% |

Size: 6 of 8 tasks at or below the baseline's p95 (dearer: dialogue_frame, canon_extract); npc_conversation's p95 21401 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -7).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 55 | 224016 | 161697 (72%) | 164313 (73%) |
| narrate | 46 | 112887 | 57684 (51%) | 32864 (29%) |
| npc_conversation | 19 | 95492 | 42317 (44%) | 15285 (16%) |
| dialogue_frame | 19 | 42653 | 22225 (52%) | 2353 (6%) |
| player_line | 58 | 31927 | 8335 (26%) | 5675 (18%) |
| combat_narrate | 11 | 30794 | 17315 (56%) | 5608 (18%) |
| exchange | 8 | 22752 | 8893 (39%) | 0 (0%) |
| hire_chat | 9 | 22595 | 12507 (55%) | 1319 (6%) |
| combat_aftermath | 7 | 13229 | 6159 (47%) | 3685 (28%) |
| combat_interpret | 9 | 8651 | 7252 (84%) | 0 (0%) |
| combat_opening | 5 | 8336 | 4220 (51%) | 0 (0%) |
| audit_compare | 30 | 6658 | 3505 (53%) | 0 (0%) |
| populate_place | 11 | 6621 | 2836 (43%) | 0 (0%) |
| road_event | 3 | 5275 | 2377 (45%) | 0 (0%) |
| ruling | 4 | 4937 | 2336 (47%) | 1219 (25%) |
| audit_meaning | 30 | 4877 | 2056 (42%) | 0 (0%) |
| board_stakes | 3 | 3369 | 1175 (35%) | 0 (0%) |
| moment | 2 | 2730 | 1495 (55%) | 0 (0%) |
| npc_profile | 5 | 2623 | 1302 (50%) | 0 (0%) |
| persona_details | 3 | 2452 | 1091 (45%) | 345 (14%) |
| overheard | 7 | 1956 | 1558 (80%) | 0 (0%) |
| canon_extract | 2 | 1902 | 1289 (68%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| clarify | 1 | 262 | 145 (55%) | 0 (0%) |
| work_offer_read | 1 | 100 | 71 (71%) | 0 (0%) |

The prompts held 658144 tokens; the constant system messages were about 370328 of them (56%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 232666 (35%) and read the rest.
The server's log: 349 prompts; 258 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 846 checkpoints made, 41 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 4 game days: 4 situations started (4 within reach of the player), 0 stages advanced, 2 ended (1 by the player, 1 settled by others, 0 left to their fallout), 0 motive steps; the player met 2 doors (a scene or a summons), 3 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 2 failed.

Per game day within reach: 1.00 situations started, 0.50 doors, 0.75 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 1 (1) | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| 3 | 1 (1) | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| 4 | 2 (2) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 3: [normal, engine-built] No way to Parth at Willowmead - starts, 1 days, 1 stages (within reach)
- day 4: [normal, engine-built] Carts on the southern trade route at Riverhaven - starts, 2 days, 1 stages (within reach)
- day 4: [uncommon, engine-built] A demand at Lethoria - starts, 4 days, 2 stages (within reach)

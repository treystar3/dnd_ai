# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 14, 0 deaths; 60 turns in 0.1 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 16 | 4.9 | 9.8 | 3.1 | 5.5 | 3.9 | 5.5 | 10 | 0 |
| move | 13 | 6.8 | 13.8 | 4.8 | 6.8 | 6.6 | 7.3 | 9 | 0 |
| search | 11 | 2.8 | 6.1 | 2.8 | 5.7 | 4.0 | 3.8 | 3 | 0 |
| talk | 6 | 3.9 | 5.1 | 3.9 | 5.0 | 4.8 | 4.4 | 2 | 0 |
| board | 5 | 6.1 | 14.3 | 5.8 | 14.3 | 7.0 | 7.8 | 3 | 0 |
| leave | 5 | 5.1 | 10.8 | 4.8 | 7.7 | 4.6 | 5.3 | 4 | 0 |
| wait | 4 | 7.4 | 8.7 | 6.5 | 7.4 | 5.8 | 7.2 | 5 | 0 |

60 turns in 5.9 minutes; 98% of it in the model; 204 embedding calls taking 1.0 s; 2 calls on background threads.
The budget: 9 optional calls deferred and 12 dropped; 6 turns told by a stand-in, 4 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 23.0 s and p90 41.1 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 14.3 s, board, 6 calls, at the adventurers' guild house: "I point to one of the blue-sealed papers. I want to take the contract "
- 14.1 s, move, 9 calls, at Parth: "Let's get moving. We're heading straight to the Adventurers' Guild Hou"
- 13.8 s, move, 9 calls, at the Red Road between Parth and Redstone: "We're turning back; we need to head toward Parth."
- 12.0 s, move, 11 calls, at the adventurers' guild house: "I check my gear and say, 'Then it's time. Let's get to the Shipwreck S"
- 10.9 s, fight, 8 calls, at the Salt Road between Kelpmoor and Parth: "I use Brutal Strike on bandit 1."

Lines by what read them: interpret 44, combat 16

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 55 of 60 (92%) |
| Lines the model wrote | 43 (template 17; model failed 0, 19 s) |
| Lines picking up the passage before | 17 of 60 (28%); in talk 2 of 6 (33%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 6 / 0 (contract 1/0, go 3/0, hunt 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 16 |
| Waits | 4 of 60 (7%) |
| Places visited | 8 |

Turns by goal: fight 16, idle 15, board 8, contract 8, hunt 6, report 4, go 2, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 30 (script 12, id 9, broken 7, note 1, first_person 1) |
| Machinery mended at the screen | 2827 (dash 2809, wrap 18) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 10.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 1 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Tamstan Oxlow in combat_narrate 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 2 lines, 12 times; 12 of the game's 43 own lines (28%); most: 'Victory. +# XP' x7; 'Tamstan sees to the wounds after the fight: +# h' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 3 / 0 / 0 (e.g. '<'; '*'; ']') |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | captive 0 of 1; hire 1 of 75 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 9 / 3 / 359 and 617 |
| Fight turns with a foe 10+ levels above the player | 0 of 16, the widest +0 |
| Marks shown from acts (Remembered here) | 2 |
| Captives escaped / handed over or let go | 1 / 0 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | none met again |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 5 | 0 | 0 | 1.6 | 124.7 | 708 | 288 | 3503 | 193.3 | 0 | 195 |
| narrate | 28 | 14 | 16 | 2.1 | 2.7 | 2645 | 186 | 5710 | 118.9 | 0 | 91 |
| combat_narrate | 17 | 7 | 8 | 2.0 | 2.7 | 2845 | 199 | 5537 | 125.1 | 0 | 48 |
| interpret_action | 52 | 0 | 0 | 0.7 | 0.9 | 3983 | 63 | 10327 | 238.0 | 0 | 36 |
| npc_conversation | 12 | 3 | 4 | 1.8 | 4.2 | 5607 | 126 | 7531 | 126.3 | 0 | 34 |
| dialogue_frame | 21 | 7 | 7 | 1.1 | 1.4 | 2182 | 67 | 4418 | 133.8 | 0 | 29 |
| combat_aftermath | 14 | 0 | 0 | 1.5 | 1.8 | 1888 | 189 | 4659 | 176.0 | 0 | 21 |
| player_line | 43 | 11 | 11 | 0.3 | 0.4 | 554 | 22 | 2834 | 134.5 | 0 | 19 |
| hire_chat | 14 | 3 | 3 | 0.9 | 1.0 | 2982 | 48 | 5239 | 170.2 | 0 | 15 |
| combat_opening | 8 | 0 | 0 | 1.9 | 2.0 | 1759 | 188 | 3723 | 133.2 | 0 | 15 |
| exchange | 12 | 1 | 1 | 1.1 | 1.3 | 3337 | 73 | 5099 | 159.5 | 0 | 14 |
| road_event | 3 | 0 | 0 | 2.4 | 2.6 | 1739 | 354 | 3744 | 176.9 | 0 | 7 |
| combat_interpret | 16 | 0 | 0 | 0.5 | 0.5 | 955 | 47 | 3127 | 303.6 | 0 | 7 |
| persona_details | 3 | 1 | 1 | 1.6 | 1.7 | 895 | 255 | 3337 | 209.4 | 0 | 6 |
| audit_compare | 21 | 0 | 0 | 0.2 | 0.3 | 213 | 39 | 2324 | 265.6 | 0 | 5 |
| audit_meaning | 21 | 0 | 0 | 0.2 | 0.2 | 163 | 22 | 1788 | 163.7 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.6 | 4.6 | 1064 | 973 | 3148 | 229.1 | 0 | 5 |
| overheard | 11 | 0 | 0 | 0.2 | 0.2 | 270 | 16 | 1881 | 309.3 | 0 | 2 |
| ruling | 3 | 0 | 0 | 0.7 | 0.7 | 1302 | 64 | 3838 | 185.6 | 0 | 2 |
| canon_extract | 4 | 0 | 0 | 0.3 | 1.0 | 824 | 4 | 3040 | 280.6 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1365 | 219 | 3679 | 147.8 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.7 | 0.8 | 624 | 113 | 3479 | 187.2 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.5 | 1.5 | 1143 | 260 | 3149 | 234.4 | 0 | 1 |
| canon_check | 1 | 0 | 0 | 0.2 | 0.2 | 214 | 14 | 2038 | 280.0 | 0 | 0 |

361 attempts for 314 calls, 9.4 minutes in the model in all.

## Fights

24 rounds with a fight call; 2.6 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 16 | 0.5 | 0.5 | 0 |
| combat_opening | 8 | 1.9 | 2.1 | 0 |
| combat_narrate | 24 | 2.0 | 2.7 | 8 |
| combat_aftermath | 14 | 1.5 | 1.8 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 83% | 21763 | 23994 | 26024 | 91 | 9% |
| npc_profile | 2 | 100% | 2493 | 2629 | 2629 | 1428 | 0% |
| dialogue_frame | 21 | 71% | 8925 | 10920 | 11680 | 4124 | 0% |
| hire_chat | 14 | 79% | 11882 | 14034 | 14047 | 2061 | 0% |
| canon_extract | 4 | 100% | 3378 | 3581 | 3581 | 746 | 0% |
| canon_check | 1 | 100% | 886 | 886 | 886 | 493 | 0% |
| exchange | 12 | 92% | 13533 | 13943 | 14192 | 62 | 0% |
| overheard | 11 | 100% | 1086 | 1138 | 1138 | 192 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 83% | 95% | -12 | 23994 | 36345 | 36500 | 26024 | 9% |
| npc_profile | 2 | 100% | 100% | +0 | 2629 | 2774 | 3000 | 2629 | 0% |
| dialogue_frame | 21 | 71% | 86% | -15 | 10920 | 10715 | 11000 | 11680 | 0% |
| hire_chat | 14 | 79% | 98% | -19 | 14034 | 16275 | 16500 | 14047 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 3581 | 3998 | 4000 | 3581 | 0% |
| canon_check | 1 | 100% | 100% | +0 | 886 | 853 | 1000 | 886 | 0% |
| exchange | 12 | 92% | 90% | +2 | 13943 | 15039 | 15500 | 14192 | 0% |
| overheard | 11 | 100% | 100% | +0 | 1138 | 1326 | 1500 | 1138 | 0% |

Size: 6 of 8 tasks at or below the baseline's p95 (dearer: dialogue_frame, canon_check); npc_conversation's p95 23994 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -12; hire_chat -19).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 52 | 212366 | 153158 (72%) | 158521 (75%) |
| narrate | 42 | 110683 | 53981 (49%) | 47938 (43%) |
| npc_conversation | 15 | 83334 | 33608 (40%) | 22322 (27%) |
| combat_narrate | 24 | 68234 | 38909 (57%) | 21844 (32%) |
| dialogue_frame | 28 | 61030 | 32364 (53%) | 14732 (24%) |
| hire_chat | 17 | 49998 | 23966 (48%) | 8946 (18%) |
| exchange | 13 | 41171 | 14694 (36%) | 3501 (9%) |
| player_line | 54 | 30450 | 7803 (26%) | 6503 (21%) |
| combat_aftermath | 14 | 26445 | 12394 (47%) | 9435 (36%) |
| combat_interpret | 16 | 15358 | 12892 (84%) | 0 (0%) |
| combat_opening | 8 | 13858 | 6751 (49%) | 0 (0%) |
| road_event | 3 | 5268 | 2381 (45%) | 0 (0%) |
| audit_compare | 21 | 4636 | 2461 (53%) | 0 (0%) |
| ruling | 3 | 3938 | 1726 (44%) | 0 (0%) |
| populate_place | 5 | 3745 | 1282 (34%) | 0 (0%) |
| audit_meaning | 21 | 3478 | 1440 (41%) | 0 (0%) |
| persona_details | 4 | 3474 | 1601 (46%) | 1124 (32%) |
| canon_extract | 4 | 3335 | 2601 (78%) | 0 (0%) |
| overheard | 11 | 2989 | 2464 (82%) | 0 (0%) |
| moment | 1 | 1365 | 757 (55%) | 0 (0%) |
| npc_profile | 2 | 1249 | 519 (42%) | 0 (0%) |
| board_stakes | 1 | 1143 | 394 (34%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| canon_check | 1 | 214 | 95 (44%) | 0 (0%) |

The prompts held 748825 tokens; the constant system messages were about 408730 of them (55%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 294866 (39%) and read the rest.
The server's log: 361 prompts; 248 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 917 checkpoints made, 36 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 2 failed.

Per game day within reach: 0.67 situations started, 0.33 doors, 0.33 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 2 (2) | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| 3 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

Situations started:
- day 2: [rare, engine-built] Cheap and then dear in Parth - starts, 13 days, 3 stages (within reach)
- day 2: [uncommon, engine-built] Who let them in at the Shipwreck Shoals - starts, 6 days, 2 stages (within reach)

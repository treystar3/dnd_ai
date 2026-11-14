# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 38 | 2.8 | 5.4 | 2.8 | 5.4 | 2.6 | 3.9 | 3 | 0 |
| move | 8 | 8.2 | 9.4 | 4.9 | 5.5 | 5.6 | 7.0 | 4 | 0 |
| leave | 8 | 3.2 | 5.8 | 3.2 | 3.4 | 4.5 | 3.7 | 1 | 0 |
| rest | 4 | 7.1 | 9.2 | 6.2 | 6.3 | 8.0 | 6.7 | 3 | 0 |
| wait | 1 | 3.0 | 3.0 | 3.0 | 3.0 | 2.0 | 1.8 | 0 | 0 |
| fight | 1 | 4.0 | 4.0 | 2.5 | 2.5 | 3.0 | 3.9 | 0 | 0 |

60 turns in 4.6 minutes; 96% of it in the model; 269 embedding calls taking 1.2 s; 1 calls on background threads.
The budget: 2 optional calls deferred and 7 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.6 s and p90 29.9 s, over 60 s in 1 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 25.7 s, talk, 2 calls, at the adventurers' guild house: "Do you know which specific room or corridor those heavy doors lead to?"
- 13.5 s, talk, 3 calls, at the adventurers' guild house: "I turn toward the polished bureaucrat and ask, "Have you noticed anyth"
- 13.2 s, move, 9 calls, at the adventurers' guild house: "I look toward Gorz and nod. 'Let's begin our trek toward Willowmead.'"
- 9.4 s, move, 9 calls, at Parth: "I turn to the group and say, 'We should make our way toward the advent"
- 9.4 s, move, 8 calls, at the Greywood: "I check my gear and turn toward the path heading for Willowmead."

Lines by what read them: interpret 55, hire 3, exit 1, combat 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 53 (template 7; model failed 0, 29 s) |
| Lines picking up the passage before | 18 of 60 (30%); in talk 12 of 38 (32%) |
| Contracts taken / finished | 0 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 4 / 0 (go 3/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 1 |
| Waits | 1 of 60 (2%) |
| Places visited | 6 |

Turns by goal: idle 42, go 6, cont 5, need 4, revisit 2, fight 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 6 (id 2, broken 2, json 1, script 1) |
| Machinery mended at the screen | 529 (dash 524, stage 2, wrap 3) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 2 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Adney Wimell in npc_conversation 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 7 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 36 ['before']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 24 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 1 / 0 / 4 and 4 |
| Fight turns with a foe 10+ levels above the player | 0 of 1, the widest -11 |
| Marks shown from acts (Remembered here) | 0 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 0 / 1 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.4 | 94.1 | 696 | 287 | 3291 | 234.8 | 0 | 225 |
| npc_conversation | 42 | 1 | 1 | 1.9 | 3.2 | 5290 | 147 | 6075 | 108.8 | 0 | 122 |
| interpret_action | 58 | 0 | 0 | 0.7 | 0.8 | 4145 | 61 | 10149 | 268.7 | 0 | 40 |
| narrate | 11 | 4 | 4 | 2.1 | 2.8 | 2394 | 182 | 4863 | 122.9 | 0 | 31 |
| player_line | 53 | 18 | 18 | 0.4 | 0.5 | 511 | 28 | 2816 | 133.7 | 0 | 29 |
| dialogue_frame | 13 | 2 | 2 | 0.9 | 1.3 | 2307 | 49 | 4192 | 127.6 | 0 | 15 |
| hire_chat | 14 | 1 | 1 | 0.9 | 1.1 | 2639 | 50 | 4767 | 185.5 | 0 | 13 |
| exchange | 5 | 2 | 2 | 1.3 | 1.4 | 3078 | 97 | 5761 | 152.1 | 0 | 9 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.6 | 826 | 248 | 3396 | 189.3 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1028 | 967 | 3087 | 237.3 | 0 | 4 |
| audit_compare | 14 | 0 | 0 | 0.2 | 0.3 | 222 | 36 | 2341 | 253.7 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 3.4 | 3.4 | 1287 | 676 | 3636 | 222.1 | 0 | 3 |
| audit_meaning | 14 | 0 | 0 | 0.2 | 0.2 | 166 | 19 | 1810 | 162.6 | 0 | 3 |
| npc_profile | 4 | 0 | 0 | 0.7 | 0.8 | 537 | 84 | 3108 | 179.5 | 0 | 3 |
| road_event | 1 | 0 | 0 | 2.5 | 2.5 | 1702 | 372 | 3833 | 184.6 | 0 | 2 |
| overheard | 11 | 0 | 0 | 0.2 | 0.2 | 271 | 16 | 1892 | 309.6 | 0 | 2 |
| moment | 1 | 1 | 1 | 0.8 | 1.4 | 1242 | 148 | 3719 | 197.1 | 0 | 2 |
| combat_narrate | 1 | 0 | 0 | 2.0 | 2.0 | 2718 | 187 | 4530 | 132.4 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 1.8 | 1.8 | 2873 | 223 | 4945 | 182.0 | 0 | 2 |
| combat_opening | 1 | 0 | 0 | 1.4 | 1.4 | 1438 | 135 | 3408 | 134.5 | 0 | 1 |
| combat_aftermath | 1 | 0 | 0 | 1.4 | 1.4 | 1771 | 160 | 3760 | 168.4 | 0 | 1 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 824 | 2 | 3068 | 192.3 | 0 | 1 |
| combat_interpret | 1 | 0 | 0 | 0.5 | 0.5 | 960 | 50 | 3276 | 310.6 | 0 | 0 |

290 attempts for 261 calls, 8.7 minutes in the model in all.

## Fights

2 rounds with a fight call; 2.0 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 1 | 0.5 | 0.5 | 0 |
| combat_opening | 1 | 1.4 | 1.4 | 0 |
| combat_narrate | 1 | 2.0 | 2.0 | 0 |
| combat_aftermath | 1 | 1.4 | 1.4 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 21366 | 23483 | 23601 | 113 | 2% |
| npc_profile | 4 | 100% | 2522 | 2613 | 2613 | 1457 | 0% |
| dialogue_frame | 13 | 85% | 9595 | 9962 | 10091 | 4475 | 0% |
| hire_chat | 14 | 93% | 10831 | 12738 | 13397 | 1621 | 4% |
| canon_extract | 3 | 100% | 3311 | 3318 | 3318 | 679 | 0% |
| exchange | 5 | 60% | 12550 | 13610 | 13610 | 63 | 0% |
| overheard | 11 | 100% | 1091 | 1212 | 1212 | 197 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 95% | +2 | 23483 | 36345 | 36500 | 23601 | 2% |
| npc_profile | 4 | 100% | 100% | +0 | 2613 | 2774 | 3000 | 2613 | 0% |
| dialogue_frame | 13 | 85% | 86% | -2 | 9962 | 10715 | 11000 | 10091 | 0% |
| hire_chat | 14 | 93% | 98% | -5 | 12738 | 16275 | 16500 | 13397 | 4% |
| canon_extract | 3 | 100% | 100% | +0 | 3318 | 3998 | 4000 | 3318 | 0% |
| exchange | 5 | 60% | 90% | -30 | 13610 | 15039 | 15500 | 13610 | 0% |
| overheard | 11 | 100% | 100% | +0 | 1212 | 1326 | 1500 | 1212 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 23483 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (exchange -30).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 58 | 239909 | 170621 (71%) | 175436 (73%) |
| npc_conversation | 43 | 217667 | 94303 (43%) | 9427 (4%) |
| hire_chat | 15 | 40901 | 20934 (51%) | 3859 (9%) |
| player_line | 71 | 37418 | 10101 (27%) | 9391 (25%) |
| narrate | 15 | 35701 | 19292 (54%) | 9848 (28%) |
| dialogue_frame | 15 | 33212 | 17874 (54%) | 4511 (14%) |
| exchange | 7 | 21424 | 7938 (37%) | 5993 (28%) |
| populate_place | 7 | 4564 | 1801 (39%) | 7 (0%) |
| audit_compare | 14 | 3102 | 1632 (53%) | 14 (0%) |
| overheard | 11 | 3028 | 2442 (81%) | 11 (0%) |
| thread_telling | 1 | 2873 | 398 (14%) | 1 (0%) |
| combat_narrate | 1 | 2718 | 1573 (58%) | 1 (0%) |
| moment | 2 | 2484 | 1645 (66%) | 1141 (46%) |
| canon_extract | 3 | 2467 | 1967 (80%) | 3 (0%) |
| persona_details | 3 | 2445 | 1089 (45%) | 347 (14%) |
| audit_meaning | 14 | 2297 | 957 (42%) | 14 (1%) |
| npc_profile | 4 | 2135 | 1046 (49%) | 4 (0%) |
| combat_aftermath | 1 | 1771 | 881 (50%) | 1 (0%) |
| road_event | 1 | 1702 | 793 (47%) | 1 (0%) |
| combat_opening | 1 | 1438 | 855 (59%) | 1 (0%) |
| board_stakes | 1 | 1287 | 406 (32%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| combat_interpret | 1 | 960 | 801 (83%) | 1 (0%) |

The prompts held 662531 tokens; the constant system messages were about 359841 of them (54%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 220013 (33%) and read the rest.
The server's log: 290 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 834 checkpoints made, 260 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 1 failed.

Per game day within reach: 1.00 situations started, 0.50 doors, 0.50 moments, 0.5 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| 2 | 2 (2) | 0 | 0 | 1 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Who let them in at Willowmead - starts, 2 days, 1 stages (within reach)
- day 2: [normal, engine-built] A spring nobody remembers in the Willowmead wetlands - starts, 2 days, 1 stages (within reach)

# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 16 | 6.0 | 8.0 | 3.3 | 7.2 | 3.8 | 5.2 | 5 | 0 |
| search | 16 | 2.9 | 6.0 | 2.9 | 5.7 | 3.6 | 3.4 | 2 | 0 |
| move | 13 | 5.8 | 8.3 | 3.5 | 6.0 | 5.5 | 5.1 | 6 | 0 |
| talk | 4 | 5.5 | 5.7 | 4.4 | 5.3 | 5.2 | 5.0 | 1 | 0 |
| leave | 3 | 6.7 | 6.8 | 3.0 | 6.8 | 5.3 | 5.2 | 0 | 0 |
| wait | 3 | 6.7 | 9.7 | 6.3 | 6.7 | 5.7 | 6.2 | 2 | 0 |
| board | 2 | 5.5 | 8.7 | 5.5 | 8.7 | 6.5 | 7.0 | 1 | 0 |
| hire | 1 | 6.5 | 6.5 | 5.0 | 5.0 | 6.0 | 6.2 | 0 | 0 |
| rest | 1 | 5.7 | 5.7 | 5.7 | 5.7 | 6.0 | 5.0 | 0 | 0 |
| shop | 1 | 12.4 | 12.4 | 2.0 | 2.0 | 6.0 | 12.4 | 2 | 0 |

60 turns in 5.1 minutes; 97% of it in the model; 162 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 2 dropped; 3 turns told by a stand-in, 3 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 21.6 s and p90 33.7 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 12.4 s, shop, 6 calls, at the adventurers' guild house: "I walk over to the meticulous clerk and offer my bronze tower shield f"
- 9.7 s, wait, 9 calls, at the adventurers' guild house: "I sit down on a nearby bench and wait for the others to finish their b"
- 8.7 s, board, 7 calls, at the adventurers' guild house: "I step forward toward the center of the hall and nod at the group, loo"
- 8.4 s, move, 4 calls, at the Greywood: "I keep my pace steady as I head us toward the Adventurers' Guild House"
- 8.3 s, move, 8 calls, at the Willowmead wetlands: "Let's get moving. We need to reach the Adventurers' Guild House before"

Lines by what read them: interpret 42, combat 16, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 56 of 60 (93%) |
| Lines the model wrote | 43 (template 17; model failed 1, 21 s) |
| Lines picking up the passage before | 15 of 60 (25%); in talk 4 of 4 (100%) |
| Contracts taken / finished | 1 / 1 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 3 / 3 (contract 1/0, find 0/1, follow 0/2, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 16 |
| Waits | 3 of 60 (5%) |
| Places visited | 9 |

Turns by goal: contract 16, fight 16, follow 10, idle 5, board 5, report 4, go 2, need 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 14 (id 9, broken 2, first_person 1, script 1, json 1) |
| Machinery mended at the screen | 3287 (dash 3263, escape 1, json 1, wrap 22) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 11.1 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 5 of the game's 35 own lines (14%); most: 'Victory. +# XP' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 3 / 0 / 0 (e.g. '['; '\\'; '}') |
| City ground in the wilds / rain under a roof / weather out of season | 3 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 60 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 9 / 1 / 5 and 263 |
| Fight turns with a foe 10+ levels above the player | 0 of 17, the widest -3 |
| Marks shown from acts (Remembered here) | 0 |
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
| populate_place | 6 | 0 | 0 | 1.4 | 22.7 | 699 | 281 | 3460 | 237.4 | 0 | 149 |
| narrate | 32 | 8 | 9 | 2.1 | 2.6 | 2447 | 178 | 5242 | 119.6 | 0 | 79 |
| combat_narrate | 19 | 5 | 5 | 2.0 | 2.5 | 2764 | 195 | 5588 | 126.1 | 0 | 49 |
| interpret_action | 50 | 0 | 0 | 0.6 | 0.8 | 3659 | 58 | 11275 | 240.2 | 0 | 31 |
| dialogue_frame | 20 | 2 | 2 | 1.0 | 1.2 | 2031 | 61 | 4032 | 135.2 | 0 | 22 |
| player_line | 44 | 12 | 13 | 0.4 | 0.4 | 554 | 24 | 2871 | 137.2 | 0 | 21 |
| combat_aftermath | 12 | 0 | 0 | 1.4 | 1.7 | 1810 | 161 | 4302 | 169.6 | 0 | 17 |
| combat_opening | 10 | 0 | 0 | 1.6 | 1.9 | 1664 | 159 | 3645 | 136.2 | 0 | 16 |
| hire_chat | 13 | 2 | 2 | 0.9 | 1.1 | 2442 | 58 | 4821 | 171.3 | 0 | 14 |
| npc_conversation | 7 | 0 | 0 | 1.6 | 2.6 | 4956 | 113 | 5934 | 122.7 | 0 | 14 |
| exchange | 9 | 2 | 2 | 1.1 | 1.3 | 2639 | 77 | 5137 | 157.4 | 0 | 12 |
| combat_interpret | 16 | 0 | 0 | 0.5 | 0.5 | 954 | 46 | 3117 | 307.6 | 0 | 7 |
| road_event | 3 | 0 | 0 | 2.3 | 2.4 | 1749 | 342 | 3846 | 190.0 | 0 | 7 |
| audit_compare | 20 | 0 | 0 | 0.2 | 0.3 | 225 | 39 | 2381 | 254.3 | 0 | 5 |
| audit_meaning | 20 | 0 | 0 | 0.2 | 0.2 | 150 | 22 | 1851 | 158.3 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.2 | 4.2 | 1036 | 914 | 3038 | 238.8 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.4 | 1.4 | 784 | 231 | 3472 | 200.0 | 0 | 4 |
| overheard | 10 | 0 | 0 | 0.2 | 0.2 | 276 | 16 | 1973 | 284.7 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1419 | 240 | 3602 | 154.4 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 1.8 | 1.8 | 2938 | 259 | 5031 | 210.6 | 0 | 2 |
| ruling | 2 | 0 | 0 | 0.7 | 0.8 | 1205 | 76 | 3624 | 194.1 | 0 | 1 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.7 | 613 | 91 | 3483 | 191.2 | 0 | 1 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 857 | 6 | 3106 | 215.4 | 0 | 1 |

335 attempts for 304 calls, 7.8 minutes in the model in all.

## Fights

26 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 16 | 0.5 | 0.5 | 0 |
| combat_opening | 10 | 1.6 | 2.0 | 0 |
| combat_narrate | 24 | 2.0 | 2.8 | 5 |
| combat_aftermath | 12 | 1.4 | 1.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 100% | 19937 | 21382 | 21382 | 92 | 0% |
| npc_profile | 2 | 100% | 2504 | 2619 | 2619 | 1439 | 0% |
| dialogue_frame | 20 | 90% | 8347 | 10091 | 10602 | 3768 | 0% |
| hire_chat | 13 | 85% | 10075 | 12189 | 13126 | 1982 | 0% |
| canon_extract | 3 | 100% | 3466 | 4162 | 4162 | 834 | 0% |
| exchange | 9 | 78% | 10877 | 15398 | 15398 | 63 | 0% |
| overheard | 10 | 100% | 1124 | 1203 | 1203 | 230 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 100% | 95% | +5 | 21382 | 36345 | 36500 | 21382 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2619 | 2774 | 3000 | 2619 | 0% |
| dialogue_frame | 20 | 90% | 86% | +4 | 10091 | 10715 | 11000 | 10602 | 0% |
| hire_chat | 13 | 85% | 98% | -13 | 12189 | 16275 | 16500 | 13126 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4162 | 3998 | 4000 | 4162 | 0% |
| exchange | 9 | 78% | 90% | -12 | 15398 | 15039 | 15500 | 15398 | 0% |
| overheard | 10 | 100% | 100% | +0 | 1203 | 1326 | 1500 | 1203 | 0% |

Size: 5 of 7 tasks at or below the baseline's p95 (dearer: canon_extract, exchange); npc_conversation's p95 21382 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -13; exchange -12).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 50 | 194700 | 145894 (75%) | 147409 (76%) |
| narrate | 40 | 101154 | 50200 (50%) | 31419 (31%) |
| combat_narrate | 24 | 66857 | 38376 (57%) | 22242 (33%) |
| dialogue_frame | 22 | 46155 | 25699 (56%) | 4190 (9%) |
| hire_chat | 15 | 39430 | 20791 (53%) | 5749 (15%) |
| npc_conversation | 7 | 34783 | 15506 (45%) | 0 (0%) |
| player_line | 56 | 31089 | 7954 (26%) | 6506 (21%) |
| exchange | 11 | 30730 | 12175 (40%) | 6245 (20%) |
| combat_aftermath | 12 | 21667 | 10601 (49%) | 5386 (25%) |
| combat_opening | 10 | 16406 | 8438 (51%) | 0 (0%) |
| combat_interpret | 16 | 15326 | 12836 (84%) | 0 (0%) |
| road_event | 3 | 5253 | 2375 (45%) | 0 (0%) |
| audit_compare | 20 | 4498 | 2309 (51%) | 0 (0%) |
| populate_place | 6 | 4367 | 1531 (35%) | 0 (0%) |
| audit_meaning | 20 | 3165 | 1342 (42%) | 0 (0%) |
| thread_telling | 1 | 2938 | 397 (14%) | 0 (0%) |
| overheard | 10 | 2762 | 2189 (79%) | 0 (0%) |
| canon_extract | 3 | 2671 | 1940 (73%) | 0 (0%) |
| ruling | 2 | 2410 | 1155 (48%) | 0 (0%) |
| persona_details | 3 | 2323 | 1102 (47%) | 0 (0%) |
| moment | 1 | 1419 | 747 (53%) | 0 (0%) |
| npc_profile | 2 | 1226 | 510 (42%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |

The prompts held 632365 tokens; the constant system messages were about 364561 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 229146 (36%) and read the rest.
The server's log: 335 prompts; 242 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 824 checkpoints made, 29 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

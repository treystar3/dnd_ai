# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| search | 23 | 4.3 | 9.4 | 4.1 | 9.2 | 3.8 | 5.3 | 5 | 0 |
| fight | 19 | 7.5 | 9.3 | 4.0 | 8.0 | 3.6 | 7.2 | 2 | 0 |
| move | 9 | 6.3 | 9.9 | 4.6 | 6.2 | 4.3 | 6.7 | 3 | 0 |
| leave | 3 | 7.0 | 8.4 | 7.0 | 8.4 | 5.3 | 6.9 | 0 | 0 |
| talk | 2 | 4.2 | 7.4 | 4.2 | 7.4 | 4.5 | 5.6 | 0 | 0 |
| hire | 1 | 11.1 | 11.1 | 7.3 | 7.3 | 8.0 | 10.8 | 0 | 0 |
| board | 1 | 9.7 | 9.7 | 9.6 | 9.6 | 6.0 | 9.5 | 0 | 0 |
| pick_up | 1 | 4.5 | 4.5 | 4.5 | 4.5 | 4.0 | 4.4 | 0 | 0 |
| shop | 1 | 15.0 | 15.0 | 8.8 | 8.8 | 9.0 | 14.3 | 0 | 0 |

60 turns in 6.8 minutes; 96% of it in the model; 145 embedding calls taking 1.7 s; 1 calls on background threads.
The budget: 5 optional calls deferred and 6 dropped; 2 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 18.5 s and p90 36.7 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 16.8 s, move, 6 calls, at the King's Road between Willowmead and Parth: "I start heading back toward the Adventurers' Guild House."
- 15.0 s, shop, 9 calls, at the adventurers' guild house: "I walk over to the spectacles clerk and hold out the grey wool robe, a"
- 14.7 s, fight, 6 calls, at the King's Road between Parth and Willowmead: "I strike at bandit 1."
- 13.3 s, fight, 7 calls, at the Willowmead wetlands: "I go for lizardfolk 1."
- 11.4 s, search, 10 calls, at the Willowmead wetlands: "I wipe my blade and tell the group we need to keep searching for those"

Lines by what read them: interpret 38, combat 19, hire 2, yielded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 58 of 60 (97%) |
| Lines the model wrote | 40 (template 20; model failed 1, 28 s) |
| Lines picking up the passage before | 12 of 60 (20%); in talk 1 of 2 (50%) |
| Contracts taken / finished | 1 / 1 |
| Situations met / followed / ended by the player | 1 / 1 / 1 |
| Goals finished / given up | 8 / 0 (contract 2/0, find 1/0, follow 1/0, go 1/0, hunt 1/0, report 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 19 |
| Waits | 0 of 60 (0%) |
| Places visited | 8 |

Turns by goal: fight 19, contract 14, hunt 7, follow 6, idle 5, report 5, go 1, board 1, stop 1, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 6 (id 6) |
| Machinery mended at the screen | 3928 (dash 3921, wrap 7) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you aren't carrying anything matching 'gear'.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 16.7 |
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
| Lines shown 5+ times word for word (digits aside) | 2 lines, 13 times; 13 of the game's 44 own lines (30%); most: 'Victory. +# XP' x8; 'Victory. +# XP, #₲ #Ş #₵' x5 |
| Refusals shown / then acted out in the passage / never logged | 1 / 0 / 1 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 2 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 5 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 86 |
| Matters the player ended: pursued / by accident | 1 / 0 |
| Fights won / for +0 XP / XP median and most | 13 / 1 / 5 and 68 |
| Fight turns with a foe 10+ levels above the player | 0 of 19, the widest -7 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 4 | 0 | 0 | 1.9 | 124.1 | 699 | 284 | 1233 | 164.4 | 0 | 129 |
| narrate | 27 | 3 | 3 | 2.6 | 3.5 | 2540 | 188 | 2738 | 112.5 | 0 | 80 |
| combat_narrate | 19 | 2 | 2 | 2.9 | 3.6 | 3002 | 195 | 2675 | 117.3 | 0 | 63 |
| combat_aftermath | 21 | 0 | 0 | 2.1 | 2.7 | 1936 | 196 | 2325 | 149.8 | 0 | 45 |
| interpret_action | 43 | 0 | 0 | 1.0 | 1.4 | 3558 | 53 | 5224 | 194.8 | 0 | 45 |
| combat_opening | 12 | 0 | 0 | 2.3 | 2.9 | 1744 | 180 | 2013 | 115.1 | 0 | 29 |
| player_line | 41 | 5 | 6 | 0.6 | 0.7 | 543 | 22 | 1431 | 96.3 | 0 | 28 |
| dialogue_frame | 14 | 2 | 2 | 1.4 | 1.9 | 2271 | 53 | 2253 | 126.5 | 0 | 23 |
| hire_chat | 14 | 0 | 0 | 1.4 | 1.6 | 2585 | 53 | 2485 | 151.7 | 0 | 20 |
| npc_conversation | 5 | 0 | 0 | 2.6 | 5.5 | 5224 | 133 | 3919 | 90.7 | 0 | 17 |
| combat_interpret | 19 | 0 | 0 | 0.9 | 0.9 | 951 | 46 | 1483 | 222.4 | 0 | 16 |
| exchange | 6 | 3 | 4 | 1.5 | 1.8 | 2598 | 93 | 2912 | 139.3 | 0 | 14 |
| road_event | 2 | 0 | 0 | 2.7 | 3.4 | 1785 | 365 | 2156 | 167.1 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.9 | 1.9 | 795 | 238 | 1894 | 165.1 | 0 | 6 |
| audit_meaning | 15 | 0 | 0 | 0.3 | 0.4 | 148 | 23 | 1088 | 120.5 | 0 | 5 |
| audit_compare | 15 | 0 | 0 | 0.3 | 0.4 | 227 | 39 | 1406 | 231.1 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.9 | 4.9 | 1036 | 893 | 1493 | 213.8 | 0 | 5 |
| overheard | 10 | 0 | 0 | 0.3 | 0.3 | 270 | 16 | 1029 | 253.6 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.8 | 2.8 | 1458 | 253 | 2160 | 122.0 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.5 | 2.5 | 2897 | 239 | 2868 | 159.5 | 0 | 3 |
| ruling | 2 | 0 | 0 | 1.0 | 1.3 | 1254 | 65 | 2011 | 122.3 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.7 | 1.1 | 633 | 87 | 1862 | 151.6 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.0 | 1.0 | 890 | 89 | 1886 | 163.0 | 0 | 1 |
| canon_extract | 1 | 0 | 0 | 0.7 | 0.7 | 815 | 2 | 1213 | 133.3 | 0 | 1 |
| plausible_object | 1 | 0 | 0 | 0.3 | 0.3 | 372 | 20 | 1576 | 188.7 | 0 | 0 |
| work_offer_read | 1 | 0 | 0 | 0.3 | 0.3 | 100 | 19 | 599 | 139.7 | 0 | 0 |

296 attempts for 281 calls, 9.2 minutes in the model in all.

## Fights

31 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 19 | 0.9 | 1.0 | 0 |
| combat_opening | 12 | 2.3 | 2.9 | 0 |
| combat_narrate | 21 | 2.9 | 4.4 | 2 |
| combat_aftermath | 21 | 2.1 | 2.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 5 | 100% | 20564 | 22158 | 22158 | 61 | 0% |
| npc_profile | 2 | 100% | 2499 | 2743 | 2743 | 1434 | 0% |
| dialogue_frame | 14 | 93% | 9675 | 10392 | 12043 | 3792 | 0% |
| work_offer_read | 1 | 100% | 340 | 340 | 340 | 91 | 0% |
| hire_chat | 14 | 100% | 10425 | 12854 | 13260 | 1461 | 4% |
| canon_extract | 1 | 100% | 3304 | 3304 | 3304 | 672 | 0% |
| exchange | 6 | 50% | 10504 | 12692 | 12692 | 63 | 17% |
| overheard | 10 | 100% | 1095 | 1187 | 1187 | 201 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 5 | 100% | 95% | +5 | 22158 | 36345 | 36500 | 22158 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2743 | 2774 | 3000 | 2743 | 0% |
| dialogue_frame | 14 | 93% | 86% | +7 | 10392 | 10715 | 11000 | 12043 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 340 | 780 | 1000 | 340 | 0% |
| hire_chat | 14 | 100% | 98% | +2 | 12854 | 16275 | 16500 | 13260 | 4% |
| canon_extract | 1 | 100% | 100% | +0 | 3304 | 3998 | 4000 | 3304 | 0% |
| exchange | 6 | 50% | 90% | -40 | 12692 | 15039 | 15500 | 12692 | 17% |
| overheard | 10 | 100% | 100% | +0 | 1187 | 1326 | 1500 | 1187 | 0% |

Size: 8 of 8 tasks at or below the baseline's p95; npc_conversation's p95 22158 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (exchange -40).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 43 | 165207 | 125243 (76%) | 123765 (75%) |
| narrate | 30 | 77185 | 42829 (55%) | 22411 (29%) |
| combat_narrate | 21 | 63560 | 40150 (63%) | 6084 (10%) |
| combat_aftermath | 21 | 40512 | 22376 (55%) | 15244 (38%) |
| hire_chat | 14 | 37073 | 22704 (61%) | 1581 (4%) |
| dialogue_frame | 16 | 35978 | 21688 (60%) | 3843 (11%) |
| npc_conversation | 5 | 26425 | 12348 (47%) | 0 (0%) |
| player_line | 46 | 25403 | 6562 (26%) | 2526 (10%) |
| exchange | 9 | 23011 | 10085 (44%) | 9963 (43%) |
| combat_opening | 12 | 20797 | 12338 (59%) | 0 (0%) |
| combat_interpret | 19 | 18204 | 15270 (84%) | 0 (0%) |
| road_event | 2 | 3571 | 1582 (44%) | 0 (0%) |
| audit_compare | 15 | 3388 | 1729 (51%) | 0 (0%) |
| thread_telling | 1 | 2897 | 397 (14%) | 0 (0%) |
| populate_place | 4 | 2808 | 1017 (36%) | 0 (0%) |
| overheard | 10 | 2735 | 2197 (80%) | 0 (0%) |
| ruling | 2 | 2508 | 1158 (46%) | 0 (0%) |
| persona_details | 3 | 2356 | 1100 (47%) | 345 (15%) |
| audit_meaning | 15 | 2334 | 1010 (43%) | 0 (0%) |
| moment | 1 | 1458 | 748 (51%) | 0 (0%) |
| npc_profile | 2 | 1266 | 514 (41%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| board_stakes | 1 | 890 | 373 (42%) | 0 (0%) |
| canon_extract | 1 | 815 | 649 (80%) | 0 (0%) |
| plausible_object | 1 | 372 | 286 (77%) | 0 (0%) |
| work_offer_read | 1 | 100 | 73 (73%) | 0 (0%) |

The prompts held 561889 tokens; the constant system messages were about 344920 of them (61%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 185762 (33%) and read the rest.
The server's log: 296 prompts; 221 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 724 checkpoints made, 18 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 1 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

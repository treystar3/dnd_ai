# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.14 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 16 | 9.7 | 14.7 | 6.0 | 9.2 | 6.6 | 9.7 | 6 | 0 |
| talk | 14 | 4.2 | 9.0 | 4.2 | 8.9 | 3.6 | 5.7 | 2 | 0 |
| leave | 12 | 6.8 | 13.6 | 6.0 | 10.0 | 5.5 | 8.2 | 4 | 0 |
| search | 10 | 3.8 | 5.7 | 3.7 | 5.7 | 3.0 | 4.5 | 1 | 0 |
| fight | 3 | 10.6 | 14.8 | 6.1 | 8.0 | 5.0 | 10.9 | 0 | 0 |
| board | 2 | 6.2 | 9.0 | 6.2 | 9.0 | 5.5 | 7.4 | 0 | 0 |
| wait | 2 | 5.7 | 8.7 | 5.3 | 5.6 | 4.5 | 6.9 | 1 | 0 |
| hire | 1 | 5.4 | 5.4 | 5.3 | 5.3 | 5.0 | 5.2 | 0 | 0 |

60 turns in 7.7 minutes; 96% of it in the model; 257 embedding calls taking 2.2 s; 3 calls on background threads.
The budget: 4 optional calls deferred and 6 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 20.4 s and p90 44.5 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 16.1 s, talk, 5 calls, at Parth: "I look him in the eye and say, "I need your help with Cheap and then d"
- 15.8 s, leave, 6 calls, at the adventurers' guild house: "I grab the coins from the desk and tell them we're moving out."
- 15.0 s, move, 6 calls, at the trading square: "I tell Ella we're headed to the Shipwreck Shoals and start making our "
- 14.8 s, fight, 6 calls, at the Salt Road between Parth and Kelpmoor: "I use Cleaving Sweep on bandit 1."
- 14.7 s, move, 12 calls, at the Willowmead wetlands: "I wipe my blade on a dry reed and tell the group we're heading back to"

Lines by what read them: interpret 53, combat 3, yielded 2, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 52 (template 8; model failed 2, 42 s) |
| Lines picking up the passage before | 25 of 60 (42%); in talk 7 of 14 (50%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 2 / 1 / 0 |
| Goals finished / given up | 6 / 3 (contract 2/0, find 0/1, follow 0/2, go 1/0, report 2/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 3 |
| Waits | 2 of 60 (3%) |
| Places visited | 10 |

Turns by goal: idle 19, contract 14, follow 10, report 6, board 3, fight 3, cont 2, revisit 2, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 5, script 2) |
| Machinery mended at the screen | 744 (dash 740, wrap 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("orric yrlaros - genasi priest, rank f, level #: a cleric who has seen ") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 1 |
| Attempts the world made room for / said no to in the world | 3 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 3 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 21.4 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 1 / 1 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 40 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '*') |
| City ground in the wilds / rain under a roof / weather out of season | 4 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | captive 0 of 5; hire 0 of 42; townsfolk 0 of 4 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 3 / 0 / 8 and 62 |
| Fight turns with a foe 10+ levels above the player | 0 of 3, the widest -7 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 1 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 4 the ink-stained girl contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 9 | 0 | 0 | 1.8 | 123.4 | 693 | 279 | 1657 | 165.5 | 0 | 275 |
| narrate | 37 | 5 | 5 | 2.7 | 3.8 | 2561 | 191 | 2639 | 114.4 | 0 | 117 |
| npc_conversation | 21 | 1 | 1 | 2.5 | 6.4 | 5169 | 138 | 4002 | 115.5 | 0 | 78 |
| interpret_action | 60 | 0 | 0 | 1.1 | 1.5 | 4279 | 68 | 5376 | 206.3 | 0 | 69 |
| player_line | 54 | 21 | 23 | 0.6 | 0.7 | 552 | 22 | 1535 | 101.3 | 0 | 42 |
| dialogue_frame | 24 | 3 | 3 | 1.4 | 1.7 | 2313 | 49 | 2328 | 124.9 | 0 | 40 |
| hire_chat | 17 | 2 | 2 | 1.3 | 1.6 | 2883 | 50 | 2874 | 160.3 | 0 | 25 |
| exchange | 10 | 3 | 4 | 1.5 | 2.5 | 3397 | 114 | 3604 | 147.8 | 0 | 22 |
| road_event | 3 | 0 | 0 | 3.6 | 4.0 | 1807 | 373 | 2044 | 147.5 | 0 | 11 |
| combat_aftermath | 4 | 0 | 0 | 2.6 | 2.9 | 1992 | 279 | 2307 | 151.9 | 0 | 10 |
| combat_narrate | 3 | 0 | 0 | 3.2 | 4.5 | 2904 | 197 | 2587 | 112.7 | 0 | 10 |
| board_stakes | 4 | 0 | 0 | 3.1 | 3.8 | 1147 | 289 | 2010 | 177.2 | 0 | 9 |
| audit_compare | 26 | 0 | 0 | 0.3 | 0.4 | 229 | 41 | 1550 | 225.8 | 0 | 9 |
| audit_meaning | 26 | 0 | 0 | 0.3 | 0.4 | 164 | 23 | 1023 | 129.5 | 0 | 9 |
| combat_opening | 3 | 0 | 0 | 2.6 | 2.8 | 1716 | 184 | 2027 | 116.0 | 0 | 7 |
| npc_profile | 6 | 0 | 0 | 0.9 | 1.0 | 635 | 82 | 1898 | 155.7 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.8 | 1.9 | 770 | 239 | 1957 | 168.8 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.2 | 5.2 | 1036 | 976 | 1663 | 212.1 | 0 | 5 |
| overheard | 13 | 0 | 0 | 0.3 | 0.3 | 272 | 16 | 1083 | 270.5 | 0 | 4 |
| ruling | 3 | 0 | 0 | 1.0 | 1.0 | 1207 | 66 | 2271 | 152.4 | 0 | 3 |
| canon_extract | 5 | 0 | 0 | 0.5 | 0.8 | 824 | 2 | 1553 | 153.8 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.4 | 2.4 | 2936 | 262 | 3255 | 182.6 | 0 | 2 |
| combat_interpret | 3 | 0 | 0 | 0.8 | 0.9 | 969 | 48 | 1614 | 266.7 | 0 | 2 |
| work_offer_read | 2 | 0 | 0 | 0.3 | 0.3 | 113 | 19 | 629 | 125.8 | 0 | 1 |
| plausible_object | 1 | 0 | 0 | 0.3 | 0.3 | 347 | 20 | 1614 | 166.7 | 0 | 0 |

374 attempts for 339 calls, 12.8 minutes in the model in all.

## Fights

6 rounds with a fight call; 2.2 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 3 | 0.8 | 0.9 | 0 |
| combat_opening | 3 | 2.6 | 2.8 | 0 |
| combat_narrate | 3 | 3.2 | 4.5 | 0 |
| combat_aftermath | 4 | 2.6 | 2.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 21 | 95% | 20607 | 23271 | 23335 | 64 | 2% |
| npc_profile | 6 | 100% | 2548 | 2786 | 2786 | 1483 | 0% |
| dialogue_frame | 24 | 88% | 9700 | 10896 | 12272 | 3824 | 0% |
| work_offer_read | 2 | 100% | 366 | 462 | 462 | 117 | 0% |
| hire_chat | 17 | 88% | 11505 | 13360 | 14480 | 1451 | 0% |
| canon_extract | 5 | 100% | 3346 | 4009 | 4009 | 714 | 0% |
| exchange | 10 | 70% | 13773 | 14745 | 14745 | 63 | 10% |
| overheard | 13 | 100% | 1114 | 1189 | 1243 | 220 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 21 | 95% | 95% | +0 | 23271 | 36345 | 36500 | 23335 | 2% |
| npc_profile | 6 | 100% | 100% | +0 | 2786 | 2774 | 3000 | 2786 | 0% |
| dialogue_frame | 24 | 88% | 86% | +1 | 10896 | 10715 | 11000 | 12272 | 0% |
| work_offer_read | 2 | 100% | 100% | +0 | 462 | 780 | 1000 | 462 | 0% |
| hire_chat | 17 | 88% | 98% | -10 | 13360 | 16275 | 16500 | 14480 | 0% |
| canon_extract | 5 | 100% | 100% | +0 | 4009 | 3998 | 4000 | 4009 | 0% |
| exchange | 10 | 70% | 90% | -20 | 14745 | 15039 | 15500 | 14745 | 10% |
| overheard | 13 | 100% | 100% | +0 | 1189 | 1326 | 1500 | 1243 | 0% |

Size: 5 of 8 tasks at or below the baseline's p95 (dearer: npc_profile, dialogue_frame, canon_extract); npc_conversation's p95 23271 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -10; exchange -20).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 60 | 258023 | 178787 (69%) | 185637 (72%) |
| npc_conversation | 22 | 114586 | 53952 (47%) | 6205 (5%) |
| narrate | 42 | 109158 | 59847 (55%) | 21002 (19%) |
| dialogue_frame | 27 | 61361 | 36434 (59%) | 6242 (10%) |
| hire_chat | 19 | 54529 | 30876 (57%) | 5788 (11%) |
| exchange | 13 | 42485 | 14602 (34%) | 13287 (31%) |
| player_line | 75 | 41901 | 10852 (26%) | 11672 (28%) |
| combat_narrate | 3 | 8979 | 5672 (63%) | 0 (0%) |
| combat_aftermath | 4 | 7930 | 4275 (54%) | 2151 (27%) |
| populate_place | 9 | 6280 | 2297 (37%) | 251 (4%) |
| audit_compare | 26 | 5986 | 3048 (51%) | 0 (0%) |
| road_event | 3 | 5399 | 2376 (44%) | 0 (0%) |
| combat_opening | 3 | 5264 | 3067 (58%) | 0 (0%) |
| board_stakes | 4 | 4474 | 1551 (35%) | 0 (0%) |
| audit_meaning | 26 | 4336 | 1755 (40%) | 0 (0%) |
| canon_extract | 5 | 4261 | 3250 (76%) | 0 (0%) |
| npc_profile | 6 | 3830 | 1551 (41%) | 0 (0%) |
| ruling | 3 | 3704 | 1743 (47%) | 0 (0%) |
| overheard | 13 | 3567 | 2860 (80%) | 0 (0%) |
| thread_telling | 1 | 2936 | 399 (14%) | 0 (0%) |
| combat_interpret | 3 | 2914 | 2423 (83%) | 0 (0%) |
| persona_details | 3 | 2339 | 1093 (47%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| plausible_object | 1 | 347 | 290 (84%) | 0 (0%) |
| work_offer_read | 2 | 227 | 137 (60%) | 0 (0%) |

The prompts held 755852 tokens; the constant system messages were about 423631 of them (56%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 252235 (33%) and read the rest.
The server's log: 374 prompts; 271 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 935 checkpoints made, 56 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 4 situations started (4 within reach of the player), 0 stages advanced, 2 ended (0 by the player, 1 settled by others, 1 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 1 failed.

Per game day within reach: 1.33 situations started, 0.33 doors, 0.33 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| 3 | 1 (1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | 2 (2) | 0 | 2 | 0 | 0 | 0 | 0 | 1 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)
- day 3: [normal, engine-built] A quarrel in Parth - starts, 1 days, 1 stages (within reach)
- day 4: [normal, engine-built] The land agent's party at the Shipwreck Shoals - starts, 1 days, 1 stages (within reach)
- day 4: [normal, engine-built] Hard labour at Greyhollow - starts, 1 days, 1 stages (within reach)

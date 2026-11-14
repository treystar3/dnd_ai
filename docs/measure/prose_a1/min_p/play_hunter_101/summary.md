# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| forage | 18 | 2.2 | 2.9 | 2.2 | 2.9 | 2.4 | 2.2 | 1 | 0 |
| move | 9 | 5.3 | 7.7 | 3.4 | 5.6 | 5.0 | 5.1 | 2 | 0 |
| fight | 9 | 3.5 | 5.6 | 2.4 | 3.5 | 3.2 | 3.9 | 0 | 0 |
| search | 7 | 2.5 | 2.8 | 2.5 | 2.8 | 2.1 | 2.3 | 0 | 0 |
| talk | 4 | 6.1 | 10.0 | 5.4 | 6.1 | 4.5 | 6.0 | 0 | 0 |
| leave | 4 | 3.2 | 7.9 | 3.2 | 5.6 | 4.0 | 3.9 | 0 | 0 |
| look | 4 | 4.1 | 4.6 | 4.1 | 4.6 | 4.0 | 3.2 | 0 | 0 |
| board | 3 | 4.0 | 7.2 | 4.0 | 4.7 | 6.7 | 4.9 | 0 | 0 |
| hire | 2 | 4.6 | 6.3 | 4.5 | 4.9 | 5.5 | 5.2 | 0 | 0 |

60 turns in 3.7 minutes; 97% of it in the model; 162 embedding calls taking 0.8 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 4 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 13.8 s and p90 28.0 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.5 s, move, 6 calls, at the Willowmead wetlands: "Let's get moving; we need to head back to the Adventurers' Guild House"
- 10.0 s, talk, 8 calls, at the adventurers' guild house: "Hey, girl: those four lizardfolks in the wetlands are dead. I'm here t"
- 7.9 s, leave, 8 calls, at the adventurers' guild house: "I give a curt nod to Alwick and Gran, then turn toward the door to hea"
- 7.7 s, move, 11 calls, at the adventurers' guild house: "I head toward the exit and tell my companions we're moving out for the"
- 7.2 s, move, 7 calls, at the Greywood: "I lead the group back toward the Adventurers' Guild House."

Lines by what read them: interpret 46, combat 9, hire 3, yielded 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 58 of 60 (97%) |
| Lines the model wrote | 49 (template 11; model failed 1, 21 s) |
| Lines picking up the passage before | 12 of 60 (20%); in talk 2 of 4 (50%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 1 |
| Goals finished / given up | 4 / 1 (contract 1/1, go 2/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 9 |
| Waits | 0 of 60 (0%) |
| Places visited | 5 |

Turns by goal: contract 30, idle 9, fight 9, board 4, report 4, go 2, cont 1, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 0 |
| Machinery mended at the screen | 1814 (dash 1809, wrap 5) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 0 |
| Attempts the world made room for / said no to in the world | 5 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 3, ruled 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 71.4 |
| Parts made different by an attempt (blocked, lit, cleared...) | 2 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 38 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 34 ['surface', 'under']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 1 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 46; townsfolk 0 of 1 |
| Matters the player ended: pursued / by accident | 0 / 1 (by accident: Cheap and then dear in Parth) |
| Fights won / for +0 XP / XP median and most | 6 / 1 / 7 and 18 |
| Fight turns with a foe 10+ levels above the player | 0 of 9, the widest -8 |
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
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 21 the ink-stained girl contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 3 | 0 | 0 | 1.4 | 73.3 | 693 | 287 | 3540 | 246.6 | 0 | 76 |
| narrate | 35 | 0 | 0 | 1.7 | 2.5 | 2377 | 142 | 4534 | 132.9 | 0 | 61 |
| interpret_action | 50 | 0 | 0 | 0.5 | 0.9 | 3634 | 45 | 10561 | 230.1 | 0 | 30 |
| player_line | 50 | 10 | 11 | 0.3 | 0.4 | 517 | 24 | 2892 | 136.3 | 0 | 21 |
| dialogue_frame | 19 | 2 | 2 | 0.9 | 1.2 | 2087 | 55 | 4064 | 146.2 | 0 | 20 |
| npc_conversation | 9 | 0 | 0 | 1.8 | 2.6 | 5170 | 150 | 6010 | 136.5 | 0 | 20 |
| combat_narrate | 9 | 0 | 0 | 1.9 | 2.8 | 2778 | 172 | 4575 | 143.0 | 0 | 17 |
| combat_opening | 6 | 0 | 0 | 1.6 | 2.0 | 1639 | 170 | 3831 | 133.5 | 0 | 11 |
| combat_aftermath | 7 | 0 | 0 | 1.4 | 1.7 | 1819 | 168 | 4039 | 167.9 | 0 | 10 |
| exchange | 8 | 0 | 0 | 1.2 | 1.3 | 3192 | 84 | 4789 | 161.5 | 0 | 9 |
| hire_chat | 10 | 0 | 0 | 0.9 | 1.0 | 2673 | 54 | 4569 | 184.7 | 0 | 9 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1036 | 943 | 3012 | 230.4 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.4 | 1.4 | 784 | 231 | 3421 | 200.0 | 0 | 4 |
| combat_interpret | 9 | 0 | 0 | 0.5 | 0.5 | 966 | 48 | 3215 | 301.5 | 0 | 4 |
| audit_compare | 14 | 0 | 0 | 0.2 | 0.3 | 226 | 38 | 2414 | 259.9 | 0 | 4 |
| ruling | 4 | 0 | 0 | 1.0 | 1.1 | 1264 | 120 | 3807 | 229.6 | 0 | 3 |
| audit_meaning | 14 | 0 | 0 | 0.2 | 0.2 | 168 | 24 | 1946 | 175.7 | 0 | 3 |
| road_event | 1 | 0 | 0 | 2.1 | 2.1 | 1700 | 300 | 3935 | 183.5 | 0 | 2 |
| discovery | 1 | 1 | 2 | 0.8 | 1.2 | 2667 | 119 | 6305 | 200.3 | 0 | 2 |
| overheard | 8 | 0 | 0 | 0.2 | 0.2 | 282 | 16 | 1930 | 291.1 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.9 | 656 | 103 | 3556 | 179.1 | 0 | 2 |
| canon_extract | 1 | 0 | 0 | 0.3 | 0.3 | 998 | 2 | 3209 | 153.8 | 0 | 0 |

277 attempts for 264 calls, 5.2 minutes in the model in all.

## Fights

15 rounds with a fight call; 2.1 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 9 | 0.5 | 0.5 | 0 |
| combat_opening | 6 | 1.6 | 2.1 | 0 |
| combat_narrate | 9 | 1.9 | 3.0 | 0 |
| combat_aftermath | 7 | 1.4 | 1.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 9 | 100% | 20693 | 21937 | 21937 | 97 | 0% |
| npc_profile | 2 | 100% | 2504 | 2954 | 2954 | 1439 | 0% |
| dialogue_frame | 19 | 95% | 8378 | 10615 | 10711 | 3665 | 0% |
| hire_chat | 10 | 100% | 10800 | 13175 | 13175 | 1978 | 0% |
| canon_extract | 1 | 100% | 4128 | 4128 | 4128 | 1496 | 0% |
| exchange | 8 | 100% | 13247 | 13639 | 13639 | 63 | 0% |
| overheard | 8 | 100% | 1145 | 1213 | 1213 | 251 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 9 | 100% | 95% | +5 | 21937 | 36345 | 36500 | 21937 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2954 | 2774 | 3000 | 2954 | 0% |
| dialogue_frame | 19 | 95% | 86% | +9 | 10615 | 10715 | 11000 | 10711 | 0% |
| hire_chat | 10 | 100% | 98% | +2 | 13175 | 16275 | 16500 | 13175 | 0% |
| canon_extract | 1 | 100% | 100% | +0 | 4128 | 3998 | 4000 | 4128 | 0% |
| exchange | 8 | 100% | 90% | +10 | 13639 | 15039 | 15500 | 13639 | 0% |
| overheard | 8 | 100% | 100% | +0 | 1213 | 1326 | 1500 | 1213 | 0% |

Size: 5 of 7 tasks at or below the baseline's p95 (dearer: npc_profile, canon_extract); npc_conversation's p95 21937 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 50 | 193966 | 145776 (75%) | 145130 (75%) |
| narrate | 35 | 83859 | 43296 (52%) | 8282 (10%) |
| npc_conversation | 9 | 46194 | 19962 (43%) | 0 (0%) |
| dialogue_frame | 21 | 43909 | 24931 (57%) | 3948 (9%) |
| player_line | 60 | 31935 | 8552 (27%) | 5192 (16%) |
| hire_chat | 10 | 27130 | 13941 (51%) | 0 (0%) |
| combat_narrate | 9 | 25168 | 14133 (56%) | 0 (0%) |
| exchange | 8 | 23712 | 8885 (37%) | 0 (0%) |
| combat_aftermath | 7 | 12808 | 6195 (48%) | 1810 (14%) |
| combat_opening | 6 | 9923 | 5082 (51%) | 0 (0%) |
| combat_interpret | 9 | 8672 | 7244 (84%) | 0 (0%) |
| discovery | 2 | 5334 | 882 (17%) | 2587 (49%) |
| ruling | 4 | 5170 | 2303 (45%) | 0 (0%) |
| audit_compare | 14 | 3210 | 1636 (51%) | 0 (0%) |
| audit_meaning | 14 | 2362 | 953 (40%) | 0 (0%) |
| persona_details | 3 | 2323 | 1102 (47%) | 0 (0%) |
| overheard | 8 | 2239 | 1761 (79%) | 0 (0%) |
| populate_place | 3 | 2078 | 760 (37%) | 0 (0%) |
| road_event | 1 | 1700 | 791 (47%) | 0 (0%) |
| npc_profile | 2 | 1312 | 512 (39%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| canon_extract | 1 | 998 | 636 (64%) | 0 (0%) |

The prompts held 535038 tokens; the constant system messages were about 309827 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 166949 (31%) and read the rest.
The server's log: 277 prompts; 209 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 686 checkpoints made, 25 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 0 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 1 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 0.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 1 | 1 | 1 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.13 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 16 | 7.5 | 12.7 | 5.7 | 10.2 | 4.4 | 7.4 | 7 | 0 |
| talk | 13 | 6.8 | 11.4 | 6.4 | 9.8 | 3.5 | 7.1 | 1 | 0 |
| leave | 9 | 6.0 | 10.5 | 6.0 | 9.1 | 4.1 | 6.4 | 0 | 0 |
| search | 9 | 3.9 | 4.7 | 4.3 | 4.7 | 3.6 | 3.9 | 0 | 0 |
| fight | 8 | 5.3 | 5.8 | 4.4 | 5.5 | 3.1 | 6.0 | 3 | 0 |
| board | 2 | 7.4 | 9.9 | 7.3 | 7.9 | 6.5 | 8.5 | 1 | 0 |
| improv | 1 | 8.0 | 8.0 | 8.0 | 8.0 | 6.0 | 7.9 | 0 | 0 |
| look | 1 | 13.4 | 13.4 | 7.5 | 7.5 | 6.0 | 13.2 | 0 | 0 |
| wait | 1 | 6.8 | 6.8 | 3.8 | 3.8 | 3.0 | 6.8 | 0 | 0 |

60 turns in 6.9 minutes; 96% of it in the model; 179 embedding calls taking 1.8 s; 2 calls on background threads.
The budget: 3 optional calls deferred and 8 dropped; 3 turns told by a stand-in, 3 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 17.4 s and p90 36.7 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 21.4 s, move, 6 calls, at the Knotted Rope: "I look at the gnome and ask how quickly we can get to Kelpmoor."
- 17.8 s, talk, 2 calls, at the adventurers' guild house: "I nod at her and ask what else has been coming across the desk lately."
- 15.0 s, fight, 6 calls, at the Salt Road between Parth and Kelpmoor: "I use Cleaving Sweep on merrow."
- 15.0 s, leave, 4 calls, at the trading square: "I give the merchant a sharp nod and turn back to the group. "Let's get"
- 13.4 s, look, 6 calls, at Kelpmoor: "I push through the crowd towards the trading square."

Lines by what read them: interpret 50, combat 8, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 49 (template 11; model failed 1, 32 s) |
| Lines picking up the passage before | 15 of 60 (25%); in talk 4 of 13 (31%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 4 / 3 (contract 0/2, follow 0/1, go 1/0, hunt 2/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 8 |
| Waits | 1 of 60 (2%) |
| Places visited | 8 |

Turns by goal: idle 21, hunt 12, follow 10, fight 8, board 4, revisit 2, cont 1, clarify 1, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 8 (broken 3, id 2, json 1, script 1, first_person 1) |
| Machinery mended at the screen | 1098 (dash 1092, stage 2, wrap 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("rurgar ormin - dwarf mage, rank e, level #: a sullen spellcaster; quie") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 3 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 43 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 4 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 51 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 4 / 1 / 3 and 359 |
| Fight turns with a foe 10+ levels above the player | 0 of 8, the widest -2 |
| Marks shown from acts (Remembered here) | 1 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 0 / 0 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 8 | 0 | 0 | 1.8 | 87.8 | 669 | 295 | 1964 | 211.5 | 0 | 185 |
| npc_conversation | 18 | 1 | 1 | 3.6 | 11.4 | 4730 | 208 | 3938 | 98.9 | 0 | 102 |
| narrate | 24 | 4 | 5 | 2.5 | 3.5 | 2547 | 182 | 2690 | 121.6 | 0 | 75 |
| interpret_action | 53 | 0 | 0 | 1.0 | 1.4 | 4097 | 65 | 5108 | 219.2 | 0 | 59 |
| player_line | 50 | 9 | 10 | 0.6 | 0.7 | 503 | 23 | 1563 | 103.4 | 0 | 32 |
| combat_narrate | 8 | 2 | 2 | 2.5 | 3.3 | 2952 | 214 | 2987 | 127.2 | 0 | 25 |
| dialogue_frame | 13 | 3 | 3 | 1.6 | 1.8 | 2259 | 70 | 2343 | 120.5 | 0 | 25 |
| hire_chat | 8 | 1 | 1 | 1.3 | 1.4 | 2633 | 52 | 2736 | 163.6 | 0 | 12 |
| exchange | 6 | 0 | 0 | 1.7 | 2.0 | 3157 | 93 | 2643 | 146.4 | 0 | 11 |
| combat_aftermath | 5 | 0 | 0 | 2.0 | 2.4 | 1917 | 179 | 2301 | 151.6 | 0 | 10 |
| combat_opening | 4 | 0 | 0 | 2.3 | 2.4 | 1641 | 168 | 1963 | 115.6 | 0 | 9 |
| thread_telling | 3 | 0 | 0 | 2.8 | 3.0 | 2981 | 306 | 2917 | 168.1 | 0 | 8 |
| moment | 3 | 0 | 0 | 2.5 | 2.9 | 1419 | 218 | 1800 | 132.4 | 0 | 8 |
| audit_compare | 22 | 0 | 0 | 0.3 | 0.4 | 225 | 38 | 1481 | 230.9 | 0 | 7 |
| audit_meaning | 22 | 0 | 0 | 0.3 | 0.4 | 158 | 21 | 1118 | 126.1 | 0 | 7 |
| persona_details | 3 | 1 | 1 | 1.7 | 1.9 | 837 | 223 | 1771 | 189.2 | 0 | 7 |
| combat_interpret | 8 | 0 | 0 | 0.8 | 0.8 | 968 | 42 | 1603 | 257.2 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.5 | 5.5 | 1064 | 982 | 1647 | 200.9 | 0 | 6 |
| situation_parts | 1 | 0 | 0 | 4.4 | 4.4 | 1688 | 891 | 1942 | 253.7 | 0 | 4 |
| npc_profile | 5 | 0 | 0 | 0.9 | 1.0 | 605 | 91 | 1851 | 161.4 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 3.3 | 3.3 | 969 | 545 | 2202 | 188.8 | 0 | 3 |
| road_event | 1 | 0 | 0 | 2.8 | 2.8 | 1723 | 326 | 2022 | 166.5 | 0 | 3 |
| overheard | 7 | 0 | 0 | 0.3 | 0.4 | 273 | 16 | 1029 | 247.8 | 0 | 2 |
| ruling | 2 | 0 | 0 | 1.1 | 1.1 | 1311 | 66 | 2123 | 150.1 | 0 | 2 |
| canon_extract | 2 | 0 | 0 | 0.5 | 0.7 | 891 | 2 | 1540 | 117.6 | 0 | 1 |
| situation_agree | 2 | 0 | 0 | 0.2 | 0.3 | 190 | 14 | 1105 | 247.8 | 0 | 0 |
| clarify | 1 | 0 | 0 | 0.4 | 0.4 | 281 | 37 | 1597 | 141.8 | 0 | 0 |
| party_intent | 1 | 0 | 0 | 0.3 | 0.3 | 328 | 12 | 1540 | 184.6 | 0 | 0 |

303 attempts for 282 calls, 10.3 minutes in the model in all.

## Fights

12 rounds with a fight call; 2.2 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 8 | 0.8 | 0.9 | 0 |
| combat_opening | 4 | 2.3 | 2.4 | 0 |
| combat_narrate | 10 | 2.5 | 3.5 | 2 |
| combat_aftermath | 5 | 2.0 | 2.4 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 18 | 94% | 18808 | 21244 | 21259 | 65 | 0% |
| npc_profile | 5 | 100% | 2489 | 2682 | 2682 | 1424 | 0% |
| dialogue_frame | 13 | 77% | 9424 | 10989 | 11176 | 3538 | 0% |
| hire_chat | 8 | 88% | 10599 | 11845 | 11845 | 1541 | 0% |
| canon_extract | 2 | 100% | 3222 | 4025 | 4025 | 590 | 0% |
| exchange | 6 | 100% | 12317 | 13258 | 13258 | 63 | 0% |
| overheard | 7 | 100% | 1081 | 1141 | 1141 | 187 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 18 | 94% | 95% | -1 | 21244 | 36345 | 36500 | 21259 | 0% |
| npc_profile | 5 | 100% | 100% | +0 | 2682 | 2774 | 3000 | 2682 | 0% |
| dialogue_frame | 13 | 77% | 86% | -9 | 10989 | 10715 | 11000 | 11176 | 0% |
| hire_chat | 8 | 88% | 98% | -10 | 11845 | 16275 | 16500 | 11845 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 4025 | 3998 | 4000 | 4025 | 0% |
| exchange | 6 | 100% | 90% | +10 | 13258 | 15039 | 15500 | 13258 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1141 | 1326 | 1500 | 1141 | 0% |

Size: 5 of 7 tasks at or below the baseline's p95 (dearer: dialogue_frame, canon_extract); npc_conversation's p95 21244 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -10).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 53 | 216044 | 156001 (72%) | 160924 (74%) |
| npc_conversation | 19 | 90805 | 46685 (51%) | 3438 (4%) |
| narrate | 28 | 72693 | 40502 (56%) | 11570 (16%) |
| dialogue_frame | 16 | 35565 | 22034 (62%) | 6354 (18%) |
| player_line | 59 | 30492 | 8641 (28%) | 4577 (15%) |
| combat_narrate | 10 | 29735 | 19349 (65%) | 5991 (20%) |
| hire_chat | 9 | 24526 | 14699 (60%) | 2928 (12%) |
| exchange | 6 | 18022 | 6794 (38%) | 0 (0%) |
| combat_aftermath | 5 | 9528 | 5356 (56%) | 1908 (20%) |
| thread_telling | 3 | 8942 | 1191 (13%) | 0 (0%) |
| combat_interpret | 8 | 7724 | 6458 (84%) | 0 (0%) |
| combat_opening | 4 | 6478 | 4162 (64%) | 0 (0%) |
| populate_place | 8 | 5094 | 2075 (41%) | 0 (0%) |
| audit_compare | 22 | 4966 | 2544 (51%) | 0 (0%) |
| moment | 3 | 4211 | 2244 (53%) | 0 (0%) |
| audit_meaning | 22 | 3527 | 1517 (43%) | 0 (0%) |
| persona_details | 4 | 3241 | 1620 (50%) | 597 (18%) |
| npc_profile | 5 | 2717 | 1308 (48%) | 0 (0%) |
| ruling | 2 | 2622 | 1144 (44%) | 0 (0%) |
| overheard | 7 | 1904 | 1573 (83%) | 0 (0%) |
| canon_extract | 2 | 1783 | 1296 (73%) | 0 (0%) |
| road_event | 1 | 1723 | 797 (46%) | 0 (0%) |
| situation_parts | 1 | 1688 | 1081 (64%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| board_stakes | 1 | 969 | 385 (40%) | 0 (0%) |
| situation_agree | 2 | 380 | 200 (53%) | 87 (23%) |
| party_intent | 1 | 328 | 260 (79%) | 0 (0%) |
| clarify | 1 | 281 | 148 (53%) | 0 (0%) |

The prompts held 587052 tokens; the constant system messages were about 350553 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 198374 (34%) and read the rest.
The server's log: 303 prompts; 225 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 750 checkpoints made, 40 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 3 situations started (3 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 3 moments, 3 lines of the room changing, 0 times people on their routine; re-tellings 3 succeeded, 1 failed.

Per game day within reach: 1.00 situations started, 0.33 doors, 1.00 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 3 (3) | 0 | 0 | 0 | 1 | 2 | 2 | 0 |
| 3 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Situations started:
- day 2: [rare, engine-built] A grudge at Kelpmoor - starts, 12 days, 3 stages (within reach)
- day 2: [uncommon, engine-built] The quartermaster and the farmer at the temple door at the Tilted Plough - starts, 5  (within reach)
- day 2: [uncommon, engine-built] What marches by night at Parth - starts, 5 days, 2 stages (within reach)

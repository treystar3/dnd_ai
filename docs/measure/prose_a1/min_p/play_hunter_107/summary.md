# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 19 | 4.2 | 8.2 | 4.0 | 5.9 | 6.0 | 5.1 | 8 | 0 |
| fight | 12 | 4.8 | 5.6 | 2.8 | 4.8 | 3.2 | 4.2 | 1 | 0 |
| search | 10 | 2.7 | 3.4 | 2.7 | 3.0 | 3.3 | 2.8 | 0 | 0 |
| wait | 7 | 2.7 | 3.2 | 2.4 | 2.8 | 2.7 | 3.1 | 1 | 0 |
| talk | 4 | 4.2 | 4.6 | 2.7 | 2.9 | 3.0 | 3.4 | 0 | 0 |
| board | 3 | 2.9 | 13.9 | 2.9 | 13.9 | 3.3 | 6.4 | 1 | 0 |
| leave | 3 | 2.5 | 4.3 | 2.5 | 4.3 | 3.0 | 3.0 | 0 | 0 |
| look | 1 | 7.2 | 7.2 | 7.2 | 7.2 | 5.0 | 7.1 | 0 | 0 |
| hire | 1 | 8.2 | 8.2 | 4.7 | 4.7 | 5.0 | 8.1 | 0 | 0 |

60 turns in 4.3 minutes; 97% of it in the model; 182 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 8 optional calls deferred and 7 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.8 s and p90 28.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 13.9 s, board, 3 calls, at the adventurers' guild house: "I walk up to the desk and demand to see the high-reward bounties."
- 10.9 s, move, 10 calls, at the Greywood: "I stand up and tell the others we're heading back to the Adventurers' "
- 8.3 s, move, 6 calls, at the south fields: "Let's head straight for the Adventurers' Guild house."
- 8.2 s, move, 11 calls, at the Tilted Plough: "I turn to the group and tell them we're heading for the Greywood."
- 8.2 s, hire, 5 calls, at the adventurers' guild house: "I stand up from the table and check my gear by the fading light."

Lines by what read them: interpret 46, combat 12, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 46 (template 14; model failed 1, 20 s) |
| Lines picking up the passage before | 7 of 60 (12%); in talk 0 of 4 (0%) |
| Contracts taken / finished | 0 / 0 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 6 / 0 (go 4/0, hunt 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 12 |
| Waits | 7 of 60 (12%) |
| Places visited | 7 |

Turns by goal: idle 15, hunt 12, fight 12, board 7, need 4, go 3, revisit 3, follow 2, clarify 1, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 2 (id 2) |
| Machinery mended at the screen | 1648 (dash 1642, wrap 6) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 12.5 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Jemny Midby in dialogue_frame 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 6 times; 6 of the game's 15 own lines (40%); most: 'Victory. +# XP' x6 |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 32 ['greywood']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 1 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 1 of 68 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 6 / 2 / 2 and 35 |
| Fight turns with a foe 10+ levels above the player | 0 of 12, the widest -7 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 2 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.4 | 74.4 | 646 | 213 | 3393 | 230.1 | 0 | 202 |
| narrate | 32 | 0 | 0 | 1.8 | 2.2 | 2406 | 175 | 4363 | 134.3 | 0 | 57 |
| interpret_action | 50 | 0 | 0 | 0.7 | 0.9 | 3880 | 60 | 10265 | 229.4 | 0 | 34 |
| combat_narrate | 15 | 1 | 1 | 2.0 | 2.4 | 2889 | 206 | 5438 | 141.9 | 0 | 31 |
| npc_conversation | 8 | 0 | 0 | 2.0 | 2.5 | 5142 | 172 | 6152 | 104.7 | 0 | 25 |
| dialogue_frame | 17 | 7 | 7 | 0.8 | 1.3 | 2226 | 58 | 4668 | 150.0 | 0 | 22 |
| player_line | 47 | 7 | 8 | 0.4 | 0.4 | 538 | 24 | 2877 | 136.8 | 0 | 20 |
| hire_chat | 15 | 0 | 0 | 0.9 | 1.0 | 2557 | 52 | 4597 | 192.6 | 0 | 13 |
| combat_aftermath | 8 | 0 | 0 | 1.5 | 1.7 | 1938 | 182 | 4406 | 173.8 | 0 | 12 |
| combat_opening | 6 | 0 | 0 | 1.9 | 1.9 | 1655 | 187 | 3866 | 133.2 | 0 | 11 |
| exchange | 10 | 0 | 0 | 1.1 | 1.2 | 2899 | 78 | 4638 | 169.1 | 0 | 11 |
| persona_details | 3 | 1 | 1 | 1.6 | 1.7 | 895 | 254 | 3321 | 207.8 | 0 | 6 |
| combat_interpret | 12 | 0 | 0 | 0.5 | 0.5 | 970 | 49 | 3173 | 289.0 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.2 | 4.2 | 1064 | 917 | 3129 | 240.1 | 0 | 4 |
| audit_compare | 16 | 0 | 0 | 0.2 | 0.3 | 218 | 37 | 2346 | 263.3 | 0 | 4 |
| audit_meaning | 16 | 0 | 0 | 0.2 | 0.2 | 155 | 20 | 1914 | 155.8 | 0 | 4 |
| thread_telling | 1 | 1 | 1 | 1.6 | 1.7 | 3103 | 239 | 6783 | 202.2 | 0 | 3 |
| situation_parts | 1 | 0 | 0 | 3.3 | 3.3 | 1846 | 769 | 3578 | 279.0 | 0 | 3 |
| overheard | 13 | 0 | 0 | 0.2 | 0.2 | 276 | 16 | 1886 | 286.1 | 0 | 3 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1365 | 219 | 3679 | 147.9 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.5 | 1.5 | 1219 | 241 | 3971 | 198.0 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.7 | 0.7 | 625 | 105 | 3456 | 189.4 | 0 | 1 |
| clarify | 1 | 1 | 1 | 0.3 | 0.3 | 308 | 40 | 2508 | 216.6 | 0 | 1 |
| canon_extract | 1 | 0 | 0 | 0.3 | 0.3 | 827 | 2 | 3063 | 153.8 | 0 | 0 |
| situation_agree | 1 | 0 | 0 | 0.2 | 0.2 | 203 | 14 | 1735 | 280.0 | 0 | 0 |

303 attempts for 285 calls, 7.9 minutes in the model in all.

## Fights

18 rounds with a fight call; 2.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 12 | 0.5 | 0.5 | 0 |
| combat_opening | 6 | 1.9 | 2.1 | 0 |
| combat_narrate | 16 | 2.0 | 2.4 | 1 |
| combat_aftermath | 8 | 1.5 | 1.8 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 100% | 20694 | 21289 | 21289 | 68 | 5% |
| npc_profile | 2 | 100% | 2493 | 2640 | 2640 | 1428 | 0% |
| dialogue_frame | 17 | 59% | 9128 | 10275 | 10368 | 4243 | 6% |
| hire_chat | 15 | 100% | 10439 | 13106 | 13387 | 1938 | 0% |
| canon_extract | 1 | 100% | 3363 | 3363 | 3363 | 731 | 0% |
| exchange | 10 | 100% | 11464 | 12706 | 12706 | 62 | 0% |
| overheard | 13 | 100% | 1114 | 1173 | 1199 | 220 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 100% | 95% | +5 | 21289 | 36345 | 36500 | 21289 | 5% |
| npc_profile | 2 | 100% | 100% | +0 | 2640 | 2774 | 3000 | 2640 | 0% |
| dialogue_frame | 17 | 59% | 86% | -27 | 10275 | 10715 | 11000 | 10368 | 6% |
| hire_chat | 15 | 100% | 98% | +2 | 13106 | 16275 | 16500 | 13387 | 0% |
| canon_extract | 1 | 100% | 100% | +0 | 3363 | 3998 | 4000 | 3363 | 0% |
| exchange | 10 | 100% | 90% | +10 | 12706 | 15039 | 15500 | 12706 | 0% |
| overheard | 13 | 100% | 100% | +0 | 1173 | 1326 | 1500 | 1199 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 21289 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 50 | 193749 | 146594 (76%) | 151441 (78%) |
| narrate | 32 | 75223 | 39712 (53%) | 4755 (6%) |
| dialogue_frame | 24 | 52970 | 28002 (53%) | 17084 (32%) |
| combat_narrate | 16 | 45623 | 25483 (56%) | 11266 (25%) |
| npc_conversation | 8 | 40680 | 17721 (44%) | 2142 (5%) |
| hire_chat | 15 | 40478 | 21011 (52%) | 0 (0%) |
| player_line | 54 | 28895 | 7787 (27%) | 3581 (12%) |
| exchange | 10 | 27507 | 11260 (41%) | 0 (0%) |
| combat_aftermath | 8 | 15355 | 7062 (46%) | 3901 (25%) |
| combat_interpret | 12 | 11635 | 9708 (83%) | 0 (0%) |
| combat_opening | 6 | 9975 | 5101 (51%) | 0 (0%) |
| thread_telling | 2 | 6206 | 826 (13%) | 2979 (48%) |
| populate_place | 7 | 4547 | 1781 (39%) | 0 (0%) |
| overheard | 13 | 3577 | 2902 (81%) | 0 (0%) |
| audit_compare | 16 | 3503 | 1876 (54%) | 0 (0%) |
| persona_details | 4 | 3474 | 1601 (46%) | 1124 (32%) |
| audit_meaning | 16 | 2522 | 1127 (45%) | 0 (0%) |
| situation_parts | 1 | 1846 | 1084 (59%) | 0 (0%) |
| moment | 1 | 1365 | 757 (55%) | 0 (0%) |
| npc_profile | 2 | 1251 | 519 (41%) | 0 (0%) |
| board_stakes | 1 | 1219 | 396 (33%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| canon_extract | 1 | 827 | 647 (78%) | 0 (0%) |
| clarify | 2 | 617 | 346 (56%) | 261 (42%) |
| situation_agree | 1 | 203 | 93 (46%) | 0 (0%) |

The prompts held 574311 tokens; the constant system messages were about 333885 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 198534 (35%) and read the rest.
The server's log: 303 prompts; 224 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 755 checkpoints made, 33 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.5 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 0 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] Cheap and then dear in Parth - starts, 13 days, 3 stages (within reach)

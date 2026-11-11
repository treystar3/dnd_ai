# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.13 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 12 | 7.9 | 12.8 | 6.3 | 8.6 | 4.2 | 7.1 | 1 | 0 |
| search | 12 | 6.3 | 12.4 | 4.6 | 11.1 | 5.0 | 6.8 | 4 | 0 |
| forage | 9 | 3.0 | 4.1 | 3.2 | 4.0 | 2.3 | 3.1 | 1 | 0 |
| talk | 8 | 6.4 | 11.6 | 4.5 | 9.2 | 3.9 | 6.9 | 0 | 0 |
| leave | 6 | 7.9 | 12.2 | 7.2 | 7.7 | 6.7 | 8.9 | 2 | 0 |
| look | 6 | 6.3 | 15.1 | 4.4 | 11.9 | 6.0 | 8.4 | 0 | 0 |
| fight | 4 | 5.6 | 5.7 | 3.8 | 4.8 | 2.5 | 4.9 | 0 | 0 |
| board | 2 | 7.1 | 14.3 | 7.1 | 7.6 | 7.5 | 10.4 | 1 | 0 |
| hire | 1 | 6.7 | 6.7 | 6.6 | 6.6 | 4.0 | 3.6 | 0 | 0 |

60 turns in 6.9 minutes; 97% of it in the model; 198 embedding calls taking 2.2 s; 0 calls on background threads.
The budget: 8 optional calls deferred and 7 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 17.4 s and p90 33.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 16.6 s, look, 5 calls, at the adventurers' guild house: "Willowmead marshes. That's where we're heading."
- 15.1 s, look, 10 calls, at the adventurers' guild house: "I reach out and take the slip."
- 14.3 s, board, 10 calls, at the adventurers' guild house: "Hey scribe, I'm taking this contract to hunt those two lizardfolks in "
- 14.2 s, search, 10 calls, at the Willowmead wetlands: "I draw my blade and signal the group to start tracking the lizardfolk "
- 13.9 s, move, 8 calls, at the Greywood: "I signal to the others that we need to move toward Parth."

Lines by what read them: interpret 52, combat 4, hire 2, yielded 1, party 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 50 (template 10; model failed 2, 43 s) |
| Lines picking up the passage before | 17 of 60 (28%); in talk 5 of 8 (62%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 6 / 2 (contract 1/0, find 0/1, follow 0/1, go 2/0, report 1/0, revisit 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 4 |
| Waits | 0 of 60 (0%) |
| Places visited | 6 |

Turns by goal: contract 20, idle 12, follow 6, revisit 5, fight 4, report 4, board 3, clarify 3, cont 2, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 3 (id 2, json 1) |
| Machinery mended at the screen | 874 (dash 857, stage 2, wrap 15) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("iron longsword is already in hand.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 15.4 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 11 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 2 (Calsa Hoyle in narrate 2) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 25 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 4 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 39 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 2 / 0 / 6 and 6 |
| Fight turns with a foe 10+ levels above the player | 0 of 4, the widest -7 |
| Marks shown from acts (Remembered here) | 0 |
| Captives escaped / handed over or let go | 0 / 0 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | kept 0 of 1 |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 6 the spectacles-wearing scribe contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 6 | 0 | 0 | 1.8 | 1.9 | 702 | 284 | 1827 | 200.6 | 0 | 133 |
| narrate | 42 | 3 | 3 | 2.6 | 3.5 | 2418 | 174 | 2450 | 107.2 | 0 | 118 |
| interpret_action | 62 | 0 | 0 | 1.0 | 1.5 | 3704 | 62 | 5367 | 196.9 | 0 | 67 |
| npc_conversation | 15 | 1 | 1 | 3.2 | 7.0 | 5173 | 177 | 3827 | 81.6 | 0 | 63 |
| player_line | 52 | 13 | 15 | 0.6 | 0.8 | 515 | 23 | 1413 | 96.0 | 0 | 43 |
| dialogue_frame | 14 | 3 | 3 | 1.7 | 2.1 | 2240 | 82 | 2073 | 114.4 | 0 | 30 |
| hire_chat | 11 | 1 | 1 | 1.7 | 1.8 | 2547 | 59 | 2336 | 144.3 | 0 | 19 |
| exchange | 8 | 1 | 2 | 1.7 | 2.3 | 2957 | 89 | 2905 | 130.2 | 0 | 16 |
| combat_narrate | 4 | 0 | 0 | 2.9 | 3.9 | 3040 | 185 | 2658 | 109.1 | 0 | 12 |
| audit_compare | 30 | 0 | 0 | 0.3 | 0.4 | 228 | 38 | 1282 | 223.2 | 0 | 11 |
| audit_meaning | 30 | 0 | 0 | 0.3 | 0.4 | 166 | 23 | 1072 | 118.1 | 0 | 11 |
| board_stakes | 3 | 0 | 0 | 3.1 | 3.5 | 1235 | 446 | 1959 | 176.3 | 0 | 9 |
| combat_opening | 3 | 0 | 0 | 2.3 | 2.8 | 1820 | 160 | 1958 | 107.6 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 1.9 | 1.9 | 791 | 233 | 1653 | 170.8 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.3 | 5.3 | 1050 | 956 | 1589 | 205.1 | 0 | 5 |
| moment | 2 | 0 | 0 | 2.1 | 2.6 | 1378 | 231 | 2015 | 136.9 | 0 | 5 |
| combat_aftermath | 2 | 0 | 0 | 2.3 | 2.4 | 1899 | 215 | 1977 | 158.4 | 0 | 5 |
| npc_profile | 4 | 0 | 0 | 1.2 | 1.3 | 637 | 105 | 1708 | 148.3 | 0 | 4 |
| overheard | 9 | 0 | 0 | 0.4 | 0.4 | 285 | 16 | 858 | 253.5 | 0 | 4 |
| combat_interpret | 4 | 0 | 0 | 0.8 | 0.9 | 964 | 48 | 1566 | 265.8 | 0 | 3 |
| canon_extract | 4 | 0 | 0 | 0.6 | 0.8 | 909 | 2 | 1526 | 127.0 | 0 | 2 |
| clarify | 3 | 0 | 0 | 0.5 | 0.6 | 278 | 34 | 1096 | 138.2 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.2 | 1.2 | 1199 | 63 | 1733 | 127.8 | 0 | 1 |
| party_intent | 1 | 0 | 0 | 0.3 | 0.3 | 320 | 12 | 1339 | 166.7 | 0 | 0 |

336 attempts for 314 calls, 9.6 minutes in the model in all.

## Fights

7 rounds with a fight call; 1.9 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 4 | 0.8 | 0.9 | 0 |
| combat_opening | 3 | 2.3 | 2.8 | 0 |
| combat_narrate | 4 | 2.9 | 3.9 | 0 |
| combat_aftermath | 2 | 2.3 | 2.4 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 15 | 93% | 20450 | 21610 | 22373 | 72 | 3% |
| npc_profile | 4 | 100% | 2674 | 2679 | 2679 | 1609 | 0% |
| dialogue_frame | 14 | 79% | 9394 | 11504 | 11602 | 3597 | 0% |
| hire_chat | 11 | 91% | 10378 | 14377 | 14377 | 1525 | 0% |
| canon_extract | 4 | 100% | 4116 | 4272 | 4272 | 1484 | 0% |
| exchange | 8 | 88% | 11996 | 16395 | 16395 | 61 | 12% |
| overheard | 9 | 100% | 1156 | 1231 | 1231 | 262 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 15 | 93% | 95% | -2 | 21610 | 36345 | 36500 | 22373 | 3% |
| npc_profile | 4 | 100% | 100% | +0 | 2679 | 2774 | 3000 | 2679 | 0% |
| dialogue_frame | 14 | 79% | 86% | -7 | 11504 | 10715 | 11000 | 11602 | 0% |
| hire_chat | 11 | 91% | 98% | -7 | 14377 | 16275 | 16500 | 14377 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 4272 | 3998 | 4000 | 4272 | 0% |
| exchange | 8 | 88% | 90% | -2 | 16395 | 15039 | 15500 | 16395 | 12% |
| overheard | 9 | 100% | 100% | +0 | 1231 | 1326 | 1500 | 1231 | 0% |

Size: 4 of 7 tasks at or below the baseline's p95 (dearer: dialogue_frame, canon_extract, exchange); npc_conversation's p95 21610 against the mark of 14000, not held; over their ceiling: dialogue_frame, canon_extract, exchange.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -7).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 62 | 250994 | 181906 (72%) | 195181 (78%) |
| narrate | 45 | 110276 | 64451 (58%) | 21599 (20%) |
| npc_conversation | 16 | 81887 | 39219 (48%) | 7578 (9%) |
| dialogue_frame | 17 | 38311 | 22482 (59%) | 6117 (16%) |
| player_line | 65 | 35455 | 9302 (26%) | 7336 (21%) |
| hire_chat | 12 | 31856 | 19640 (62%) | 2308 (7%) |
| exchange | 9 | 27506 | 10118 (37%) | 5906 (21%) |
| combat_narrate | 4 | 12011 | 7576 (63%) | 0 (0%) |
| audit_compare | 30 | 6792 | 3466 (51%) | 0 (0%) |
| combat_opening | 3 | 5314 | 3086 (58%) | 0 (0%) |
| audit_meaning | 30 | 5151 | 2031 (39%) | 0 (0%) |
| populate_place | 6 | 4223 | 1530 (36%) | 0 (0%) |
| combat_interpret | 4 | 3851 | 3222 (84%) | 0 (0%) |
| combat_aftermath | 2 | 3798 | 2149 (57%) | 0 (0%) |
| canon_extract | 4 | 3631 | 2566 (71%) | 0 (0%) |
| board_stakes | 3 | 3447 | 1182 (34%) | 0 (0%) |
| moment | 2 | 2757 | 1491 (54%) | 0 (0%) |
| overheard | 9 | 2565 | 1996 (78%) | 0 (0%) |
| npc_profile | 4 | 2520 | 1027 (41%) | 0 (0%) |
| persona_details | 3 | 2378 | 1094 (46%) | 345 (15%) |
| ruling | 1 | 1199 | 596 (50%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| clarify | 3 | 835 | 431 (52%) | 0 (0%) |
| party_intent | 1 | 320 | 255 (80%) | 0 (0%) |

The prompts held 638127 tokens; the constant system messages were about 381304 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 246370 (39%) and read the rest.
The server's log: 336 prompts; 242 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 806 checkpoints made, 33 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 1 ended (0 by the player, 1 settled by others, 0 left to their fallout), 2 motive steps; the player met 0 doors (a scene or a summons), 2 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.67 situations started, 0.00 doors, 0.67 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 1 (1) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 3 | 1 (1) | 0 | 1 | 2 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 3: [uncommon, engine-built] What ails the beasts at Kelpmoor - starts, 3 days, 2 stages (within reach)

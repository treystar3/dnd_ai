# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 17 | 5.9 | 8.5 | 4.9 | 6.1 | 6.7 | 6.1 | 1 | 0 |
| fight | 12 | 4.2 | 6.8 | 2.6 | 4.1 | 3.4 | 4.4 | 1 | 0 |
| forage | 9 | 2.2 | 3.0 | 2.2 | 3.0 | 2.8 | 2.4 | 1 | 0 |
| talk | 6 | 3.7 | 6.5 | 3.7 | 6.5 | 4.3 | 4.7 | 0 | 0 |
| leave | 6 | 4.5 | 7.0 | 4.4 | 5.1 | 5.7 | 4.9 | 1 | 0 |
| search | 4 | 3.0 | 4.7 | 2.5 | 3.0 | 3.0 | 2.8 | 0 | 0 |
| board | 3 | 4.5 | 5.8 | 4.5 | 5.8 | 5.7 | 4.7 | 1 | 0 |
| look | 2 | 2.5 | 3.0 | 2.5 | 3.0 | 5.0 | 2.8 | 0 | 0 |
| hire | 1 | 3.6 | 3.6 | 3.5 | 3.5 | 4.0 | 2.4 | 0 | 0 |

60 turns in 4.6 minutes; 97% of it in the model; 196 embedding calls taking 0.9 s; 0 calls on background threads.
The budget: 3 optional calls deferred and 4 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 18.5 s and p90 34.9 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 11.0 s, fight, 6 calls, at the King's Road between Willowmead and Parth: "I use Cleaving Sweep on lizardfolk 1."
- 10.9 s, move, 10 calls, at the King's Road between Parth and Willowmead: "I push past the bramble wall and signal the group to start heading tow"
- 10.4 s, move, 11 calls, at the Greywood: "I wipe my blade on the grass and tell the group we need to head back t"
- 9.0 s, talk, 7 calls, at the adventurers' guild house: "Scribe, we finished those two lizardfolk in the wetlands. Hand over my"
- 8.5 s, move, 6 calls, at the south fields: "I signal the group to move out toward Parth."

Lines by what read them: interpret 49, combat 10, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 58 of 60 (97%) |
| Lines the model wrote | 46 (template 14; model failed 0, 20 s) |
| Lines picking up the passage before | 16 of 60 (27%); in talk 3 of 6 (50%) |
| Contracts taken / finished | 3 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 1 |
| Goals finished / given up | 5 / 1 (contract 1/1, go 1/0, hunt 1/0, report 1/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 12 |
| Waits | 0 of 60 (0%) |
| Places visited | 9 |

Turns by goal: contract 19, idle 12, fight 10, board 7, hunt 6, report 3, revisit 2, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 3 (id 2, placeholder 1) |
| Machinery mended at the screen | 1745 (dash 1730, stage 4, wrap 11) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("iron longsword is already in hand.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 3 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 1, narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 1 |
| Additions to the world per hour | 25.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 1 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 5 of the game's 43 own lines (12%); most: 'Victory. +# XP' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 4 / 1 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 65 |
| Matters the player ended: pursued / by accident | 0 / 1 (by accident: The unquiet of the Greywood) |
| Fights won / for +0 XP / XP median and most | 7 / 2 / 4 and 5 |
| Fight turns with a foe 10+ levels above the player | 0 of 10, the widest -10 |
| Marks shown from acts (Remembered here) | 4 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 1 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 42 the ink-stained scribe contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.3 | 1.5 | 696 | 275 | 2762 | 194.0 | 0 | 132 |
| narrate | 35 | 1 | 1 | 1.7 | 2.3 | 2348 | 168 | 4523 | 136.0 | 0 | 62 |
| interpret_action | 56 | 0 | 0 | 0.7 | 0.9 | 4001 | 60 | 10917 | 252.2 | 0 | 36 |
| dialogue_frame | 23 | 1 | 1 | 1.0 | 1.2 | 2313 | 60 | 4090 | 144.0 | 0 | 24 |
| combat_narrate | 11 | 0 | 0 | 1.9 | 2.3 | 2780 | 198 | 4796 | 134.8 | 0 | 21 |
| npc_conversation | 8 | 1 | 1 | 2.0 | 2.7 | 5453 | 169 | 6568 | 132.7 | 0 | 20 |
| player_line | 46 | 9 | 9 | 0.4 | 0.4 | 536 | 24 | 2915 | 138.0 | 0 | 20 |
| combat_aftermath | 10 | 0 | 0 | 1.4 | 1.7 | 1857 | 178 | 4467 | 170.6 | 0 | 15 |
| combat_opening | 7 | 2 | 2 | 1.6 | 1.9 | 1681 | 173 | 4149 | 142.6 | 0 | 14 |
| exchange | 11 | 0 | 0 | 1.2 | 1.5 | 2950 | 94 | 4699 | 168.7 | 0 | 13 |
| hire_chat | 13 | 0 | 0 | 1.0 | 1.1 | 2622 | 64 | 4393 | 176.5 | 0 | 13 |
| audit_compare | 29 | 0 | 0 | 0.2 | 0.3 | 225 | 38 | 2405 | 257.0 | 0 | 7 |
| audit_meaning | 29 | 0 | 0 | 0.2 | 0.3 | 158 | 23 | 1971 | 163.3 | 0 | 7 |
| road_event | 2 | 0 | 0 | 2.3 | 3.2 | 1733 | 413 | 3909 | 177.8 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.7 | 819 | 236 | 3437 | 182.4 | 0 | 5 |
| combat_interpret | 10 | 0 | 0 | 0.5 | 0.5 | 954 | 47 | 3104 | 308.1 | 0 | 5 |
| ruling | 6 | 0 | 0 | 0.7 | 0.7 | 1241 | 67 | 3750 | 208.1 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.3 | 4.3 | 1050 | 934 | 3097 | 236.8 | 0 | 4 |
| board_stakes | 2 | 0 | 0 | 1.5 | 2.1 | 1050 | 313 | 3750 | 205.0 | 0 | 4 |
| moment | 2 | 0 | 0 | 1.6 | 1.9 | 1375 | 233 | 3657 | 173.2 | 0 | 3 |
| overheard | 13 | 0 | 0 | 0.2 | 0.2 | 283 | 16 | 1977 | 295.5 | 0 | 3 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 811 | 2 | 3049 | 192.3 | 0 | 1 |
| npc_profile | 1 | 0 | 0 | 0.7 | 0.7 | 598 | 93 | 3322 | 192.9 | 0 | 1 |

342 attempts for 328 calls, 7.0 minutes in the model in all.

## Fights

17 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 10 | 0.5 | 0.5 | 0 |
| combat_opening | 9 | 1.6 | 2.2 | 2 |
| combat_narrate | 11 | 1.9 | 2.4 | 0 |
| combat_aftermath | 10 | 1.4 | 2.0 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 88% | 21860 | 22699 | 22699 | 103 | 0% |
| npc_profile | 1 | 100% | 2482 | 2482 | 2482 | 1417 | 0% |
| dialogue_frame | 23 | 96% | 9600 | 10090 | 10272 | 4544 | 4% |
| hire_chat | 13 | 100% | 10907 | 14066 | 14195 | 2143 | 0% |
| canon_extract | 3 | 100% | 3291 | 3301 | 3301 | 659 | 0% |
| exchange | 11 | 100% | 12179 | 13343 | 13343 | 61 | 0% |
| overheard | 13 | 100% | 1155 | 1226 | 1295 | 261 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 88% | 95% | -8 | 22699 | 36345 | 36500 | 22699 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2482 | 2774 | 3000 | 2482 | 0% |
| dialogue_frame | 23 | 96% | 86% | +10 | 10090 | 10715 | 11000 | 10272 | 4% |
| hire_chat | 13 | 100% | 98% | +2 | 14066 | 16275 | 16500 | 14195 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 3301 | 3998 | 4000 | 3301 | 0% |
| exchange | 11 | 100% | 90% | +10 | 13343 | 15039 | 15500 | 13343 | 0% |
| overheard | 13 | 100% | 100% | +0 | 1226 | 1326 | 1500 | 1295 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 22699 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -8).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 56 | 227453 | 164445 (72%) | 164906 (73%) |
| narrate | 36 | 84668 | 44137 (52%) | 10125 (12%) |
| dialogue_frame | 24 | 52513 | 27944 (53%) | 4241 (8%) |
| npc_conversation | 9 | 48728 | 20055 (41%) | 5692 (12%) |
| hire_chat | 13 | 35819 | 17970 (50%) | 0 (0%) |
| exchange | 11 | 31285 | 12238 (39%) | 0 (0%) |
| combat_narrate | 11 | 30233 | 17323 (57%) | 2800 (9%) |
| player_line | 55 | 30152 | 7886 (26%) | 4709 (16%) |
| combat_aftermath | 10 | 18228 | 8867 (49%) | 5469 (30%) |
| combat_opening | 9 | 15423 | 7803 (51%) | 4385 (28%) |
| combat_interpret | 10 | 9574 | 8033 (84%) | 0 (0%) |
| ruling | 6 | 7499 | 3476 (46%) | 0 (0%) |
| audit_compare | 29 | 6668 | 3374 (51%) | 0 (0%) |
| populate_place | 7 | 4869 | 1785 (37%) | 0 (0%) |
| audit_meaning | 29 | 4830 | 1982 (41%) | 0 (0%) |
| overheard | 13 | 3715 | 2856 (77%) | 0 (0%) |
| road_event | 2 | 3467 | 1587 (46%) | 0 (0%) |
| moment | 2 | 2750 | 1491 (54%) | 0 (0%) |
| canon_extract | 3 | 2436 | 1953 (80%) | 0 (0%) |
| persona_details | 3 | 2413 | 1090 (45%) | 345 (14%) |
| board_stakes | 2 | 2100 | 776 (37%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| npc_profile | 1 | 598 | 257 (43%) | 0 (0%) |

The prompts held 626471 tokens; the constant system messages were about 357816 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 202672 (32%) and read the rest.
The server's log: 342 prompts; 262 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 829 checkpoints made, 33 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 2 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 0.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 2 (2) | 0 | 1 | 0 | 0 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 2: [normal, engine-built] The unquiet of the Greywood at Parth - starts, 2 days, 1 stages (within reach)

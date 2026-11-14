# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 19 | 4.9 | 7.8 | 3.3 | 5.6 | 4.1 | 4.2 | 1 | 0 |
| wait | 11 | 3.8 | 6.0 | 2.7 | 6.0 | 3.3 | 4.0 | 4 | 0 |
| fight | 9 | 4.1 | 5.9 | 2.7 | 4.4 | 3.1 | 4.2 | 0 | 0 |
| search | 7 | 2.4 | 2.8 | 2.4 | 2.8 | 2.6 | 2.4 | 0 | 0 |
| talk | 5 | 5.6 | 10.6 | 4.2 | 5.6 | 5.6 | 6.2 | 3 | 0 |
| leave | 4 | 3.9 | 9.2 | 3.4 | 3.9 | 4.0 | 4.2 | 1 | 0 |
| hire | 2 | 3.9 | 5.3 | 3.6 | 3.9 | 6.5 | 4.0 | 0 | 0 |
| board | 2 | 4.3 | 5.2 | 4.3 | 5.2 | 5.5 | 4.6 | 0 | 0 |
| work | 1 | 2.6 | 2.6 | 2.6 | 2.6 | 2.0 | 2.5 | 0 | 0 |

60 turns in 4.2 minutes; 97% of it in the model; 157 embedding calls taking 0.8 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 2 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 15.9 s and p90 33.1 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.6 s, talk, 7 calls, at the adventurers' guild house: "I sign the paper and look at the group, asking who here I can actually"
- 9.2 s, leave, 7 calls, at the adventurers' guild house: "I nod once at the scout and turn to head for the door."
- 8.4 s, move, 8 calls, at the King's Pass between Ironvein and Parth: "We don't have time for cargo; let's keep heading toward the Adventurer"
- 8.3 s, wait, 5 calls, at the adventurers' guild house: "I stay leaned up against the pillar, watching them work."
- 8.2 s, talk, 8 calls, at the trading square: "I walk over to the baker and ask if she knows of any local work."

Lines by what read them: interpret 49, combat 9, party 1, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 48 (template 12; model failed 1, 19 s) |
| Lines picking up the passage before | 9 of 60 (15%); in talk 4 of 5 (80%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 1 |
| Goals finished / given up | 4 / 2 (contract 0/1, go 3/0, hunt 1/0, revisit 0/1) |
| Deaths (above the level band) | 0 (0) |
| Fights | 9 |
| Waits | 11 of 60 (18%) |
| Places visited | 10 |

Turns by goal: board 15, idle 14, fight 9, hunt 6, revisit 6, contract 4, go 2, cont 2, need 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 6 (broken 3, id 2, script 1) |
| Machinery mended at the screen | 2185 (dash 2177, json 1, stage 1, wrap 6) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("your party will hold back and come running if the alarm goes up. they ") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 1 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 1 (Calsa Hoyle in narrate 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 0 of the game's 24 own lines (0%); most: "You are back at the adventurers' guild house." x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '}') |
| City ground in the wilds / rain under a roof / weather out of season | 2 / 4 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 61 |
| Matters the player ended: pursued / by accident | 1 / 0 |
| Fights won / for +0 XP / XP median and most | 5 / 0 / 263 and 263 |
| Fight turns with a foe 10+ levels above the player | 0 of 9, the widest -3 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 0 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| narrate | 34 | 5 | 6 | 1.8 | 2.4 | 2415 | 173 | 4947 | 128.6 | 0 | 74 |
| interpret_action | 51 | 0 | 0 | 0.7 | 0.9 | 3935 | 50 | 9739 | 237.3 | 0 | 34 |
| populate_place | 6 | 0 | 0 | 1.1 | 1.6 | 662 | 254 | 3345 | 232.3 | 0 | 30 |
| combat_narrate | 11 | 0 | 0 | 2.0 | 2.3 | 2817 | 181 | 5205 | 133.7 | 0 | 21 |
| npc_conversation | 11 | 1 | 1 | 1.8 | 2.3 | 4881 | 132 | 6198 | 144.1 | 0 | 21 |
| dialogue_frame | 18 | 3 | 3 | 1.0 | 1.2 | 2305 | 54 | 4326 | 141.2 | 0 | 21 |
| player_line | 49 | 7 | 8 | 0.3 | 0.4 | 540 | 22 | 2873 | 135.6 | 0 | 19 |
| combat_aftermath | 7 | 0 | 0 | 1.4 | 1.7 | 1878 | 171 | 4498 | 170.6 | 0 | 10 |
| exchange | 8 | 0 | 0 | 1.2 | 1.4 | 2769 | 92 | 4592 | 159.6 | 0 | 10 |
| combat_opening | 5 | 0 | 0 | 1.8 | 1.8 | 1694 | 169 | 3774 | 137.6 | 0 | 9 |
| hire_chat | 8 | 0 | 0 | 0.9 | 0.9 | 2488 | 59 | 4445 | 175.0 | 0 | 7 |
| road_event | 3 | 0 | 0 | 2.3 | 2.3 | 1761 | 326 | 3989 | 178.7 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.7 | 820 | 256 | 3532 | 190.5 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.1 | 4.1 | 1050 | 899 | 3134 | 240.4 | 0 | 4 |
| combat_interpret | 9 | 0 | 0 | 0.5 | 0.5 | 957 | 47 | 3162 | 312.1 | 0 | 4 |
| npc_profile | 5 | 0 | 0 | 0.7 | 0.9 | 613 | 100 | 3320 | 181.8 | 0 | 4 |
| audit_compare | 14 | 0 | 0 | 0.2 | 0.3 | 225 | 39 | 2402 | 256.2 | 0 | 4 |
| thread_telling | 2 | 0 | 0 | 1.5 | 1.9 | 2863 | 204 | 4980 | 179.7 | 0 | 3 |
| audit_meaning | 14 | 0 | 0 | 0.2 | 0.2 | 161 | 24 | 2016 | 173.8 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.3 | 2.3 | 1168 | 407 | 3685 | 208.4 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1411 | 266 | 3450 | 173.3 | 0 | 2 |
| overheard | 8 | 0 | 0 | 0.2 | 0.2 | 281 | 16 | 1931 | 308.4 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 829 | 2 | 3178 | 192.3 | 0 | 1 |
| work_offer_read | 1 | 0 | 0 | 0.2 | 0.2 | 140 | 23 | 1346 | 198.3 | 0 | 0 |
| party_intent | 1 | 0 | 0 | 0.2 | 0.2 | 316 | 12 | 2569 | 230.8 | 0 | 0 |

290 attempts for 274 calls, 4.9 minutes in the model in all.

## Fights

14 rounds with a fight call; 2.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 9 | 0.5 | 0.5 | 0 |
| combat_opening | 5 | 1.8 | 1.8 | 0 |
| combat_narrate | 11 | 2.0 | 2.4 | 0 |
| combat_aftermath | 7 | 1.4 | 1.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 11 | 91% | 19456 | 21345 | 21345 | 54 | 0% |
| npc_profile | 5 | 100% | 2531 | 2723 | 2723 | 1466 | 0% |
| dialogue_frame | 18 | 83% | 9056 | 10307 | 10318 | 4273 | 0% |
| work_offer_read | 1 | 100% | 533 | 533 | 533 | 284 | 0% |
| hire_chat | 8 | 100% | 10222 | 12338 | 12338 | 2001 | 0% |
| canon_extract | 3 | 100% | 3361 | 4194 | 4194 | 729 | 0% |
| exchange | 8 | 100% | 12165 | 12587 | 12587 | 61 | 0% |
| overheard | 8 | 100% | 1146 | 1158 | 1158 | 252 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 11 | 91% | 95% | -4 | 21345 | 36345 | 36500 | 21345 | 0% |
| npc_profile | 5 | 100% | 100% | +0 | 2723 | 2774 | 3000 | 2723 | 0% |
| dialogue_frame | 18 | 83% | 86% | -3 | 10307 | 10715 | 11000 | 10318 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 533 | 780 | 1000 | 533 | 0% |
| hire_chat | 8 | 100% | 98% | +2 | 12338 | 16275 | 16500 | 12338 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4194 | 3998 | 4000 | 4194 | 0% |
| exchange | 8 | 100% | 90% | +10 | 12587 | 15039 | 15500 | 12587 | 0% |
| overheard | 8 | 100% | 100% | +0 | 1158 | 1326 | 1500 | 1158 | 0% |

Size: 7 of 8 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 21345 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 51 | 202546 | 149848 (74%) | 149516 (74%) |
| narrate | 39 | 94447 | 49050 (52%) | 22113 (23%) |
| npc_conversation | 12 | 58218 | 26580 (46%) | 4811 (8%) |
| dialogue_frame | 21 | 46796 | 24748 (53%) | 7009 (15%) |
| combat_narrate | 11 | 30855 | 17362 (56%) | 5575 (18%) |
| player_line | 56 | 29762 | 7980 (27%) | 4346 (15%) |
| exchange | 8 | 21839 | 8896 (41%) | 0 (0%) |
| hire_chat | 8 | 20138 | 11085 (55%) | 0 (0%) |
| combat_aftermath | 7 | 13238 | 6227 (47%) | 3825 (29%) |
| combat_interpret | 9 | 8620 | 7232 (84%) | 0 (0%) |
| combat_opening | 5 | 8466 | 4218 (50%) | 0 (0%) |
| thread_telling | 2 | 5727 | 795 (14%) | 0 (0%) |
| road_event | 3 | 5230 | 2394 (46%) | 0 (0%) |
| populate_place | 6 | 3900 | 1525 (39%) | 0 (0%) |
| audit_compare | 14 | 3159 | 1617 (51%) | 0 (0%) |
| npc_profile | 5 | 3121 | 1290 (41%) | 0 (0%) |
| canon_extract | 3 | 2654 | 1935 (73%) | 0 (0%) |
| persona_details | 3 | 2416 | 1089 (45%) | 690 (29%) |
| audit_meaning | 14 | 2334 | 950 (41%) | 0 (0%) |
| overheard | 8 | 2227 | 1769 (79%) | 0 (0%) |
| moment | 1 | 1411 | 748 (53%) | 0 (0%) |
| board_stakes | 1 | 1168 | 392 (34%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| party_intent | 1 | 316 | 255 (81%) | 0 (0%) |
| work_offer_read | 1 | 140 | 65 (47%) | 0 (0%) |

The prompts held 569778 tokens; the constant system messages were about 328538 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 197885 (35%) and read the rest.
The server's log: 290 prompts; 209 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 729 checkpoints made, 43 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 4 situations started (4 within reach of the player), 0 stages advanced, 2 ended (1 by the player, 1 settled by others, 0 left to their fallout), 2 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 2 succeeded, 0 failed.

Per game day within reach: 1.33 situations started, 0.00 doors, 0.33 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 (2) | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| 3 | 2 (2) | 0 | 2 | 1 | 0 | 0 | 0 | 0 |
| 4 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Talk in Parth - starts, 1 days, 1 stages (within reach)
- day 2: [uncommon, engine-built] Held at the toll on the Salt Road at Kelpmoor - starts, 6 days, 2 stages (within reach)
- day 3: [normal, engine-built] Tribute for the Grey Mountains - starts, 1 days, 1 stages (within reach)
- day 3: [normal, engine-built] A hunter's debt at Parth - starts, 1 days, 1 stages (within reach)

# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 14, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 16 | 5.1 | 7.8 | 3.2 | 5.1 | 3.7 | 5.0 | 5 | 0 |
| move | 14 | 6.3 | 10.8 | 5.2 | 8.6 | 5.7 | 7.0 | 10 | 0 |
| search | 10 | 4.2 | 6.0 | 2.9 | 6.0 | 3.6 | 4.3 | 7 | 0 |
| wait | 9 | 3.9 | 7.5 | 3.3 | 3.9 | 5.2 | 4.6 | 3 | 0 |
| board | 4 | 8.2 | 12.2 | 4.8 | 12.2 | 3.8 | 5.4 | 1 | 0 |
| talk | 4 | 5.5 | 5.6 | 5.5 | 5.6 | 3.5 | 3.9 | 1 | 0 |
| leave | 3 | 2.6 | 7.2 | 2.6 | 7.2 | 4.3 | 3.4 | 1 | 0 |

60 turns in 5.3 minutes; 98% of it in the model; 208 embedding calls taking 1.0 s; 0 calls on background threads.
The budget: 5 optional calls deferred and 8 dropped; 4 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 20.4 s and p90 35.5 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.7 s, move, 2 calls, at the trading square: "I head toward the gate and tell the guards I'm moving out for the Iron"
- 12.2 s, board, 5 calls, at the adventurers' guild house: "I step up to the clerk and point at the board, saying, 'I'm taking the"
- 10.8 s, move, 8 calls, at the King's Pass between Ironvein and Parth: "Let's move out. We need to reach the Adventurers' Guild House as soon "
- 10.7 s, move, 10 calls, at the Ironcrown Peaks: "I let the woman walk and head back toward the Adventurers' Guild House"
- 10.0 s, move, 8 calls, at the trading square: "Let's get moving toward the Ironcrown Peaks."

Lines by what read them: interpret 40, combat 16, hire 4

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 52 of 60 (87%) |
| Lines the model wrote | 42 (template 18; model failed 0, 19 s) |
| Lines picking up the passage before | 25 of 60 (42%); in talk 2 of 4 (50%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 1 / 5 (contract 0/2, go 1/0, revisit 0/3) |
| Deaths (above the level band) | 0 (0) |
| Fights | 16 |
| Waits | 9 of 60 (15%) |
| Places visited | 6 |

Turns by goal: contract 17, fight 16, revisit 9, idle 8, board 4, follow 3, cont 2, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 22 (id 8, first_person 8, script 3, broken 2, note 1) |
| Machinery mended at the screen | 4213 (dash 4193, stage 1, wrap 19) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 4 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 11.1 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 3 / 1 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 4 (Rimali Vamatho in combat_narrate 1; Jemny Midby in combat_narrate 1; Brannoc in dialogue_frame 1; Rimali Vamatho in dialogue_frame 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 46 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 2 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | captive 1 of 4; hire 2 of 92 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 7 / 0 / 494 and 763 |
| Fight turns with a foe 10+ levels above the player | 0 of 16, the widest +0 |
| Marks shown from acts (Remembered here) | 1 |
| Captives escaped / handed over or let go | 0 / 1 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | none met again |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 5 | 0 | 0 | 1.4 | 124.7 | 708 | 300 | 2443 | 229.6 | 0 | 130 |
| narrate | 24 | 9 | 10 | 1.8 | 2.3 | 2522 | 174 | 5258 | 130.6 | 0 | 59 |
| combat_narrate | 22 | 4 | 4 | 1.9 | 2.5 | 2858 | 194 | 5944 | 138.1 | 0 | 49 |
| npc_conversation | 8 | 1 | 1 | 2.0 | 9.4 | 5187 | 150 | 6436 | 141.7 | 0 | 37 |
| dialogue_frame | 20 | 9 | 10 | 1.1 | 1.3 | 2168 | 91 | 4604 | 139.9 | 0 | 32 |
| interpret_action | 44 | 0 | 0 | 0.7 | 0.9 | 3954 | 57 | 9201 | 231.4 | 0 | 31 |
| player_line | 42 | 7 | 7 | 0.4 | 0.4 | 529 | 23 | 2825 | 136.9 | 0 | 19 |
| exchange | 14 | 2 | 2 | 1.2 | 1.4 | 3085 | 100 | 5070 | 176.1 | 0 | 19 |
| combat_aftermath | 11 | 0 | 0 | 1.6 | 1.9 | 1911 | 196 | 4456 | 173.3 | 0 | 17 |
| combat_opening | 6 | 2 | 4 | 1.8 | 2.0 | 1791 | 196 | 4315 | 151.4 | 0 | 13 |
| hire_chat | 13 | 0 | 0 | 0.9 | 1.1 | 2812 | 62 | 4728 | 165.0 | 0 | 13 |
| combat_interpret | 16 | 0 | 0 | 0.5 | 0.5 | 956 | 48 | 3039 | 305.4 | 0 | 8 |
| persona_details | 3 | 1 | 1 | 1.7 | 1.8 | 883 | 271 | 3404 | 206.5 | 0 | 6 |
| board_stakes | 2 | 0 | 0 | 2.6 | 2.7 | 1120 | 493 | 3811 | 210.4 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1064 | 945 | 3111 | 234.3 | 0 | 4 |
| audit_compare | 15 | 0 | 0 | 0.2 | 0.3 | 213 | 37 | 2480 | 250.8 | 0 | 4 |
| audit_meaning | 15 | 0 | 0 | 0.2 | 0.3 | 157 | 23 | 1917 | 172.5 | 0 | 3 |
| situation_parts | 1 | 0 | 0 | 2.7 | 2.7 | 1579 | 607 | 3463 | 273.7 | 0 | 3 |
| road_event | 1 | 0 | 0 | 2.3 | 2.3 | 1814 | 327 | 4086 | 179.0 | 0 | 2 |
| canon_extract | 4 | 0 | 0 | 0.6 | 0.7 | 849 | 61 | 3010 | 254.0 | 0 | 2 |
| npc_profile | 3 | 0 | 0 | 0.7 | 0.8 | 611 | 93 | 3482 | 180.8 | 0 | 2 |
| overheard | 9 | 0 | 0 | 0.2 | 0.2 | 280 | 16 | 1942 | 287.4 | 0 | 2 |
| ruling | 1 | 0 | 0 | 0.7 | 0.7 | 1162 | 68 | 3724 | 204.2 | 0 | 1 |
| situation_agree | 2 | 0 | 0 | 0.1 | 0.2 | 211 | 14 | 2100 | 277.2 | 0 | 0 |

317 attempts for 282 calls, 7.7 minutes in the model in all.

## Fights

22 rounds with a fight call; 2.8 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 16 | 0.5 | 0.5 | 0 |
| combat_opening | 8 | 1.8 | 2.1 | 4 |
| combat_narrate | 26 | 1.9 | 2.6 | 4 |
| combat_aftermath | 11 | 1.6 | 1.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 88% | 20771 | 21643 | 21643 | 63 | 5% |
| npc_profile | 3 | 100% | 2524 | 2650 | 2650 | 1459 | 0% |
| dialogue_frame | 20 | 70% | 8851 | 9898 | 10827 | 4325 | 5% |
| hire_chat | 13 | 100% | 11452 | 12912 | 13164 | 2204 | 4% |
| canon_extract | 4 | 100% | 3480 | 4353 | 4353 | 848 | 0% |
| exchange | 14 | 86% | 12115 | 13015 | 13587 | 62 | 0% |
| overheard | 9 | 100% | 1125 | 1268 | 1268 | 231 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 8 | 88% | 95% | -8 | 21643 | 36345 | 36500 | 21643 | 5% |
| npc_profile | 3 | 100% | 100% | +0 | 2650 | 2774 | 3000 | 2650 | 0% |
| dialogue_frame | 20 | 70% | 86% | -16 | 9898 | 10715 | 11000 | 10827 | 5% |
| hire_chat | 13 | 100% | 98% | +2 | 12912 | 16275 | 16500 | 13164 | 4% |
| canon_extract | 4 | 100% | 100% | +0 | 4353 | 3998 | 4000 | 4353 | 0% |
| exchange | 14 | 86% | 90% | -4 | 13015 | 15039 | 15500 | 13587 | 0% |
| overheard | 9 | 100% | 100% | +0 | 1268 | 1326 | 1500 | 1268 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 21643 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -8).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 44 | 176959 | 129911 (73%) | 126568 (72%) |
| narrate | 33 | 82156 | 42042 (51%) | 28952 (35%) |
| combat_narrate | 26 | 74557 | 41859 (56%) | 28127 (38%) |
| dialogue_frame | 29 | 62754 | 32233 (51%) | 21491 (34%) |
| exchange | 16 | 48228 | 18213 (38%) | 6098 (13%) |
| npc_conversation | 9 | 44983 | 19910 (44%) | 6535 (15%) |
| hire_chat | 13 | 37498 | 18254 (49%) | 1319 (4%) |
| player_line | 49 | 26752 | 7096 (27%) | 3954 (15%) |
| combat_aftermath | 11 | 21009 | 9800 (47%) | 7625 (36%) |
| combat_interpret | 16 | 15334 | 12893 (84%) | 0 (0%) |
| combat_opening | 8 | 14868 | 7019 (47%) | 3529 (24%) |
| populate_place | 5 | 3635 | 1281 (35%) | 0 (0%) |
| canon_extract | 4 | 3612 | 2612 (72%) | 0 (0%) |
| persona_details | 4 | 3411 | 1654 (48%) | 942 (28%) |
| audit_compare | 15 | 3380 | 1714 (51%) | 0 (0%) |
| overheard | 9 | 2560 | 2003 (78%) | 0 (0%) |
| audit_meaning | 15 | 2394 | 1023 (43%) | 0 (0%) |
| board_stakes | 2 | 2241 | 788 (35%) | 0 (0%) |
| npc_profile | 3 | 1856 | 774 (42%) | 0 (0%) |
| road_event | 1 | 1814 | 795 (44%) | 0 (0%) |
| situation_parts | 1 | 1579 | 1055 (67%) | 0 (0%) |
| ruling | 1 | 1162 | 590 (51%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| situation_agree | 2 | 422 | 198 (47%) | 87 (21%) |

The prompts held 634228 tokens; the constant system messages were about 354206 of them (56%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 235227 (37%) and read the rest.
The server's log: 317 prompts; 217 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 811 checkpoints made, 44 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 4 situations started (4 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 1 failed.

Per game day within reach: 1.33 situations started, 0.33 doors, 0.33 moments, 0.3 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| 2 | 3 (3) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] The price of peace at Ironvein at the Ironcrown Peaks - starts, 13 days, 3 stages (within reach)
- day 2: [normal, engine-built] A find at the Ironcrown Peaks - starts, 2 days, 1 stages (within reach)
- day 2: [uncommon, engine-built] Saber-toothed tigers out of the Ironcrown Peaks at Ironvein - starts, 4 days, 2 stage (within reach)
- day 3: [uncommon, engine-built] The guild instructor and the baker at the temple door at Parth - starts, 6 days, 2 st (within reach)

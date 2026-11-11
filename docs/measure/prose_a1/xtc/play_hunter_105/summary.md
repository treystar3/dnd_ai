# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 21 | 5.2 | 9.1 | 5.0 | 6.6 | 5.9 | 5.4 | 9 | 0 |
| wait | 12 | 5.0 | 5.6 | 4.5 | 5.6 | 3.6 | 4.1 | 6 | 0 |
| talk | 6 | 3.1 | 4.2 | 3.1 | 4.2 | 3.7 | 3.4 | 1 | 0 |
| leave | 6 | 5.2 | 5.4 | 3.0 | 5.2 | 6.3 | 5.2 | 1 | 0 |
| search | 6 | 3.2 | 4.1 | 2.5 | 3.5 | 4.5 | 3.2 | 2 | 0 |
| rest | 4 | 5.2 | 5.7 | 2.7 | 5.7 | 4.0 | 3.7 | 1 | 0 |
| hire | 1 | 3.3 | 3.3 | 3.3 | 3.3 | 4.0 | 2.1 | 0 | 0 |
| board | 1 | 4.9 | 4.9 | 4.9 | 4.9 | 6.0 | 4.8 | 0 | 0 |
| pick_up | 1 | 1.6 | 1.6 | 1.5 | 1.5 | 2.0 | 1.5 | 0 | 0 |
| fight | 1 | 4.6 | 4.6 | 2.6 | 2.6 | 3.0 | 4.6 | 0 | 0 |
| look | 1 | 7.4 | 7.4 | 6.2 | 6.2 | 9.0 | 7.3 | 0 | 0 |

60 turns in 4.6 minutes; 97% of it in the model; 239 embedding calls taking 1.1 s; 1 calls on background threads.
The budget: 3 optional calls deferred and 3 dropped; 3 turns told by a stand-in, 3 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 18.2 s and p90 29.9 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 11.5 s, leave, 7 calls, at the adventurers' guild house: "That's all from me. Let's hit the road."
- 11.5 s, move, 10 calls, at Parth: "Let's move out toward the Willowmead wetlands; time to see if these mo"
- 9.5 s, move, 9 calls, at the Willowmead wetlands: "We have enough here; let's head back to the Adventurers' Guild House."
- 9.1 s, move, 10 calls, at the King's Road between Parth and Willowmead: "Let's push toward the Willowmead wetlands; I want to see what kind of "
- 8.5 s, move, 9 calls, at the adventurers' guild house: "We should move to the Tilted Plough."

Lines by what read them: interpret 57, hire 2, combat 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 57 (template 3; model failed 1, 25 s) |
| Lines picking up the passage before | 11 of 60 (18%); in talk 4 of 6 (67%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 1 |
| Goals finished / given up | 7 / 1 (contract 4/0, go 1/0, report 2/0, revisit 0/1) |
| Deaths (above the level band) | 0 (0) |
| Fights | 1 |
| Waits | 12 of 60 (20%) |
| Places visited | 7 |

Turns by goal: report 21, idle 12, need 11, contract 7, revisit 3, board 2, cont 1, stop 1, fight 1, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 19 (id 8, broken 7, escape 2, script 1, first_person 1) |
| Machinery mended at the screen | 147 (dash 126, json 1, stage 5, wrap 15) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 7 times; 0 of the game's 18 own lines (0%); most: "You are back at the adventurers' guild house." x7 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '}') |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 49 |
| Matters the player ended: pursued / by accident | 0 / 1 (by accident: The land about Willowmead) |
| Fights won / for +0 XP / XP median and most | 1 / 0 / 4 and 4 |
| Fight turns with a foe 10+ levels above the player | 0 of 1, the widest -10 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 3 / 0 (e.g. turn 5 the ink-stained scribe contract_taken; turn 48 the barrel-chested host contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| narrate | 38 | 13 | 15 | 1.7 | 2.3 | 2415 | 182 | 5185 | 137.5 | 0 | 88 |
| populate_place | 6 | 0 | 0 | 1.4 | 1.5 | 702 | 291 | 3556 | 234.3 | 0 | 48 |
| interpret_action | 66 | 0 | 0 | 0.6 | 0.8 | 4016 | 64 | 11813 | 240.1 | 0 | 42 |
| dialogue_frame | 21 | 6 | 7 | 1.1 | 1.6 | 2119 | 83 | 4370 | 128.6 | 0 | 31 |
| player_line | 58 | 14 | 15 | 0.4 | 0.4 | 537 | 24 | 2862 | 135.9 | 0 | 25 |
| npc_conversation | 10 | 0 | 0 | 2.0 | 2.6 | 5035 | 180 | 5893 | 139.4 | 0 | 21 |
| exchange | 15 | 0 | 0 | 1.3 | 1.4 | 3132 | 112 | 4919 | 165.4 | 0 | 20 |
| hire_chat | 21 | 1 | 1 | 0.9 | 1.0 | 2675 | 56 | 4813 | 179.5 | 0 | 20 |
| audit_compare | 30 | 0 | 0 | 0.3 | 0.3 | 225 | 42 | 2400 | 250.9 | 0 | 8 |
| audit_meaning | 30 | 0 | 0 | 0.2 | 0.2 | 164 | 22 | 1981 | 163.3 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.6 | 819 | 229 | 3342 | 178.0 | 0 | 5 |
| overheard | 21 | 0 | 0 | 0.2 | 0.2 | 275 | 16 | 1958 | 299.2 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.2 | 4.2 | 1050 | 912 | 3116 | 239.7 | 0 | 4 |
| board_stakes | 2 | 0 | 0 | 1.4 | 2.6 | 1128 | 354 | 3905 | 205.2 | 0 | 4 |
| road_event | 1 | 0 | 0 | 2.7 | 2.7 | 1745 | 370 | 3469 | 170.6 | 0 | 3 |
| combat_opening | 1 | 1 | 1 | 1.0 | 1.4 | 1656 | 140 | 4382 | 179.0 | 0 | 2 |
| combat_narrate | 1 | 0 | 0 | 2.1 | 2.1 | 2630 | 201 | 4465 | 130.7 | 0 | 2 |
| combat_aftermath | 1 | 0 | 0 | 2.0 | 2.0 | 1791 | 243 | 3778 | 162.0 | 0 | 2 |
| npc_profile | 3 | 0 | 0 | 0.6 | 0.7 | 603 | 90 | 3339 | 190.0 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1402 | 268 | 3739 | 179.6 | 0 | 2 |
| ruling | 2 | 0 | 0 | 0.7 | 0.7 | 1208 | 68 | 3812 | 181.7 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.3 | 1.0 | 935 | 82 | 3243 | 256.6 | 0 | 1 |
| combat_interpret | 1 | 0 | 0 | 0.5 | 0.5 | 972 | 49 | 3047 | 304.3 | 0 | 0 |
| clarify | 1 | 0 | 0 | 0.3 | 0.3 | 278 | 36 | 2598 | 187.5 | 0 | 0 |

371 attempts for 336 calls, 5.7 minutes in the model in all.

## Fights

2 rounds with a fight call; 2.5 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 1 | 0.5 | 0.5 | 0 |
| combat_opening | 2 | 1.0 | 1.4 | 1 |
| combat_narrate | 1 | 2.1 | 2.1 | 0 |
| combat_aftermath | 1 | 2.0 | 2.0 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 10 | 100% | 20197 | 21473 | 21473 | 52 | 0% |
| npc_profile | 3 | 100% | 2482 | 2605 | 2605 | 1417 | 0% |
| dialogue_frame | 21 | 81% | 8462 | 10185 | 10508 | 3707 | 4% |
| hire_chat | 21 | 95% | 10787 | 13230 | 13330 | 2075 | 0% |
| canon_extract | 2 | 100% | 3339 | 4323 | 4323 | 707 | 0% |
| exchange | 15 | 100% | 12761 | 15151 | 15164 | 61 | 0% |
| overheard | 21 | 100% | 1105 | 1173 | 1302 | 211 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 10 | 100% | 95% | +5 | 21473 | 36345 | 36500 | 21473 | 0% |
| npc_profile | 3 | 100% | 100% | +0 | 2605 | 2774 | 3000 | 2605 | 0% |
| dialogue_frame | 21 | 81% | 86% | -5 | 10185 | 10715 | 11000 | 10508 | 4% |
| hire_chat | 21 | 95% | 98% | -3 | 13230 | 16275 | 16500 | 13330 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 4323 | 3998 | 4000 | 4323 | 0% |
| exchange | 15 | 100% | 90% | +10 | 15151 | 15039 | 15500 | 15164 | 0% |
| overheard | 21 | 100% | 100% | +0 | 1173 | 1326 | 1500 | 1302 | 0% |

Size: 5 of 7 tasks at or below the baseline's p95 (dearer: canon_extract, exchange); npc_conversation's p95 21473 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 66 | 264519 | 194286 (73%) | 207394 (78%) |
| narrate | 51 | 125455 | 64703 (52%) | 41385 (33%) |
| hire_chat | 22 | 62093 | 30913 (50%) | 3309 (5%) |
| dialogue_frame | 27 | 56010 | 30921 (55%) | 14410 (26%) |
| npc_conversation | 10 | 50122 | 22066 (44%) | 0 (0%) |
| exchange | 15 | 47064 | 16833 (36%) | 0 (0%) |
| player_line | 72 | 38280 | 10458 (27%) | 7511 (20%) |
| audit_compare | 30 | 6822 | 3488 (51%) | 0 (0%) |
| overheard | 21 | 5849 | 4677 (80%) | 0 (0%) |
| audit_meaning | 30 | 4924 | 2069 (42%) | 0 (0%) |
| populate_place | 6 | 4281 | 1535 (36%) | 0 (0%) |
| combat_opening | 2 | 3313 | 1792 (54%) | 1563 (47%) |
| combat_narrate | 1 | 2630 | 1586 (60%) | 0 (0%) |
| ruling | 2 | 2417 | 1164 (48%) | 0 (0%) |
| persona_details | 3 | 2406 | 1090 (45%) | 0 (0%) |
| board_stakes | 2 | 2257 | 782 (35%) | 0 (0%) |
| canon_extract | 2 | 1871 | 1287 (69%) | 0 (0%) |
| npc_profile | 3 | 1830 | 773 (42%) | 0 (0%) |
| combat_aftermath | 1 | 1791 | 893 (50%) | 0 (0%) |
| road_event | 1 | 1745 | 791 (45%) | 0 (0%) |
| moment | 1 | 1402 | 746 (53%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| combat_interpret | 1 | 972 | 809 (83%) | 0 (0%) |
| clarify | 1 | 278 | 143 (51%) | 0 (0%) |

The prompts held 689381 tokens; the constant system messages were about 394293 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 275572 (40%) and read the rest.
The server's log: 371 prompts; 262 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 894 checkpoints made, 48 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 3 situations started (3 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 0.00 doors, 0.33 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 2 (2) | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| 3 | 1 (1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] The land about Willowmead - starts, 1 days, 1 stages (within reach)
- day 2: [normal, engine-built] The unquiet of the Shipwreck Shoals at Kelpmoor - starts, 1 days, 1 stages (within reach)
- day 3: [normal, engine-built] A hunt for the octopus at Kelpmoor - starts, 1 days, 1 stages (within reach)

# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| search | 20 | 5.2 | 7.8 | 5.2 | 6.8 | 4.3 | 4.9 | 1 | 0 |
| move | 16 | 9.9 | 13.0 | 7.2 | 9.6 | 7.4 | 9.0 | 6 | 0 |
| fight | 13 | 6.8 | 9.0 | 3.2 | 6.2 | 3.3 | 6.0 | 2 | 0 |
| wait | 6 | 5.3 | 8.0 | 5.3 | 6.8 | 4.8 | 6.7 | 2 | 0 |
| rest | 2 | 8.5 | 9.3 | 6.0 | 9.3 | 6.5 | 8.7 | 1 | 0 |
| board | 1 | 8.9 | 8.9 | 6.8 | 6.8 | 7.0 | 8.7 | 0 | 0 |
| talk | 1 | 2.9 | 2.9 | 2.9 | 2.9 | 2.0 | 2.8 | 0 | 0 |
| leave | 1 | 14.4 | 14.4 | 8.1 | 8.1 | 7.0 | 14.2 | 0 | 0 |

60 turns in 6.9 minutes; 97% of it in the model; 206 embedding calls taking 1.8 s; 1 calls on background threads.
The budget: 9 optional calls deferred and 5 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 19.9 s and p90 36.7 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 14.8 s, move, 11 calls, at the trading square: "I gesture toward the north and tell the others we're headed for the Gr"
- 14.4 s, leave, 7 calls, at the adventurers' guild house: "I nod at the group and turn toward the door, ready to head out."
- 13.0 s, move, 9 calls, at the Tilted Plough: "I stand up and tell them we're headed straight for the Adventurers' Gu"
- 12.6 s, move, 8 calls, at the adventurers' guild house: "Enough talk. Let's head straight to the Tilted Plough."
- 12.3 s, wait, 9 calls, at the adventurers' guild house: "I lean back against the wall and wait for everyone to finish prepping."

Lines by what read them: interpret 47, combat 10, hire 3

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 55 of 60 (92%) |
| Lines the model wrote | 46 (template 14; model failed 0, 30 s) |
| Lines picking up the passage before | 9 of 60 (15%); in talk 0 of 1 (0%) |
| Contracts taken / finished | 0 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 6 / 3 (go 2/0, hunt 4/0, revisit 0/3) |
| Deaths (above the level band) | 0 (0) |
| Fights | 13 |
| Waits | 6 of 60 (10%) |
| Places visited | 5 |

Turns by goal: hunt 25, revisit 11, fight 10, idle 7, need 4, go 2, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 4, note 2, script 1) |
| Machinery mended at the screen | 1062 (dash 1054, stage 1, wrap 7) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("there's nothing here to skin or butcher.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 16.7 |
| Parts made different by an attempt (blocked, lit, cleared...) | 3 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 6 times; 6 of the game's 32 own lines (19%); most: 'Victory. +# XP' x6 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 2 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 90 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 7 / 5 / 0 and 43 |
| Fight turns with a foe 10+ levels above the player | 0 of 10, the widest -8 |
| Marks shown from acts (Remembered here) | 7 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 4 | 0 | 0 | 1.8 | 123.9 | 671 | 253 | 1287 | 160.8 | 0 | 128 |
| narrate | 48 | 3 | 4 | 2.3 | 2.9 | 2373 | 170 | 2816 | 116.8 | 0 | 117 |
| interpret_action | 51 | 1 | 1 | 0.9 | 1.2 | 3613 | 51 | 6040 | 197.5 | 0 | 51 |
| dialogue_frame | 25 | 2 | 2 | 1.4 | 1.8 | 2065 | 63 | 2367 | 125.0 | 0 | 40 |
| combat_narrate | 12 | 2 | 2 | 2.3 | 3.3 | 2957 | 183 | 3360 | 123.8 | 0 | 35 |
| player_line | 46 | 8 | 8 | 0.6 | 0.6 | 553 | 23 | 1617 | 102.5 | 0 | 30 |
| combat_aftermath | 13 | 0 | 0 | 2.1 | 2.6 | 1914 | 219 | 2762 | 155.6 | 0 | 27 |
| hire_chat | 19 | 1 | 1 | 1.2 | 1.4 | 2729 | 49 | 2947 | 165.1 | 0 | 26 |
| exchange | 13 | 1 | 1 | 1.5 | 1.8 | 3016 | 88 | 2934 | 150.0 | 0 | 22 |
| combat_opening | 7 | 1 | 1 | 2.2 | 2.6 | 1785 | 180 | 2450 | 119.5 | 0 | 18 |
| npc_conversation | 3 | 0 | 0 | 2.7 | 6.6 | 5133 | 137 | 4058 | 71.5 | 0 | 11 |
| ruling | 7 | 0 | 0 | 1.2 | 1.4 | 1313 | 87 | 2251 | 173.5 | 0 | 9 |
| audit_compare | 27 | 0 | 0 | 0.3 | 0.3 | 216 | 39 | 1506 | 229.2 | 0 | 9 |
| audit_meaning | 27 | 0 | 0 | 0.3 | 0.3 | 146 | 23 | 1138 | 132.9 | 0 | 8 |
| persona_details | 3 | 1 | 2 | 2.1 | 2.2 | 720 | 252 | 1720 | 167.7 | 0 | 8 |
| combat_interpret | 10 | 0 | 0 | 0.8 | 0.8 | 972 | 47 | 1717 | 248.8 | 0 | 8 |
| overheard | 17 | 0 | 0 | 0.3 | 0.3 | 277 | 16 | 1086 | 255.1 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.8 | 4.8 | 1064 | 900 | 1586 | 216.6 | 0 | 5 |
| situation_parts | 1 | 0 | 0 | 3.5 | 3.5 | 1556 | 680 | 2066 | 248.6 | 0 | 4 |
| canon_extract | 6 | 0 | 0 | 0.5 | 0.6 | 764 | 4 | 1543 | 176.5 | 0 | 3 |
| npc_profile | 1 | 0 | 0 | 0.8 | 0.8 | 636 | 78 | 2106 | 172.9 | 0 | 1 |
| situation_agree | 1 | 0 | 0 | 0.2 | 0.2 | 175 | 14 | 921 | 259.3 | 0 | 0 |

362 attempts for 342 calls, 9.4 minutes in the model in all.

## Fights

17 rounds with a fight call; 2.6 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 10 | 0.8 | 0.8 | 0 |
| combat_opening | 8 | 2.2 | 2.7 | 1 |
| combat_narrate | 14 | 2.3 | 3.3 | 2 |
| combat_aftermath | 13 | 2.1 | 2.6 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 20311 | 20517 | 20517 | 47 | 0% |
| npc_profile | 1 | 100% | 2642 | 2642 | 2642 | 1577 | 0% |
| dialogue_frame | 25 | 92% | 8552 | 10079 | 10224 | 3256 | 5% |
| hire_chat | 19 | 95% | 11025 | 13691 | 14112 | 1643 | 0% |
| canon_extract | 6 | 100% | 2771 | 3551 | 3551 | 139 | 0% |
| exchange | 13 | 92% | 12193 | 12929 | 13679 | 62 | 0% |
| overheard | 17 | 100% | 1102 | 1130 | 1145 | 208 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 95% | +5 | 20517 | 36345 | 36500 | 20517 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2642 | 2774 | 3000 | 2642 | 0% |
| dialogue_frame | 25 | 92% | 86% | +6 | 10079 | 10715 | 11000 | 10224 | 5% |
| hire_chat | 19 | 95% | 98% | -3 | 13691 | 16275 | 16500 | 14112 | 0% |
| canon_extract | 6 | 100% | 100% | +0 | 3551 | 3998 | 4000 | 3551 | 0% |
| exchange | 13 | 92% | 90% | +3 | 12929 | 15039 | 15500 | 13679 | 0% |
| overheard | 17 | 100% | 100% | +0 | 1130 | 1326 | 1500 | 1145 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 20517 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 52 | 193788 | 151025 (78%) | 148692 (77%) |
| narrate | 51 | 118839 | 69001 (58%) | 35180 (30%) |
| dialogue_frame | 27 | 56661 | 35137 (62%) | 6452 (11%) |
| hire_chat | 20 | 56653 | 32689 (58%) | 3458 (6%) |
| combat_narrate | 14 | 41474 | 26174 (63%) | 11619 (28%) |
| exchange | 14 | 39377 | 15726 (40%) | 3098 (8%) |
| player_line | 54 | 29871 | 7719 (26%) | 4700 (16%) |
| combat_aftermath | 13 | 24859 | 13531 (54%) | 11305 (45%) |
| npc_conversation | 3 | 15081 | 7397 (49%) | 0 (0%) |
| combat_opening | 8 | 14027 | 8166 (58%) | 3884 (28%) |
| combat_interpret | 10 | 9656 | 8070 (84%) | 0 (0%) |
| ruling | 7 | 9115 | 4032 (44%) | 0 (0%) |
| audit_compare | 27 | 5869 | 3131 (53%) | 0 (0%) |
| overheard | 17 | 4682 | 3805 (81%) | 0 (0%) |
| canon_extract | 6 | 4640 | 3980 (86%) | 0 (0%) |
| audit_meaning | 27 | 4009 | 1899 (47%) | 0 (0%) |
| persona_details | 4 | 2934 | 1652 (56%) | 597 (20%) |
| populate_place | 4 | 2693 | 1018 (38%) | 0 (0%) |
| situation_parts | 1 | 1556 | 1050 (68%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| npc_profile | 1 | 636 | 256 (40%) | 0 (0%) |
| situation_agree | 1 | 175 | 100 (57%) | 0 (0%) |

The prompts held 637659 tokens; the constant system messages were about 396047 of them (62%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 228985 (36%) and read the rest.
The server's log: 362 prompts; 266 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 875 checkpoints made, 28 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.00 doors, 0.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | 1 (1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] Not come back from the Greywood - starts, 11 days, 3 stages (within reach)

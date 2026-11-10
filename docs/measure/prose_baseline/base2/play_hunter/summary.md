# Night run: play_hunter

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.14 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 22 | 6.2 | 12.3 | 4.2 | 6.2 | 3.3 | 7.2 | 1 | 0 |
| search | 18 | 4.9 | 7.8 | 4.5 | 5.5 | 4.4 | 5.9 | 3 | 0 |
| move | 7 | 11.3 | 15.0 | 8.1 | 9.4 | 7.4 | 10.0 | 4 | 0 |
| talk | 5 | 9.1 | 30.4 | 9.1 | 30.3 | 3.8 | 13.5 | 2 | 0 |
| leave | 3 | 8.8 | 15.4 | 7.5 | 8.7 | 6.0 | 9.5 | 1 | 0 |
| hire | 2 | 6.7 | 9.4 | 6.6 | 7.4 | 6.5 | 7.8 | 0 | 0 |
| board | 2 | 1.3 | 7.8 | 7.8 | 7.8 | 3.0 | 4.5 | 0 | 0 |
| look | 1 | 4.7 | 4.7 | 4.7 | 4.7 | 5.0 | 4.6 | 0 | 0 |

60 turns in 7.9 minutes; 97% of it in the model; 149 embedding calls taking 1.9 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 4 dropped; 3 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 19.1 s and p90 36.4 s, over 60 s in 1 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 30.4 s, talk, 6 calls, at the adventurers' guild house: "Hey, girl, those four lizardfolks in Willowmead are dead. Give me my c"
- 18.1 s, talk, 2 calls, at the adventurers' guild house: "I take the parchment and nod to her. Is there anything else that needs"
- 16.3 s, move, 12 calls, at the Willowmead wetlands: "I signal to the group and tell them we're heading back to the Adventur"
- 15.4 s, leave, 9 calls, at the adventurers' guild house: "I turn away from the group and head for the door without another word."
- 15.0 s, move, 10 calls, at the adventurers' guild house: "We're heading out to the Willowmead wetlands; I want those rewards."

Lines by what read them: interpret 37, combat 22, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 50 of 60 (83%) |
| Lines the model wrote | 37 (template 23; model failed 1, 26 s) |
| Lines picking up the passage before | 18 of 60 (30%); in talk 3 of 5 (60%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 3 / 3 (contract 1/0, find 0/1, follow 0/2, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 22 |
| Waits | 0 of 60 (0%) |
| Places visited | 9 |

Turns by goal: fight 22, contract 15, follow 11, idle 5, report 4, board 2, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 6 (script 3, id 2, escape 1) |
| Machinery mended at the screen | 5208 (dash 5192, note 2, wrap 14) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("bronze longsword is already in hand.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 2 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 14.3 |
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
| Lines shown 5+ times word for word (digits aside) | 2 lines, 14 times; 14 of the game's 38 own lines (37%); most: 'Victory. +# XP' x8; 'The fallen can be skinned or butchered for its h' x6 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 1 / 0 (e.g. '[') |
| City ground in the wilds / rain under a roof / weather out of season | 3 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 95 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 12 / 0 / 9 and 476 |
| Fight turns with a foe 10+ levels above the player | 0 of 22, the widest -1 |
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
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 3 | 0 | 0 | 2.0 | 125.7 | 693 | 291 | 1079 | 118.6 | 0 | 129 |
| combat_narrate | 24 | 1 | 1 | 3.1 | 4.2 | 3033 | 205 | 2468 | 114.7 | 0 | 77 |
| narrate | 22 | 3 | 3 | 2.5 | 3.5 | 2341 | 160 | 2208 | 111.9 | 0 | 63 |
| npc_conversation | 7 | 1 | 1 | 3.6 | 16.9 | 5169 | 182 | 3394 | 85.7 | 0 | 59 |
| interpret_action | 41 | 0 | 0 | 1.1 | 1.6 | 3679 | 66 | 4649 | 203.9 | 0 | 49 |
| combat_aftermath | 17 | 0 | 0 | 2.4 | 2.7 | 1973 | 191 | 1945 | 144.4 | 0 | 40 |
| combat_opening | 12 | 1 | 1 | 2.7 | 3.2 | 1836 | 192 | 1759 | 117.6 | 0 | 34 |
| dialogue_frame | 17 | 2 | 2 | 1.7 | 1.8 | 2197 | 55 | 1920 | 117.9 | 0 | 32 |
| player_line | 38 | 4 | 5 | 0.6 | 0.7 | 549 | 24 | 1386 | 106.9 | 0 | 26 |
| exchange | 9 | 3 | 5 | 1.8 | 2.6 | 2600 | 78 | 2614 | 140.3 | 0 | 22 |
| hire_chat | 12 | 0 | 0 | 1.6 | 1.8 | 2560 | 52 | 2195 | 150.1 | 0 | 19 |
| combat_interpret | 22 | 0 | 0 | 0.9 | 0.9 | 953 | 47 | 1389 | 248.6 | 0 | 19 |
| road_event | 3 | 0 | 0 | 3.0 | 3.2 | 1717 | 319 | 1812 | 154.3 | 0 | 9 |
| audit_compare | 23 | 0 | 0 | 0.3 | 0.4 | 220 | 38 | 1276 | 216.4 | 0 | 8 |
| audit_meaning | 23 | 0 | 0 | 0.3 | 0.4 | 146 | 23 | 1017 | 127.5 | 0 | 8 |
| persona_details | 3 | 0 | 0 | 2.0 | 2.0 | 804 | 229 | 1698 | 159.5 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.5 | 5.5 | 1036 | 930 | 1347 | 197.7 | 0 | 5 |
| overheard | 10 | 0 | 0 | 0.3 | 0.4 | 276 | 16 | 972 | 241.7 | 0 | 4 |
| npc_profile | 3 | 0 | 0 | 1.0 | 1.1 | 650 | 99 | 1707 | 151.4 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.6 | 2.6 | 1407 | 231 | 1759 | 125.8 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.0 | 2.0 | 890 | 243 | 1618 | 170.6 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.6 | 0.6 | 821 | 2 | 1476 | 127.7 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.2 | 1.2 | 1328 | 72 | 1886 | 146.0 | 0 | 1 |

311 attempts for 296 calls, 10.4 minutes in the model in all.

## Fights

33 rounds with a fight call; 2.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 22 | 0.9 | 0.9 | 0 |
| combat_opening | 13 | 2.7 | 3.2 | 1 |
| combat_narrate | 25 | 3.1 | 4.2 | 1 |
| combat_aftermath | 17 | 2.4 | 2.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 20379 | 21130 | 21130 | 88 | 0% |
| npc_profile | 3 | 100% | 2710 | 2767 | 2767 | 1645 | 0% |
| dialogue_frame | 17 | 88% | 8949 | 10377 | 10463 | 3113 | 0% |
| hire_chat | 12 | 100% | 10429 | 12114 | 13502 | 1574 | 0% |
| canon_extract | 3 | 100% | 3332 | 3418 | 3418 | 700 | 0% |
| exchange | 9 | 67% | 10820 | 14068 | 14068 | 63 | 23% |
| overheard | 10 | 100% | 1124 | 1161 | 1161 | 230 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 95% | -9 | 21130 | 36345 | 36500 | 21130 | 0% |
| npc_profile | 3 | 100% | 100% | +0 | 2767 | 2774 | 3000 | 2767 | 0% |
| dialogue_frame | 17 | 88% | 86% | +2 | 10377 | 10715 | 11000 | 10463 | 0% |
| hire_chat | 12 | 100% | 98% | +2 | 12114 | 16275 | 16500 | 13502 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 3418 | 3998 | 4000 | 3418 | 0% |
| exchange | 9 | 67% | 90% | -23 | 14068 | 15039 | 15500 | 14068 | 23% |
| overheard | 10 | 100% | 100% | +0 | 1161 | 1326 | 1500 | 1161 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 21130 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -9; exchange -23).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 41 | 161031 | 119793 (74%) | 118809 (74%) |
| combat_narrate | 25 | 75064 | 47427 (63%) | 8870 (12%) |
| narrate | 25 | 60018 | 35882 (60%) | 17064 (28%) |
| dialogue_frame | 19 | 41723 | 26047 (62%) | 4589 (11%) |
| npc_conversation | 8 | 39779 | 19553 (49%) | 4290 (11%) |
| exchange | 12 | 34266 | 13385 (39%) | 11768 (34%) |
| combat_aftermath | 17 | 33193 | 18065 (54%) | 9772 (29%) |
| hire_chat | 12 | 31986 | 19391 (61%) | 0 (0%) |
| combat_opening | 13 | 23057 | 13581 (59%) | 3360 (15%) |
| player_line | 42 | 22873 | 6025 (26%) | 2061 (9%) |
| combat_interpret | 22 | 21029 | 17625 (84%) | 0 (0%) |
| road_event | 3 | 5228 | 2381 (46%) | 0 (0%) |
| audit_compare | 23 | 5116 | 2656 (52%) | 0 (0%) |
| audit_meaning | 23 | 3526 | 1555 (44%) | 0 (0%) |
| overheard | 10 | 2762 | 2195 (79%) | 0 (0%) |
| canon_extract | 3 | 2478 | 1944 (78%) | 0 (0%) |
| persona_details | 3 | 2387 | 1095 (46%) | 0 (0%) |
| populate_place | 3 | 2078 | 760 (37%) | 0 (0%) |
| npc_profile | 3 | 1963 | 772 (39%) | 0 (0%) |
| moment | 1 | 1407 | 752 (53%) | 0 (0%) |
| ruling | 1 | 1328 | 568 (43%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| board_stakes | 1 | 890 | 373 (42%) | 0 (0%) |

The prompts held 574218 tokens; the constant system messages were about 352319 of them (61%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 180583 (31%) and read the rest.
The server's log: 311 prompts; 238 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 757 checkpoints made, 22 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 2 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 1 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| 3 | 1 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)
- day 3: [normal, engine-built] The unquiet of the Greywood at Parth - starts, 1 days, 1 stages

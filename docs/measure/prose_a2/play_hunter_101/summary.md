# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.13 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| search | 15 | 4.5 | 10.7 | 4.5 | 10.7 | 3.7 | 5.5 | 1 | 0 |
| fight | 14 | 7.0 | 12.1 | 4.9 | 7.1 | 3.5 | 7.4 | 4 | 0 |
| move | 12 | 7.2 | 13.6 | 5.5 | 10.4 | 4.4 | 6.3 | 2 | 0 |
| talk | 8 | 5.3 | 6.9 | 5.3 | 6.9 | 4.1 | 5.5 | 1 | 0 |
| leave | 6 | 10.5 | 13.0 | 4.5 | 5.1 | 6.7 | 9.5 | 0 | 0 |
| board | 2 | 6.7 | 8.5 | 6.6 | 8.5 | 6.0 | 7.4 | 1 | 0 |
| hire | 1 | 10.4 | 10.4 | 6.7 | 6.7 | 8.0 | 10.1 | 0 | 0 |
| pick_up | 1 | 4.0 | 4.0 | 3.9 | 3.9 | 4.0 | 3.9 | 0 | 0 |
| shop | 1 | 15.4 | 15.4 | 10.3 | 10.3 | 8.0 | 15.2 | 0 | 0 |

60 turns in 7.0 minutes; 97% of it in the model; 163 embedding calls taking 1.8 s; 1 calls on background threads.
The budget: 3 optional calls deferred and 4 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 22.0 s and p90 41.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.4 s, shop, 8 calls, at the adventurers' guild house: "I approach the clerk and tell him I want to sell this shortbow."
- 13.7 s, move, 9 calls, at the King's Road between Parth and Willowmead: "We need to move towards the Willowmead wetlands while the mist is stil"
- 13.6 s, move, 8 calls, at the King's Pass between Parth and Ironvein: "We're heading for the Grey Mountains; let's see what's hiding in that "
- 13.5 s, leave, 8 calls, at the adventurers' guild house: "I give a sharp nod and start moving toward the door with my gear packe"
- 13.2 s, fight, 5 calls, at the King's Road between Willowmead and Parth: "I use Brutal Strike on giant toad."

Lines by what read them: interpret 46, combat 13, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 55 of 60 (92%) |
| Lines the model wrote | 45 (template 15; model failed 0, 36 s) |
| Lines picking up the passage before | 21 of 60 (35%); in talk 2 of 8 (25%) |
| Contracts taken / finished | 3 / 1 |
| Situations met / followed / ended by the player | 1 / 1 / 0 |
| Goals finished / given up | 3 / 3 (contract 1/0, find 0/1, follow 0/2, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 14 |
| Waits | 0 of 60 (0%) |
| Places visited | 10 |

Turns by goal: contract 15, fight 13, idle 10, follow 10, board 4, report 4, go 1, cont 1, stop 1, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 9 (id 4, script 2, first_person 1, note 1, json 1) |
| Machinery mended at the screen | 4135 (dash 4124, stage 1, wrap 10) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("there's no one here to let go.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 3 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 3 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 23.1 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 34 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 2 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 6 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 62 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 6 / 0 / 135 and 1427 |
| Fight turns with a foe 10+ levels above the player | 0 of 14, the widest -1 |
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
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 4 the ink-stained girl contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 5 | 0 | 0 | 1.9 | 125.7 | 706 | 282 | 1787 | 178.1 | 0 | 254 |
| narrate | 35 | 2 | 2 | 2.5 | 3.3 | 2438 | 191 | 2863 | 114.6 | 0 | 96 |
| interpret_action | 53 | 0 | 0 | 1.1 | 1.4 | 4100 | 59 | 5277 | 196.2 | 0 | 59 |
| combat_narrate | 16 | 4 | 4 | 2.9 | 3.5 | 3095 | 246 | 3420 | 123.6 | 0 | 57 |
| npc_conversation | 16 | 0 | 0 | 2.8 | 3.8 | 5209 | 160 | 4073 | 108.1 | 0 | 47 |
| player_line | 45 | 12 | 12 | 0.6 | 0.7 | 531 | 23 | 1516 | 104.8 | 0 | 36 |
| dialogue_frame | 15 | 2 | 2 | 1.4 | 1.7 | 2166 | 50 | 2284 | 126.8 | 0 | 24 |
| combat_opening | 8 | 0 | 0 | 2.6 | 3.2 | 1801 | 199 | 2004 | 119.0 | 0 | 21 |
| combat_aftermath | 9 | 0 | 0 | 2.2 | 2.9 | 2039 | 242 | 2432 | 153.2 | 0 | 21 |
| hire_chat | 10 | 1 | 1 | 1.4 | 1.4 | 2586 | 54 | 2707 | 166.3 | 0 | 15 |
| combat_interpret | 13 | 0 | 0 | 0.8 | 0.8 | 955 | 47 | 1595 | 266.6 | 0 | 10 |
| exchange | 6 | 0 | 0 | 1.5 | 1.7 | 2895 | 76 | 2726 | 134.6 | 0 | 10 |
| road_event | 3 | 0 | 0 | 3.1 | 3.4 | 1744 | 376 | 2337 | 158.6 | 0 | 9 |
| audit_meaning | 25 | 0 | 0 | 0.3 | 0.4 | 165 | 23 | 1075 | 124.2 | 0 | 9 |
| audit_compare | 25 | 0 | 0 | 0.3 | 0.4 | 221 | 40 | 1501 | 225.8 | 0 | 9 |
| persona_details | 3 | 0 | 0 | 1.7 | 1.9 | 784 | 221 | 1955 | 165.3 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.9 | 4.9 | 1036 | 918 | 1553 | 219.3 | 0 | 5 |
| npc_profile | 3 | 0 | 0 | 1.0 | 1.0 | 653 | 104 | 1825 | 165.4 | 0 | 3 |
| board_stakes | 2 | 0 | 0 | 0.9 | 1.8 | 954 | 161 | 2055 | 189.0 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.6 | 2.6 | 1410 | 232 | 1803 | 125.3 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.5 | 2.5 | 2935 | 254 | 2855 | 170.7 | 0 | 3 |
| overheard | 7 | 0 | 0 | 0.3 | 0.4 | 278 | 16 | 1008 | 247.8 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.0 | 1.0 | 1295 | 63 | 2133 | 151.4 | 0 | 1 |

324 attempts for 303 calls, 11.7 minutes in the model in all.

## Fights

21 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 13 | 0.8 | 0.8 | 0 |
| combat_opening | 8 | 2.6 | 3.2 | 0 |
| combat_narrate | 20 | 2.9 | 3.7 | 4 |
| combat_aftermath | 9 | 2.2 | 3.0 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 16 | 100% | 20690 | 22528 | 24086 | 72 | 3% |
| npc_profile | 3 | 100% | 2689 | 2696 | 2696 | 1624 | 0% |
| dialogue_frame | 15 | 87% | 8999 | 10832 | 11530 | 3591 | 0% |
| hire_chat | 10 | 90% | 10459 | 12577 | 12577 | 1499 | 6% |
| exchange | 6 | 100% | 11916 | 14919 | 14919 | 63 | 0% |
| overheard | 7 | 100% | 1139 | 1156 | 1156 | 245 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 16 | 100% | 95% | +5 | 22528 | 36345 | 36500 | 24086 | 3% |
| npc_profile | 3 | 100% | 100% | +0 | 2696 | 2774 | 3000 | 2696 | 0% |
| dialogue_frame | 15 | 87% | 86% | +1 | 10832 | 10715 | 11000 | 11530 | 0% |
| hire_chat | 10 | 90% | 98% | -8 | 12577 | 16275 | 16500 | 12577 | 6% |
| exchange | 6 | 100% | 90% | +10 | 14919 | 15039 | 15500 | 14919 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1156 | 1326 | 1500 | 1156 | 0% |

Size: 5 of 6 tasks at or below the baseline's p95 (dearer: dialogue_frame); npc_conversation's p95 22528 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -8).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 53 | 215605 | 156008 (72%) | 161013 (75%) |
| narrate | 37 | 89079 | 50401 (57%) | 33335 (37%) |
| npc_conversation | 16 | 85334 | 39316 (46%) | 2404 (3%) |
| combat_narrate | 20 | 62575 | 37380 (60%) | 21553 (34%) |
| dialogue_frame | 17 | 37394 | 22542 (60%) | 4405 (12%) |
| player_line | 57 | 31223 | 8198 (26%) | 6340 (20%) |
| hire_chat | 11 | 29273 | 17833 (61%) | 4153 (14%) |
| combat_aftermath | 9 | 17972 | 9283 (52%) | 6001 (33%) |
| exchange | 6 | 17199 | 6607 (38%) | 0 (0%) |
| combat_opening | 8 | 14488 | 7902 (55%) | 0 (0%) |
| combat_interpret | 13 | 12490 | 10432 (84%) | 0 (0%) |
| audit_compare | 25 | 5590 | 2890 (52%) | 0 (0%) |
| road_event | 3 | 5306 | 2370 (45%) | 0 (0%) |
| audit_meaning | 25 | 4194 | 1658 (40%) | 0 (0%) |
| populate_place | 5 | 3743 | 1280 (34%) | 0 (0%) |
| thread_telling | 1 | 2935 | 398 (14%) | 0 (0%) |
| persona_details | 3 | 2323 | 1093 (47%) | 345 (15%) |
| overheard | 7 | 1939 | 1540 (79%) | 0 (0%) |
| board_stakes | 2 | 1909 | 752 (39%) | 0 (0%) |
| npc_profile | 3 | 1900 | 772 (41%) | 0 (0%) |
| moment | 1 | 1410 | 752 (53%) | 0 (0%) |
| ruling | 1 | 1295 | 571 (44%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |

The prompts held 646212 tokens; the constant system messages were about 380472 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 239549 (37%) and read the rest.
The server's log: 324 prompts; 227 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 797 checkpoints made, 39 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

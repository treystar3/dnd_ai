# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 14 | 5.2 | 8.2 | 3.2 | 5.7 | 3.6 | 5.3 | 2 | 0 |
| search | 10 | 2.4 | 4.6 | 2.4 | 2.6 | 3.2 | 2.7 | 0 | 0 |
| move | 9 | 3.5 | 6.5 | 3.5 | 5.2 | 4.2 | 3.6 | 0 | 0 |
| forage | 7 | 2.9 | 4.4 | 2.4 | 2.9 | 3.7 | 3.2 | 2 | 0 |
| leave | 5 | 4.1 | 6.8 | 4.0 | 4.1 | 4.6 | 4.1 | 0 | 0 |
| talk | 4 | 2.4 | 5.1 | 2.4 | 5.1 | 3.2 | 2.6 | 1 | 0 |
| wait | 3 | 5.1 | 6.2 | 5.1 | 6.2 | 3.3 | 4.6 | 1 | 0 |
| board | 2 | 6.8 | 8.0 | 5.2 | 6.8 | 7.5 | 7.3 | 2 | 0 |
| shop | 2 | 1.5 | 9.5 | 4.2 | 4.2 | 6.0 | 5.5 | 0 | 0 |
| look | 2 | 1.9 | 2.0 | 1.9 | 2.0 | 2.0 | 1.9 | 0 | 0 |
| hire | 1 | 6.3 | 6.3 | 4.8 | 4.8 | 6.0 | 6.0 | 0 | 0 |
| pick_up | 1 | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 | 0 | 0 |

60 turns in 4.1 minutes; 98% of it in the model; 124 embedding calls taking 0.8 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 5 dropped; 2 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.0 s and p90 34.1 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.3 s, fight, 5 calls, at the King's Road between Willowmead and Parth: "I go for black bear."
- 9.5 s, shop, 9 calls, at the adventurers' guild house: "I turn to the clerk with the spectacles and offer my willow crossbow f"
- 8.2 s, fight, 4 calls, at the Willowmead wetlands: "I use Brutal Strike on reed lurker."
- 8.0 s, board, 8 calls, at the adventurers' guild house: "I point at the board and tell the girl I'm taking the contract to hunt"
- 7.8 s, fight, 5 calls, at the Willowmead wetlands: "I strike at lizardfolk 2."

Lines by what read them: interpret 44, combat 14, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 57 of 60 (95%) |
| Lines the model wrote | 45 (template 15; model failed 1, 19 s) |
| Lines picking up the passage before | 13 of 60 (22%); in talk 1 of 4 (25%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 6 / 0 (contract 3/0, go 1/0, report 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 14 |
| Waits | 3 of 60 (5%) |
| Places visited | 6 |

Turns by goal: contract 22, fight 14, report 10, idle 7, board 3, need 2, go 1, stop 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 4, broken 2, first_person 1) |
| Machinery mended at the screen | 1925 (dash 1913, wrap 12) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you aren't carrying that.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 6 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 14.3 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 39 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 3 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '*') |
| City ground in the wilds / rain under a roof / weather out of season | 3 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 45 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 6 / 0 / 9 and 263 |
| Fight turns with a foe 10+ levels above the player | 0 of 14, the widest -3 |
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
| populate_place | 3 | 0 | 0 | 1.4 | 122.5 | 693 | 287 | 3370 | 183.8 | 0 | 125 |
| narrate | 34 | 3 | 3 | 1.8 | 2.5 | 2303 | 156 | 4980 | 126.1 | 0 | 67 |
| combat_narrate | 18 | 2 | 3 | 2.0 | 2.8 | 2856 | 193 | 5680 | 131.7 | 0 | 41 |
| interpret_action | 47 | 0 | 0 | 0.6 | 0.9 | 3644 | 49 | 10475 | 239.4 | 0 | 31 |
| player_line | 46 | 8 | 9 | 0.3 | 0.4 | 522 | 23 | 2890 | 137.4 | 0 | 19 |
| combat_aftermath | 10 | 0 | 0 | 1.5 | 2.2 | 1855 | 205 | 4816 | 172.8 | 0 | 16 |
| npc_conversation | 7 | 2 | 2 | 1.5 | 2.0 | 5291 | 142 | 7015 | 156.6 | 0 | 15 |
| dialogue_frame | 12 | 1 | 1 | 1.0 | 1.3 | 2153 | 53 | 4033 | 138.7 | 0 | 13 |
| combat_opening | 6 | 0 | 0 | 1.8 | 2.0 | 1777 | 188 | 3873 | 132.3 | 0 | 11 |
| hire_chat | 8 | 0 | 0 | 0.8 | 0.9 | 2375 | 51 | 4288 | 197.4 | 0 | 7 |
| combat_interpret | 14 | 0 | 0 | 0.5 | 0.5 | 960 | 48 | 3129 | 299.2 | 0 | 6 |
| audit_compare | 22 | 0 | 0 | 0.2 | 0.3 | 222 | 38 | 2374 | 261.8 | 0 | 6 |
| audit_meaning | 22 | 0 | 0 | 0.2 | 0.3 | 164 | 23 | 1849 | 174.2 | 0 | 5 |
| road_event | 2 | 0 | 0 | 2.4 | 2.4 | 1729 | 353 | 3971 | 182.1 | 0 | 5 |
| exchange | 4 | 0 | 0 | 1.1 | 1.4 | 2369 | 74 | 4382 | 155.6 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.3 | 4.3 | 1036 | 921 | 3029 | 233.6 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.4 | 1.4 | 784 | 231 | 3472 | 200.1 | 0 | 4 |
| ruling | 2 | 0 | 0 | 0.7 | 1.1 | 1219 | 116 | 3575 | 219.7 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.7 | 1.7 | 1445 | 173 | 3499 | 135.6 | 0 | 2 |
| overheard | 7 | 0 | 0 | 0.2 | 0.2 | 267 | 16 | 1969 | 305.2 | 0 | 1 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.7 | 631 | 90 | 3489 | 193.8 | 0 | 1 |
| canon_extract | 1 | 0 | 0 | 0.3 | 0.3 | 793 | 6 | 3004 | 230.8 | 0 | 0 |

288 attempts for 272 calls, 6.4 minutes in the model in all.

## Fights

20 rounds with a fight call; 2.5 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 14 | 0.5 | 0.5 | 0 |
| combat_opening | 6 | 1.8 | 2.0 | 0 |
| combat_narrate | 20 | 2.0 | 3.0 | 3 |
| combat_aftermath | 10 | 1.5 | 2.4 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 20372 | 21369 | 21369 | 86 | 0% |
| npc_profile | 2 | 100% | 2504 | 2757 | 2757 | 1439 | 0% |
| dialogue_frame | 12 | 92% | 8958 | 10369 | 11164 | 4042 | 0% |
| hire_chat | 8 | 100% | 9709 | 11189 | 11189 | 1993 | 0% |
| canon_extract | 1 | 100% | 3205 | 3205 | 3205 | 573 | 0% |
| exchange | 4 | 100% | 10032 | 13982 | 13982 | 65 | 0% |
| overheard | 7 | 100% | 1079 | 1181 | 1181 | 185 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 95% | -9 | 21369 | 36345 | 36500 | 21369 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2757 | 2774 | 3000 | 2757 | 0% |
| dialogue_frame | 12 | 92% | 86% | +6 | 10369 | 10715 | 11000 | 11164 | 0% |
| hire_chat | 8 | 100% | 98% | +2 | 11189 | 16275 | 16500 | 11189 | 0% |
| canon_extract | 1 | 100% | 100% | +0 | 3205 | 3998 | 4000 | 3205 | 0% |
| exchange | 4 | 100% | 90% | +10 | 13982 | 15039 | 15500 | 13982 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1181 | 1326 | 1500 | 1181 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 21369 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -9).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 47 | 184242 | 137246 (74%) | 137178 (74%) |
| narrate | 37 | 89614 | 45059 (50%) | 21180 (24%) |
| combat_narrate | 20 | 57593 | 31729 (55%) | 17217 (30%) |
| npc_conversation | 9 | 46973 | 20225 (43%) | 10165 (22%) |
| player_line | 54 | 28261 | 7685 (27%) | 4409 (16%) |
| dialogue_frame | 13 | 28078 | 15343 (55%) | 2149 (8%) |
| hire_chat | 8 | 19106 | 11091 (58%) | 0 (0%) |
| combat_aftermath | 10 | 18552 | 8772 (47%) | 7299 (39%) |
| combat_interpret | 14 | 13450 | 11249 (84%) | 0 (0%) |
| combat_opening | 6 | 10640 | 5028 (47%) | 0 (0%) |
| exchange | 4 | 10433 | 4393 (42%) | 0 (0%) |
| audit_compare | 22 | 4962 | 2549 (51%) | 0 (0%) |
| audit_meaning | 22 | 3690 | 1459 (40%) | 0 (0%) |
| road_event | 2 | 3459 | 1582 (46%) | 0 (0%) |
| ruling | 2 | 2438 | 1165 (48%) | 0 (0%) |
| persona_details | 3 | 2323 | 1102 (47%) | 0 (0%) |
| populate_place | 3 | 2039 | 759 (37%) | 0 (0%) |
| overheard | 7 | 1869 | 1545 (83%) | 0 (0%) |
| moment | 1 | 1445 | 755 (52%) | 0 (0%) |
| npc_profile | 2 | 1263 | 511 (40%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| canon_extract | 1 | 793 | 651 (82%) | 0 (0%) |

The prompts held 532259 tokens; the constant system messages were about 310392 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 199597 (37%) and read the rest.
The server's log: 288 prompts; 208 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 701 checkpoints made, 27 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 1 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

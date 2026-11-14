# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 22 | 2.7 | 6.1 | 2.7 | 6.1 | 3.4 | 3.9 | 3 | 0 |
| move | 12 | 4.4 | 8.1 | 3.5 | 5.7 | 4.8 | 4.4 | 1 | 0 |
| forage | 10 | 2.3 | 3.7 | 2.3 | 3.7 | 3.1 | 2.4 | 1 | 0 |
| leave | 5 | 5.2 | 8.0 | 2.6 | 5.1 | 6.4 | 5.3 | 1 | 0 |
| wait | 3 | 2.6 | 3.1 | 2.6 | 3.1 | 2.3 | 2.2 | 0 | 0 |
| look | 3 | 2.8 | 4.8 | 2.8 | 3.7 | 6.0 | 3.3 | 0 | 0 |
| rest | 3 | 4.3 | 10.6 | 2.8 | 3.3 | 7.3 | 6.1 | 0 | 0 |
| board | 2 | 0.8 | 4.7 | 4.7 | 4.7 | 3.5 | 2.7 | 0 | 0 |

60 turns in 3.9 minutes; 97% of it in the model; 227 embedding calls taking 1.1 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 15.7 s and p90 26.6 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 14.5 s, talk, 2 calls, at the trading square: ""Tell me about yourself.""
- 10.6 s, rest, 9 calls, at the Tilted Plough: "I settle back into my seat and watch the flames, closing my eyes as I "
- 8.7 s, move, 6 calls, at the south fields: "I turn to the group and say we should head back to the adventurers' gu"
- 8.1 s, move, 6 calls, at the temple of Parth: "Alright everyone, let's move out towards the Adventurers' Guild House."
- 8.0 s, move, 10 calls, at the south fields: "I check my pack for that single clove and suggest we head back to the "

Lines by what read them: interpret 59, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 52 (template 8; model failed 2, 26 s) |
| Lines picking up the passage before | 22 of 60 (37%); in talk 7 of 22 (32%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 3 / 1 (contract 1/1, go 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 3 of 60 (5%) |
| Places visited | 5 |

Turns by goal: idle 25, contract 14, cont 6, report 5, need 5, board 2, revisit 2, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 3 (id 2, script 1) |
| Machinery mended at the screen | 12 (dash 5, escape 1, stage 2, wrap 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 14.3 |
| Parts made different by an attempt (blocked, lit, cleared...) | 1 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 2 (Yamaku Omari in dialogue_frame 2) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 16 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '\\') |
| City ground in the wilds / rain under a roof / weather out of season | 2 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 2 of 26; townsfolk 0 of 1 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 0 / 0 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | not recorded on this night |
| Marks shown from acts (Remembered here) | 1 |
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
| populate_place | 5 | 0 | 0 | 1.1 | 82.5 | 650 | 217 | 3345 | 235.0 | 0 | 87 |
| npc_conversation | 26 | 1 | 2 | 1.6 | 2.1 | 4451 | 131 | 6177 | 120.0 | 0 | 58 |
| narrate | 36 | 2 | 2 | 1.2 | 1.9 | 2161 | 115 | 4413 | 130.8 | 0 | 52 |
| interpret_action | 67 | 0 | 0 | 0.7 | 0.9 | 3984 | 59 | 10561 | 251.9 | 0 | 44 |
| player_line | 54 | 22 | 24 | 0.4 | 0.4 | 493 | 25 | 2809 | 140.3 | 0 | 26 |
| dialogue_frame | 17 | 2 | 2 | 0.9 | 1.3 | 2157 | 52 | 4095 | 140.7 | 0 | 19 |
| hire_chat | 14 | 1 | 1 | 0.9 | 1.1 | 2573 | 51 | 4672 | 176.5 | 0 | 13 |
| exchange | 7 | 0 | 0 | 1.3 | 1.4 | 2917 | 120 | 4643 | 160.8 | 0 | 9 |
| audit_compare | 21 | 0 | 0 | 0.2 | 0.3 | 221 | 39 | 2343 | 258.3 | 0 | 5 |
| npc_profile | 7 | 0 | 0 | 0.8 | 0.9 | 629 | 105 | 3307 | 182.5 | 0 | 5 |
| audit_meaning | 21 | 0 | 0 | 0.2 | 0.2 | 169 | 23 | 1916 | 162.8 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.6 | 826 | 248 | 3382 | 189.0 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.2 | 4.2 | 1028 | 936 | 3087 | 241.4 | 0 | 4 |
| overheard | 13 | 0 | 0 | 0.2 | 0.2 | 272 | 16 | 1917 | 304.6 | 0 | 3 |
| board_stakes | 2 | 0 | 0 | 0.7 | 1.4 | 1000 | 165 | 3571 | 209.4 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1395 | 233 | 3532 | 152.5 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 1.9 | 1.9 | 2882 | 232 | 4852 | 184.6 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.0 | 1.0 | 1178 | 164 | 3788 | 233.0 | 0 | 1 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 825 | 2 | 3179 | 192.3 | 0 | 1 |

328 attempts for 300 calls, 5.7 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 26 | 96% | 17857 | 20794 | 21067 | 81 | 9% |
| npc_profile | 7 | 100% | 2606 | 2690 | 2690 | 1541 | 0% |
| dialogue_frame | 17 | 88% | 8973 | 9614 | 10081 | 3853 | 0% |
| hire_chat | 14 | 93% | 10243 | 11901 | 12159 | 1821 | 0% |
| canon_extract | 3 | 100% | 3316 | 4178 | 4178 | 684 | 0% |
| exchange | 7 | 100% | 11850 | 12311 | 12311 | 63 | 0% |
| overheard | 13 | 100% | 1090 | 1145 | 1157 | 196 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 26 | 96% | 95% | +1 | 20794 | 36345 | 36500 | 21067 | 9% |
| npc_profile | 7 | 100% | 100% | +0 | 2690 | 2774 | 3000 | 2690 | 0% |
| dialogue_frame | 17 | 88% | 86% | +2 | 9614 | 10715 | 11000 | 10081 | 0% |
| hire_chat | 14 | 93% | 98% | -5 | 11901 | 16275 | 16500 | 12159 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4178 | 3998 | 4000 | 4178 | 0% |
| exchange | 7 | 100% | 90% | +10 | 12311 | 15039 | 15500 | 12311 | 0% |
| overheard | 13 | 100% | 100% | +0 | 1145 | 1326 | 1500 | 1157 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 20794 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 67 | 266518 | 197002 (74%) | 201374 (76%) |
| npc_conversation | 27 | 121588 | 58998 (49%) | 14718 (12%) |
| narrate | 38 | 80697 | 46866 (58%) | 13886 (17%) |
| dialogue_frame | 19 | 40110 | 22458 (56%) | 4659 (12%) |
| hire_chat | 15 | 39664 | 21069 (53%) | 2957 (7%) |
| player_line | 76 | 38887 | 10915 (28%) | 11269 (29%) |
| exchange | 7 | 19686 | 7840 (40%) | 7 (0%) |
| audit_compare | 21 | 4662 | 2437 (52%) | 21 (0%) |
| npc_profile | 7 | 4378 | 1800 (41%) | 7 (0%) |
| overheard | 13 | 3564 | 2902 (81%) | 13 (0%) |
| audit_meaning | 21 | 3550 | 1461 (41%) | 21 (1%) |
| populate_place | 5 | 3315 | 1271 (38%) | 5 (0%) |
| thread_telling | 1 | 2882 | 397 (14%) | 1 (0%) |
| canon_extract | 3 | 2648 | 1945 (73%) | 3 (0%) |
| persona_details | 3 | 2445 | 1089 (45%) | 347 (14%) |
| board_stakes | 2 | 2000 | 767 (38%) | 2 (0%) |
| moment | 1 | 1395 | 748 (54%) | 1 (0%) |
| ruling | 1 | 1178 | 586 (50%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |

The prompts held 640195 tokens; the constant system messages were about 381043 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 249292 (39%) and read the rest.
The server's log: 328 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 931 checkpoints made, 288 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Sides taken in Parth - starts, 1 days, 1 stages (within reach)

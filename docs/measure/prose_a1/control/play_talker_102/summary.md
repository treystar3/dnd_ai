# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.06 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 25 | 2.7 | 4.2 | 2.7 | 4.2 | 2.4 | 2.9 | 0 | 0 |
| forage | 11 | 2.1 | 3.3 | 1.9 | 2.8 | 2.7 | 2.3 | 1 | 0 |
| move | 8 | 5.2 | 7.3 | 3.9 | 5.2 | 5.2 | 4.9 | 3 | 0 |
| leave | 6 | 2.5 | 5.0 | 2.5 | 3.3 | 3.0 | 3.3 | 1 | 0 |
| wait | 3 | 3.4 | 6.7 | 3.4 | 5.2 | 4.3 | 4.4 | 1 | 0 |
| look | 3 | 4.0 | 5.6 | 2.9 | 2.9 | 5.0 | 3.6 | 0 | 0 |
| rest | 3 | 5.5 | 5.9 | 5.1 | 5.5 | 6.0 | 5.4 | 1 | 0 |
| board | 1 | 5.4 | 5.4 | 5.4 | 5.4 | 6.0 | 5.3 | 0 | 0 |

60 turns in 3.4 minutes; 97% of it in the model; 209 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 3 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 15.5 s and p90 25.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 9.6 s, move, 8 calls, at the adventurers' guild house: "I wonder if they're hiring for more than just manual labor; let's head"
- 7.3 s, move, 6 calls, at the south fields: "Let's make our way back to the Adventurers' Guild House."
- 6.9 s, leave, 5 calls, at the Tilted Plough: "I stand up and give Brisen a respectful nod before turning to the grou"
- 6.7 s, wait, 6 calls, at the south fields: ""Is everything alright with the harvest this year?" I ask Gorz, watchi"
- 5.9 s, rest, 7 calls, at the Tilted Plough: "I nod to the host and look at the others, asking if they want to find "

Lines by what read them: interpret 59, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 56 (template 4; model failed 0, 24 s) |
| Lines picking up the passage before | 20 of 60 (33%); in talk 8 of 25 (32%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 2 / 0 (go 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 3 of 60 (5%) |
| Places visited | 4 |

Turns by goal: idle 29, contract 15, cont 4, revisit 4, need 4, go 2, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 5 (id 3, broken 1, script 1) |
| Machinery mended at the screen | 9 (dash 4, wrap 5) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("part of that stood: speaking to gorz about the weather.. the rest came") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 5 of the game's 19 own lines (26%); most: 'Gathered: # yarrow.' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '<') |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 15; townsfolk 0 of 2 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 0 / 0 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | not recorded on this night |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 2 / 0 / 0 / 1 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 33 | 1 | 1 | 1.7 | 3.5 | 4917 | 141 | 6255 | 139.8 | 0 | 67 |
| populate_place | 4 | 0 | 0 | 1.5 | 59.7 | 673 | 255 | 3549 | 235.9 | 0 | 63 |
| narrate | 32 | 5 | 5 | 1.4 | 2.1 | 2159 | 134 | 4723 | 145.6 | 0 | 53 |
| interpret_action | 60 | 0 | 0 | 0.6 | 0.9 | 4046 | 60 | 11280 | 250.3 | 0 | 37 |
| player_line | 56 | 8 | 8 | 0.4 | 0.5 | 498 | 27 | 2790 | 132.7 | 0 | 24 |
| dialogue_frame | 10 | 1 | 1 | 0.9 | 1.1 | 2117 | 50 | 4046 | 145.1 | 0 | 11 |
| hire_chat | 6 | 0 | 0 | 0.8 | 0.8 | 2390 | 49 | 4265 | 199.5 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.6 | 823 | 265 | 3452 | 197.4 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1028 | 956 | 3078 | 237.6 | 0 | 4 |
| exchange | 3 | 0 | 0 | 1.3 | 1.9 | 2851 | 126 | 4406 | 156.0 | 0 | 4 |
| audit_compare | 16 | 0 | 0 | 0.2 | 0.3 | 233 | 39 | 2394 | 252.2 | 0 | 4 |
| audit_meaning | 16 | 0 | 0 | 0.2 | 0.3 | 171 | 22 | 1983 | 160.1 | 0 | 4 |
| npc_profile | 4 | 0 | 0 | 0.7 | 0.8 | 632 | 95 | 3380 | 187.8 | 0 | 3 |
| board_stakes | 2 | 0 | 0 | 0.7 | 1.3 | 989 | 157 | 3762 | 210.2 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 1.8 | 1.8 | 2888 | 217 | 4937 | 182.7 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.4 | 1.4 | 1330 | 154 | 3464 | 149.5 | 0 | 1 |
| overheard | 4 | 0 | 0 | 0.2 | 0.2 | 270 | 16 | 2004 | 313.7 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.3 | 0.3 | 931 | 2 | 3196 | 153.8 | 0 | 1 |

269 attempts for 254 calls, 4.8 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 33 | 97% | 19747 | 22981 | 23376 | 107 | 7% |
| npc_profile | 4 | 100% | 2629 | 2700 | 2700 | 1564 | 0% |
| dialogue_frame | 10 | 90% | 8701 | 10322 | 10322 | 3843 | 0% |
| hire_chat | 6 | 100% | 9512 | 10848 | 10848 | 1745 | 0% |
| canon_extract | 2 | 100% | 3217 | 4387 | 4387 | 585 | 0% |
| exchange | 3 | 100% | 11574 | 11890 | 11890 | 63 | 0% |
| overheard | 4 | 100% | 1100 | 1181 | 1181 | 206 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 33 | 97% | 95% | +2 | 22981 | 36345 | 36500 | 23376 | 7% |
| npc_profile | 4 | 100% | 100% | +0 | 2700 | 2774 | 3000 | 2700 | 0% |
| dialogue_frame | 10 | 90% | 86% | +4 | 10322 | 10715 | 11000 | 10322 | 0% |
| hire_chat | 6 | 100% | 98% | +2 | 10848 | 16275 | 16500 | 10848 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 4387 | 3998 | 4000 | 4387 | 0% |
| exchange | 3 | 100% | 90% | +10 | 11890 | 15039 | 15500 | 11890 | 0% |
| overheard | 4 | 100% | 100% | +0 | 1181 | 1326 | 1500 | 1181 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 22981 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 60 | 240002 | 177081 (74%) | 184796 (77%) |
| npc_conversation | 34 | 166900 | 74344 (45%) | 16637 (10%) |
| narrate | 37 | 80887 | 46145 (57%) | 21000 (26%) |
| player_line | 64 | 32856 | 9014 (27%) | 4231 (13%) |
| dialogue_frame | 11 | 23408 | 12985 (55%) | 1752 (7%) |
| hire_chat | 6 | 14299 | 8283 (58%) | 6 (0%) |
| exchange | 3 | 7667 | 3357 (44%) | 3 (0%) |
| audit_compare | 16 | 3675 | 1834 (50%) | 16 (0%) |
| thread_telling | 1 | 2888 | 397 (14%) | 1 (0%) |
| audit_meaning | 16 | 2721 | 1100 (40%) | 17 (1%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| npc_profile | 4 | 2515 | 1032 (41%) | 4 (0%) |
| persona_details | 3 | 2444 | 1093 (45%) | 4 (0%) |
| board_stakes | 2 | 1979 | 767 (39%) | 2 (0%) |
| canon_extract | 2 | 1863 | 1293 (69%) | 2 (0%) |
| moment | 1 | 1330 | 751 (56%) | 1 (0%) |
| overheard | 4 | 1086 | 884 (81%) | 4 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |

The prompts held 590242 tokens; the constant system messages were about 341870 of them (58%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 228480 (39%) and read the rest.
The server's log: 269 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 752 checkpoints made, 223 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.5 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Sides taken in Parth - starts, 1 days, 1 stages (within reach)

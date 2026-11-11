# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 25 | 3.1 | 7.2 | 3.1 | 7.1 | 3.1 | 3.9 | 6 | 0 |
| move | 17 | 3.6 | 8.3 | 2.5 | 4.8 | 4.6 | 4.0 | 7 | 0 |
| fight | 5 | 4.6 | 6.4 | 2.9 | 5.8 | 3.2 | 4.7 | 1 | 0 |
| leave | 4 | 3.5 | 3.5 | 3.5 | 3.5 | 3.5 | 3.1 | 1 | 0 |
| search | 4 | 3.2 | 6.5 | 3.2 | 6.5 | 3.2 | 3.7 | 2 | 0 |
| wait | 3 | 5.6 | 6.7 | 3.9 | 5.3 | 5.0 | 5.3 | 0 | 0 |
| rest | 2 | 5.1 | 8.4 | 4.6 | 5.1 | 6.5 | 6.7 | 0 | 0 |

60 turns in 4.2 minutes; 98% of it in the model; 222 embedding calls taking 1.1 s; 0 calls on background threads.
The budget: 1 optional calls deferred and 2 dropped; 1 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.4 s and p90 29.4 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.2 s, move, 10 calls, at the trading square: "I stand up from the crate and look at Wilwick, then suggest we make ou"
- 10.0 s, talk, 8 calls, at the Tilted Plough: "That'll be sixty copper for everyone. Besides the food, who is the per"
- 9.9 s, move, 10 calls, at the adventurers' guild house: "The contracts here look dense; let's head to the trading square instea"
- 8.4 s, rest, 7 calls, at the Tilted Plough: "I settle onto my bunk and prepare to sleep until the sun comes up."
- 8.3 s, move, 7 calls, at the south fields: "Let's make our way back to the Adventurers' Guild House then."

Lines by what read them: interpret 51, combat 5, hire 4

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 51 (template 9; model failed 0, 23 s) |
| Lines picking up the passage before | 22 of 60 (37%); in talk 10 of 25 (40%) |
| Contracts taken / finished | 0 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 3 / 0 (go 2/0, hunt 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 5 |
| Waits | 3 of 60 (5%) |
| Places visited | 5 |

Turns by goal: idle 28, go 9, hunt 6, fight 5, cont 4, revisit 4, need 4

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 12 (id 6, script 3, note 2, broken 1) |
| Machinery mended at the screen | 1170 (dash 1165, stage 2, wrap 3) |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 14 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 1 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 45; townsfolk 0 of 3 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 3 / 0 / 4 and 5 |
| Fight turns with a foe 10+ levels above the player | 0 of 5, the widest -10 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 5 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 4 | 0 | 0 | 1.5 | 123.0 | 673 | 251 | 2414 | 199.7 | 0 | 127 |
| npc_conversation | 31 | 6 | 7 | 1.8 | 2.5 | 4748 | 152 | 6828 | 137.1 | 0 | 75 |
| narrate | 19 | 6 | 6 | 1.6 | 2.5 | 2250 | 155 | 5320 | 128.2 | 0 | 43 |
| interpret_action | 52 | 0 | 0 | 0.7 | 0.9 | 4092 | 65 | 10227 | 250.1 | 0 | 35 |
| player_line | 51 | 8 | 8 | 0.4 | 0.5 | 509 | 29 | 2821 | 133.1 | 0 | 23 |
| dialogue_frame | 15 | 1 | 1 | 1.0 | 1.3 | 2129 | 55 | 3813 | 133.9 | 0 | 16 |
| combat_narrate | 6 | 1 | 2 | 2.1 | 2.4 | 2784 | 212 | 5456 | 132.6 | 0 | 15 |
| hire_chat | 13 | 1 | 1 | 0.9 | 1.0 | 2362 | 51 | 4419 | 181.4 | 0 | 12 |
| exchange | 5 | 1 | 1 | 1.2 | 1.2 | 2830 | 102 | 5071 | 158.0 | 0 | 8 |
| combat_aftermath | 4 | 0 | 0 | 1.6 | 1.9 | 1846 | 184 | 4234 | 172.0 | 0 | 6 |
| combat_opening | 3 | 1 | 1 | 1.6 | 1.6 | 1608 | 146 | 4174 | 144.3 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.6 | 823 | 265 | 3452 | 197.4 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1028 | 946 | 3096 | 234.1 | 0 | 4 |
| audit_compare | 16 | 0 | 0 | 0.2 | 0.3 | 225 | 39 | 2361 | 259.0 | 0 | 4 |
| audit_meaning | 16 | 0 | 0 | 0.2 | 0.3 | 163 | 24 | 1902 | 169.9 | 0 | 4 |
| npc_profile | 4 | 0 | 0 | 0.8 | 0.9 | 638 | 94 | 3302 | 173.3 | 0 | 3 |
| combat_interpret | 5 | 0 | 0 | 0.5 | 0.5 | 959 | 50 | 3088 | 311.9 | 0 | 2 |
| overheard | 11 | 0 | 0 | 0.2 | 0.2 | 278 | 16 | 1939 | 289.7 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1384 | 230 | 3585 | 152.7 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 1.9 | 1.9 | 2882 | 226 | 4868 | 176.0 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.4 | 1.4 | 889 | 247 | 3735 | 210.8 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.3 | 0.4 | 928 | 2 | 3044 | 153.8 | 0 | 1 |

289 attempts for 264 calls, 6.6 minutes in the model in all.

## Fights

8 rounds with a fight call; 2.5 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 5 | 0.5 | 0.5 | 0 |
| combat_opening | 4 | 1.6 | 1.6 | 1 |
| combat_narrate | 7 | 2.1 | 3.0 | 2 |
| combat_aftermath | 4 | 1.6 | 1.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 31 | 81% | 19267 | 21725 | 21854 | 127 | 8% |
| npc_profile | 4 | 100% | 2629 | 2663 | 2663 | 1564 | 0% |
| dialogue_frame | 15 | 93% | 8822 | 9872 | 10671 | 3867 | 0% |
| hire_chat | 13 | 92% | 9721 | 10369 | 11183 | 1975 | 0% |
| canon_extract | 2 | 100% | 3259 | 4313 | 4313 | 627 | 0% |
| exchange | 5 | 80% | 11189 | 11970 | 11970 | 63 | 0% |
| overheard | 11 | 100% | 1124 | 1221 | 1221 | 230 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 31 | 81% | 95% | -15 | 21725 | 36345 | 36500 | 21854 | 8% |
| npc_profile | 4 | 100% | 100% | +0 | 2663 | 2774 | 3000 | 2663 | 0% |
| dialogue_frame | 15 | 93% | 86% | +7 | 9872 | 10715 | 11000 | 10671 | 0% |
| hire_chat | 13 | 92% | 98% | -5 | 10369 | 16275 | 16500 | 11183 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 4313 | 3998 | 4000 | 4313 | 0% |
| exchange | 5 | 80% | 90% | -10 | 11970 | 15039 | 15500 | 11970 | 0% |
| overheard | 11 | 100% | 100% | +0 | 1221 | 1326 | 1500 | 1221 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 21725 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -15; exchange -10).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 52 | 207499 | 153555 (74%) | 158216 (76%) |
| npc_conversation | 37 | 176003 | 81057 (46%) | 40396 (23%) |
| narrate | 25 | 56840 | 31885 (56%) | 24353 (43%) |
| dialogue_frame | 16 | 33905 | 18729 (55%) | 2069 (6%) |
| hire_chat | 14 | 33360 | 19353 (58%) | 2324 (7%) |
| player_line | 59 | 30496 | 8390 (28%) | 4507 (15%) |
| combat_narrate | 7 | 19485 | 11171 (57%) | 5428 (28%) |
| exchange | 6 | 16401 | 6803 (41%) | 2920 (18%) |
| combat_aftermath | 4 | 7240 | 3509 (48%) | 1836 (25%) |
| combat_opening | 4 | 6607 | 3455 (52%) | 1750 (26%) |
| combat_interpret | 5 | 4798 | 4006 (83%) | 5 (0%) |
| audit_compare | 16 | 3647 | 1847 (51%) | 16 (0%) |
| overheard | 11 | 3068 | 2426 (79%) | 11 (0%) |
| thread_telling | 1 | 2882 | 397 (14%) | 1 (0%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| audit_meaning | 16 | 2569 | 1101 (43%) | 17 (1%) |
| npc_profile | 4 | 2533 | 1034 (41%) | 4 (0%) |
| persona_details | 3 | 2444 | 1093 (45%) | 4 (0%) |
| canon_extract | 2 | 1857 | 1293 (70%) | 2 (0%) |
| moment | 1 | 1384 | 749 (54%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 889 | 374 (42%) | 1 (0%) |

The prompts held 617629 tokens; the constant system messages were about 353737 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 243865 (39%) and read the rest.
The server's log: 289 prompts; 2 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 829 checkpoints made, 236 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 2 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 2 | 1 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Sides taken in Parth - starts, 1 days, 1 stages (within reach)

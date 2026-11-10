# Night run: play_talker

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.14 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 34 | 5.8 | 11.5 | 5.8 | 10.4 | 3.2 | 7.3 | 9 | 0 |
| leave | 8 | 8.7 | 10.9 | 5.1 | 7.2 | 4.5 | 7.9 | 2 | 0 |
| move | 6 | 10.8 | 13.2 | 6.3 | 9.4 | 4.8 | 8.9 | 0 | 0 |
| wait | 5 | 6.3 | 15.0 | 5.8 | 8.0 | 5.0 | 7.0 | 1 | 0 |
| rest | 3 | 6.9 | 10.8 | 5.4 | 6.8 | 5.7 | 7.6 | 0 | 0 |
| fight | 2 | 4.3 | 7.6 | 3.6 | 4.3 | 3.0 | 5.9 | 0 | 0 |
| board | 1 | 1.4 | 1.4 | - | - | 1.0 | 1.4 | 0 | 0 |
| look | 1 | 6.0 | 6.0 | - | - | 5.0 | 5.9 | 0 | 0 |

60 turns in 7.6 minutes; 97% of it in the model; 242 embedding calls taking 2.2 s; 1 calls on background threads.
The budget: 8 optional calls deferred and 1 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 18.8 s and p90 31.3 s, over 60 s in 1 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 33.5 s, talk, 3 calls, at the adventurers' guild house: ""I appreciate the clarity. Is there any word from the surrounding town"
- 16.6 s, talk, 7 calls, at the adventurers' guild house: "I look at him and ask, 'When things start moving, what kind of speed a"
- 16.1 s, leave, 10 calls, at the adventurers' guild house: "I appreciate the information, Liesl. I'll head out now and get started"
- 15.0 s, wait, 10 calls, at the adventurers' guild house: "I stand near Yamaku and Gorz, watching them while we wait for the wand"
- 14.4 s, move, 8 calls, at the trading square: "I head toward the tavern-like structure and say, "Let's head to the Ad"

Lines by what read them: interpret 57, combat 2, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 57 of 60 (95%) |
| Lines the model wrote | 49 (template 11; model failed 2, 46 s) |
| Lines picking up the passage before | 24 of 60 (40%); in talk 12 of 34 (35%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 2 / 1 (contract 0/1, go 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 2 |
| Waits | 5 of 60 (8%) |
| Places visited | 5 |

Turns by goal: idle 37, cont 7, board 6, need 3, revisit 3, fight 2, go 1, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 5 (id 4, script 1) |
| Machinery mended at the screen | 369 (dash 366, wrap 3) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 7.1 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 3 (Dith Wyncroft in dialogue_frame 1; Geir Heyshaw in npc_conversation 1; Wilwick Neale in dialogue_frame 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 7 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 1 of 25; townsfolk 0 of 4 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 1 / 0 / 1 and 1 |
| Fight turns with a foe 10+ levels above the player | 0 of 2, the widest -11 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 1 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 43 | 2 | 2 | 3.0 | 4.8 | 5263 | 156 | 3273 | 94.7 | 0 | 176 |
| populate_place | 4 | 0 | 0 | 1.9 | 97.7 | 673 | 248 | 1481 | 194.0 | 0 | 103 |
| interpret_action | 63 | 0 | 0 | 1.6 | 1.9 | 4243 | 63 | 3648 | 211.1 | 0 | 95 |
| narrate | 18 | 3 | 3 | 2.7 | 3.3 | 2433 | 165 | 2077 | 113.4 | 0 | 56 |
| player_line | 51 | 15 | 17 | 0.7 | 0.8 | 525 | 29 | 1222 | 106.2 | 0 | 46 |
| dialogue_frame | 18 | 7 | 9 | 1.7 | 2.1 | 2281 | 53 | 1913 | 111.2 | 0 | 43 |
| hire_chat | 6 | 0 | 0 | 1.7 | 1.8 | 3186 | 56 | 2322 | 141.7 | 0 | 11 |
| npc_profile | 9 | 0 | 0 | 1.1 | 1.3 | 619 | 101 | 1603 | 138.1 | 0 | 10 |
| persona_details | 3 | 0 | 0 | 2.1 | 2.3 | 822 | 244 | 1434 | 157.6 | 0 | 6 |
| audit_compare | 17 | 0 | 0 | 0.4 | 0.4 | 222 | 38 | 1230 | 215.1 | 0 | 6 |
| combat_narrate | 2 | 0 | 0 | 2.7 | 3.3 | 2908 | 186 | 2192 | 111.0 | 0 | 6 |
| audit_meaning | 17 | 0 | 0 | 0.3 | 0.4 | 169 | 22 | 968 | 129.0 | 0 | 6 |
| moment | 2 | 0 | 0 | 2.7 | 3.0 | 1377 | 234 | 1643 | 116.5 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.3 | 5.3 | 1028 | 902 | 1384 | 198.4 | 0 | 5 |
| exchange | 3 | 0 | 0 | 1.7 | 1.9 | 2597 | 93 | 1973 | 161.9 | 0 | 5 |
| combat_aftermath | 2 | 0 | 0 | 1.7 | 2.2 | 1869 | 146 | 2071 | 141.3 | 0 | 4 |
| thread_telling | 1 | 0 | 0 | 2.7 | 2.7 | 2882 | 253 | 2519 | 164.5 | 0 | 3 |
| combat_opening | 1 | 0 | 0 | 2.6 | 2.6 | 1545 | 166 | 1431 | 112.4 | 0 | 3 |
| canon_extract | 3 | 0 | 0 | 0.7 | 0.7 | 846 | 2 | 1329 | 153.8 | 0 | 2 |
| combat_interpret | 2 | 0 | 0 | 0.9 | 0.9 | 954 | 43 | 1328 | 229.9 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.1 | 1.1 | 889 | 98 | 1622 | 169.8 | 0 | 1 |
| overheard | 3 | 0 | 0 | 0.4 | 0.4 | 285 | 16 | 955 | 247.4 | 0 | 1 |
| clarify | 1 | 0 | 0 | 0.4 | 0.4 | 288 | 30 | 1365 | 132.2 | 0 | 0 |

298 attempts for 271 calls, 9.9 minutes in the model in all.

## Fights

3 rounds with a fight call; 2.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 2 | 0.9 | 0.9 | 0 |
| combat_opening | 1 | 2.6 | 2.6 | 0 |
| combat_narrate | 2 | 2.7 | 3.3 | 0 |
| combat_aftermath | 2 | 1.7 | 2.2 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 43 | 95% | 20913 | 23314 | 23701 | 123 | 2% |
| npc_profile | 9 | 100% | 2573 | 2745 | 2745 | 1508 | 0% |
| dialogue_frame | 18 | 67% | 9274 | 10432 | 10503 | 3388 | 0% |
| hire_chat | 6 | 100% | 12088 | 13489 | 13489 | 1397 | 9% |
| canon_extract | 3 | 100% | 3406 | 3411 | 3411 | 774 | 0% |
| exchange | 3 | 100% | 10547 | 10952 | 10952 | 50 | 0% |
| overheard | 3 | 100% | 1153 | 1270 | 1270 | 259 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 43 | 95% | 95% | +0 | 23314 | 36345 | 36500 | 23701 | 2% |
| npc_profile | 9 | 100% | 100% | +0 | 2745 | 2774 | 3000 | 2745 | 0% |
| dialogue_frame | 18 | 67% | 86% | -19 | 10432 | 10715 | 11000 | 10503 | 0% |
| hire_chat | 6 | 100% | 98% | +2 | 13489 | 16275 | 16500 | 13489 | 9% |
| canon_extract | 3 | 100% | 100% | +0 | 3411 | 3998 | 4000 | 3411 | 0% |
| exchange | 3 | 100% | 90% | +10 | 10952 | 15039 | 15500 | 10952 | 0% |
| overheard | 3 | 100% | 100% | +0 | 1270 | 1326 | 1500 | 1270 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 23314 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 63 | 264433 | 186421 (70%) | 188298 (71%) |
| npc_conversation | 45 | 233450 | 109423 (47%) | 14851 (6%) |
| dialogue_frame | 25 | 56738 | 35449 (62%) | 15606 (28%) |
| narrate | 21 | 49448 | 30457 (62%) | 12087 (24%) |
| player_line | 66 | 35652 | 9277 (26%) | 8574 (24%) |
| hire_chat | 6 | 18072 | 9858 (55%) | 1586 (9%) |
| exchange | 3 | 7474 | 3360 (45%) | 3 (0%) |
| combat_narrate | 2 | 5816 | 3812 (66%) | 2 (0%) |
| npc_profile | 9 | 5611 | 2312 (41%) | 9 (0%) |
| audit_compare | 17 | 3757 | 1945 (52%) | 17 (0%) |
| combat_aftermath | 2 | 3738 | 2129 (57%) | 1843 (49%) |
| thread_telling | 1 | 2882 | 397 (14%) | 1 (0%) |
| audit_meaning | 17 | 2853 | 1138 (40%) | 18 (1%) |
| moment | 2 | 2754 | 1493 (54%) | 2 (0%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| canon_extract | 3 | 2515 | 1964 (78%) | 3 (0%) |
| persona_details | 3 | 2433 | 1091 (45%) | 691 (28%) |
| combat_interpret | 2 | 1908 | 1603 (84%) | 2 (0%) |
| combat_opening | 1 | 1545 | 1054 (68%) | 872 (56%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 889 | 374 (42%) | 1 (0%) |
| overheard | 3 | 868 | 663 (76%) | 3 (0%) |
| clarify | 1 | 288 | 142 (49%) | 1 (0%) |

The prompts held 706846 tokens; the constant system messages were about 405872 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 244474 (35%) and read the rest.
The server's log: 298 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 873 checkpoints made, 267 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 2 moments, 2 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 1.00 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 2 | 1 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Sides taken in Parth - starts, 1 days, 1 stages (within reach)

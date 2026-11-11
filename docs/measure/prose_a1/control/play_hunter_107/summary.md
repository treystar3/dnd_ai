# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 18 | 4.1 | 6.1 | 4.1 | 5.9 | 4.7 | 4.4 | 8 | 0 |
| search | 11 | 2.9 | 5.2 | 2.7 | 3.4 | 3.6 | 3.0 | 1 | 0 |
| wait | 9 | 3.0 | 4.2 | 2.8 | 4.0 | 3.2 | 3.3 | 0 | 0 |
| talk | 6 | 3.1 | 6.5 | 3.1 | 6.5 | 3.5 | 4.8 | 1 | 0 |
| leave | 6 | 5.0 | 6.2 | 3.2 | 4.2 | 6.2 | 5.4 | 2 | 0 |
| fight | 5 | 3.8 | 8.1 | 2.3 | 5.0 | 3.4 | 4.3 | 0 | 0 |
| board | 3 | 5.0 | 7.2 | 5.0 | 5.7 | 5.3 | 5.0 | 0 | 0 |
| look | 1 | 4.2 | 4.2 | 4.2 | 4.2 | 6.0 | 4.1 | 0 | 0 |
| hire | 1 | 2.8 | 2.8 | 2.8 | 2.8 | 5.0 | 2.8 | 0 | 0 |

60 turns in 4.2 minutes; 98% of it in the model; 180 embedding calls taking 0.9 s; 0 calls on background threads.
The budget: 3 optional calls deferred and 4 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 17.1 s and p90 29.1 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 11.0 s, move, 11 calls, at the Greywood: "Let's get this thing skinned, then we're heading straight to the Adven"
- 9.4 s, talk, 4 calls, at the adventurers' guild house: "I step up beside the sellsword and ask, 'Who here would you trust with"
- 8.5 s, move, 6 calls, at Parth: "I head straight for the Adventurers' Guild House."
- 8.1 s, fight, 5 calls, at the Greywood: "I use Brutal Strike on wolf 2."
- 7.3 s, leave, 9 calls, at the adventurers' guild house: "I nod once at the scout and turn toward the door."

Lines by what read them: interpret 55, combat 4, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 55 (template 5; model failed 0, 24 s) |
| Lines picking up the passage before | 12 of 60 (20%); in talk 4 of 6 (67%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 1 / 1 / 1 |
| Goals finished / given up | 6 / 1 (contract 0/1, find 1/0, follow 1/0, go 3/0, hunt 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 5 |
| Waits | 9 of 60 (15%) |
| Places visited | 7 |

Turns by goal: idle 20, board 19, hunt 7, follow 6, fight 4, need 3, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 5 (id 4, broken 1) |
| Machinery mended at the screen | 487 (dash 480, wrap 7) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 12.5 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Rimali Vamatho in dialogue_frame 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 0 of the game's 28 own lines (0%); most: "You are back at the adventurers' guild house." x5 |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 16 ['against', 'pillar', 'watching']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 41 |
| Matters the player ended: pursued / by accident | 1 / 0 |
| Fights won / for +0 XP / XP median and most | 4 / 4 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | 0 of 4, the widest -11 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.4 | 1.6 | 697 | 289 | 2509 | 231.9 | 0 | 132 |
| narrate | 40 | 3 | 3 | 1.6 | 2.2 | 2321 | 149 | 4579 | 134.6 | 0 | 72 |
| interpret_action | 60 | 0 | 0 | 0.7 | 0.9 | 3890 | 50 | 9975 | 237.7 | 0 | 39 |
| npc_conversation | 14 | 2 | 2 | 1.8 | 3.7 | 4937 | 142 | 6422 | 124.8 | 0 | 36 |
| player_line | 55 | 8 | 8 | 0.4 | 0.4 | 525 | 24 | 2872 | 136.2 | 0 | 24 |
| dialogue_frame | 16 | 3 | 3 | 0.9 | 1.2 | 2039 | 54 | 4016 | 143.4 | 0 | 18 |
| exchange | 9 | 2 | 3 | 1.1 | 1.4 | 3049 | 91 | 5763 | 173.5 | 0 | 12 |
| combat_narrate | 5 | 0 | 0 | 1.9 | 2.4 | 2746 | 179 | 5172 | 137.4 | 0 | 10 |
| hire_chat | 9 | 1 | 1 | 0.8 | 0.9 | 2478 | 52 | 4676 | 184.6 | 0 | 8 |
| combat_aftermath | 6 | 0 | 0 | 1.2 | 1.5 | 1779 | 165 | 4594 | 178.0 | 0 | 8 |
| combat_opening | 4 | 0 | 0 | 1.8 | 2.0 | 1562 | 167 | 3886 | 131.2 | 0 | 7 |
| audit_compare | 24 | 0 | 0 | 0.2 | 0.3 | 214 | 39 | 2366 | 258.5 | 0 | 6 |
| persona_details | 3 | 1 | 1 | 1.5 | 1.7 | 883 | 267 | 3326 | 215.7 | 0 | 6 |
| audit_meaning | 24 | 0 | 0 | 0.2 | 0.2 | 155 | 23 | 1897 | 163.3 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.3 | 4.3 | 1064 | 928 | 3148 | 235.3 | 0 | 4 |
| situation_parts | 1 | 0 | 0 | 3.0 | 3.0 | 1949 | 707 | 3691 | 281.2 | 0 | 3 |
| npc_profile | 4 | 0 | 0 | 0.7 | 0.9 | 610 | 97 | 3437 | 184.8 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.8 | 2.8 | 966 | 535 | 3730 | 210.6 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.5 | 2.5 | 3023 | 342 | 5089 | 183.9 | 0 | 2 |
| overheard | 9 | 0 | 0 | 0.2 | 0.2 | 283 | 16 | 1917 | 300.0 | 0 | 2 |
| combat_interpret | 4 | 0 | 0 | 0.5 | 0.5 | 967 | 40 | 3216 | 321.4 | 0 | 2 |
| ruling | 2 | 0 | 0 | 0.7 | 0.8 | 1258 | 75 | 3835 | 195.6 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.3 | 0.3 | 821 | 2 | 3086 | 153.8 | 0 | 1 |
| party_intent | 1 | 0 | 0 | 0.2 | 0.2 | 339 | 12 | 2511 | 226.4 | 0 | 0 |
| situation_agree | 1 | 0 | 0 | 0.2 | 0.2 | 217 | 14 | 1808 | 280.0 | 0 | 0 |

323 attempts for 303 calls, 6.7 minutes in the model in all.

## Fights

8 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 4 | 0.5 | 0.5 | 0 |
| combat_opening | 4 | 1.8 | 2.0 | 0 |
| combat_narrate | 5 | 1.9 | 2.4 | 0 |
| combat_aftermath | 6 | 1.2 | 1.8 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 14 | 86% | 19423 | 21537 | 22478 | 56 | 0% |
| npc_profile | 4 | 100% | 2524 | 2607 | 2607 | 1459 | 0% |
| dialogue_frame | 16 | 81% | 8580 | 10005 | 10370 | 3975 | 0% |
| hire_chat | 9 | 89% | 10132 | 12994 | 12994 | 1879 | 0% |
| canon_extract | 2 | 100% | 3267 | 3356 | 3356 | 635 | 0% |
| exchange | 9 | 78% | 12075 | 12829 | 12829 | 63 | 12% |
| overheard | 9 | 100% | 1125 | 1148 | 1148 | 231 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 14 | 86% | 95% | -9 | 21537 | 36345 | 36500 | 22478 | 0% |
| npc_profile | 4 | 100% | 100% | +0 | 2607 | 2774 | 3000 | 2607 | 0% |
| dialogue_frame | 16 | 81% | 86% | -5 | 10005 | 10715 | 11000 | 10370 | 0% |
| hire_chat | 9 | 89% | 98% | -9 | 12994 | 16275 | 16500 | 12994 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 3356 | 3998 | 4000 | 3356 | 0% |
| exchange | 9 | 78% | 90% | -12 | 12829 | 15039 | 15500 | 12829 | 12% |
| overheard | 9 | 100% | 100% | +0 | 1148 | 1326 | 1500 | 1148 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 21537 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -9; hire_chat -9; exchange -12).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 60 | 235706 | 176337 (75%) | 179034 (76%) |
| narrate | 43 | 98556 | 53410 (54%) | 16659 (17%) |
| npc_conversation | 16 | 78594 | 35460 (45%) | 10054 (13%) |
| dialogue_frame | 19 | 39838 | 22335 (56%) | 6126 (15%) |
| player_line | 63 | 33494 | 8938 (27%) | 4517 (13%) |
| exchange | 11 | 32712 | 12625 (39%) | 9193 (28%) |
| hire_chat | 10 | 25920 | 14041 (54%) | 2226 (9%) |
| combat_narrate | 5 | 13515 | 7931 (59%) | 2790 (21%) |
| combat_aftermath | 6 | 10896 | 5302 (49%) | 3633 (33%) |
| combat_opening | 4 | 6261 | 3428 (55%) | 864 (14%) |
| audit_compare | 24 | 5205 | 2788 (54%) | 0 (0%) |
| populate_place | 7 | 4901 | 1790 (37%) | 0 (0%) |
| combat_interpret | 4 | 3853 | 3235 (84%) | 0 (0%) |
| audit_meaning | 24 | 3783 | 1674 (44%) | 0 (0%) |
| persona_details | 4 | 3403 | 1651 (49%) | 597 (18%) |
| thread_telling | 1 | 3023 | 396 (13%) | 0 (0%) |
| ruling | 2 | 2516 | 1164 (46%) | 0 (0%) |
| overheard | 9 | 2492 | 2010 (81%) | 0 (0%) |
| npc_profile | 4 | 2464 | 1035 (42%) | 0 (0%) |
| situation_parts | 1 | 1949 | 1085 (56%) | 0 (0%) |
| canon_extract | 2 | 1642 | 1305 (79%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| board_stakes | 1 | 966 | 384 (40%) | 0 (0%) |
| party_intent | 1 | 339 | 265 (78%) | 0 (0%) |
| situation_agree | 1 | 217 | 95 (44%) | 0 (0%) |

The prompts held 613309 tokens; the constant system messages were about 359173 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 235693 (38%) and read the rest.
The server's log: 323 prompts; 232 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 799 checkpoints made, 44 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 1 |
| 2 | 1 (1) | 0 | 1 | 0 | 1 | 0 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] The fair on the Old Quarry Road at Parth - starts, 7 days, 3 stages (within reach)

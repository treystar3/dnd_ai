# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 17 | 5.3 | 6.4 | 4.7 | 6.4 | 4.5 | 4.7 | 7 | 0 |
| wait | 14 | 2.9 | 6.0 | 2.9 | 5.6 | 2.6 | 3.4 | 4 | 0 |
| talk | 6 | 2.7 | 3.1 | 2.7 | 3.1 | 3.5 | 3.2 | 1 | 0 |
| leave | 6 | 4.6 | 5.9 | 2.8 | 4.6 | 6.0 | 4.7 | 1 | 0 |
| search | 6 | 2.6 | 6.7 | 2.6 | 3.1 | 5.2 | 4.3 | 2 | 0 |
| board | 4 | 5.7 | 7.3 | 5.7 | 5.8 | 5.0 | 4.2 | 0 | 0 |
| look | 4 | 3.8 | 6.6 | 3.8 | 6.6 | 5.0 | 3.9 | 0 | 0 |
| fight | 3 | 7.8 | 11.7 | 6.3 | 11.7 | 5.0 | 8.1 | 4 | 0 |

60 turns in 4.4 minutes; 97% of it in the model; 190 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 3 optional calls deferred and 4 dropped; 2 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.6 s and p90 33.5 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 11.7 s, fight, 6 calls, at the Greywood: "I use Brutal Strike on giant centipede 1."
- 10.8 s, move, 12 calls, at the adventurers' guild house: "I gesture toward the street and say we're heading to the Tilted Plough"
- 8.5 s, move, 6 calls, at Parth: "I lead the way toward the Adventurers' Guild House."
- 7.8 s, fight, 5 calls, at the Greywood: "I use Cleaving Sweep on dire wolf 2."
- 7.6 s, search, 7 calls, at the Greywood: "I kick a piece of the shell aside and start poking through its carcass"

Lines by what read them: interpret 55, combat 3, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 56 (template 4; model failed 0, 23 s) |
| Lines picking up the passage before | 9 of 60 (15%); in talk 1 of 6 (17%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 4 / 1 (contract 0/1, go 3/0, hunt 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 3 |
| Waits | 14 of 60 (23%) |
| Places visited | 6 |

Turns by goal: board 20, idle 19, hunt 6, clarify 4, fight 3, need 3, revisit 3, cont 1, go 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 9 (id 5, escape 2, script 1, note 1) |
| Machinery mended at the screen | 582 (dash 570, stage 1, wrap 11) |
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
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 1 (Jemny Midby in combat_narrate 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 26 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 33 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 3 / 1 / 1 and 13 |
| Fight turns with a foe 10+ levels above the player | 0 of 3, the widest -7 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 1 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 4 the stout bookkeeper contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| narrate | 40 | 2 | 2 | 1.9 | 2.5 | 2417 | 175 | 4591 | 127.3 | 0 | 79 |
| populate_place | 6 | 0 | 0 | 1.4 | 1.6 | 702 | 294 | 3538 | 235.0 | 0 | 63 |
| interpret_action | 72 | 2 | 2 | 0.6 | 0.8 | 4067 | 60 | 11644 | 240.4 | 0 | 49 |
| npc_conversation | 12 | 0 | 0 | 1.8 | 2.8 | 5143 | 138 | 5980 | 134.5 | 0 | 25 |
| player_line | 56 | 11 | 11 | 0.3 | 0.4 | 542 | 22 | 2855 | 135.3 | 0 | 23 |
| combat_narrate | 5 | 4 | 4 | 2.0 | 2.6 | 2883 | 221 | 7295 | 131.9 | 0 | 19 |
| dialogue_frame | 13 | 4 | 4 | 1.1 | 1.3 | 2051 | 69 | 4284 | 136.8 | 0 | 18 |
| exchange | 7 | 2 | 2 | 1.1 | 1.2 | 3084 | 83 | 5484 | 168.9 | 0 | 10 |
| combat_opening | 4 | 1 | 1 | 2.1 | 2.3 | 1775 | 202 | 4619 | 131.9 | 0 | 10 |
| hire_chat | 7 | 2 | 2 | 0.8 | 1.0 | 2726 | 54 | 5306 | 184.7 | 0 | 8 |
| persona_details | 3 | 1 | 1 | 1.5 | 1.7 | 883 | 267 | 3323 | 215.7 | 0 | 6 |
| audit_compare | 20 | 0 | 0 | 0.2 | 0.3 | 218 | 40 | 2370 | 259.3 | 0 | 5 |
| combat_aftermath | 3 | 0 | 0 | 1.4 | 1.6 | 1675 | 188 | 4255 | 176.0 | 0 | 4 |
| audit_meaning | 20 | 0 | 0 | 0.2 | 0.2 | 162 | 20 | 1947 | 163.4 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.0 | 4.0 | 1064 | 904 | 3157 | 248.8 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 3.0 | 3.0 | 968 | 562 | 3709 | 205.6 | 0 | 3 |
| npc_profile | 4 | 0 | 0 | 0.8 | 0.8 | 625 | 101 | 3461 | 178.8 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.9 | 2.9 | 3023 | 381 | 5313 | 165.7 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.0 | 2.0 | 1426 | 290 | 3694 | 175.2 | 0 | 2 |
| ruling | 3 | 0 | 0 | 0.6 | 0.7 | 1178 | 66 | 4843 | 198.3 | 0 | 2 |
| combat_interpret | 3 | 0 | 0 | 0.5 | 0.5 | 975 | 50 | 3099 | 307.4 | 0 | 1 |
| clarify | 4 | 1 | 1 | 0.3 | 0.3 | 257 | 34 | 2386 | 197.9 | 0 | 1 |
| overheard | 7 | 0 | 0 | 0.2 | 0.2 | 277 | 16 | 1993 | 286.4 | 0 | 1 |
| canon_extract | 4 | 0 | 0 | 0.3 | 0.3 | 902 | 2 | 3199 | 150.9 | 0 | 1 |

327 attempts for 297 calls, 5.7 minutes in the model in all.

## Fights

6 rounds with a fight call; 3.3 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 3 | 0.5 | 0.5 | 0 |
| combat_opening | 5 | 2.1 | 2.3 | 1 |
| combat_narrate | 9 | 2.0 | 2.8 | 4 |
| combat_aftermath | 3 | 1.4 | 1.6 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 100% | 20555 | 22347 | 23570 | 65 | 0% |
| npc_profile | 4 | 100% | 2614 | 2653 | 2653 | 1549 | 0% |
| dialogue_frame | 13 | 69% | 8988 | 10199 | 11036 | 3868 | 0% |
| hire_chat | 7 | 71% | 10700 | 12927 | 12927 | 2013 | 0% |
| canon_extract | 4 | 100% | 3982 | 4086 | 4086 | 1350 | 0% |
| exchange | 7 | 71% | 12363 | 12512 | 12512 | 63 | 0% |
| overheard | 7 | 100% | 1101 | 1164 | 1164 | 207 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 100% | 95% | +5 | 22347 | 36345 | 36500 | 23570 | 0% |
| npc_profile | 4 | 100% | 100% | +0 | 2653 | 2774 | 3000 | 2653 | 0% |
| dialogue_frame | 13 | 69% | 86% | -17 | 10199 | 10715 | 11000 | 11036 | 0% |
| hire_chat | 7 | 71% | 98% | -26 | 12927 | 16275 | 16500 | 12927 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 4086 | 3998 | 4000 | 4086 | 0% |
| exchange | 7 | 71% | 90% | -18 | 12512 | 15039 | 15500 | 12512 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1164 | 1326 | 1500 | 1164 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 22347 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -26; exchange -18).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 74 | 298385 | 218527 (73%) | 241827 (81%) |
| narrate | 42 | 101058 | 52221 (52%) | 12656 (13%) |
| npc_conversation | 12 | 61178 | 26595 (43%) | 0 (0%) |
| dialogue_frame | 17 | 35913 | 19716 (55%) | 7873 (22%) |
| player_line | 67 | 35118 | 9507 (27%) | 5935 (17%) |
| exchange | 9 | 27169 | 10351 (38%) | 6187 (23%) |
| combat_narrate | 9 | 26574 | 14902 (56%) | 17010 (64%) |
| hire_chat | 9 | 25472 | 12786 (50%) | 5892 (23%) |
| combat_opening | 5 | 8578 | 4356 (51%) | 3433 (40%) |
| combat_aftermath | 3 | 5123 | 2678 (52%) | 1627 (32%) |
| audit_compare | 20 | 4432 | 2322 (52%) | 0 (0%) |
| populate_place | 6 | 4281 | 1537 (36%) | 0 (0%) |
| ruling | 3 | 3681 | 1751 (48%) | 1177 (32%) |
| canon_extract | 4 | 3589 | 2587 (72%) | 0 (0%) |
| persona_details | 4 | 3403 | 1651 (49%) | 597 (18%) |
| audit_meaning | 20 | 3190 | 1381 (43%) | 0 (0%) |
| thread_telling | 1 | 3023 | 395 (13%) | 0 (0%) |
| combat_interpret | 3 | 2922 | 2426 (83%) | 0 (0%) |
| npc_profile | 4 | 2499 | 1035 (41%) | 0 (0%) |
| overheard | 7 | 1919 | 1566 (82%) | 0 (0%) |
| moment | 1 | 1426 | 756 (53%) | 0 (0%) |
| clarify | 5 | 1298 | 785 (60%) | 237 (18%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| board_stakes | 1 | 968 | 385 (40%) | 0 (0%) |

The prompts held 662263 tokens; the constant system messages were about 390705 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 304451 (46%) and read the rest.
The server's log: 327 prompts; 214 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 791 checkpoints made, 48 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 1 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.50 doors, 0.50 moments, 0.5 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 0 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] The fair on the Old Quarry Road at Parth - starts, 7 days, 3 stages (within reach)

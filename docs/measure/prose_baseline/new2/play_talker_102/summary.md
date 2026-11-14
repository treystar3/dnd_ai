# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 34 | 4.8 | 8.9 | 4.8 | 8.9 | 2.7 | 5.6 | 1 | 0 |
| move | 11 | 7.2 | 12.3 | 5.3 | 10.6 | 5.2 | 6.8 | 3 | 0 |
| leave | 7 | 5.4 | 8.8 | 4.9 | 5.2 | 4.1 | 6.1 | 0 | 0 |
| wait | 2 | 4.0 | 6.7 | 3.9 | 6.7 | 2.0 | 3.8 | 0 | 0 |
| search | 2 | 3.8 | 7.7 | 3.8 | 7.6 | 4.0 | 5.6 | 0 | 0 |
| board | 1 | 7.4 | 7.4 | 7.4 | 7.4 | 6.0 | 7.3 | 0 | 0 |
| improv | 1 | 3.2 | 3.2 | 3.2 | 3.2 | 2.0 | 2.9 | 0 | 0 |
| fight | 1 | 10.8 | 10.8 | 3.2 | 3.2 | 5.0 | 10.6 | 0 | 0 |
| rest | 1 | 14.5 | 14.5 | 9.8 | 9.8 | 9.0 | 14.2 | 0 | 0 |

60 turns in 6.2 minutes; 97% of it in the model; 241 embedding calls taking 2.6 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 17.0 s and p90 31.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.8 s, talk, 3 calls, at the adventurers' guild house: "I nod slowly and ask her, "Is there anyone else here today that you th"
- 14.5 s, rest, 9 calls, at the Tilted Plough: "I'll take a room here tonight; where can I find some proper rest?"
- 12.8 s, move, 6 calls, at the south fields: "I turn to Gorz and say we should head toward the Adventurers' Guild Ho"
- 12.3 s, move, 7 calls, at the trading square: "I scan the crowd for any familiar faces before heading toward the Adve"
- 11.0 s, move, 8 calls, at the Greywood: "I wipe my blade clean and turn to the others. 'The fight is over; let'"

Lines by what read them: interpret 56, hire 3, combat 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 53 (template 7; model failed 0, 46 s) |
| Lines picking up the passage before | 20 of 60 (33%); in talk 11 of 34 (32%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 3 / 1 (contract 0/1, go 3/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 1 |
| Waits | 2 of 60 (3%) |
| Places visited | 6 |

Turns by goal: idle 46, cont 6, revisit 3, go 2, need 2, fight 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 3 (id 1, escape 1, script 1) |
| Machinery mended at the screen | 366 (dash 359, stage 1, wrap 6) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
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
| Companion sentences with the other gender's pronoun | 1 (Dith Wyncroft in npc_conversation 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 6 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '? Yes') |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 17 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 1 / 0 / 1 and 1 |
| Fight turns with a foe 10+ levels above the player | 0 of 1, the widest -11 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 6 | 0 | 0 | 1.9 | 123.2 | 659 | 251 | 819 | 160.4 | 0 | 255 |
| npc_conversation | 42 | 1 | 1 | 3.0 | 4.3 | 5103 | 155 | 3657 | 106.8 | 0 | 148 |
| interpret_action | 60 | 0 | 0 | 1.3 | 1.7 | 4020 | 65 | 4333 | 207.8 | 0 | 77 |
| narrate | 18 | 2 | 2 | 2.3 | 2.9 | 2257 | 166 | 2386 | 113.6 | 0 | 48 |
| player_line | 53 | 17 | 17 | 0.7 | 0.8 | 521 | 27 | 1363 | 98.3 | 0 | 46 |
| dialogue_frame | 14 | 1 | 1 | 1.6 | 1.8 | 2196 | 59 | 2012 | 113.0 | 0 | 24 |
| hire_chat | 10 | 0 | 0 | 1.4 | 1.7 | 2542 | 61 | 2469 | 154.9 | 0 | 15 |
| npc_profile | 7 | 0 | 0 | 1.0 | 1.1 | 631 | 91 | 1693 | 135.8 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 2.2 | 2.3 | 836 | 268 | 1448 | 163.2 | 0 | 7 |
| audit_compare | 16 | 0 | 0 | 0.4 | 0.4 | 227 | 38 | 1335 | 213.5 | 0 | 6 |
| exchange | 3 | 0 | 0 | 2.0 | 2.0 | 2122 | 91 | 2065 | 133.2 | 0 | 6 |
| audit_meaning | 16 | 0 | 0 | 0.3 | 0.4 | 165 | 21 | 1041 | 118.0 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.4 | 5.4 | 1028 | 945 | 1507 | 200.6 | 0 | 5 |
| overheard | 9 | 0 | 0 | 0.4 | 0.4 | 274 | 19 | 993 | 246.2 | 0 | 3 |
| combat_narrate | 1 | 0 | 0 | 2.4 | 2.4 | 2710 | 137 | 2530 | 104.3 | 0 | 2 |
| combat_aftermath | 1 | 0 | 0 | 2.3 | 2.3 | 1706 | 163 | 1490 | 144.4 | 0 | 2 |
| combat_opening | 1 | 0 | 0 | 2.0 | 2.0 | 1570 | 117 | 1894 | 104.5 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 1.1 | 1.1 | 889 | 94 | 1637 | 162.1 | 0 | 1 |
| canon_extract | 2 | 0 | 0 | 0.5 | 0.6 | 822 | 2 | 1578 | 125.0 | 0 | 1 |
| ruling | 1 | 0 | 0 | 1.0 | 1.0 | 1224 | 67 | 2071 | 163.4 | 0 | 1 |
| combat_interpret | 1 | 0 | 0 | 0.8 | 0.8 | 956 | 50 | 1609 | 276.2 | 0 | 1 |
| party_intent | 1 | 0 | 0 | 0.4 | 0.4 | 344 | 12 | 1113 | 171.4 | 0 | 0 |

288 attempts for 267 calls, 11.1 minutes in the model in all.

## Fights

2 rounds with a fight call; 2.0 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 1 | 0.8 | 0.8 | 0 |
| combat_opening | 1 | 2.0 | 2.0 | 0 |
| combat_narrate | 1 | 2.4 | 2.4 | 0 |
| combat_aftermath | 1 | 2.3 | 2.3 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 20449 | 22665 | 24486 | 107 | 3% |
| npc_profile | 7 | 100% | 2581 | 2693 | 2693 | 1516 | 0% |
| dialogue_frame | 14 | 93% | 8894 | 10075 | 10200 | 3142 | 0% |
| hire_chat | 10 | 100% | 9990 | 13965 | 13965 | 1432 | 0% |
| canon_extract | 2 | 100% | 3273 | 3278 | 3278 | 641 | 0% |
| exchange | 3 | 100% | 8786 | 12177 | 12177 | 63 | 0% |
| overheard | 9 | 100% | 1113 | 1340 | 1340 | 219 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 95% | +2 | 22665 | 36345 | 36500 | 24486 | 3% |
| npc_profile | 7 | 100% | 100% | +0 | 2693 | 2774 | 3000 | 2693 | 0% |
| dialogue_frame | 14 | 93% | 86% | +7 | 10075 | 10715 | 11000 | 10200 | 0% |
| hire_chat | 10 | 100% | 98% | +2 | 13965 | 16275 | 16500 | 13965 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 3278 | 3998 | 4000 | 3278 | 0% |
| exchange | 3 | 100% | 90% | +10 | 12177 | 15039 | 15500 | 12177 | 0% |
| overheard | 9 | 100% | 100% | +0 | 1340 | 1326 | 1500 | 1340 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: overheard); npc_conversation's p95 22665 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 60 | 240783 | 176554 (73%) | 173935 (72%) |
| npc_conversation | 43 | 220204 | 104496 (47%) | 7251 (3%) |
| narrate | 20 | 44745 | 28653 (64%) | 10128 (23%) |
| player_line | 70 | 36847 | 9911 (27%) | 8987 (24%) |
| dialogue_frame | 15 | 33118 | 21066 (64%) | 2408 (7%) |
| hire_chat | 10 | 26214 | 16281 (62%) | 10 (0%) |
| exchange | 3 | 6923 | 3338 (48%) | 3 (0%) |
| npc_profile | 7 | 4402 | 1806 (41%) | 7 (0%) |
| populate_place | 6 | 3926 | 1527 (39%) | 6 (0%) |
| audit_compare | 16 | 3698 | 1837 (50%) | 16 (0%) |
| combat_narrate | 1 | 2710 | 1889 (70%) | 1 (0%) |
| audit_meaning | 16 | 2649 | 1091 (41%) | 16 (1%) |
| overheard | 9 | 2546 | 1999 (79%) | 9 (0%) |
| persona_details | 3 | 2465 | 1096 (44%) | 347 (14%) |
| combat_aftermath | 1 | 1706 | 1065 (62%) | 1 (0%) |
| canon_extract | 2 | 1644 | 1321 (80%) | 2 (0%) |
| combat_opening | 1 | 1570 | 1035 (66%) | 1 (0%) |
| ruling | 1 | 1224 | 582 (48%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| combat_interpret | 1 | 956 | 801 (84%) | 1 (0%) |
| board_stakes | 1 | 889 | 374 (42%) | 1 (0%) |
| party_intent | 1 | 344 | 262 (76%) | 1 (0%) |

The prompts held 640591 tokens; the constant system messages were about 377476 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 203132 (32%) and read the rest.
The server's log: 288 prompts; 4 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 841 checkpoints made, 258 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 0 lines of the room changing, 2 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 2 |

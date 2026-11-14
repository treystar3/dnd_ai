# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 17 | 7.2 | 11.6 | 4.9 | 7.2 | 4.7 | 7.1 | 3 | 0 |
| talk | 13 | 4.8 | 15.4 | 4.7 | 15.3 | 3.2 | 6.8 | 4 | 0 |
| leave | 12 | 4.9 | 9.7 | 4.7 | 5.8 | 4.2 | 5.7 | 1 | 0 |
| fight | 5 | 7.7 | 15.5 | 3.1 | 7.1 | 4.6 | 9.1 | 1 | 0 |
| search | 5 | 3.6 | 8.1 | 5.2 | 5.3 | 3.4 | 4.3 | 1 | 0 |
| board | 3 | 6.7 | 8.7 | 6.7 | 8.6 | 5.3 | 7.0 | 0 | 0 |
| rest | 2 | 4.2 | 5.8 | 4.2 | 5.7 | 4.5 | 4.9 | 0 | 0 |
| hire | 1 | 8.3 | 8.3 | 8.3 | 8.3 | 4.0 | 5.0 | 0 | 0 |
| look | 1 | 3.5 | 3.5 | 3.5 | 3.5 | 5.0 | 3.4 | 0 | 0 |
| wait | 1 | 6.2 | 6.2 | 6.2 | 6.2 | 3.0 | 6.1 | 0 | 0 |

60 turns in 6.7 minutes; 97% of it in the model; 201 embedding calls taking 2.1 s; 1 calls on background threads.
The budget: 4 optional calls deferred and 3 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 19.5 s and p90 32.7 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.7 s, talk, 7 calls, at the adventurers' guild house: ""Keep my place by the fire. I'll be back, I swear it.""
- 15.5 s, fight, 7 calls, at the King's Road between Parth and Willowmead: "I attack bugbear."
- 15.4 s, talk, 2 calls, at the adventurers' guild house: "Then someone must be moving them. Tell me who's taking these contracts"
- 15.3 s, move, 6 calls, at the trading square: "Parth, I need to see those high-tier contracts now."
- 11.9 s, fight, 6 calls, at the King's Pass between Parth and Ironvein: "I use Cleaving Sweep on lesser drake."

Lines by what read them: interpret 53, combat 5, yielded 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 52 (template 8; model failed 0, 35 s) |
| Lines picking up the passage before | 17 of 60 (28%); in talk 6 of 13 (46%) |
| Contracts taken / finished | 3 / 1 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 4 / 1 (contract 1/1, go 1/0, report 1/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 5 |
| Waits | 1 of 60 (2%) |
| Places visited | 9 |

Turns by goal: idle 23, contract 9, revisit 8, board 6, fight 5, report 4, cont 2, need 2, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 5 (script 2, id 2, note 1) |
| Machinery mended at the screen | 1521 (dash 1513, stage 1, wrap 7) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you need to be at a dungeon's entrance to go down.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 1 (Calsa Hoyle in narrate 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 6 times; 0 of the game's 50 own lines (0%); most: 'You step away from the ink-stained scribe.' x6 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 4 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 34 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 4 / 0 / 17 and 476 |
| Fight turns with a foe 10+ levels above the player | 0 of 6, the widest -1 |
| Marks shown from acts (Remembered here) | 0 |
| Captives escaped / handed over or let go | 0 / 0 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | kept 0 of 1 |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 6 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 6 | 0 | 0 | 1.6 | 1.7 | 702 | 281 | 1514 | 156.3 | 0 | 135 |
| npc_conversation | 29 | 2 | 2 | 2.7 | 4.4 | 5646 | 161 | 4384 | 97.2 | 0 | 101 |
| narrate | 26 | 3 | 3 | 2.5 | 3.2 | 2475 | 197 | 2958 | 117.1 | 0 | 73 |
| interpret_action | 59 | 0 | 0 | 1.3 | 1.5 | 4717 | 67 | 5161 | 214.3 | 0 | 71 |
| player_line | 52 | 9 | 9 | 0.6 | 0.7 | 529 | 23 | 1598 | 102.6 | 0 | 35 |
| dialogue_frame | 14 | 4 | 5 | 1.5 | 2.1 | 2293 | 67 | 2525 | 101.3 | 0 | 32 |
| combat_aftermath | 8 | 0 | 0 | 2.3 | 2.6 | 1879 | 248 | 2802 | 154.1 | 0 | 18 |
| combat_opening | 5 | 1 | 1 | 2.2 | 2.7 | 1756 | 187 | 2207 | 126.7 | 0 | 14 |
| hire_chat | 9 | 0 | 0 | 1.4 | 1.6 | 2611 | 54 | 2666 | 150.1 | 0 | 13 |
| combat_narrate | 5 | 0 | 0 | 2.4 | 2.8 | 2838 | 182 | 2810 | 118.0 | 0 | 12 |
| audit_compare | 26 | 0 | 0 | 0.3 | 0.4 | 224 | 40 | 1486 | 226.0 | 0 | 9 |
| audit_meaning | 26 | 0 | 0 | 0.3 | 0.3 | 183 | 21 | 1191 | 124.3 | 0 | 8 |
| road_event | 3 | 0 | 0 | 2.8 | 2.9 | 1719 | 335 | 2263 | 166.1 | 0 | 8 |
| persona_details | 3 | 0 | 0 | 1.9 | 2.0 | 819 | 247 | 1920 | 164.4 | 0 | 6 |
| exchange | 3 | 0 | 0 | 1.9 | 2.0 | 2860 | 104 | 2824 | 143.0 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.1 | 5.1 | 1050 | 925 | 1383 | 215.9 | 0 | 5 |
| moment | 2 | 0 | 0 | 2.2 | 2.5 | 1367 | 245 | 2052 | 142.3 | 0 | 5 |
| board_stakes | 2 | 0 | 0 | 1.9 | 1.9 | 1109 | 254 | 2182 | 186.8 | 0 | 4 |
| combat_interpret | 5 | 0 | 0 | 0.7 | 0.8 | 957 | 47 | 1676 | 275.5 | 0 | 4 |
| overheard | 7 | 0 | 0 | 0.3 | 0.4 | 273 | 16 | 1015 | 262.6 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.9 | 1.1 | 614 | 92 | 1771 | 144.8 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.0 | 1.0 | 1259 | 67 | 2323 | 160.3 | 0 | 1 |
| canon_extract | 1 | 0 | 0 | 0.5 | 0.5 | 820 | 2 | 1779 | 117.6 | 0 | 0 |
| clarify | 1 | 0 | 0 | 0.5 | 0.5 | 341 | 37 | 1705 | 151.0 | 0 | 0 |
| work_offer_read | 1 | 0 | 0 | 0.4 | 0.4 | 129 | 18 | 639 | 81.8 | 0 | 0 |

316 attempts for 297 calls, 9.4 minutes in the model in all.

## Fights

10 rounds with a fight call; 2.4 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 5 | 0.7 | 0.8 | 0 |
| combat_opening | 6 | 2.2 | 2.7 | 1 |
| combat_narrate | 5 | 2.4 | 2.8 | 0 |
| combat_aftermath | 8 | 2.3 | 2.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 29 | 93% | 22499 | 24859 | 25078 | 97 | 2% |
| npc_profile | 2 | 100% | 2476 | 2600 | 2600 | 1411 | 0% |
| dialogue_frame | 14 | 79% | 9269 | 10065 | 10319 | 3605 | 8% |
| work_offer_read | 1 | 100% | 491 | 491 | 491 | 242 | 0% |
| hire_chat | 9 | 100% | 10528 | 12977 | 12977 | 1502 | 0% |
| canon_extract | 1 | 100% | 3294 | 3294 | 3294 | 662 | 0% |
| exchange | 3 | 100% | 11893 | 13063 | 13063 | 61 | 0% |
| overheard | 7 | 100% | 1104 | 1216 | 1216 | 210 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 29 | 93% | 95% | -2 | 24859 | 36345 | 36500 | 25078 | 2% |
| npc_profile | 2 | 100% | 100% | +0 | 2600 | 2774 | 3000 | 2600 | 0% |
| dialogue_frame | 14 | 79% | 86% | -7 | 10065 | 10715 | 11000 | 10319 | 8% |
| work_offer_read | 1 | 100% | 100% | +0 | 491 | 780 | 1000 | 491 | 0% |
| hire_chat | 9 | 100% | 98% | +2 | 12977 | 16275 | 16500 | 12977 | 0% |
| canon_extract | 1 | 100% | 100% | +0 | 3294 | 3998 | 4000 | 3294 | 0% |
| exchange | 3 | 100% | 90% | +10 | 13063 | 15039 | 15500 | 13063 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1216 | 1326 | 1500 | 1216 | 0% |

Size: 8 of 8 tasks at or below the baseline's p95; npc_conversation's p95 24859 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 59 | 263204 | 176506 (67%) | 183116 (70%) |
| npc_conversation | 31 | 174730 | 76190 (44%) | 13746 (8%) |
| narrate | 29 | 71106 | 40123 (56%) | 24670 (35%) |
| dialogue_frame | 18 | 41291 | 24544 (59%) | 11897 (29%) |
| player_line | 61 | 33876 | 8947 (26%) | 5583 (16%) |
| hire_chat | 9 | 24360 | 14669 (60%) | 0 (0%) |
| combat_aftermath | 8 | 15199 | 8388 (55%) | 7465 (49%) |
| combat_narrate | 5 | 14130 | 9258 (66%) | 0 (0%) |
| combat_opening | 6 | 10410 | 6147 (59%) | 1814 (17%) |
| exchange | 3 | 8892 | 3340 (38%) | 0 (0%) |
| audit_compare | 26 | 5834 | 3016 (52%) | 0 (0%) |
| road_event | 3 | 5195 | 2384 (46%) | 0 (0%) |
| combat_interpret | 5 | 4802 | 4020 (84%) | 0 (0%) |
| audit_meaning | 26 | 4601 | 1748 (38%) | 0 (0%) |
| populate_place | 6 | 4126 | 1530 (37%) | 0 (0%) |
| moment | 2 | 2735 | 1492 (55%) | 0 (0%) |
| persona_details | 3 | 2402 | 1092 (45%) | 345 (14%) |
| board_stakes | 2 | 2219 | 783 (35%) | 0 (0%) |
| overheard | 7 | 1952 | 1555 (80%) | 0 (0%) |
| ruling | 1 | 1259 | 576 (46%) | 0 (0%) |
| npc_profile | 2 | 1229 | 516 (42%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| canon_extract | 1 | 820 | 655 (80%) | 0 (0%) |
| clarify | 1 | 341 | 147 (43%) | 0 (0%) |
| work_offer_read | 1 | 129 | 65 (51%) | 0 (0%) |

The prompts held 695892 tokens; the constant system messages were about 388179 of them (56%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 248636 (36%) and read the rest.
The server's log: 316 prompts; 221 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 787 checkpoints made, 51 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 1 ended (0 by the player, 1 settled by others, 0 left to their fallout), 1 motive steps; the player met 0 doors (a scene or a summons), 2 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.67 situations started, 0.00 doors, 0.67 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 2 (2) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 3 | 0 (0) | 0 | 1 | 1 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 2: [normal, engine-built] The unquiet of the Shipwreck Shoals at Kelpmoor - starts, 1 days, 1 stages (within reach)

# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.15 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 24 | 10.5 | 13.7 | 7.6 | 9.6 | 6.0 | 9.0 | 7 | 0 |
| wait | 10 | 5.6 | 9.4 | 3.8 | 6.9 | 4.1 | 5.6 | 5 | 0 |
| talk | 7 | 8.6 | 12.6 | 8.6 | 10.8 | 4.7 | 8.7 | 1 | 0 |
| leave | 6 | 6.1 | 13.3 | 6.1 | 12.9 | 4.8 | 9.5 | 1 | 0 |
| fight | 5 | 8.6 | 12.2 | 5.7 | 7.9 | 4.0 | 7.9 | 2 | 0 |
| hire | 2 | 7.0 | 9.6 | 7.0 | 9.5 | 4.5 | 6.0 | 0 | 0 |
| board | 2 | 3.7 | 10.0 | 3.7 | 10.0 | 5.0 | 6.7 | 0 | 0 |
| rest | 2 | 5.1 | 6.9 | 5.0 | 6.9 | 4.5 | 5.9 | 0 | 0 |
| search | 1 | 3.6 | 3.6 | 3.6 | 3.6 | 2.0 | 3.4 | 0 | 0 |
| shop | 1 | 5.5 | 5.5 | - | - | 2.0 | 5.4 | 0 | 0 |

60 turns in 8.3 minutes; 95% of it in the model; 226 embedding calls taking 2.0 s; 3 calls on background threads.
The budget: 2 optional calls deferred and 6 dropped; 5 turns told by a stand-in, 4 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 22.6 s and p90 41.4 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 20.8 s, leave, 6 calls, at the adventurers' guild house: "I grunt at the scribe and turn around to head out."
- 15.7 s, talk, 3 calls, at the Riverhaven guild hall: "I walk over to the wanderer and ask, "What's the oldest thing in this "
- 15.7 s, move, 10 calls, at the King's Road between Willowmead and Parth: "Keep moving; we've got an appointment at the Adventurers' Guild House."
- 15.1 s, move, 9 calls, at the River Road between Willowmead and Riverhaven: "I stand up and tell everyone we're heading straight for the Riverhaven"
- 13.7 s, move, 8 calls, at the wharfside trading house: "I tell the others that we need to head straight for the Riverhaven gui"

Lines by what read them: interpret 53, combat 5, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 53 (template 7; model failed 0, 39 s) |
| Lines picking up the passage before | 18 of 60 (30%); in talk 4 of 7 (57%) |
| Contracts taken / finished | 1 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 0 |
| Goals finished / given up | 7 / 0 (contract 1/0, go 4/0, report 1/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 5 |
| Waits | 10 of 60 (17%) |
| Places visited | 15 |

Turns by goal: idle 16, board 14, revisit 8, go 6, fight 5, need 5, report 3, contract 2, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 15 (broken 7, id 5, script 2, escape 1) |
| Machinery mended at the screen | 864 (dash 859, stage 2, wrap 3) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 2 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 6.7 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 1 (Calsa Hoyle in dialogue_frame 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 24 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 2 / 1 / 0 (e.g. turn 33 ['flask']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 3 / 4 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 63 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 3 / 0 / 40 and 263 |
| Fight turns with a foe 10+ levels above the player | 0 of 5, the widest -3 |
| Marks shown from acts (Remembered here) | 1 |
| Captives escaped / handed over or let go | 1 / 0 |
| A speaker told ASKED BEFORE for a line that asked nothing | 0 |

## Continuity (from the page)

| Continuity (read from what was shown, against what the night recorded) | Value |
| --- | --- |
| C1 Time since the last meeting, said two steps or more from the calendar / times it was said | 0 / 0 |
| C2 Openings: someone met greets the player as a stranger / someone never met, as known | 0 / 0 |
| C3 What is owed, spoken of wrongly by its holder: open as done / closed as still open | 0 / 0 |
| C4 A kept or broken matter raised by its holder the next time they speak (raised of met), by how it ended | none met again |
| C5 Owed things gone with no line saying so / work offers left to lapse / ended for a reason the game kept (f481) | 0 / 0 / 0 |
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 15 | 0 | 0 | 1.7 | 43.6 | 539 | 231 | 1661 | 188.4 | 0 | 221 |
| narrate | 43 | 8 | 10 | 2.4 | 3.1 | 2457 | 182 | 2671 | 117.7 | 0 | 126 |
| interpret_action | 57 | 0 | 0 | 1.2 | 1.6 | 3944 | 59 | 5008 | 199.4 | 0 | 67 |
| npc_conversation | 13 | 0 | 0 | 3.1 | 11.8 | 5270 | 180 | 3890 | 71.8 | 0 | 67 |
| dialogue_frame | 25 | 5 | 5 | 1.6 | 2.2 | 2219 | 66 | 2301 | 117.9 | 0 | 49 |
| player_line | 53 | 15 | 15 | 0.6 | 0.7 | 544 | 23 | 1468 | 105.4 | 0 | 39 |
| exchange | 13 | 0 | 0 | 1.8 | 2.1 | 2740 | 99 | 2572 | 137.5 | 0 | 24 |
| hire_chat | 14 | 0 | 0 | 1.5 | 1.6 | 2958 | 60 | 2750 | 149.2 | 0 | 20 |
| combat_narrate | 6 | 2 | 2 | 2.6 | 3.0 | 3068 | 216 | 3457 | 129.4 | 0 | 20 |
| road_event | 4 | 0 | 0 | 3.1 | 3.7 | 1727 | 371 | 2076 | 165.6 | 0 | 13 |
| combat_aftermath | 5 | 0 | 0 | 2.3 | 2.9 | 2052 | 206 | 2572 | 158.6 | 0 | 11 |
| board_stakes | 4 | 0 | 0 | 2.2 | 3.9 | 1089 | 278 | 2092 | 189.5 | 0 | 10 |
| combat_opening | 3 | 1 | 2 | 2.6 | 2.9 | 1884 | 209 | 2197 | 136.5 | 0 | 10 |
| audit_meaning | 25 | 0 | 0 | 0.3 | 0.4 | 156 | 23 | 1033 | 120.8 | 0 | 9 |
| audit_compare | 25 | 0 | 0 | 0.3 | 0.4 | 224 | 36 | 1410 | 226.7 | 0 | 9 |
| persona_details | 3 | 0 | 0 | 1.8 | 2.1 | 812 | 239 | 1651 | 174.2 | 0 | 6 |
| overheard | 14 | 0 | 0 | 0.3 | 0.4 | 281 | 16 | 987 | 249.4 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.8 | 4.8 | 1050 | 914 | 1646 | 221.6 | 0 | 5 |
| combat_interpret | 5 | 0 | 0 | 0.8 | 0.9 | 958 | 48 | 1581 | 259.4 | 0 | 4 |
| npc_profile | 4 | 0 | 0 | 0.9 | 0.9 | 454 | 93 | 1662 | 159.5 | 0 | 3 |
| ruling | 3 | 0 | 0 | 1.0 | 1.1 | 1224 | 68 | 2123 | 148.6 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.5 | 2.5 | 1380 | 272 | 2107 | 147.3 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.5 | 2.5 | 2925 | 265 | 2958 | 179.1 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.6 | 0.6 | 812 | 2 | 1705 | 161.3 | 0 | 2 |
| work_offer_read | 2 | 0 | 0 | 0.4 | 0.5 | 119 | 19 | 499 | 101.3 | 0 | 1 |

373 attempts for 342 calls, 12.1 minutes in the model in all.

## Fights

8 rounds with a fight call; 2.8 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 5 | 0.8 | 0.9 | 0 |
| combat_opening | 4 | 2.6 | 2.9 | 2 |
| combat_narrate | 8 | 2.6 | 3.1 | 2 |
| combat_aftermath | 5 | 2.3 | 2.9 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 13 | 100% | 20855 | 22399 | 22577 | 56 | 4% |
| npc_profile | 4 | 100% | 1905 | 2443 | 2443 | 840 | 0% |
| dialogue_frame | 25 | 80% | 9282 | 11048 | 11109 | 3904 | 0% |
| work_offer_read | 2 | 100% | 445 | 460 | 460 | 196 | 0% |
| hire_chat | 14 | 100% | 11987 | 12462 | 13577 | 1615 | 0% |
| canon_extract | 3 | 100% | 3309 | 4056 | 4056 | 677 | 0% |
| exchange | 13 | 100% | 11359 | 13630 | 15715 | 61 | 0% |
| overheard | 14 | 100% | 1141 | 1212 | 1229 | 247 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 13 | 100% | 95% | +5 | 22399 | 36345 | 36500 | 22577 | 4% |
| npc_profile | 4 | 100% | 100% | +0 | 2443 | 2774 | 3000 | 2443 | 0% |
| dialogue_frame | 25 | 80% | 86% | -6 | 11048 | 10715 | 11000 | 11109 | 0% |
| work_offer_read | 2 | 100% | 100% | +0 | 460 | 780 | 1000 | 460 | 0% |
| hire_chat | 14 | 100% | 98% | +2 | 12462 | 16275 | 16500 | 13577 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4056 | 3998 | 4000 | 4056 | 0% |
| exchange | 13 | 100% | 90% | +10 | 13630 | 15039 | 15500 | 15715 | 0% |
| overheard | 14 | 100% | 100% | +0 | 1212 | 1326 | 1500 | 1229 | 0% |

Size: 6 of 8 tasks at or below the baseline's p95 (dearer: dialogue_frame, canon_extract); npc_conversation's p95 22399 against the mark of 14000, not held; over their ceiling: dialogue_frame, canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 57 | 232845 | 167812 (72%) | 172509 (74%) |
| narrate | 51 | 127019 | 73751 (58%) | 32749 (26%) |
| dialogue_frame | 30 | 68443 | 40088 (59%) | 11490 (17%) |
| npc_conversation | 13 | 67464 | 31956 (47%) | 2404 (4%) |
| hire_chat | 14 | 40255 | 22871 (57%) | 0 (0%) |
| player_line | 68 | 37627 | 9766 (26%) | 7963 (21%) |
| exchange | 13 | 36484 | 14464 (40%) | 0 (0%) |
| combat_narrate | 8 | 24798 | 15578 (63%) | 9174 (37%) |
| combat_aftermath | 5 | 10188 | 5337 (52%) | 4061 (40%) |
| populate_place | 15 | 8539 | 3870 (45%) | 0 (0%) |
| combat_opening | 4 | 7489 | 4265 (57%) | 1846 (25%) |
| road_event | 4 | 7067 | 3162 (45%) | 754 (11%) |
| audit_compare | 25 | 5637 | 2911 (52%) | 0 (0%) |
| combat_interpret | 5 | 4807 | 4025 (84%) | 0 (0%) |
| board_stakes | 4 | 4258 | 1594 (37%) | 0 (0%) |
| audit_meaning | 25 | 4088 | 1715 (42%) | 0 (0%) |
| overheard | 14 | 3986 | 3107 (78%) | 0 (0%) |
| ruling | 3 | 3621 | 1760 (49%) | 0 (0%) |
| thread_telling | 1 | 2925 | 396 (14%) | 0 (0%) |
| canon_extract | 3 | 2591 | 1928 (74%) | 0 (0%) |
| persona_details | 3 | 2386 | 1083 (45%) | 345 (14%) |
| npc_profile | 4 | 1915 | 1044 (55%) | 0 (0%) |
| moment | 1 | 1380 | 748 (54%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| work_offer_read | 2 | 239 | 132 (55%) | 0 (0%) |

The prompts held 707101 tokens; the constant system messages were about 413851 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 243295 (34%) and read the rest.
The server's log: 373 prompts; 274 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 933 checkpoints made, 47 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 6 game days: 5 situations started (5 within reach of the player), 1 stages advanced, 3 ended (0 by the player, 3 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 2 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 0.83 situations started, 0.00 doors, 0.33 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 2 (2) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 0 (0) | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 4 | 2 (2) | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 5 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 | 1 (1) | 1 | 1 | 0 | 0 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 2: [normal, engine-built] The unquiet of the Greywood at Parth - starts, 2 days, 1 stages (within reach)
- day 4: [normal, engine-built] Cut off at Willowmead - starts, 2 days, 1 stages (within reach)
- day 4: [uncommon, engine-built] The strike at the Greywood at Parth - starts, 3 days, 2 stages (within reach)
- day 6: [normal, engine-built] Yarrow by the cartload at Willowmead - starts, 1 days, 1 stages (within reach)

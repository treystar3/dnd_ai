# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.09 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 18 | 5.2 | 7.8 | 4.6 | 6.3 | 5.3 | 5.3 | 4 | 0 |
| search | 11 | 2.9 | 7.0 | 2.9 | 5.3 | 3.7 | 3.6 | 2 | 0 |
| fight | 9 | 6.6 | 11.1 | 3.3 | 4.0 | 4.6 | 6.8 | 2 | 0 |
| wait | 6 | 2.9 | 7.7 | 2.9 | 4.2 | 5.7 | 5.2 | 4 | 0 |
| talk | 4 | 4.6 | 8.6 | 4.6 | 4.8 | 4.8 | 4.5 | 1 | 0 |
| leave | 4 | 5.8 | 8.9 | 3.6 | 4.0 | 5.8 | 5.5 | 0 | 0 |
| board | 2 | 4.5 | 5.2 | 4.5 | 5.2 | 6.0 | 4.7 | 1 | 0 |
| shop | 2 | 3.6 | 11.1 | 3.6 | 6.7 | 6.0 | 7.2 | 1 | 0 |
| hire | 1 | 6.5 | 6.5 | 5.0 | 5.0 | 6.0 | 6.2 | 0 | 0 |
| pick_up | 1 | 2.6 | 2.6 | 2.6 | 2.6 | 4.0 | 2.6 | 0 | 0 |
| work | 1 | 6.1 | 6.1 | 6.1 | 6.1 | 4.0 | 6.1 | 1 | 0 |
| look | 1 | 1.9 | 1.9 | - | - | 5.0 | 1.9 | 0 | 0 |

60 turns in 5.3 minutes; 98% of it in the model; 218 embedding calls taking 1.1 s; 1 calls on background threads.
The budget: 2 optional calls deferred and 4 dropped; 4 turns told by a stand-in, 4 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 20.6 s and p90 34.4 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 11.8 s, move, 11 calls, at the Salt Road between Parth and Kelpmoor: "I tighten my grip on my weapon and signal the group to push ahead towa"
- 11.3 s, fight, 5 calls, at the Salt Road between Kelpmoor and Parth: "I use Brutal Strike on bandit 2."
- 11.1 s, shop, 9 calls, at the adventurers' guild house: "I walk up to the sharp-eyed clerk and offer my copper sabatons for som"
- 11.1 s, fight, 6 calls, at the King's Road between Willowmead and Parth: "I use Brutal Strike on swarm of wasps."
- 10.5 s, fight, 8 calls, at the King's Road between Parth and Willowmead: "I strike at swarm of insects."

Lines by what read them: interpret 45, combat 9, hire 3, yielded 3

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 49 (template 11; model failed 1, 21 s) |
| Lines picking up the passage before | 17 of 60 (28%); in talk 1 of 4 (25%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 2 / 0 / 0 |
| Goals finished / given up | 6 / 0 (contract 3/0, go 2/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 9 |
| Waits | 6 of 60 (10%) |
| Places visited | 10 |

Turns by goal: contract 22, idle 10, report 10, fight 9, go 2, board 2, need 2, stop 1, cont 1, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 5 (id 3, broken 1, script 1) |
| Machinery mended at the screen | 1895 (dash 1876, stage 2, wrap 17) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 1 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 42 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 1 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 5 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 74 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 7 / 0 / 5 and 8 |
| Fight turns with a foe 10+ levels above the player | 0 of 9, the widest -10 |
| Marks shown from acts (Remembered here) | 1 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 1 / 0 (e.g. turn 28 the ink-stained girl contract_taken) |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 5 | 0 | 0 | 1.1 | 123.2 | 687 | 218 | 2352 | 203.3 | 0 | 127 |
| narrate | 35 | 4 | 4 | 1.9 | 2.6 | 2382 | 175 | 5049 | 126.6 | 0 | 76 |
| interpret_action | 52 | 0 | 0 | 0.7 | 0.9 | 3853 | 63 | 10227 | 243.4 | 0 | 35 |
| dialogue_frame | 26 | 4 | 5 | 1.0 | 1.3 | 2124 | 71 | 4193 | 134.7 | 0 | 32 |
| npc_conversation | 11 | 1 | 1 | 1.9 | 2.4 | 5249 | 151 | 6307 | 144.9 | 0 | 23 |
| player_line | 50 | 7 | 8 | 0.4 | 0.5 | 560 | 25 | 2942 | 134.3 | 0 | 21 |
| combat_narrate | 9 | 0 | 0 | 2.1 | 2.7 | 2842 | 194 | 4481 | 124.4 | 0 | 19 |
| exchange | 13 | 2 | 2 | 1.2 | 1.4 | 3006 | 99 | 5099 | 160.8 | 0 | 18 |
| road_event | 6 | 2 | 2 | 2.3 | 2.3 | 1765 | 345 | 4372 | 191.2 | 0 | 18 |
| combat_aftermath | 10 | 0 | 0 | 1.5 | 1.9 | 1840 | 212 | 4492 | 168.3 | 0 | 16 |
| hire_chat | 17 | 0 | 0 | 0.9 | 1.1 | 2499 | 59 | 4417 | 175.2 | 0 | 16 |
| combat_opening | 7 | 0 | 0 | 1.7 | 1.9 | 1639 | 176 | 3727 | 130.7 | 0 | 12 |
| audit_compare | 24 | 0 | 0 | 0.2 | 0.3 | 222 | 37 | 2454 | 255.6 | 0 | 6 |
| thread_telling | 2 | 1 | 1 | 2.2 | 2.4 | 2943 | 285 | 6183 | 199.9 | 0 | 6 |
| audit_meaning | 24 | 0 | 0 | 0.2 | 0.2 | 156 | 22 | 1931 | 171.0 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1036 | 957 | 3047 | 234.7 | 0 | 4 |
| combat_interpret | 9 | 0 | 0 | 0.4 | 0.5 | 965 | 36 | 2976 | 284.8 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.4 | 1.4 | 784 | 231 | 3431 | 199.8 | 0 | 4 |
| overheard | 14 | 0 | 0 | 0.2 | 0.2 | 280 | 16 | 1990 | 279.6 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.5 | 2.5 | 1624 | 394 | 3894 | 186.5 | 0 | 3 |
| discovery | 1 | 1 | 2 | 0.9 | 1.3 | 2795 | 126 | 6485 | 193.3 | 0 | 2 |
| npc_profile | 3 | 0 | 0 | 0.6 | 0.7 | 605 | 84 | 3421 | 193.1 | 0 | 2 |
| board_stakes | 2 | 0 | 0 | 0.8 | 1.0 | 1000 | 136 | 3914 | 208.7 | 0 | 2 |
| ruling | 2 | 0 | 0 | 0.6 | 1.0 | 1180 | 103 | 3627 | 218.0 | 0 | 2 |
| canon_extract | 2 | 0 | 0 | 0.5 | 0.6 | 818 | 70 | 3026 | 244.4 | 0 | 1 |
| work_offer_read | 3 | 0 | 0 | 0.2 | 0.2 | 121 | 19 | 1167 | 167.1 | 0 | 1 |
| clarify | 1 | 1 | 1 | 0.3 | 0.3 | 278 | 36 | 2422 | 212.8 | 0 | 1 |

356 attempts for 333 calls, 7.7 minutes in the model in all.

## Fights

16 rounds with a fight call; 2.2 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 9 | 0.4 | 0.8 | 0 |
| combat_opening | 7 | 1.7 | 1.9 | 0 |
| combat_narrate | 9 | 2.1 | 2.8 | 0 |
| combat_aftermath | 10 | 1.5 | 2.1 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 11 | 91% | 20707 | 21960 | 21960 | 83 | 0% |
| npc_profile | 3 | 100% | 2520 | 2655 | 2655 | 1455 | 0% |
| dialogue_frame | 26 | 88% | 8506 | 10119 | 11102 | 3922 | 4% |
| work_offer_read | 3 | 100% | 440 | 457 | 457 | 191 | 0% |
| hire_chat | 17 | 100% | 10286 | 11624 | 11636 | 2010 | 0% |
| canon_extract | 2 | 100% | 3292 | 3305 | 3305 | 660 | 0% |
| exchange | 13 | 85% | 12381 | 14003 | 14117 | 63 | 0% |
| overheard | 14 | 100% | 1143 | 1187 | 1239 | 249 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 11 | 91% | 95% | -4 | 21960 | 36345 | 36500 | 21960 | 0% |
| npc_profile | 3 | 100% | 100% | +0 | 2655 | 2774 | 3000 | 2655 | 0% |
| dialogue_frame | 26 | 88% | 86% | +2 | 10119 | 10715 | 11000 | 11102 | 4% |
| work_offer_read | 3 | 100% | 100% | +0 | 457 | 780 | 1000 | 457 | 0% |
| hire_chat | 17 | 100% | 98% | +2 | 11624 | 16275 | 16500 | 11636 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 3305 | 3998 | 4000 | 3305 | 0% |
| exchange | 13 | 85% | 90% | -5 | 14003 | 15039 | 15500 | 14117 | 0% |
| overheard | 14 | 100% | 100% | +0 | 1187 | 1326 | 1500 | 1239 | 0% |

Size: 8 of 8 tasks at or below the baseline's p95; npc_conversation's p95 21960 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 52 | 208145 | 153150 (74%) | 157609 (76%) |
| narrate | 39 | 98674 | 48438 (49%) | 24547 (25%) |
| dialogue_frame | 30 | 63573 | 34091 (54%) | 10718 (17%) |
| npc_conversation | 12 | 62402 | 26815 (43%) | 5097 (8%) |
| exchange | 15 | 44752 | 16689 (37%) | 5807 (13%) |
| hire_chat | 17 | 43192 | 23456 (54%) | 0 (0%) |
| player_line | 57 | 31886 | 8139 (26%) | 3702 (12%) |
| combat_narrate | 9 | 24936 | 14168 (57%) | 0 (0%) |
| combat_aftermath | 10 | 18245 | 8819 (48%) | 5364 (29%) |
| road_event | 8 | 14719 | 6702 (46%) | 3445 (23%) |
| combat_opening | 7 | 11770 | 5909 (50%) | 0 (0%) |
| thread_telling | 3 | 9163 | 1242 (14%) | 2939 (32%) |
| combat_interpret | 9 | 8679 | 7251 (84%) | 0 (0%) |
| discovery | 2 | 5590 | 868 (16%) | 2711 (48%) |
| audit_compare | 24 | 5360 | 2770 (52%) | 0 (0%) |
| overheard | 14 | 3921 | 3066 (78%) | 0 (0%) |
| audit_meaning | 24 | 3880 | 1602 (41%) | 0 (0%) |
| populate_place | 5 | 3311 | 1266 (38%) | 0 (0%) |
| ruling | 2 | 2361 | 1166 (49%) | 0 (0%) |
| persona_details | 3 | 2323 | 1102 (47%) | 0 (0%) |
| board_stakes | 2 | 2000 | 758 (38%) | 0 (0%) |
| npc_profile | 3 | 1837 | 764 (42%) | 0 (0%) |
| canon_extract | 2 | 1637 | 1306 (80%) | 0 (0%) |
| moment | 1 | 1624 | 748 (46%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| clarify | 2 | 557 | 318 (57%) | 235 (42%) |
| work_offer_read | 3 | 356 | 205 (58%) | 0 (0%) |

The prompts held 675929 tokens; the constant system messages were about 371302 of them (55%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 222174 (33%) and read the rest.
The server's log: 356 prompts; 271 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 892 checkpoints made, 33 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 4 game days: 5 situations started (4 within reach of the player), 0 stages advanced, 3 ended (0 by the player, 2 settled by others, 1 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 2 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 0.25 doors, 0.25 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| 3 | 1 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | 2 (2) | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| 5 | 1 (1) | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)
- day 3: [normal, engine-built] The good year at Cinderhold - starts, 1 days, 1 stages
- day 4: [normal, engine-built] The price of peace at Saltmarsh Landing at the Tidepool Caves - starts, 1 days, 1 stage (within reach)
- day 4: [normal, engine-built] The weather turns on Kelpmoor - starts, 2 days, 1 stages (within reach)
- day 5: [uncommon, engine-built] Yarrow by the cartload at Parth - starts, 5 days, 2 stages (within reach)

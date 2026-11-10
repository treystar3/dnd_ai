# Night run: play_hunter

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 14 | 5.9 | 11.8 | 4.2 | 6.5 | 3.0 | 6.5 | 2 | 0 |
| forage | 12 | 4.0 | 4.4 | 4.0 | 4.4 | 2.5 | 3.7 | 0 | 0 |
| move | 9 | 10.9 | 16.5 | 8.3 | 10.8 | 5.7 | 9.5 | 2 | 0 |
| search | 7 | 5.2 | 6.9 | 4.0 | 5.2 | 3.6 | 5.1 | 0 | 0 |
| talk | 5 | 4.9 | 14.1 | 4.9 | 8.3 | 4.2 | 7.5 | 1 | 0 |
| leave | 5 | 10.3 | 12.2 | 7.6 | 8.5 | 6.2 | 7.5 | 0 | 0 |
| wait | 3 | 6.5 | 16.1 | 6.3 | 6.5 | 6.0 | 8.7 | 2 | 0 |
| board | 2 | 6.8 | 9.8 | 6.7 | 9.8 | 5.5 | 8.1 | 0 | 0 |
| look | 2 | 2.6 | 3.2 | 2.6 | 3.2 | 2.0 | 2.9 | 0 | 0 |
| hire | 1 | 12.2 | 12.2 | 8.2 | 8.2 | 8.0 | 11.9 | 0 | 0 |

60 turns in 6.8 minutes; 96% of it in the model; 158 embedding calls taking 1.7 s; 1 calls on background threads.
The budget: 2 optional calls deferred and 1 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 14.9 s and p90 32.8 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 22.2 s, move, 11 calls, at the King's Road between Willowmead and Parth: "I ignore the carts and tell the group we're heading straight to the Ad"
- 16.5 s, move, 8 calls, at the trading square: "Alright, let's move out. We're heading straight for the Willowmead wet"
- 16.1 s, wait, 11 calls, at the adventurers' guild house: "I lean against a nearby pillar and watch the crowd, waiting for the ri"
- 15.5 s, fight, 6 calls, at the Willowmead wetlands: "I use Cleaving Sweep on lizardfolk 1."
- 14.2 s, move, 8 calls, at the trading square: "I nod at Gran and start walking towards the treeline, saying, 'Then le"

Lines by what read them: interpret 44, combat 14, hire 1, yielded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 55 of 60 (92%) |
| Lines the model wrote | 45 (template 15; model failed 0, 37 s) |
| Lines picking up the passage before | 10 of 60 (17%); in talk 2 of 5 (40%) |
| Contracts taken / finished | 2 / 1 |
| Situations met / followed / ended by the player | 1 / 0 / 1 |
| Goals finished / given up | 4 / 0 (contract 2/0, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 14 |
| Waits | 3 of 60 (5%) |
| Places visited | 6 |

Turns by goal: contract 25, fight 14, idle 8, report 8, board 3, go 1, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 1 (id 1) |
| Machinery mended at the screen | 2275 (dash 2264, escape 1, json 1, wrap 9) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("bronze longsword is already in hand.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 3 / 2 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 3 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 25.0 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 38 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 57 ['toward']) |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 1 / 0 (e.g. '\\') |
| City ground in the wilds / rain under a roof / weather out of season | 5 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 72 |
| Matters the player ended: pursued / by accident | 0 / 1 (by accident: Cheap and then dear in Parth) |
| Fights won / for +0 XP / XP median and most | 7 / 1 / 4 and 28 |
| Fight turns with a foe 10+ levels above the player | 0 of 14, the widest -8 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 4 | 0 | 0 | 2.0 | 123.5 | 666 | 241 | 898 | 170.0 | 0 | 128 |
| narrate | 32 | 0 | 0 | 2.6 | 3.6 | 2405 | 137 | 1990 | 105.0 | 0 | 88 |
| interpret_action | 48 | 0 | 0 | 1.1 | 1.6 | 3628 | 56 | 4589 | 185.0 | 0 | 57 |
| combat_narrate | 14 | 1 | 1 | 3.1 | 3.8 | 2912 | 202 | 2164 | 113.6 | 0 | 47 |
| player_line | 45 | 13 | 13 | 0.6 | 0.8 | 507 | 23 | 1274 | 100.2 | 0 | 37 |
| dialogue_frame | 17 | 3 | 3 | 1.9 | 2.0 | 2166 | 65 | 1825 | 111.4 | 0 | 37 |
| npc_conversation | 7 | 1 | 1 | 2.9 | 3.8 | 5368 | 153 | 3559 | 110.0 | 0 | 24 |
| combat_aftermath | 8 | 0 | 0 | 2.5 | 3.1 | 1881 | 187 | 1542 | 140.8 | 0 | 21 |
| combat_opening | 7 | 0 | 0 | 2.7 | 3.0 | 1706 | 164 | 1489 | 104.2 | 0 | 19 |
| hire_chat | 10 | 1 | 1 | 1.8 | 1.8 | 2882 | 61 | 2290 | 142.1 | 0 | 19 |
| exchange | 8 | 1 | 1 | 1.8 | 2.0 | 3096 | 75 | 2439 | 138.1 | 0 | 17 |
| combat_interpret | 14 | 0 | 0 | 0.9 | 1.1 | 953 | 47 | 1243 | 227.3 | 0 | 14 |
| audit_compare | 21 | 0 | 0 | 0.4 | 0.4 | 217 | 40 | 1227 | 210.9 | 0 | 8 |
| audit_meaning | 21 | 0 | 0 | 0.3 | 0.4 | 170 | 22 | 1032 | 120.2 | 0 | 8 |
| ruling | 5 | 0 | 0 | 1.2 | 2.2 | 1222 | 68 | 1598 | 148.1 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 2.1 | 2.1 | 823 | 241 | 1636 | 160.6 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.3 | 5.3 | 1036 | 889 | 1372 | 196.5 | 0 | 5 |
| road_event | 1 | 0 | 0 | 4.2 | 4.2 | 1850 | 453 | 1872 | 141.8 | 0 | 4 |
| overheard | 7 | 0 | 0 | 0.4 | 0.4 | 284 | 16 | 933 | 239.8 | 0 | 3 |
| moment | 1 | 0 | 0 | 2.6 | 2.6 | 1348 | 245 | 1660 | 139.9 | 0 | 3 |
| thread_telling | 1 | 0 | 0 | 2.3 | 2.3 | 2897 | 115 | 2378 | 110.3 | 0 | 2 |
| board_stakes | 2 | 0 | 0 | 1.0 | 1.3 | 952 | 97 | 1808 | 166.0 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.7 | 0.7 | 842 | 6 | 1317 | 175.0 | 0 | 2 |
| npc_profile | 1 | 0 | 0 | 1.0 | 1.0 | 594 | 108 | 1702 | 164.1 | 0 | 1 |
| work_offer_read | 1 | 0 | 0 | 0.4 | 0.4 | 143 | 21 | 675 | 148.9 | 0 | 0 |

302 attempts for 282 calls, 9.3 minutes in the model in all.

## Fights

21 rounds with a fight call; 2.1 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 14 | 0.9 | 1.1 | 0 |
| combat_opening | 7 | 2.7 | 3.2 | 0 |
| combat_narrate | 15 | 3.1 | 3.8 | 1 |
| combat_aftermath | 8 | 2.5 | 3.7 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 21356 | 22616 | 22616 | 78 | 0% |
| npc_profile | 1 | 100% | 2487 | 2487 | 2487 | 1422 | 0% |
| dialogue_frame | 17 | 82% | 8896 | 10692 | 10753 | 3212 | 0% |
| work_offer_read | 1 | 100% | 548 | 548 | 548 | 299 | 0% |
| hire_chat | 10 | 90% | 10915 | 14391 | 14391 | 1498 | 0% |
| canon_extract | 3 | 100% | 3431 | 3458 | 3458 | 799 | 0% |
| exchange | 8 | 88% | 12735 | 14229 | 14229 | 63 | 0% |
| overheard | 7 | 100% | 1161 | 1223 | 1223 | 267 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 86% | 95% | -9 | 22616 | 36345 | 36500 | 22616 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2487 | 2774 | 3000 | 2487 | 0% |
| dialogue_frame | 17 | 82% | 86% | -4 | 10692 | 10715 | 11000 | 10753 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 548 | 780 | 1000 | 548 | 0% |
| hire_chat | 10 | 90% | 98% | -8 | 14391 | 16275 | 16500 | 14391 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 3458 | 3998 | 4000 | 3458 | 0% |
| exchange | 8 | 88% | 90% | -2 | 14229 | 15039 | 15500 | 14229 | 0% |
| overheard | 7 | 100% | 100% | +0 | 1223 | 1326 | 1500 | 1223 | 0% |

Size: 8 of 8 tasks at or below the baseline's p95; npc_conversation's p95 22616 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -9; hire_chat -8).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 48 | 187430 | 140184 (75%) | 143681 (77%) |
| narrate | 32 | 78502 | 45403 (58%) | 3698 (5%) |
| combat_narrate | 15 | 44273 | 28515 (64%) | 2914 (7%) |
| dialogue_frame | 20 | 43481 | 26622 (61%) | 6540 (15%) |
| npc_conversation | 8 | 42902 | 19676 (46%) | 5692 (13%) |
| hire_chat | 11 | 32544 | 17879 (55%) | 3567 (11%) |
| player_line | 58 | 31192 | 8319 (27%) | 6903 (22%) |
| exchange | 9 | 27750 | 10026 (36%) | 3092 (11%) |
| combat_aftermath | 8 | 15047 | 8540 (57%) | 0 (0%) |
| combat_interpret | 14 | 13369 | 11221 (84%) | 0 (0%) |
| combat_opening | 7 | 11807 | 7209 (61%) | 830 (7%) |
| ruling | 5 | 6243 | 2891 (46%) | 0 (0%) |
| audit_compare | 21 | 4699 | 2445 (52%) | 0 (0%) |
| audit_meaning | 21 | 3563 | 1398 (39%) | 0 (0%) |
| thread_telling | 1 | 2897 | 397 (14%) | 0 (0%) |
| populate_place | 4 | 2592 | 1005 (39%) | 0 (0%) |
| canon_extract | 3 | 2536 | 1941 (77%) | 0 (0%) |
| persona_details | 3 | 2411 | 1089 (45%) | 345 (14%) |
| overheard | 7 | 1983 | 1538 (78%) | 0 (0%) |
| board_stakes | 2 | 1904 | 751 (39%) | 0 (0%) |
| road_event | 1 | 1850 | 789 (43%) | 0 (0%) |
| moment | 1 | 1348 | 754 (56%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| npc_profile | 1 | 594 | 254 (43%) | 0 (0%) |
| work_offer_read | 1 | 143 | 65 (45%) | 0 (0%) |

The prompts held 562096 tokens; the constant system messages were about 339405 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 177262 (32%) and read the rest.
The server's log: 302 prompts; 229 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 745 checkpoints made, 29 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 1 | 0 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

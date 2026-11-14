# Night run: play_talker

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.11 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 24 | 4.6 | 7.5 | 4.5 | 7.5 | 2.5 | 5.3 | 0 | 0 |
| forage | 10 | 3.9 | 6.0 | 3.4 | 4.5 | 3.5 | 4.2 | 1 | 0 |
| move | 7 | 10.4 | 13.0 | 7.6 | 10.2 | 6.6 | 9.8 | 2 | 0 |
| leave | 7 | 4.5 | 8.3 | 4.2 | 5.3 | 3.1 | 5.5 | 0 | 0 |
| look | 5 | 4.7 | 10.9 | 3.9 | 9.1 | 5.0 | 5.0 | 0 | 0 |
| rest | 4 | 9.9 | 10.2 | 9.9 | 10.2 | 6.0 | 9.1 | 1 | 0 |
| board | 2 | 3.9 | 4.9 | 4.9 | 4.9 | 4.0 | 4.4 | 0 | 0 |
| wait | 1 | 6.0 | 6.0 | 6.0 | 6.0 | 2.0 | 3.3 | 0 | 0 |

60 turns in 6.0 minutes; 97% of it in the model; 287 embedding calls taking 2.3 s; 1 calls on background threads.
The budget: 2 optional calls deferred and 0 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.5 s and p90 26.0 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.0 s, talk, 7 calls, at the Tilted Plough: "I approach the counter and look at the host. 'How long have you been r"
- 13.0 s, move, 6 calls, at the trading square: "I head toward the Adventurers' Guild House to see if any new contracts"
- 13.0 s, move, 8 calls, at the adventurers' guild house: ""We should head to the Tilted Plough first," I say, glancing at the gr"
- 12.2 s, leave, 7 calls, at the Tilted Plough: "I give a short nod of thanks to the host and start to turn toward the "
- 11.8 s, move, 6 calls, at the south fields: "I turn to the others and say we should head back toward the adventurer"

Lines by what read them: interpret 55, hire 5

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 55 (template 5; model failed 1, 47 s) |
| Lines picking up the passage before | 24 of 60 (40%); in talk 10 of 24 (42%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 4 / 1 (contract 1/1, go 2/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 1 of 60 (2%) |
| Places visited | 4 |

Turns by goal: idle 28, contract 14, need 7, cont 4, report 3, board 2, go 1, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 4 (script 3, json 1) |
| Machinery mended at the screen | 9 (dash 5, stage 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 9.1 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Gorz Skorgarth in narrate 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 12 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 32; townsfolk 0 of 2 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 2 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 32 | 0 | 0 | 3.0 | 3.9 | 5301 | 162 | 3391 | 105.4 | 0 | 104 |
| interpret_action | 58 | 0 | 0 | 1.2 | 1.6 | 4144 | 64 | 4416 | 215.3 | 0 | 73 |
| populate_place | 4 | 0 | 0 | 1.6 | 66.8 | 673 | 242 | 1657 | 203.0 | 0 | 72 |
| narrate | 22 | 2 | 2 | 2.1 | 2.8 | 2179 | 129 | 1967 | 119.5 | 0 | 52 |
| player_line | 56 | 16 | 17 | 0.7 | 0.8 | 517 | 29 | 1329 | 104.4 | 0 | 47 |
| dialogue_frame | 21 | 2 | 3 | 1.8 | 2.1 | 2101 | 76 | 1807 | 115.7 | 0 | 42 |
| hire_chat | 15 | 0 | 0 | 1.6 | 1.9 | 2585 | 61 | 2131 | 148.4 | 0 | 24 |
| exchange | 10 | 0 | 0 | 2.0 | 2.4 | 2929 | 110 | 2245 | 134.1 | 0 | 21 |
| persona_details | 3 | 0 | 0 | 2.0 | 2.0 | 824 | 250 | 1676 | 170.4 | 0 | 6 |
| overheard | 15 | 0 | 0 | 0.4 | 0.4 | 284 | 16 | 974 | 262.6 | 0 | 5 |
| audit_compare | 15 | 0 | 0 | 0.3 | 0.4 | 227 | 39 | 1325 | 222.2 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.4 | 5.4 | 1028 | 943 | 1391 | 204.4 | 0 | 5 |
| audit_meaning | 15 | 0 | 0 | 0.3 | 0.4 | 167 | 22 | 1005 | 128.2 | 0 | 5 |
| npc_profile | 4 | 0 | 0 | 1.1 | 1.4 | 635 | 94 | 1613 | 141.4 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 2.3 | 2.3 | 887 | 280 | 1493 | 169.6 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.6 | 0.7 | 818 | 6 | 1442 | 172.8 | 0 | 2 |
| ruling | 1 | 0 | 0 | 1.2 | 1.2 | 1270 | 67 | 1809 | 146.6 | 0 | 1 |
| clarify | 1 | 0 | 0 | 0.4 | 0.4 | 258 | 29 | 1229 | 136.2 | 0 | 0 |
| work_offer_read | 1 | 0 | 0 | 0.3 | 0.3 | 130 | 19 | 710 | 133.8 | 0 | 0 |

298 attempts for 278 calls, 7.9 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 32 | 100% | 21399 | 22536 | 23028 | 108 | 3% |
| npc_profile | 4 | 100% | 2652 | 2661 | 2661 | 1587 | 0% |
| dialogue_frame | 21 | 90% | 8645 | 9946 | 10180 | 2903 | 0% |
| work_offer_read | 1 | 100% | 491 | 491 | 491 | 242 | 1% |
| hire_chat | 15 | 100% | 10446 | 11090 | 12656 | 1535 | 0% |
| canon_extract | 3 | 100% | 3322 | 4240 | 4240 | 690 | 0% |
| exchange | 10 | 100% | 11873 | 12449 | 12449 | 63 | 0% |
| overheard | 15 | 100% | 1152 | 1276 | 1290 | 258 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 32 | 100% | 95% | +5 | 22536 | 36345 | 36500 | 23028 | 3% |
| npc_profile | 4 | 100% | 100% | +0 | 2661 | 2774 | 3000 | 2661 | 0% |
| dialogue_frame | 21 | 90% | 86% | +4 | 9946 | 10715 | 11000 | 10180 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 491 | 780 | 1000 | 491 | 1% |
| hire_chat | 15 | 100% | 98% | +2 | 11090 | 16275 | 16500 | 12656 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4240 | 3998 | 4000 | 4240 | 0% |
| exchange | 10 | 100% | 90% | +10 | 12449 | 15039 | 15500 | 12449 | 0% |
| overheard | 15 | 100% | 100% | +0 | 1276 | 1326 | 1500 | 1290 | 0% |

Size: 7 of 8 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 22536 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 58 | 236809 | 170949 (72%) | 174636 (74%) |
| npc_conversation | 32 | 167803 | 77773 (46%) | 4838 (3%) |
| narrate | 24 | 51621 | 34405 (67%) | 8231 (16%) |
| dialogue_frame | 23 | 47958 | 31078 (65%) | 3955 (8%) |
| hire_chat | 15 | 38946 | 24291 (62%) | 15 (0%) |
| player_line | 72 | 38323 | 10243 (27%) | 8556 (22%) |
| exchange | 10 | 28120 | 11232 (40%) | 10 (0%) |
| overheard | 15 | 4312 | 3311 (77%) | 15 (0%) |
| audit_compare | 15 | 3413 | 1741 (51%) | 15 (0%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| canon_extract | 3 | 2644 | 1933 (73%) | 3 (0%) |
| npc_profile | 4 | 2541 | 1026 (40%) | 4 (0%) |
| audit_meaning | 15 | 2493 | 1038 (42%) | 15 (1%) |
| persona_details | 3 | 2433 | 1092 (45%) | 347 (14%) |
| ruling | 1 | 1270 | 576 (45%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 887 | 373 (42%) | 1 (0%) |
| clarify | 1 | 258 | 141 (55%) | 1 (0%) |
| work_offer_read | 1 | 130 | 66 (51%) | 1 (1%) |

The prompts held 633683 tokens; the constant system messages were about 372778 of them (59%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 200648 (32%) and read the rest.
The server's log: 298 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 852 checkpoints made, 268 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 2 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 2.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

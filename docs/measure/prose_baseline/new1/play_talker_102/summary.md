# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.11 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 28 | 4.0 | 10.0 | 4.0 | 6.3 | 2.8 | 5.3 | 2 | 0 |
| wait | 10 | 3.9 | 6.1 | 4.0 | 6.0 | 2.4 | 3.8 | 1 | 0 |
| move | 10 | 6.9 | 11.1 | 6.4 | 8.6 | 5.8 | 7.6 | 4 | 0 |
| leave | 6 | 4.7 | 7.3 | 4.4 | 5.0 | 4.2 | 5.4 | 0 | 0 |
| board | 2 | 8.1 | 14.0 | 8.1 | 10.0 | 7.0 | 10.8 | 0 | 0 |
| improv | 2 | 2.2 | 4.1 | 2.2 | 4.0 | 2.5 | 3.0 | 0 | 0 |
| search | 1 | 5.4 | 5.4 | 5.4 | 5.4 | 3.0 | 5.2 | 0 | 0 |
| rest | 1 | 6.5 | 6.5 | 6.5 | 6.5 | 6.0 | 6.4 | 0 | 0 |

60 turns in 5.8 minutes; 96% of it in the model; 247 embedding calls taking 2.3 s; 1 calls on background threads.
The budget: 10 optional calls deferred and 3 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 14.9 s and p90 32.6 s, over 60 s in 1 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 19.4 s, talk, 4 calls, at the adventurers' guild house: ""Excuse me, friend, do you mind if I ask what brings someone like you "
- 14.0 s, board, 7 calls, at the adventurers' guild house: "Excuse me, I'd like to take the contract to hunt four bandit captains "
- 13.8 s, move, 9 calls, at the south fields: "I think we should head back toward the town and reach the adventurers'"
- 11.1 s, move, 6 calls, at the adventurers' guild house: "Well, if we're going by your advice about the road, I think it's time "
- 10.6 s, talk, 5 calls, at the adventurers' guild house: ""Which of these contracts would you recommend as a starting point for "

Lines by what read them: interpret 56, hire 3, party 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 58 of 60 (97%) |
| Lines the model wrote | 54 (template 6; model failed 1, 51 s) |
| Lines picking up the passage before | 19 of 60 (32%); in talk 9 of 28 (32%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 3 / 4 (contract 0/1, go 3/0, revisit 0/3) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 10 of 60 (17%) |
| Places visited | 5 |

Turns by goal: idle 36, board 8, revisit 8, cont 5, go 2, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 2 (id 1, script 1) |
| Machinery mended at the screen | 9 (dash 4, stage 1, wrap 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("your party will hold back and come running if the alarm goes up. they ") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 8 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 6 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 17 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 1 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 6 | 0 | 0 | 1.8 | 58.1 | 701 | 277 | 1778 | 207.6 | 0 | 188 |
| npc_conversation | 38 | 2 | 2 | 2.6 | 3.5 | 5221 | 138 | 3941 | 114.3 | 0 | 125 |
| interpret_action | 59 | 0 | 0 | 1.1 | 1.5 | 4028 | 64 | 4959 | 207.5 | 0 | 70 |
| narrate | 19 | 2 | 2 | 2.6 | 3.1 | 2394 | 169 | 2360 | 113.3 | 0 | 53 |
| player_line | 55 | 22 | 23 | 0.6 | 0.8 | 537 | 28 | 1421 | 104.1 | 0 | 51 |
| dialogue_frame | 14 | 0 | 0 | 1.7 | 2.0 | 2098 | 68 | 1995 | 118.7 | 0 | 23 |
| hire_chat | 11 | 3 | 3 | 1.4 | 1.7 | 3090 | 55 | 2857 | 167.9 | 0 | 20 |
| exchange | 6 | 0 | 0 | 1.7 | 2.0 | 2835 | 100 | 2435 | 144.2 | 0 | 10 |
| persona_details | 3 | 0 | 0 | 2.0 | 2.1 | 824 | 254 | 1595 | 168.8 | 0 | 6 |
| audit_compare | 15 | 0 | 0 | 0.4 | 0.5 | 228 | 39 | 1344 | 218.2 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.4 | 5.4 | 1028 | 927 | 1412 | 197.8 | 0 | 5 |
| audit_meaning | 15 | 0 | 0 | 0.3 | 0.4 | 171 | 22 | 1029 | 117.7 | 0 | 5 |
| npc_profile | 5 | 0 | 0 | 0.9 | 1.2 | 612 | 84 | 1630 | 150.9 | 0 | 5 |
| overheard | 11 | 0 | 0 | 0.4 | 0.5 | 275 | 16 | 878 | 249.7 | 0 | 4 |
| canon_extract | 4 | 0 | 0 | 0.6 | 0.8 | 821 | 2 | 1505 | 197.8 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 1.9 | 1.9 | 888 | 247 | 1685 | 188.5 | 0 | 2 |
| work_offer_read | 1 | 0 | 0 | 0.5 | 0.5 | 167 | 19 | 582 | 105.6 | 0 | 0 |
| party_intent | 1 | 0 | 0 | 0.4 | 0.4 | 336 | 12 | 1124 | 134.8 | 0 | 0 |

294 attempts for 265 calls, 9.6 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 38 | 95% | 20939 | 22912 | 23860 | 108 | 5% |
| npc_profile | 5 | 100% | 2545 | 2704 | 2704 | 1480 | 0% |
| dialogue_frame | 14 | 100% | 8441 | 10227 | 10752 | 3027 | 0% |
| work_offer_read | 1 | 100% | 670 | 670 | 670 | 421 | 1% |
| hire_chat | 11 | 73% | 12157 | 13503 | 13503 | 1310 | 0% |
| canon_extract | 4 | 100% | 3334 | 3353 | 3353 | 702 | 0% |
| exchange | 6 | 100% | 11345 | 12308 | 12308 | 63 | 0% |
| overheard | 11 | 100% | 1107 | 1261 | 1261 | 213 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 38 | 95% | 95% | -1 | 22912 | 36345 | 36500 | 23860 | 5% |
| npc_profile | 5 | 100% | 100% | +0 | 2704 | 2774 | 3000 | 2704 | 0% |
| dialogue_frame | 14 | 100% | 86% | +14 | 10227 | 10715 | 11000 | 10752 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 670 | 780 | 1000 | 670 | 1% |
| hire_chat | 11 | 73% | 98% | -25 | 13503 | 16275 | 16500 | 13503 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 3353 | 3998 | 4000 | 3353 | 0% |
| exchange | 6 | 100% | 90% | +10 | 12308 | 15039 | 15500 | 12308 | 0% |
| overheard | 11 | 100% | 100% | +0 | 1261 | 1326 | 1500 | 1261 | 0% |

Size: 8 of 8 tasks at or below the baseline's p95; npc_conversation's p95 22912 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -25).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 59 | 242899 | 174536 (72%) | 192993 (79%) |
| npc_conversation | 40 | 211928 | 97847 (46%) | 18747 (9%) |
| narrate | 21 | 49387 | 30323 (61%) | 7132 (14%) |
| hire_chat | 14 | 41724 | 23175 (56%) | 8987 (22%) |
| player_line | 77 | 41298 | 10826 (26%) | 11764 (28%) |
| dialogue_frame | 14 | 29381 | 18826 (64%) | 14 (0%) |
| exchange | 6 | 16252 | 6729 (41%) | 6 (0%) |
| populate_place | 6 | 4282 | 1537 (36%) | 6 (0%) |
| audit_compare | 15 | 3449 | 1704 (49%) | 15 (0%) |
| canon_extract | 4 | 3284 | 2602 (79%) | 4 (0%) |
| npc_profile | 5 | 3088 | 1286 (42%) | 5 (0%) |
| overheard | 11 | 3083 | 2433 (79%) | 11 (0%) |
| audit_meaning | 15 | 2472 | 987 (40%) | 16 (1%) |
| persona_details | 3 | 2427 | 1093 (45%) | 347 (14%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 888 | 374 (42%) | 1 (0%) |
| party_intent | 1 | 336 | 260 (77%) | 1 (0%) |
| work_offer_read | 1 | 167 | 62 (37%) | 1 (1%) |

The prompts held 657373 tokens; the constant system messages were about 375092 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 240050 (37%) and read the rest.
The server's log: 294 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 850 checkpoints made, 254 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 3 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 3.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 3 | 1 |

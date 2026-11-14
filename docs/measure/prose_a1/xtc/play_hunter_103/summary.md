# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| wait | 21 | 3.0 | 6.5 | 3.0 | 4.5 | 3.5 | 3.4 | 9 | 0 |
| move | 18 | 3.6 | 8.2 | 3.2 | 5.8 | 5.4 | 4.2 | 2 | 0 |
| forage | 11 | 2.8 | 3.6 | 2.3 | 3.5 | 2.8 | 2.7 | 2 | 0 |
| look | 3 | 3.7 | 4.0 | 3.7 | 4.0 | 3.7 | 3.6 | 2 | 0 |
| board | 2 | 1.4 | 6.2 | 6.2 | 6.2 | 4.5 | 3.7 | 0 | 0 |
| talk | 1 | 4.2 | 4.2 | 4.2 | 4.2 | 2.0 | 4.1 | 0 | 0 |
| leave | 1 | 2.8 | 2.8 | 2.8 | 2.8 | 2.0 | 2.7 | 0 | 0 |
| improv | 1 | 3.0 | 3.0 | 3.0 | 3.0 | 5.0 | 3.0 | 0 | 0 |
| hire | 1 | 5.5 | 5.5 | 5.5 | 5.5 | 6.0 | 5.4 | 1 | 0 |
| search | 1 | 4.3 | 4.3 | 4.3 | 4.3 | 6.0 | 4.3 | 1 | 0 |

60 turns in 3.6 minutes; 98% of it in the model; 179 embedding calls taking 0.8 s; 0 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 14.7 s and p90 25.8 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 9.3 s, move, 8 calls, at the adventurers' guild house: "Alright, enough waiting in this drafty hall. Let's get moving to the T"
- 9.0 s, move, 10 calls, at the adventurers' guild house: "I stand up and motion toward the door, telling them we're heading to t"
- 8.2 s, move, 6 calls, at Parth: "I head toward the Adventurers' Guild House."
- 6.6 s, wait, 4 calls, at the adventurers' guild house: "I keep my eyes shut and just stay still, letting the silence settle."
- 6.5 s, wait, 6 calls, at the adventurers' guild house: "I lean back against the timber and close my eyes, waiting for some res"

Lines by what read them: interpret 59, hire 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 60 (template 0; model failed 0, 25 s) |
| Lines picking up the passage before | 6 of 60 (10%); in talk 1 of 1 (100%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 9 / 0 (contract 8/0, go 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 21 of 60 (35%) |
| Places visited | 6 |

Turns by goal: report 27, contract 15, idle 10, need 6, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 14 (id 10, escape 2, script 1, broken 1) |
| Machinery mended at the screen | 18 (dash 2, stage 1, wrap 15) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you look about for bram burwright, but nothing here goes by that name.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 14.3 |
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
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 16 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 1 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 60 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 0 / 0 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | not recorded on this night |
| Marks shown from acts (Remembered here) | 2 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.4 | 1.5 | 694 | 289 | 2796 | 216.4 | 0 | 134 |
| narrate | 54 | 12 | 12 | 1.5 | 1.9 | 2199 | 137 | 4652 | 133.4 | 0 | 98 |
| interpret_action | 65 | 0 | 0 | 0.6 | 0.9 | 3842 | 50 | 10011 | 227.2 | 0 | 41 |
| player_line | 60 | 15 | 15 | 0.3 | 0.4 | 492 | 23 | 2729 | 137.3 | 0 | 25 |
| dialogue_frame | 12 | 4 | 4 | 1.1 | 1.3 | 1910 | 80 | 4201 | 141.8 | 0 | 16 |
| hire_chat | 15 | 1 | 1 | 0.9 | 1.0 | 2436 | 56 | 4493 | 178.9 | 0 | 14 |
| exchange | 9 | 0 | 0 | 1.0 | 1.2 | 2716 | 71 | 4528 | 164.3 | 0 | 9 |
| npc_conversation | 3 | 0 | 0 | 3.0 | 3.3 | 4911 | 235 | 5905 | 111.5 | 0 | 8 |
| audit_compare | 21 | 0 | 0 | 0.3 | 0.3 | 219 | 39 | 2325 | 254.1 | 0 | 5 |
| audit_meaning | 21 | 0 | 0 | 0.2 | 0.2 | 159 | 22 | 1963 | 162.6 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.5 | 4.5 | 1093 | 959 | 3132 | 230.0 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.5 | 796 | 231 | 3457 | 187.7 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 2.9 | 2.9 | 970 | 544 | 3834 | 210.3 | 0 | 3 |
| overheard | 13 | 0 | 0 | 0.2 | 0.2 | 277 | 16 | 1954 | 295.0 | 0 | 3 |
| ruling | 3 | 0 | 0 | 0.7 | 0.7 | 1213 | 66 | 3834 | 189.1 | 0 | 2 |
| npc_profile | 1 | 0 | 0 | 0.6 | 0.6 | 611 | 78 | 3511 | 170.7 | 0 | 1 |
| canon_extract | 1 | 0 | 0 | 0.3 | 0.3 | 816 | 2 | 3213 | 153.8 | 0 | 0 |

322 attempts for 290 calls, 6.2 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 19557 | 19828 | 19828 | 84 | 0% |
| npc_profile | 1 | 100% | 2552 | 2552 | 2552 | 1487 | 0% |
| dialogue_frame | 12 | 67% | 7974 | 9270 | 9330 | 3500 | 0% |
| hire_chat | 15 | 93% | 9972 | 10593 | 12321 | 2127 | 0% |
| canon_extract | 1 | 100% | 3319 | 3319 | 3319 | 687 | 0% |
| exchange | 9 | 100% | 10916 | 11283 | 11283 | 67 | 0% |
| overheard | 13 | 100% | 1118 | 1154 | 1186 | 224 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 95% | +5 | 19828 | 36345 | 36500 | 19828 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2552 | 2774 | 3000 | 2552 | 0% |
| dialogue_frame | 12 | 67% | 86% | -19 | 9270 | 10715 | 11000 | 9330 | 0% |
| hire_chat | 15 | 93% | 98% | -4 | 10593 | 16275 | 16500 | 12321 | 0% |
| canon_extract | 1 | 100% | 100% | +0 | 3319 | 3998 | 4000 | 3319 | 0% |
| exchange | 9 | 100% | 90% | +10 | 11283 | 15039 | 15500 | 11283 | 0% |
| overheard | 13 | 100% | 100% | +0 | 1154 | 1326 | 1500 | 1186 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 19828 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 65 | 248354 | 190331 (77%) | 189444 (76%) |
| narrate | 66 | 144183 | 81968 (57%) | 39680 (28%) |
| hire_chat | 16 | 39365 | 22330 (57%) | 2428 (6%) |
| player_line | 75 | 36787 | 10750 (29%) | 7474 (20%) |
| dialogue_frame | 16 | 31251 | 17879 (57%) | 7415 (24%) |
| exchange | 9 | 23824 | 10201 (43%) | 0 (0%) |
| npc_conversation | 3 | 14673 | 6678 (46%) | 0 (0%) |
| populate_place | 7 | 4947 | 1791 (36%) | 0 (0%) |
| audit_compare | 21 | 4545 | 2466 (54%) | 0 (0%) |
| ruling | 3 | 3773 | 1738 (46%) | 0 (0%) |
| overheard | 13 | 3565 | 2870 (81%) | 0 (0%) |
| audit_meaning | 21 | 3361 | 1481 (44%) | 0 (0%) |
| persona_details | 3 | 2389 | 1082 (45%) | 345 (14%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| board_stakes | 1 | 970 | 384 (40%) | 0 (0%) |
| canon_extract | 1 | 816 | 647 (79%) | 0 (0%) |
| npc_profile | 1 | 611 | 255 (42%) | 0 (0%) |

The prompts held 564507 tokens; the constant system messages were about 353340 of them (63%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 246786 (44%) and read the rest.
The server's log: 322 prompts; 215 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 796 checkpoints made, 52 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 1 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

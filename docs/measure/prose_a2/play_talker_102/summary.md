# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.1 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 30 | 4.3 | 6.4 | 4.2 | 6.0 | 2.5 | 4.5 | 1 | 0 |
| leave | 9 | 5.2 | 7.9 | 4.6 | 5.2 | 4.2 | 5.6 | 2 | 0 |
| forage | 9 | 3.9 | 6.6 | 3.6 | 4.4 | 3.7 | 4.5 | 0 | 0 |
| move | 7 | 5.0 | 9.6 | 5.0 | 8.3 | 4.7 | 6.1 | 0 | 0 |
| board | 2 | 7.1 | 7.5 | 7.1 | 7.5 | 6.0 | 7.1 | 0 | 0 |
| look | 2 | 4.4 | 7.0 | 4.4 | 5.0 | 5.0 | 5.6 | 0 | 0 |
| wait | 1 | 6.1 | 6.1 | 6.1 | 6.1 | 2.0 | 3.1 | 0 | 0 |

60 turns in 5.1 minutes; 96% of it in the model; 236 embedding calls taking 2.4 s; 0 calls on background threads.
The budget: 2 optional calls deferred and 2 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 17.6 s and p90 24.5 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.9 s, move, 6 calls, at the south fields: "I stand up and tell the others that we should head toward the adventur"
- 9.7 s, leave, 8 calls, at the adventurers' guild house: "I nod my thanks to the ink-stained girl and turn to my companions. "We"
- 9.6 s, move, 6 calls, at the trading square: "Let's make our way over to the Tilted Plough first."
- 9.2 s, talk, 6 calls, at the adventurers' guild house: ""You can count on that," I tell her before looking around at the other"
- 8.3 s, move, 8 calls, at the trading square: "I turn to the group and suggest we head toward the watch tower next."

Lines by what read them: interpret 58, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 54 (template 6; model failed 1, 41 s) |
| Lines picking up the passage before | 24 of 60 (40%); in talk 12 of 30 (40%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 3 / 1 (contract 0/1, go 2/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 1 of 60 (2%) |
| Places visited | 4 |

Turns by goal: idle 38, contract 13, cont 4, board 3, go 1, revisit 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 0 |
| Machinery mended at the screen | 19 (dash 13, stage 1, wrap 5) |
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
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 10 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 11; townsfolk 0 of 1 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 4 / 1 / 0 / 0 (planted 1, set straight 1) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 4 | 0 | 0 | 1.7 | 125.5 | 673 | 249 | 1344 | 131.4 | 0 | 130 |
| npc_conversation | 40 | 2 | 2 | 2.6 | 3.4 | 5631 | 158 | 4224 | 120.4 | 0 | 115 |
| interpret_action | 64 | 0 | 0 | 1.2 | 1.4 | 4149 | 60 | 5167 | 216.7 | 0 | 73 |
| narrate | 25 | 0 | 0 | 1.9 | 2.6 | 2076 | 111 | 2445 | 117.4 | 0 | 48 |
| player_line | 55 | 12 | 13 | 0.6 | 0.7 | 522 | 28 | 1500 | 106.7 | 0 | 40 |
| hire_chat | 10 | 1 | 1 | 1.3 | 1.5 | 2702 | 51 | 2652 | 156.1 | 0 | 16 |
| dialogue_frame | 9 | 0 | 0 | 1.5 | 1.6 | 2082 | 51 | 2149 | 119.3 | 0 | 13 |
| audit_compare | 16 | 0 | 0 | 0.4 | 0.4 | 227 | 42 | 1427 | 220.9 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.9 | 2.0 | 811 | 243 | 1848 | 169.3 | 0 | 6 |
| audit_meaning | 16 | 0 | 0 | 0.3 | 0.4 | 168 | 22 | 1113 | 122.1 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.8 | 4.8 | 1028 | 908 | 1532 | 222.0 | 0 | 5 |
| exchange | 2 | 0 | 0 | 1.9 | 2.1 | 2739 | 120 | 2576 | 131.3 | 0 | 4 |
| overheard | 8 | 0 | 0 | 0.4 | 0.4 | 276 | 16 | 969 | 267.8 | 0 | 3 |
| npc_profile | 3 | 0 | 0 | 0.9 | 1.0 | 621 | 89 | 1830 | 155.2 | 0 | 3 |
| canon_extract | 2 | 0 | 0 | 0.6 | 0.6 | 916 | 6 | 1600 | 179.1 | 0 | 1 |
| board_stakes | 1 | 0 | 0 | 1.0 | 1.0 | 887 | 95 | 1743 | 185.2 | 0 | 1 |
| party_intent | 1 | 0 | 0 | 0.3 | 0.3 | 323 | 12 | 1392 | 157.9 | 0 | 0 |

275 attempts for 260 calls, 7.8 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 40 | 95% | 22640 | 24297 | 24868 | 116 | 4% |
| npc_profile | 3 | 100% | 2534 | 2700 | 2700 | 1469 | 0% |
| dialogue_frame | 9 | 100% | 8740 | 9667 | 9667 | 3609 | 0% |
| hire_chat | 10 | 90% | 10883 | 12474 | 12474 | 1282 | 6% |
| canon_extract | 2 | 100% | 3407 | 4129 | 4129 | 775 | 0% |
| exchange | 2 | 100% | 10963 | 11296 | 11296 | 63 | 0% |
| overheard | 8 | 100% | 1124 | 1272 | 1272 | 230 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 40 | 95% | 95% | +0 | 24297 | 36345 | 36500 | 24868 | 4% |
| npc_profile | 3 | 100% | 100% | +0 | 2700 | 2774 | 3000 | 2700 | 0% |
| dialogue_frame | 9 | 100% | 86% | +14 | 9667 | 10715 | 11000 | 9667 | 0% |
| hire_chat | 10 | 90% | 98% | -8 | 12474 | 16275 | 16500 | 12474 | 6% |
| canon_extract | 2 | 100% | 100% | +0 | 4129 | 3998 | 4000 | 4129 | 0% |
| exchange | 2 | 100% | 90% | +10 | 11296 | 15039 | 15500 | 11296 | 0% |
| overheard | 8 | 100% | 100% | +0 | 1272 | 1326 | 1500 | 1272 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 24297 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -8).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 64 | 263905 | 188632 (71%) | 197706 (75%) |
| npc_conversation | 42 | 232346 | 102489 (44%) | 21223 (9%) |
| narrate | 25 | 51166 | 33678 (66%) | 10337 (20%) |
| player_line | 67 | 35320 | 9346 (26%) | 6487 (18%) |
| hire_chat | 11 | 29932 | 17878 (60%) | 4229 (14%) |
| dialogue_frame | 9 | 18937 | 11992 (63%) | 8 (0%) |
| exchange | 2 | 5479 | 2255 (41%) | 2 (0%) |
| audit_compare | 16 | 3717 | 1840 (49%) | 16 (0%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| audit_meaning | 16 | 2679 | 1075 (40%) | 16 (1%) |
| persona_details | 3 | 2404 | 1090 (45%) | 347 (14%) |
| overheard | 8 | 2238 | 1757 (79%) | 7 (0%) |
| npc_profile | 3 | 1881 | 777 (41%) | 3 (0%) |
| canon_extract | 2 | 1832 | 1281 (70%) | 1 (0%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 887 | 373 (42%) | 1 (0%) |
| party_intent | 1 | 323 | 256 (79%) | 1 (0%) |

The prompts held 656768 tokens; the constant system messages were about 376229 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 240388 (37%) and read the rest.
The server's log: 275 prompts; 5 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 783 checkpoints made, 232 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 2 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 2.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 24 | 5.1 | 8.0 | 4.3 | 5.5 | 5.8 | 4.5 | 3 | 0 |
| wait | 21 | 2.7 | 4.9 | 2.6 | 3.7 | 3.7 | 3.2 | 4 | 0 |
| forage | 6 | 1.5 | 2.0 | 1.5 | 2.0 | 2.3 | 1.7 | 0 | 0 |
| search | 2 | 2.5 | 3.7 | 2.5 | 3.7 | 3.5 | 3.1 | 0 | 0 |
| board | 1 | 8.1 | 8.1 | 8.1 | 8.1 | 5.0 | 8.0 | 0 | 0 |
| talk | 1 | 3.3 | 3.3 | 3.3 | 3.3 | 4.0 | 3.2 | 0 | 0 |
| leave | 1 | 8.1 | 8.1 | 4.3 | 4.3 | 8.0 | 7.9 | 1 | 0 |
| look | 1 | 2.9 | 2.9 | 2.9 | 2.9 | 5.0 | 2.8 | 0 | 0 |
| hire | 1 | 4.8 | 4.8 | 4.8 | 4.8 | 6.0 | 4.7 | 1 | 0 |
| rest | 1 | 7.7 | 7.7 | 6.0 | 6.0 | 9.0 | 7.6 | 1 | 0 |
| improv | 1 | 3.2 | 3.2 | 3.2 | 3.2 | 5.0 | 3.2 | 0 | 0 |

60 turns in 3.9 minutes; 98% of it in the model; 258 embedding calls taking 1.0 s; 0 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 13.2 s and p90 22.9 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 8.2 s, move, 10 calls, at the south fields: "We've got enough; let's get back to the Adventurers' Guild House."
- 8.1 s, board, 5 calls, at the adventurers' guild house: "Hey, I'm taking that 'Gather 4 wild garlic' contract off the board."
- 8.1 s, leave, 8 calls, at the adventurers' guild house: "I turn away from the table and head for the door."
- 8.0 s, move, 9 calls, at the adventurers' guild house: "I push off the wall and tell everyone we're heading to the Tilted Plou"
- 8.0 s, move, 6 calls, at Parth: "I head straight for the adventurers' guild house."

Lines by what read them: interpret 56, hire 4

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 59 (template 1; model failed 0, 24 s) |
| Lines picking up the passage before | 7 of 60 (12%); in talk 0 of 1 (0%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 8 / 0 (contract 7/0, go 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 21 of 60 (35%) |
| Places visited | 5 |

Turns by goal: report 30, need 11, idle 9, contract 8, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 4, escape 2, script 1) |
| Machinery mended at the screen | 8 (dash 1, stage 2, wrap 5) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you have nothing like that you can use.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 1 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 3 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 2 |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 6 times; 0 of the game's 10 own lines (0%); most: "You are back at the adventurers' guild house." x6 |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 0 (e.g. turn 46 ['drink']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 57 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | no false name given on this night |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 6 | 0 | 0 | 1.4 | 1.5 | 700 | 292 | 2779 | 201.2 | 0 | 132 |
| narrate | 43 | 5 | 5 | 1.5 | 1.9 | 2224 | 130 | 4406 | 134.2 | 0 | 69 |
| interpret_action | 63 | 0 | 0 | 0.7 | 0.9 | 3962 | 52 | 9513 | 224.5 | 0 | 43 |
| dialogue_frame | 24 | 3 | 3 | 1.1 | 1.2 | 1952 | 84 | 3874 | 146.1 | 0 | 29 |
| player_line | 59 | 10 | 10 | 0.3 | 0.4 | 508 | 21 | 2838 | 133.1 | 0 | 24 |
| exchange | 20 | 0 | 0 | 1.1 | 1.3 | 2832 | 84 | 4681 | 167.2 | 0 | 23 |
| hire_chat | 22 | 2 | 2 | 0.9 | 1.0 | 2605 | 57 | 4794 | 193.1 | 0 | 21 |
| npc_conversation | 3 | 0 | 0 | 2.0 | 6.0 | 4818 | 159 | 5873 | 101.8 | 0 | 10 |
| audit_compare | 27 | 0 | 0 | 0.2 | 0.3 | 211 | 39 | 2394 | 253.7 | 0 | 7 |
| audit_meaning | 27 | 0 | 0 | 0.2 | 0.2 | 158 | 20 | 1957 | 164.0 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.5 | 796 | 231 | 3447 | 187.3 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.1 | 4.1 | 1093 | 895 | 3123 | 237.9 | 0 | 4 |
| overheard | 19 | 0 | 0 | 0.2 | 0.2 | 276 | 16 | 1964 | 296.0 | 0 | 4 |
| ruling | 4 | 0 | 0 | 0.8 | 1.0 | 1157 | 96 | 3757 | 214.0 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.2 | 2.2 | 965 | 398 | 3814 | 201.3 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1358 | 228 | 3690 | 153.5 | 0 | 2 |
| canon_extract | 6 | 0 | 0 | 0.3 | 0.3 | 819 | 2 | 3137 | 175.8 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.7 | 628 | 91 | 3434 | 183.8 | 0 | 1 |

351 attempts for 331 calls, 6.4 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 19355 | 19828 | 19828 | 79 | 0% |
| npc_profile | 2 | 100% | 2552 | 2675 | 2675 | 1487 | 0% |
| dialogue_frame | 24 | 88% | 8083 | 9017 | 9839 | 3526 | 0% |
| hire_chat | 22 | 91% | 10618 | 12439 | 12885 | 1837 | 0% |
| canon_extract | 6 | 100% | 3283 | 4089 | 4089 | 651 | 0% |
| exchange | 20 | 100% | 11400 | 12191 | 12282 | 63 | 0% |
| overheard | 19 | 100% | 1119 | 1173 | 1184 | 225 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 95% | +5 | 19828 | 36345 | 36500 | 19828 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2675 | 2774 | 3000 | 2675 | 0% |
| dialogue_frame | 24 | 88% | 86% | +1 | 9017 | 10715 | 11000 | 9839 | 0% |
| hire_chat | 22 | 91% | 98% | -7 | 12439 | 16275 | 16500 | 12885 | 0% |
| canon_extract | 6 | 100% | 100% | +0 | 4089 | 3998 | 4000 | 4089 | 0% |
| exchange | 20 | 100% | 90% | +10 | 12191 | 15039 | 15500 | 12282 | 0% |
| overheard | 19 | 100% | 100% | +0 | 1173 | 1326 | 1500 | 1184 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 19828 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -7).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 63 | 248856 | 185289 (74%) | 181617 (73%) |
| narrate | 48 | 107517 | 60326 (56%) | 16143 (15%) |
| hire_chat | 24 | 64624 | 33841 (52%) | 5549 (9%) |
| exchange | 20 | 56565 | 22709 (40%) | 0 (0%) |
| dialogue_frame | 27 | 53316 | 29805 (56%) | 5898 (11%) |
| player_line | 69 | 35104 | 9910 (28%) | 5527 (16%) |
| npc_conversation | 3 | 14594 | 6644 (46%) | 0 (0%) |
| audit_compare | 27 | 5768 | 3168 (55%) | 0 (0%) |
| overheard | 19 | 5236 | 4209 (80%) | 0 (0%) |
| canon_extract | 6 | 5088 | 3902 (77%) | 0 (0%) |
| ruling | 4 | 4644 | 2346 (51%) | 0 (0%) |
| audit_meaning | 27 | 4356 | 1880 (43%) | 0 (0%) |
| populate_place | 6 | 4277 | 1535 (36%) | 0 (0%) |
| persona_details | 3 | 2389 | 1082 (45%) | 345 (14%) |
| moment | 1 | 1358 | 753 (55%) | 0 (0%) |
| npc_profile | 2 | 1257 | 512 (41%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| board_stakes | 1 | 965 | 384 (40%) | 0 (0%) |

The prompts held 617007 tokens; the constant system messages were about 368784 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 215079 (35%) and read the rest.
The server's log: 351 prompts; 264 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 871 checkpoints made, 53 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 1 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 1.00 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 1 | 1 |

# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 24 | 4.3 | 8.5 | 4.2 | 6.2 | 5.3 | 4.4 | 6 | 0 |
| wait | 19 | 3.1 | 5.8 | 3.0 | 5.0 | 3.5 | 3.8 | 4 | 0 |
| forage | 6 | 1.8 | 1.9 | 1.8 | 1.9 | 2.3 | 1.9 | 0 | 0 |
| talk | 2 | 3.0 | 5.0 | 3.0 | 5.0 | 4.5 | 4.0 | 1 | 0 |
| leave | 2 | 2.0 | 3.4 | 1.9 | 3.4 | 2.5 | 2.6 | 0 | 0 |
| search | 2 | 2.5 | 4.9 | 2.5 | 4.9 | 2.5 | 3.6 | 0 | 0 |
| hire | 2 | 1.2 | 4.8 | 1.2 | 3.6 | 5.0 | 2.9 | 0 | 0 |
| board | 1 | 5.5 | 5.5 | 5.5 | 5.5 | 6.0 | 5.4 | 0 | 0 |
| look | 1 | 2.7 | 2.7 | 2.7 | 2.7 | 5.0 | 2.6 | 0 | 0 |
| rest | 1 | 2.1 | 2.1 | 2.1 | 2.1 | 2.0 | 2.0 | 0 | 0 |

60 turns in 3.8 minutes; 98% of it in the model; 200 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 13.9 s and p90 24.0 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.1 s, move, 10 calls, at the adventurers' guild house: "Let's get to the Temple of Parth before it gets any later."
- 9.5 s, wait, 8 calls, at the adventurers' guild house: "I lean back against the pillar and keep my eyes on the board, waiting."
- 9.5 s, move, 12 calls, at the south fields: "We've got enough; let's head back to the Adventurers' Guild House."
- 8.5 s, move, 6 calls, at Parth: "I head straight for the adventurers' guild house."
- 8.1 s, move, 7 calls, at the adventurers' guild house: "Time to get moving. Let's head to the Tilted Plough."

Lines by what read them: interpret 58, hire 2

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 60 (template 0; model failed 0, 24 s) |
| Lines picking up the passage before | 7 of 60 (12%); in talk 1 of 2 (50%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 9 / 0 (contract 7/0, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 19 of 60 (32%) |
| Places visited | 6 |

Turns by goal: report 30, need 11, idle 9, contract 8, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 3, script 2, json 2) |
| Machinery mended at the screen | 15 (dash 5, stage 1, wrap 9) |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 9 times; 0 of the game's 7 own lines (0%); most: "You are back at the adventurers' guild house." x9 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 1 / 0 / 0 (e.g. '*') |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 1 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 51 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 0 / 0 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | not recorded on this night |
| Marks shown from acts (Remembered here) | 1 |
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
| populate_place | 7 | 0 | 0 | 1.4 | 1.5 | 694 | 289 | 2715 | 203.4 | 0 | 134 |
| narrate | 46 | 5 | 6 | 1.7 | 2.3 | 2312 | 150 | 4723 | 127.3 | 0 | 89 |
| interpret_action | 63 | 0 | 0 | 0.7 | 0.9 | 3973 | 53 | 9774 | 225.7 | 0 | 42 |
| dialogue_frame | 20 | 4 | 4 | 1.1 | 1.2 | 1980 | 78 | 4129 | 142.2 | 0 | 24 |
| player_line | 60 | 12 | 12 | 0.3 | 0.4 | 516 | 22 | 2835 | 135.6 | 0 | 24 |
| hire_chat | 17 | 2 | 2 | 0.9 | 1.0 | 2516 | 57 | 4718 | 180.2 | 0 | 17 |
| exchange | 14 | 0 | 0 | 1.1 | 1.3 | 2784 | 94 | 4633 | 172.2 | 0 | 16 |
| npc_conversation | 4 | 0 | 0 | 2.0 | 2.5 | 4841 | 164 | 5927 | 135.6 | 0 | 8 |
| audit_compare | 22 | 0 | 0 | 0.2 | 0.3 | 216 | 37 | 2321 | 268.2 | 0 | 5 |
| audit_meaning | 22 | 0 | 0 | 0.2 | 0.2 | 158 | 20 | 1920 | 164.6 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.5 | 796 | 231 | 3437 | 187.8 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.1 | 4.1 | 1093 | 909 | 3168 | 241.8 | 0 | 4 |
| overheard | 15 | 0 | 0 | 0.2 | 0.2 | 285 | 16 | 1856 | 298.7 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.2 | 2.2 | 965 | 398 | 3770 | 201.5 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1358 | 228 | 3670 | 153.5 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.7 | 611 | 86 | 3484 | 175.3 | 0 | 1 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.3 | 946 | 2 | 3327 | 153.8 | 0 | 1 |
| ruling | 1 | 0 | 0 | 0.7 | 0.7 | 1206 | 70 | 3745 | 187.7 | 0 | 1 |

325 attempts for 302 calls, 6.4 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 4 | 100% | 19412 | 19709 | 19709 | 56 | 0% |
| npc_profile | 2 | 100% | 2535 | 2552 | 2552 | 1470 | 0% |
| dialogue_frame | 20 | 85% | 8069 | 9809 | 10526 | 3606 | 0% |
| hire_chat | 17 | 88% | 10257 | 12282 | 12289 | 2068 | 0% |
| canon_extract | 3 | 100% | 3895 | 4259 | 4259 | 1263 | 0% |
| exchange | 14 | 100% | 11185 | 11897 | 12214 | 63 | 0% |
| overheard | 15 | 100% | 1134 | 1166 | 1175 | 240 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 4 | 100% | 95% | +5 | 19709 | 36345 | 36500 | 19709 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2552 | 2774 | 3000 | 2552 | 0% |
| dialogue_frame | 20 | 85% | 86% | -1 | 9809 | 10715 | 11000 | 10526 | 0% |
| hire_chat | 17 | 88% | 98% | -10 | 12282 | 16275 | 16500 | 12289 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4259 | 3998 | 4000 | 4259 | 0% |
| exchange | 14 | 100% | 90% | +10 | 11897 | 15039 | 15500 | 12214 | 0% |
| overheard | 15 | 100% | 100% | +0 | 1166 | 1326 | 1500 | 1175 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 19709 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -10).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 63 | 248712 | 185104 (74%) | 182664 (73%) |
| narrate | 51 | 120709 | 63196 (52%) | 25277 (21%) |
| hire_chat | 19 | 49587 | 26723 (54%) | 5081 (10%) |
| dialogue_frame | 24 | 47981 | 27405 (57%) | 8224 (17%) |
| exchange | 14 | 39325 | 15917 (40%) | 11 (0%) |
| player_line | 72 | 36734 | 10339 (28%) | 7101 (19%) |
| npc_conversation | 4 | 19434 | 8901 (46%) | 0 (0%) |
| populate_place | 7 | 4900 | 1788 (36%) | 1 (0%) |
| audit_compare | 22 | 4759 | 2578 (54%) | 12 (0%) |
| overheard | 15 | 4178 | 3320 (79%) | 13 (0%) |
| audit_meaning | 22 | 3508 | 1537 (44%) | 12 (0%) |
| canon_extract | 3 | 2785 | 1918 (69%) | 1 (0%) |
| persona_details | 3 | 2389 | 1082 (45%) | 345 (14%) |
| moment | 1 | 1358 | 753 (55%) | 0 (0%) |
| npc_profile | 2 | 1223 | 512 (42%) | 0 (0%) |
| ruling | 1 | 1206 | 577 (48%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| board_stakes | 1 | 965 | 384 (40%) | 0 (0%) |

The prompts held 590846 tokens; the constant system messages were about 352523 of them (60%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 228742 (39%) and read the rest.
The server's log: 325 prompts; 106 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 872 checkpoints made, 181 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 1 |

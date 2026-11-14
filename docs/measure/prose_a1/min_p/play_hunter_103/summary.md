# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 24 | 2.8 | 8.4 | 2.3 | 5.2 | 4.0 | 3.5 | 6 | 1 |
| wait | 18 | 2.6 | 5.6 | 2.6 | 4.0 | 3.6 | 3.4 | 3 | 0 |
| forage | 7 | 1.7 | 2.1 | 1.7 | 2.1 | 2.1 | 1.8 | 0 | 0 |
| board | 4 | 2.7 | 5.5 | 2.7 | 5.5 | 5.0 | 3.2 | 2 | 0 |
| look | 4 | 3.3 | 4.9 | 3.3 | 4.9 | 4.2 | 3.2 | 0 | 0 |
| talk | 1 | 8.3 | 8.3 | 5.9 | 5.9 | 6.0 | 8.2 | 0 | 0 |
| leave | 1 | 7.0 | 7.0 | 4.3 | 4.3 | 7.0 | 6.9 | 0 | 0 |
| improv | 1 | 3.4 | 3.4 | 3.3 | 3.3 | 5.0 | 3.3 | 0 | 0 |

60 turns in 3.4 minutes; 98% of it in the model; 193 embedding calls taking 0.9 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 0 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 12.2 s and p90 24.2 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 9.0 s, move, 10 calls, at the adventurers' guild house: "Forget the grain talk; I'm headed to the Tilted Plough to get a drink."
- 8.6 s, move, 12 calls, at the Tilted Plough: "I turn to the group and head toward the adventurers' guild house."
- 8.4 s, move, 6 calls, at Parth: "I head straight for the adventurers' guild house."
- 8.4 s, wait, 6 calls, at the adventurers' guild house: "I lean back against the wall and wait for someone else to make the fir"
- 8.3 s, talk, 6 calls, at the adventurers' guild house: "I grab the paper and look him in the eye. Who among these people can I"

Lines by what read them: interpret 56, hire 3, unrecorded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 60 (template 0; model failed 0, 24 s) |
| Lines picking up the passage before | 4 of 60 (7%); in talk 0 of 1 (0%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 7 / 0 (contract 6/0, go 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 18 of 60 (30%) |
| Places visited | 6 |

Turns by goal: report 29, contract 10, idle 9, need 8, board 2, clarify 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 2 (id 2) |
| Machinery mended at the screen | 8 (dash 3, stage 1, wrap 4) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("gunga balkald - dwarf priest, rank f, level #: a wandering healer of t") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 14.3 |
| Parts made different by an attempt (blocked, lit, cleared...) | 1 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 8 times; 0 of the game's 36 own lines (0%); most: "You are back at the adventurers' guild house." x8 |
| Refusals shown / then acted out in the passage / never logged | 2 / 2 / 1 (e.g. turn 29 ['against', 'pillar']; 33 ['plough', 'tilted']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 47 |
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
| populate_place | 7 | 0 | 0 | 1.3 | 1.5 | 694 | 289 | 2896 | 196.5 | 0 | 133 |
| narrate | 46 | 1 | 1 | 1.6 | 2.0 | 2194 | 141 | 4488 | 136.6 | 0 | 73 |
| interpret_action | 62 | 0 | 0 | 0.7 | 0.9 | 3923 | 49 | 8910 | 227.3 | 0 | 44 |
| player_line | 60 | 15 | 15 | 0.3 | 0.4 | 489 | 22 | 2811 | 135.5 | 0 | 24 |
| dialogue_frame | 17 | 6 | 6 | 1.0 | 1.3 | 2017 | 71 | 4420 | 145.0 | 0 | 22 |
| hire_chat | 14 | 2 | 2 | 0.9 | 1.0 | 2493 | 60 | 4744 | 186.7 | 0 | 14 |
| exchange | 12 | 1 | 1 | 1.1 | 1.2 | 2788 | 82 | 4687 | 166.2 | 0 | 14 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.5 | 796 | 231 | 3428 | 187.6 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1093 | 933 | 3150 | 230.2 | 0 | 4 |
| board_stakes | 2 | 0 | 0 | 1.5 | 2.9 | 1094 | 399 | 3852 | 209.2 | 0 | 4 |
| audit_compare | 18 | 0 | 0 | 0.2 | 0.3 | 209 | 38 | 2385 | 267.9 | 0 | 4 |
| audit_meaning | 18 | 0 | 0 | 0.2 | 0.2 | 159 | 21 | 1857 | 168.1 | 0 | 4 |
| npc_conversation | 2 | 0 | 0 | 1.7 | 1.9 | 4915 | 144 | 5922 | 154.0 | 0 | 4 |
| ruling | 3 | 0 | 0 | 0.7 | 1.0 | 1164 | 66 | 3688 | 216.3 | 0 | 2 |
| overheard | 10 | 0 | 0 | 0.2 | 0.2 | 279 | 16 | 1856 | 289.3 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.8 | 1.8 | 1352 | 238 | 3704 | 167.4 | 0 | 2 |
| canon_extract | 4 | 0 | 0 | 0.3 | 0.3 | 831 | 2 | 3232 | 153.8 | 0 | 1 |
| clarify | 2 | 1 | 1 | 0.3 | 0.3 | 263 | 34 | 2399 | 188.1 | 0 | 1 |
| npc_profile | 1 | 0 | 0 | 0.6 | 0.6 | 611 | 78 | 3452 | 170.7 | 0 | 1 |

309 attempts for 283 calls, 6.0 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 2 | 100% | 19325 | 19817 | 19817 | 62 | 0% |
| npc_profile | 1 | 100% | 2552 | 2552 | 2552 | 1487 | 0% |
| dialogue_frame | 17 | 65% | 8486 | 9697 | 9829 | 3757 | 7% |
| hire_chat | 14 | 86% | 9877 | 12472 | 12485 | 2121 | 0% |
| canon_extract | 4 | 100% | 3445 | 3466 | 3466 | 813 | 0% |
| exchange | 12 | 92% | 11187 | 11460 | 11513 | 63 | 0% |
| overheard | 10 | 100% | 1122 | 1196 | 1196 | 228 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 2 | 100% | 95% | +5 | 19817 | 36345 | 36500 | 19817 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2552 | 2774 | 3000 | 2552 | 0% |
| dialogue_frame | 17 | 65% | 86% | -21 | 9697 | 10715 | 11000 | 9829 | 7% |
| hire_chat | 14 | 86% | 98% | -12 | 12472 | 16275 | 16500 | 12485 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 3466 | 3998 | 4000 | 3466 | 0% |
| exchange | 12 | 92% | 90% | +2 | 11460 | 15039 | 15500 | 11513 | 0% |
| overheard | 10 | 100% | 100% | +0 | 1196 | 1326 | 1500 | 1196 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 19817 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -12).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 62 | 243213 | 182141 (75%) | 174600 (72%) |
| narrate | 47 | 103971 | 58641 (56%) | 17383 (17%) |
| dialogue_frame | 23 | 46833 | 26068 (56%) | 14048 (30%) |
| hire_chat | 16 | 42303 | 22616 (53%) | 4767 (11%) |
| player_line | 75 | 37563 | 10809 (29%) | 8801 (23%) |
| exchange | 13 | 35409 | 14781 (42%) | 2732 (8%) |
| npc_conversation | 2 | 9831 | 4449 (45%) | 0 (0%) |
| populate_place | 7 | 4900 | 1788 (36%) | 0 (0%) |
| audit_compare | 18 | 3849 | 2092 (54%) | 0 (0%) |
| ruling | 3 | 3518 | 1750 (50%) | 0 (0%) |
| canon_extract | 4 | 3313 | 2591 (78%) | 0 (0%) |
| audit_meaning | 18 | 2895 | 1249 (43%) | 0 (0%) |
| overheard | 10 | 2797 | 2213 (79%) | 0 (0%) |
| persona_details | 3 | 2389 | 1082 (45%) | 345 (14%) |
| board_stakes | 2 | 2188 | 778 (36%) | 0 (0%) |
| moment | 1 | 1352 | 752 (56%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| clarify | 3 | 830 | 494 (59%) | 258 (31%) |
| npc_profile | 1 | 611 | 255 (42%) | 0 (0%) |

The prompts held 548858 tokens; the constant system messages were about 335038 of them (61%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 222934 (41%) and read the rest.
The server's log: 309 prompts; 203 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 786 checkpoints made, 70 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 1 |

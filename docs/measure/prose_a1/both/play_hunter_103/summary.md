# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 25 | 3.5 | 6.5 | 3.3 | 6.1 | 4.4 | 3.6 | 6 | 0 |
| wait | 15 | 2.7 | 5.6 | 2.7 | 3.9 | 3.9 | 3.1 | 0 | 0 |
| forage | 9 | 3.0 | 3.4 | 2.8 | 3.4 | 3.4 | 2.8 | 1 | 0 |
| talk | 4 | 2.7 | 4.1 | 2.7 | 4.1 | 3.0 | 2.7 | 0 | 0 |
| leave | 3 | 5.1 | 8.0 | 3.5 | 5.1 | 4.0 | 5.1 | 1 | 0 |
| board | 2 | 4.5 | 6.0 | 4.5 | 6.0 | 6.5 | 5.2 | 1 | 0 |
| look | 2 | 2.0 | 2.3 | 2.0 | 2.3 | 3.0 | 2.2 | 0 | 0 |

60 turns in 3.4 minutes; 98% of it in the model; 221 embedding calls taking 1.0 s; 0 calls on background threads.
The budget: 1 optional calls deferred and 2 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 12.4 s and p90 22.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.4 s, move, 12 calls, at the south fields: "I signal the group and head toward the Adventurers' Guild House."
- 8.0 s, move, 6 calls, at Parth: "I go to the adventurers' guild house to see what work the board has."
- 8.0 s, leave, 8 calls, at the adventurers' guild house: "I turn away from the group and head for the exit."
- 7.3 s, wait, 8 calls, at the adventurers' guild house: "I sit back down on my bench and lean against the wall, waiting for som"
- 6.5 s, move, 8 calls, at the adventurers' guild house: "We aren't heading to the clerk yet; let's hit the Tilted Plough first."

Lines by what read them: interpret 56, hire 4

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 58 (template 2; model failed 1, 24 s) |
| Lines picking up the passage before | 4 of 60 (7%); in talk 1 of 4 (25%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 7 / 1 (contract 5/0, go 1/0, report 1/0, revisit 0/1) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 15 of 60 (25%) |
| Places visited | 6 |

Turns by goal: report 26, contract 12, idle 9, need 5, revisit 5, board 2, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 7 (id 5, script 1, broken 1) |
| Machinery mended at the screen | 16 (stage 3, wrap 13) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("there's no item box here.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 3 / 3 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 3 |
| ...said no to, about someone in the party (likely a misread) | 1 |
| Additions to the world per hour | 42.9 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 2 (Gharta Kulgarth in narrate 1; Gwild Coleford in dialogue_frame 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 2 lines, 14 times; 0 of the game's 15 own lines (0%); most: "You are back at the adventurers' guild house." x8; 'You are back at the Tilted Plough.' x6 |
| Refusals shown / then acted out in the passage / never logged | 2 / 2 / 0 (e.g. turn 10 ['silverleaf', 'stand']; 60 ['against', 'pillar', 'waiting']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 1 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 2 of 60; townsfolk 0 of 1 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 0 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| populate_place | 7 | 0 | 0 | 1.5 | 1.5 | 694 | 295 | 2735 | 206.6 | 0 | 133 |
| narrate | 39 | 3 | 3 | 1.4 | 1.9 | 2148 | 115 | 4195 | 121.5 | 0 | 63 |
| interpret_action | 59 | 0 | 0 | 0.7 | 0.9 | 3879 | 58 | 9387 | 232.6 | 0 | 40 |
| player_line | 59 | 8 | 9 | 0.3 | 0.4 | 478 | 22 | 2793 | 135.9 | 0 | 24 |
| dialogue_frame | 16 | 4 | 4 | 1.1 | 1.3 | 1973 | 78 | 4067 | 134.9 | 0 | 21 |
| hire_chat | 16 | 2 | 2 | 0.9 | 1.0 | 2753 | 57 | 4902 | 180.3 | 0 | 16 |
| npc_conversation | 7 | 0 | 0 | 1.8 | 2.0 | 4901 | 125 | 6099 | 121.5 | 0 | 15 |
| exchange | 12 | 0 | 0 | 1.1 | 1.9 | 2720 | 74 | 4391 | 161.8 | 0 | 15 |
| audit_compare | 26 | 0 | 0 | 0.2 | 0.3 | 207 | 37 | 2289 | 260.6 | 0 | 6 |
| audit_meaning | 26 | 0 | 0 | 0.2 | 0.2 | 158 | 21 | 1926 | 164.5 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.4 | 4.4 | 1093 | 939 | 3168 | 230.3 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.5 | 1.5 | 796 | 231 | 3472 | 187.4 | 0 | 4 |
| ruling | 4 | 0 | 0 | 1.0 | 1.1 | 1180 | 146 | 3706 | 223.5 | 0 | 4 |
| overheard | 14 | 0 | 0 | 0.2 | 0.2 | 276 | 16 | 1952 | 292.0 | 0 | 3 |
| board_stakes | 1 | 0 | 0 | 2.7 | 2.7 | 971 | 513 | 3838 | 208.9 | 0 | 3 |
| canon_extract | 5 | 0 | 0 | 0.3 | 0.4 | 845 | 2 | 3048 | 177.2 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.6 | 629 | 74 | 3456 | 181.5 | 0 | 1 |

314 attempts for 297 calls, 6.0 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 100% | 19737 | 20910 | 20910 | 93 | 6% |
| npc_profile | 2 | 100% | 2552 | 2665 | 2665 | 1487 | 0% |
| dialogue_frame | 16 | 75% | 8289 | 8943 | 9162 | 3418 | 0% |
| hire_chat | 16 | 88% | 11834 | 12734 | 13192 | 2218 | 0% |
| canon_extract | 5 | 100% | 3444 | 4069 | 4069 | 812 | 0% |
| exchange | 12 | 100% | 11031 | 11687 | 12112 | 67 | 0% |
| overheard | 14 | 100% | 1114 | 1156 | 1201 | 220 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 7 | 100% | 95% | +5 | 20910 | 36345 | 36500 | 20910 | 6% |
| npc_profile | 2 | 100% | 100% | +0 | 2665 | 2774 | 3000 | 2665 | 0% |
| dialogue_frame | 16 | 75% | 86% | -11 | 8943 | 10715 | 11000 | 9162 | 0% |
| hire_chat | 16 | 88% | 98% | -10 | 12734 | 16275 | 16500 | 13192 | 0% |
| canon_extract | 5 | 100% | 100% | +0 | 4069 | 3998 | 4000 | 4069 | 0% |
| exchange | 12 | 100% | 90% | +10 | 11687 | 15039 | 15500 | 12112 | 0% |
| overheard | 14 | 100% | 100% | +0 | 1156 | 1326 | 1500 | 1201 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 20910 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -10).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 59 | 228653 | 173313 (76%) | 167036 (73%) |
| narrate | 42 | 88363 | 52010 (59%) | 9566 (11%) |
| hire_chat | 18 | 49784 | 25524 (51%) | 5575 (11%) |
| dialogue_frame | 20 | 39157 | 22621 (58%) | 7498 (19%) |
| npc_conversation | 7 | 34388 | 15442 (45%) | 2142 (6%) |
| player_line | 67 | 32407 | 9727 (30%) | 4598 (14%) |
| exchange | 12 | 32385 | 13539 (42%) | 0 (0%) |
| audit_compare | 26 | 5481 | 3041 (55%) | 0 (0%) |
| populate_place | 7 | 4947 | 1791 (36%) | 0 (0%) |
| ruling | 4 | 4747 | 2341 (49%) | 0 (0%) |
| canon_extract | 5 | 4356 | 3215 (74%) | 0 (0%) |
| audit_meaning | 26 | 4136 | 1831 (44%) | 0 (0%) |
| overheard | 14 | 3862 | 3093 (80%) | 0 (0%) |
| persona_details | 3 | 2389 | 1082 (45%) | 345 (14%) |
| npc_profile | 2 | 1258 | 514 (41%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| board_stakes | 1 | 971 | 385 (40%) | 0 (0%) |

The prompts held 538377 tokens; the constant system messages were about 329958 of them (61%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 196760 (37%) and read the rest.
The server's log: 314 prompts; 228 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 775 checkpoints made, 53 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

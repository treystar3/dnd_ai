# Night run: play_hunter_101

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.08 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 16 | 5.9 | 9.0 | 4.5 | 7.1 | 4.2 | 6.0 | 9 | 0 |
| search | 12 | 2.4 | 3.8 | 2.4 | 3.5 | 2.8 | 2.7 | 1 | 0 |
| move | 11 | 3.8 | 7.5 | 3.8 | 5.4 | 4.0 | 4.4 | 2 | 0 |
| talk | 6 | 2.8 | 9.6 | 2.6 | 3.8 | 4.5 | 5.9 | 2 | 0 |
| leave | 6 | 4.6 | 7.9 | 3.9 | 5.1 | 6.2 | 5.7 | 1 | 0 |
| forage | 4 | 2.0 | 2.5 | 2.0 | 2.5 | 2.8 | 1.8 | 0 | 0 |
| board | 2 | 4.3 | 6.0 | 4.3 | 6.0 | 6.5 | 5.1 | 1 | 0 |
| hire | 1 | 6.4 | 6.4 | 5.0 | 5.0 | 6.0 | 6.1 | 0 | 0 |
| rest | 1 | 8.9 | 8.9 | 6.7 | 6.7 | 10.0 | 8.2 | 1 | 0 |
| look | 1 | 1.7 | 1.7 | 1.7 | 1.7 | 2.0 | 1.6 | 0 | 0 |

60 turns in 4.8 minutes; 98% of it in the model; 140 embedding calls taking 0.8 s; 1 calls on background threads.
The budget: 2 optional calls deferred and 4 dropped; 2 turns told by a stand-in, 2 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 20.6 s and p90 39.5 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.9 s, leave, 9 calls, at the adventurers' guild house: "I pocket the coin and nod at her before turning toward the door."
- 10.4 s, talk, 8 calls, at the adventurers' guild house: "I look at the girl and ask, 'What's the oldest thing in this whole bui"
- 10.3 s, fight, 6 calls, at the King's Road between Willowmead and Parth: "I go for ghoul 1."
- 9.6 s, talk, 6 calls, at the adventurers' guild house: "I walk over to the ink-stained girl and say, 'Got the five yarrow. I'm"
- 9.0 s, fight, 7 calls, at the King's Road between Parth and Willowmead: "I use Cleaving Sweep on hobgoblin 2."

Lines by what read them: interpret 42, combat 16, hire 1, yielded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 41 (template 19; model failed 2, 19 s) |
| Lines picking up the passage before | 12 of 60 (20%); in talk 3 of 6 (50%) |
| Contracts taken / finished | 2 / 2 |
| Situations met / followed / ended by the player | 1 / 1 / 1 |
| Goals finished / given up | 7 / 0 (contract 2/0, find 1/0, follow 1/0, go 1/0, report 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 16 |
| Waits | 0 of 60 (0%) |
| Places visited | 8 |

Turns by goal: fight 16, contract 15, idle 9, report 6, hunt 5, board 3, follow 3, go 1, cont 1, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 12 (id 11, script 1) |
| Machinery mended at the screen | 2814 (dash 2802, json 1, stage 1, wrap 10) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("any coin worth taking is already in your purse (#₲ #ş #₵); none lies h") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 1 |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 5 of the game's 35 own lines (14%); most: 'Victory. +# XP' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 2 / 1 / 0 (e.g. '}'; '<') |
| City ground in the wilds / rain under a roof / weather out of season | 6 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 61 |
| Matters the player ended: pursued / by accident | 1 / 0 |
| Fights won / for +0 XP / XP median and most | 9 / 0 / 5 and 48 |
| Fight turns with a foe 10+ levels above the player | 0 of 17, the widest -7 |
| Marks shown from acts (Remembered here) | 2 |
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
| populate_place | 5 | 0 | 0 | 1.4 | 122.0 | 693 | 287 | 2119 | 233.5 | 0 | 127 |
| combat_narrate | 23 | 8 | 8 | 1.9 | 2.5 | 2848 | 227 | 6369 | 150.4 | 0 | 59 |
| narrate | 31 | 2 | 2 | 1.7 | 2.2 | 2303 | 148 | 4786 | 133.9 | 0 | 56 |
| interpret_action | 45 | 0 | 0 | 0.6 | 0.9 | 4066 | 52 | 10284 | 246.0 | 0 | 29 |
| npc_conversation | 12 | 1 | 1 | 1.8 | 3.6 | 5094 | 139 | 6282 | 124.8 | 0 | 28 |
| combat_aftermath | 14 | 0 | 0 | 1.6 | 1.8 | 1858 | 186 | 4616 | 173.0 | 0 | 21 |
| combat_opening | 11 | 2 | 2 | 1.5 | 1.8 | 1818 | 160 | 4150 | 134.4 | 0 | 21 |
| player_line | 43 | 13 | 15 | 0.4 | 0.4 | 536 | 23 | 2921 | 138.1 | 0 | 19 |
| dialogue_frame | 14 | 3 | 3 | 0.9 | 1.0 | 2210 | 50 | 4331 | 151.4 | 0 | 15 |
| combat_interpret | 16 | 0 | 0 | 0.5 | 0.5 | 965 | 47 | 3096 | 308.6 | 0 | 7 |
| hire_chat | 7 | 0 | 0 | 0.9 | 0.9 | 2442 | 56 | 4458 | 186.4 | 0 | 6 |
| exchange | 4 | 1 | 1 | 1.0 | 1.2 | 3009 | 73 | 5294 | 169.3 | 0 | 5 |
| road_event | 2 | 0 | 0 | 2.2 | 2.5 | 1720 | 335 | 3960 | 176.2 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.2 | 4.2 | 1036 | 899 | 2994 | 236.0 | 0 | 4 |
| persona_details | 3 | 0 | 0 | 1.4 | 1.4 | 784 | 231 | 3478 | 200.2 | 0 | 4 |
| audit_compare | 16 | 0 | 0 | 0.2 | 0.3 | 220 | 37 | 2422 | 251.1 | 0 | 4 |
| audit_meaning | 16 | 0 | 0 | 0.2 | 0.3 | 166 | 23 | 1895 | 172.3 | 0 | 4 |
| moment | 1 | 0 | 0 | 2.3 | 2.3 | 1364 | 292 | 3696 | 152.9 | 0 | 2 |
| ruling | 3 | 0 | 0 | 0.7 | 0.7 | 1269 | 66 | 3822 | 192.2 | 0 | 2 |
| thread_telling | 1 | 0 | 0 | 2.0 | 2.0 | 2935 | 259 | 5060 | 182.1 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.6 | 0.8 | 635 | 96 | 3492 | 188.1 | 0 | 1 |
| canon_extract | 3 | 0 | 0 | 0.3 | 0.7 | 809 | 6 | 3104 | 252.8 | 0 | 1 |
| overheard | 5 | 0 | 0 | 0.2 | 0.2 | 276 | 16 | 1993 | 290.9 | 0 | 1 |
| work_offer_read | 1 | 0 | 0 | 0.2 | 0.2 | 96 | 19 | 793 | 181.0 | 0 | 0 |

309 attempts for 279 calls, 7.1 minutes in the model in all.

## Fights

26 rounds with a fight call; 2.8 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 16 | 0.5 | 0.5 | 0 |
| combat_opening | 13 | 1.5 | 1.8 | 2 |
| combat_narrate | 31 | 1.9 | 2.5 | 8 |
| combat_aftermath | 14 | 1.6 | 1.8 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 92% | 20334 | 21513 | 21890 | 108 | 0% |
| npc_profile | 2 | 100% | 2504 | 2804 | 2804 | 1439 | 0% |
| dialogue_frame | 14 | 79% | 9131 | 10736 | 10770 | 4011 | 0% |
| work_offer_read | 1 | 100% | 321 | 321 | 321 | 72 | 0% |
| hire_chat | 7 | 100% | 10046 | 11649 | 11649 | 1842 | 0% |
| canon_extract | 3 | 100% | 3259 | 3355 | 3355 | 627 | 0% |
| exchange | 4 | 75% | 12978 | 13799 | 13799 | 63 | 0% |
| overheard | 5 | 100% | 1120 | 1181 | 1181 | 226 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 12 | 92% | 95% | -3 | 21513 | 36345 | 36500 | 21890 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2804 | 2774 | 3000 | 2804 | 0% |
| dialogue_frame | 14 | 79% | 86% | -7 | 10736 | 10715 | 11000 | 10770 | 0% |
| work_offer_read | 1 | 100% | 100% | +0 | 321 | 780 | 1000 | 321 | 0% |
| hire_chat | 7 | 100% | 98% | +2 | 11649 | 16275 | 16500 | 11649 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 3355 | 3998 | 4000 | 3355 | 0% |
| exchange | 4 | 75% | 90% | -15 | 13799 | 15039 | 15500 | 13799 | 0% |
| overheard | 5 | 100% | 100% | +0 | 1181 | 1326 | 1500 | 1181 | 0% |

Size: 6 of 8 tasks at or below the baseline's p95 (dearer: npc_profile, dialogue_frame); npc_conversation's p95 21513 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (exchange -15).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 45 | 179594 | 131917 (73%) | 133058 (74%) |
| combat_narrate | 31 | 89334 | 50057 (56%) | 42138 (47%) |
| narrate | 33 | 79119 | 40732 (51%) | 16703 (21%) |
| npc_conversation | 13 | 66396 | 28980 (44%) | 5400 (8%) |
| dialogue_frame | 17 | 37540 | 20208 (54%) | 6646 (18%) |
| player_line | 56 | 30877 | 8142 (26%) | 7146 (23%) |
| combat_aftermath | 14 | 25930 | 12295 (47%) | 9228 (36%) |
| combat_opening | 13 | 23135 | 11149 (48%) | 5376 (23%) |
| hire_chat | 7 | 17923 | 9683 (54%) | 0 (0%) |
| combat_interpret | 16 | 15386 | 12876 (84%) | 0 (0%) |
| exchange | 5 | 15067 | 5593 (37%) | 2889 (19%) |
| ruling | 3 | 3772 | 1740 (46%) | 0 (0%) |
| audit_compare | 16 | 3621 | 1871 (52%) | 0 (0%) |
| road_event | 2 | 3441 | 1592 (46%) | 0 (0%) |
| populate_place | 5 | 3354 | 1266 (38%) | 0 (0%) |
| thread_telling | 1 | 2935 | 398 (14%) | 0 (0%) |
| audit_meaning | 16 | 2666 | 1059 (40%) | 0 (0%) |
| canon_extract | 3 | 2443 | 1956 (80%) | 0 (0%) |
| persona_details | 3 | 2323 | 1102 (47%) | 0 (0%) |
| overheard | 5 | 1393 | 1105 (79%) | 0 (0%) |
| moment | 1 | 1364 | 753 (55%) | 0 (0%) |
| npc_profile | 2 | 1271 | 510 (40%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1036 | 494 (48%) | 0 (0%) |
| work_offer_read | 1 | 96 | 74 (78%) | 0 (0%) |

The prompts held 610016 tokens; the constant system messages were about 345552 of them (57%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 228584 (37%) and read the rest.
The server's log: 310 prompts; 217 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 774 checkpoints made, 30 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 1 ended (1 by the player, 0 settled by others, 0 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 1 succeeded, 0 failed.

Per game day within reach: 1.00 situations started, 1.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 1 (1) | 0 | 1 | 1 | 1 | 1 | 0 | 0 |

Situations started:
- day 2: [normal, engine-built] Cheap and then dear in Parth - starts, 2 days, 1 stages (within reach)

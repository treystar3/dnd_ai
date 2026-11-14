# Night run: play_hunter_105

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.11 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 21 | 6.3 | 12.6 | 5.4 | 7.0 | 6.4 | 7.1 | 9 | 0 |
| search | 13 | 2.9 | 8.0 | 2.8 | 5.4 | 3.5 | 3.7 | 3 | 0 |
| fight | 9 | 5.2 | 7.9 | 3.3 | 6.1 | 3.7 | 5.5 | 4 | 0 |
| talk | 6 | 5.0 | 7.8 | 3.9 | 5.0 | 5.7 | 6.3 | 2 | 0 |
| leave | 6 | 3.5 | 5.6 | 3.5 | 13.8 | 4.7 | 5.0 | 2 | 0 |
| hire | 1 | 3.6 | 3.6 | 3.6 | 3.6 | 4.0 | 2.4 | 0 | 0 |
| board | 1 | 23.8 | 23.8 | 23.8 | 23.8 | 5.0 | 23.8 | 0 | 0 |
| pick_up | 1 | 4.4 | 4.4 | 4.4 | 4.4 | 4.0 | 4.4 | 2 | 0 |
| shop | 1 | 10.7 | 10.7 | 9.1 | 9.1 | 7.0 | 10.6 | 0 | 0 |
| look | 1 | 9.3 | 9.3 | 4.7 | 4.7 | 8.0 | 9.0 | 0 | 0 |

60 turns in 6.2 minutes; 98% of it in the model; 232 embedding calls taking 1.1 s; 1 calls on background threads.
The budget: 10 optional calls deferred and 12 dropped; 7 turns told by a stand-in, 7 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 21.5 s and p90 49.8 s, over 60 s in 2 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 23.8 s, board, 5 calls, at the adventurers' guild house: "I walk up to the scribe and point to the board. I want the contract to"
- 14.8 s, move, 7 calls, at Willowmead: "I signal for us to keep moving past this village towards Riverhaven."
- 13.8 s, leave, 8 calls, at the adventurers' guild house: "I nod once at the magistrate and turn toward the door."
- 13.0 s, move, 11 calls, at the King's Road between Parth and Willowmead: "I look ahead at the road and say, "Let's push through this mud and kee"
- 12.6 s, move, 12 calls, at the Willowmead wetlands: "The job's done. Let's head back to the Adventurers' Guild House and ge"

Lines by what read them: interpret 50, combat 9, yielded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 48 (template 12; model failed 1, 22 s) |
| Lines picking up the passage before | 18 of 60 (30%); in talk 3 of 6 (50%) |
| Contracts taken / finished | 1 / 1 |
| Situations met / followed / ended by the player | 2 / 1 / 1 |
| Goals finished / given up | 9 / 2 (contract 2/0, find 0/1, follow 0/1, go 2/0, hunt 2/0, report 2/0, revisit 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 9 |
| Waits | 0 of 60 (0%) |
| Places visited | 10 |

Turns by goal: idle 13, hunt 12, fight 9, revisit 6, report 5, contract 4, follow 4, board 3, stop 1, need 1, cont 1, clarify 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 21 (id 12, broken 4, escape 3, script 1, json 1) |
| Machinery mended at the screen | 2334 (dash 2311, id 1, stage 1, wrap 21) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 2 / 0 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | narrated 2 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 18.2 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 1 (Calsa Hoyle in dialogue_frame 1) |
| Companion sentences naming another people | 2 (Frib Sprocketcrank in narrate 1; Calsa Hoyle in dialogue_frame 1) |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 5 times; 5 of the game's 31 own lines (16%); most: 'Victory. +# XP' x5 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 2 / 0 / 0 (e.g. '? Yes'; '\\') |
| City ground in the wilds / rain under a roof / weather out of season | 2 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 1 of 56 |
| Matters the player ended: pursued / by accident | 0 / 1 (by accident: Hunt 2 lizardfolks in the Willowmead wetlands) |
| Fights won / for +0 XP / XP median and most | 6 / 0 / 15 and 263 |
| Fight turns with a foe 10+ levels above the player | 0 of 9, the widest -3 |
| Marks shown from acts (Remembered here) | 2 |
| Captives escaped / handed over or let go | 2 / 0 |
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
| populate_place | 8 | 0 | 0 | 1.5 | 1.5 | 668 | 295 | 3311 | 189.2 | 0 | 134 |
| narrate | 33 | 12 | 15 | 2.1 | 2.6 | 2465 | 194 | 5255 | 117.5 | 0 | 93 |
| npc_conversation | 18 | 2 | 3 | 2.0 | 4.3 | 4962 | 147 | 6293 | 97.2 | 0 | 67 |
| interpret_action | 60 | 0 | 0 | 0.7 | 0.9 | 4189 | 72 | 10695 | 250.6 | 0 | 41 |
| combat_narrate | 10 | 4 | 4 | 2.0 | 3.1 | 2948 | 218 | 5821 | 123.7 | 0 | 31 |
| dialogue_frame | 18 | 3 | 3 | 1.1 | 1.3 | 2053 | 73 | 4089 | 130.1 | 0 | 23 |
| player_line | 49 | 13 | 14 | 0.4 | 0.5 | 555 | 25 | 2898 | 136.3 | 0 | 22 |
| hire_chat | 14 | 1 | 1 | 1.0 | 1.1 | 2686 | 65 | 4675 | 163.5 | 0 | 15 |
| exchange | 11 | 0 | 0 | 1.3 | 1.3 | 2570 | 99 | 4548 | 158.3 | 0 | 14 |
| combat_opening | 7 | 0 | 0 | 2.1 | 2.2 | 1741 | 214 | 4139 | 130.0 | 0 | 14 |
| combat_aftermath | 8 | 0 | 0 | 1.5 | 1.8 | 1913 | 189 | 4290 | 173.1 | 0 | 12 |
| road_event | 4 | 0 | 0 | 2.5 | 3.7 | 1755 | 329 | 3742 | 175.1 | 0 | 10 |
| audit_compare | 28 | 0 | 0 | 0.2 | 0.3 | 231 | 40 | 2399 | 252.9 | 0 | 7 |
| audit_meaning | 28 | 0 | 0 | 0.2 | 0.3 | 166 | 22 | 1887 | 159.6 | 0 | 7 |
| board_stakes | 2 | 0 | 0 | 2.3 | 2.8 | 1032 | 469 | 3647 | 209.2 | 0 | 5 |
| persona_details | 3 | 0 | 0 | 1.6 | 1.7 | 819 | 236 | 3365 | 181.1 | 0 | 5 |
| npc_profile | 6 | 0 | 0 | 0.7 | 0.8 | 626 | 104 | 3238 | 187.7 | 0 | 4 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.3 | 4.3 | 1050 | 959 | 3107 | 239.1 | 0 | 4 |
| combat_interpret | 9 | 0 | 0 | 0.5 | 0.5 | 968 | 48 | 3142 | 307.2 | 0 | 4 |
| ruling | 4 | 0 | 0 | 0.7 | 1.0 | 1278 | 66 | 3753 | 216.4 | 0 | 3 |
| overheard | 10 | 0 | 0 | 0.2 | 0.2 | 283 | 16 | 1879 | 289.9 | 0 | 2 |
| moment | 1 | 0 | 0 | 1.9 | 1.9 | 1402 | 268 | 3739 | 179.6 | 0 | 2 |
| clarify | 1 | 0 | 0 | 0.3 | 0.3 | 292 | 31 | 2101 | 183.4 | 0 | 0 |
| canon_extract | 1 | 0 | 0 | 0.3 | 0.3 | 875 | 2 | 3159 | 153.8 | 0 | 0 |

369 attempts for 334 calls, 8.7 minutes in the model in all.

## Fights

15 rounds with a fight call; 2.5 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 9 | 0.5 | 0.5 | 0 |
| combat_opening | 7 | 2.1 | 2.3 | 0 |
| combat_narrate | 14 | 2.0 | 3.1 | 4 |
| combat_aftermath | 8 | 1.5 | 1.8 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 18 | 89% | 19286 | 20888 | 22016 | 54 | 2% |
| npc_profile | 6 | 100% | 2557 | 2730 | 2730 | 1492 | 0% |
| dialogue_frame | 18 | 89% | 8382 | 10207 | 11894 | 3326 | 0% |
| hire_chat | 14 | 93% | 10710 | 11894 | 11962 | 2134 | 4% |
| canon_extract | 1 | 100% | 3512 | 3512 | 3512 | 880 | 0% |
| exchange | 11 | 100% | 10727 | 13320 | 13320 | 61 | 0% |
| overheard | 10 | 100% | 1131 | 1316 | 1316 | 237 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 18 | 89% | 95% | -6 | 20888 | 36345 | 36500 | 22016 | 2% |
| npc_profile | 6 | 100% | 100% | +0 | 2730 | 2774 | 3000 | 2730 | 0% |
| dialogue_frame | 18 | 89% | 86% | +3 | 10207 | 10715 | 11000 | 11894 | 0% |
| hire_chat | 14 | 93% | 98% | -5 | 11894 | 16275 | 16500 | 11962 | 4% |
| canon_extract | 1 | 100% | 100% | +0 | 3512 | 3998 | 4000 | 3512 | 0% |
| exchange | 11 | 100% | 90% | +10 | 13320 | 15039 | 15500 | 13320 | 0% |
| overheard | 10 | 100% | 100% | +0 | 1316 | 1326 | 1500 | 1316 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 20888 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -6).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 60 | 249991 | 176618 (71%) | 182915 (73%) |
| narrate | 45 | 112033 | 57617 (51%) | 38774 (35%) |
| npc_conversation | 20 | 97313 | 44519 (46%) | 12268 (13%) |
| dialogue_frame | 21 | 43442 | 24408 (56%) | 5810 (13%) |
| combat_narrate | 14 | 41413 | 22585 (55%) | 14349 (35%) |
| hire_chat | 15 | 39543 | 20850 (53%) | 4001 (10%) |
| player_line | 62 | 35087 | 8985 (26%) | 7345 (21%) |
| exchange | 11 | 29532 | 12201 (41%) | 0 (0%) |
| combat_aftermath | 8 | 15216 | 7043 (46%) | 3768 (25%) |
| combat_opening | 7 | 12164 | 5892 (48%) | 1806 (15%) |
| combat_interpret | 9 | 8685 | 7266 (84%) | 0 (0%) |
| road_event | 4 | 7155 | 3159 (44%) | 0 (0%) |
| audit_compare | 28 | 6504 | 3254 (50%) | 0 (0%) |
| populate_place | 8 | 5324 | 2054 (39%) | 0 (0%) |
| ruling | 4 | 5146 | 2316 (45%) | 0 (0%) |
| audit_meaning | 28 | 4810 | 1902 (40%) | 0 (0%) |
| npc_profile | 6 | 3614 | 1547 (43%) | 0 (0%) |
| overheard | 10 | 2869 | 2212 (77%) | 0 (0%) |
| persona_details | 3 | 2413 | 1090 (45%) | 345 (14%) |
| board_stakes | 2 | 2064 | 774 (38%) | 0 (0%) |
| moment | 1 | 1402 | 746 (53%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1050 | 488 (46%) | 0 (0%) |
| canon_extract | 1 | 875 | 656 (75%) | 0 (0%) |
| clarify | 1 | 292 | 150 (51%) | 0 (0%) |

The prompts held 727937 tokens; the constant system messages were about 408332 of them (56%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 271381 (37%) and read the rest.
The server's log: 369 prompts; 262 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 914 checkpoints made, 44 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 3 game days: 2 situations started (2 within reach of the player), 0 stages advanced, 2 ended (1 by the player, 1 settled by others, 0 left to their fallout), 1 motive steps; the player met 1 doors (a scene or a summons), 2 moments, 1 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 1 failed.

Per game day within reach: 0.67 situations started, 0.33 doors, 0.67 moments, 0.3 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 1 (1) | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| 3 | 1 (1) | 0 | 1 | 1 | 1 | 0 | 1 | 0 |

Situations started:
- day 2: [normal, engine-built] Hard labour at Willowmead at the Willowmead wetlands - starts, 1 days, 1 stages (within reach)
- day 3: [normal, engine-built] The hunters of Riverhaven and the stranger - starts, 2 days, 1 stages (within reach)

# Night run: play_hunter_107

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| wait | 17 | 4.5 | 6.4 | 4.0 | 5.8 | 4.0 | 4.9 | 2 | 0 |
| move | 13 | 7.7 | 11.4 | 5.8 | 8.8 | 5.4 | 7.4 | 4 | 0 |
| search | 12 | 4.0 | 7.6 | 4.0 | 5.9 | 3.9 | 4.9 | 1 | 0 |
| fight | 11 | 7.5 | 10.0 | 3.7 | 8.2 | 3.7 | 7.1 | 4 | 0 |
| hire | 3 | 6.3 | 6.3 | 6.1 | 6.3 | 5.7 | 6.1 | 1 | 0 |
| board | 2 | 1.0 | 11.2 | 6.8 | 6.8 | 3.5 | 6.0 | 0 | 0 |
| talk | 1 | 7.5 | 7.5 | 7.5 | 7.5 | 5.0 | 7.4 | 0 | 0 |
| leave | 1 | 6.5 | 6.5 | 6.5 | 6.5 | 7.0 | 6.3 | 1 | 0 |

60 turns in 6.2 minutes; 97% of it in the model; 144 embedding calls taking 1.7 s; 0 calls on background threads.
The budget: 7 optional calls deferred and 3 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 18.3 s and p90 29.4 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 16.9 s, move, 11 calls, at the watch tower: "I push past the guards and head straight for the Adventurers' Guild Ho"
- 11.4 s, move, 7 calls, at the adventurers' guild house: "Let's get out of here; we're heading to the Greywood."
- 11.2 s, board, 6 calls, at the adventurers' guild house: "I walk over to the man in silk and demand to see the high-reward contr"
- 11.1 s, move, 6 calls, at the south fields: "I lead the way toward the Adventurers' Guild House."
- 10.5 s, fight, 5 calls, at the Greywood: "I go for hobgoblin 2."

Lines by what read them: interpret 48, combat 11, yielded 1

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 49 (template 11; model failed 0, 38 s) |
| Lines picking up the passage before | 5 of 60 (8%); in talk 0 of 1 (0%) |
| Contracts taken / finished | 0 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 5 / 0 (go 3/0, hunt 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 11 |
| Waits | 17 of 60 (28%) |
| Places visited | 6 |

Turns by goal: board 19, idle 14, hunt 12, fight 11, go 2, need 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 8 (id 7, first_person 1) |
| Machinery mended at the screen | 1459 (dash 1445, stage 2, wrap 12) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 0 |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 1 |
| Attempts the world made room for / said no to in the world | 1 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | ruled 1 |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 8.3 |
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
| Lines shown 5+ times word for word (digits aside) | 1 lines, 6 times; 6 of the game's 23 own lines (26%); most: 'Victory. +# XP' x6 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 2 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 71 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 8 / 4 / 1 and 13 |
| Fight turns with a foe 10+ levels above the player | 0 of 11, the widest -7 |
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
| populate_place | 6 | 0 | 0 | 1.9 | 121.7 | 707 | 283 | 1660 | 175.8 | 0 | 254 |
| narrate | 39 | 2 | 2 | 2.3 | 2.9 | 2497 | 155 | 2534 | 111.4 | 0 | 97 |
| interpret_action | 52 | 0 | 0 | 1.0 | 1.4 | 3864 | 54 | 5443 | 177.0 | 0 | 55 |
| combat_narrate | 13 | 4 | 4 | 2.6 | 2.9 | 2988 | 190 | 3199 | 120.6 | 0 | 42 |
| player_line | 49 | 13 | 13 | 0.6 | 0.7 | 532 | 23 | 1494 | 98.2 | 0 | 38 |
| combat_aftermath | 13 | 0 | 0 | 2.1 | 2.6 | 1925 | 195 | 2322 | 149.7 | 0 | 28 |
| dialogue_frame | 13 | 3 | 3 | 1.6 | 1.9 | 2049 | 69 | 2243 | 122.7 | 0 | 25 |
| combat_opening | 8 | 0 | 0 | 2.4 | 2.6 | 1802 | 169 | 1974 | 110.9 | 0 | 20 |
| hire_chat | 12 | 2 | 2 | 1.3 | 1.5 | 2795 | 51 | 2934 | 165.5 | 0 | 18 |
| exchange | 7 | 1 | 1 | 1.6 | 1.7 | 3054 | 72 | 2787 | 149.4 | 0 | 12 |
| combat_interpret | 11 | 0 | 0 | 0.8 | 0.9 | 972 | 49 | 1578 | 242.3 | 0 | 9 |
| audit_compare | 23 | 0 | 0 | 0.3 | 0.4 | 212 | 38 | 1250 | 220.1 | 0 | 8 |
| persona_details | 3 | 1 | 1 | 2.1 | 2.2 | 952 | 279 | 1739 | 192.1 | 0 | 8 |
| npc_conversation | 3 | 0 | 0 | 2.6 | 2.7 | 4876 | 124 | 3576 | 109.5 | 0 | 8 |
| audit_meaning | 23 | 0 | 0 | 0.3 | 0.4 | 147 | 21 | 1098 | 123.3 | 0 | 7 |
| ruling | 5 | 0 | 0 | 1.1 | 1.1 | 1213 | 67 | 2195 | 155.1 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.1 | 5.1 | 1064 | 914 | 1610 | 208.2 | 0 | 5 |
| situation_parts | 1 | 0 | 0 | 3.9 | 3.9 | 1556 | 638 | 1517 | 226.3 | 0 | 4 |
| overheard | 11 | 0 | 0 | 0.3 | 0.4 | 271 | 16 | 979 | 272.4 | 0 | 4 |
| board_stakes | 1 | 0 | 0 | 2.5 | 2.5 | 1208 | 278 | 1611 | 158.0 | 0 | 3 |
| canon_extract | 4 | 0 | 0 | 0.6 | 0.8 | 837 | 4 | 1630 | 189.6 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 1.0 | 1.0 | 633 | 100 | 1689 | 166.3 | 0 | 2 |
| situation_agree | 2 | 0 | 0 | 0.2 | 0.3 | 192 | 14 | 837 | 225.8 | 0 | 1 |
| party_intent | 1 | 0 | 0 | 0.3 | 0.3 | 318 | 12 | 1389 | 164.4 | 0 | 0 |

329 attempts for 303 calls, 10.9 minutes in the model in all.

## Fights

19 rounds with a fight call; 2.6 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 11 | 0.8 | 1.0 | 0 |
| combat_opening | 8 | 2.4 | 3.0 | 0 |
| combat_narrate | 17 | 2.6 | 3.1 | 4 |
| combat_aftermath | 13 | 2.1 | 2.6 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 19385 | 20478 | 20478 | 54 | 0% |
| npc_profile | 2 | 100% | 2613 | 2626 | 2626 | 1548 | 0% |
| dialogue_frame | 13 | 77% | 8610 | 10307 | 10580 | 3364 | 0% |
| hire_chat | 12 | 83% | 11209 | 13270 | 13382 | 1594 | 0% |
| canon_extract | 4 | 100% | 3420 | 4128 | 4128 | 788 | 0% |
| exchange | 7 | 86% | 12148 | 12934 | 12934 | 62 | 0% |
| overheard | 11 | 100% | 1086 | 1188 | 1188 | 192 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 95% | +5 | 20478 | 36345 | 36500 | 20478 | 0% |
| npc_profile | 2 | 100% | 100% | +0 | 2626 | 2774 | 3000 | 2626 | 0% |
| dialogue_frame | 13 | 77% | 86% | -9 | 10307 | 10715 | 11000 | 10580 | 0% |
| hire_chat | 12 | 83% | 98% | -15 | 13270 | 16275 | 16500 | 13382 | 0% |
| canon_extract | 4 | 100% | 100% | +0 | 4128 | 3998 | 4000 | 4128 | 0% |
| exchange | 7 | 86% | 90% | -4 | 12934 | 15039 | 15500 | 12934 | 0% |
| overheard | 11 | 100% | 100% | +0 | 1188 | 1326 | 1500 | 1188 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 20478 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (hire_chat -15).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 52 | 197242 | 151958 (77%) | 154951 (79%) |
| narrate | 41 | 101739 | 58435 (57%) | 12569 (12%) |
| combat_narrate | 17 | 50613 | 32895 (65%) | 17152 (34%) |
| hire_chat | 14 | 40164 | 23050 (57%) | 5556 (14%) |
| dialogue_frame | 16 | 34764 | 21369 (61%) | 6248 (18%) |
| player_line | 62 | 32908 | 8861 (27%) | 6674 (20%) |
| combat_aftermath | 13 | 24992 | 13815 (55%) | 9527 (38%) |
| exchange | 8 | 23864 | 9113 (38%) | 3013 (13%) |
| npc_conversation | 3 | 14657 | 7346 (50%) | 0 (0%) |
| combat_opening | 8 | 14242 | 8198 (58%) | 0 (0%) |
| combat_interpret | 11 | 10660 | 8899 (83%) | 0 (0%) |
| ruling | 5 | 6124 | 2902 (47%) | 0 (0%) |
| audit_compare | 23 | 4944 | 2683 (54%) | 0 (0%) |
| populate_place | 6 | 4430 | 1536 (35%) | 0 (0%) |
| persona_details | 4 | 3644 | 1579 (43%) | 1152 (32%) |
| canon_extract | 4 | 3478 | 2580 (74%) | 0 (0%) |
| audit_meaning | 23 | 3431 | 1614 (47%) | 0 (0%) |
| overheard | 11 | 2994 | 2465 (82%) | 0 (0%) |
| situation_parts | 1 | 1556 | 1050 (68%) | 0 (0%) |
| npc_profile | 2 | 1267 | 515 (41%) | 0 (0%) |
| board_stakes | 1 | 1208 | 394 (33%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1064 | 489 (46%) | 0 (0%) |
| situation_agree | 2 | 384 | 198 (51%) | 87 (23%) |
| party_intent | 1 | 318 | 258 (81%) | 0 (0%) |

The prompts held 580687 tokens; the constant system messages were about 362202 of them (62%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 216929 (37%) and read the rest.
The server's log: 329 prompts; 238 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 804 checkpoints made, 36 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 2 game days: 1 situations started (1 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 0 lines of the room changing, 0 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.50 situations started, 0.00 doors, 0.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | 1 (1) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Situations started:
- day 2: [rare, engine-built] Not come back from the Greywood - starts, 11 days, 3 stages (within reach)

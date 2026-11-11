# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| move | 22 | 7.7 | 12.6 | 5.5 | 8.9 | 5.8 | 7.1 | 6 | 0 |
| wait | 20 | 5.2 | 10.1 | 4.4 | 6.9 | 4.2 | 5.9 | 3 | 0 |
| forage | 7 | 2.9 | 4.6 | 2.8 | 3.1 | 2.7 | 3.1 | 0 | 0 |
| talk | 3 | 3.6 | 7.1 | 3.6 | 7.1 | 3.3 | 4.6 | 0 | 0 |
| board | 2 | 2.4 | 9.4 | 9.4 | 9.4 | 4.5 | 5.8 | 0 | 0 |
| leave | 2 | 7.8 | 8.8 | 4.1 | 5.3 | 6.5 | 8.0 | 1 | 0 |
| look | 2 | 2.3 | 3.2 | 2.3 | 3.2 | 3.0 | 2.7 | 0 | 0 |
| hire | 1 | 5.2 | 5.2 | 5.2 | 5.2 | 3.0 | 5.1 | 0 | 0 |
| rest | 1 | 6.3 | 6.3 | 3.9 | 3.9 | 6.0 | 6.2 | 0 | 0 |

60 turns in 6.1 minutes; 97% of it in the model; 276 embedding calls taking 2.2 s; 1 calls on background threads.
The budget: 1 optional calls deferred and 2 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 12.8 s and p90 27.9 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.6 s, wait, 12 calls, at the adventurers' guild house: "I lean against the wall and cross my arms, just waiting for them to ca"
- 13.6 s, move, 11 calls, at the south fields: "We've got enough for now; let's head back to the Adventurers' Guild ho"
- 13.1 s, move, 9 calls, at the adventurers' guild house: "I push off my chair and stand up. 'Let's get out of here and hit the T"
- 12.6 s, move, 9 calls, at the adventurers' guild house: "I grab my gear and tell the others we're moving out toward the watch t"
- 12.4 s, move, 9 calls, at the temple of Parth: "The altar isn't paying us anything. Let's move out toward the Adventur"

Lines by what read them: interpret 55, hire 5

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 60 (template 0; model failed 0, 45 s) |
| Lines picking up the passage before | 11 of 60 (18%); in talk 1 of 3 (33%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 9 / 0 (contract 7/0, go 1/0, report 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 20 of 60 (33%) |
| Places visited | 7 |

Turns by goal: report 30, idle 11, contract 10, need 7, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 3 (id 3) |
| Machinery mended at the screen | 13 (dash 5, stage 5, wrap 3) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("you aren't carrying anything matching 'gear'.") |
| Goals the bot gave up on meeting the same refusal twice | 0 |
| Facades met / dead ends | 0 / 0 |
| Attempts the world made room for / said no to in the world | 0 / 1 |
| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | none |
| ...said no to, about someone in the party (likely a misread) | 0 |
| Additions to the world per hour | 0.0 |
| Parts made different by an attempt (blocked, lit, cleared...) | 0 |
| Turns the game believed the player was in a dungeon they had left | 0 |
| Longest run of the party held back | 0 turns |
| Captives held at once (most) / longest held | 0 / 0 days |
| Left the party, and named afterwards | nobody left |
| Companion sentences with the other gender's pronoun | 4 (Gwild Coleford in dialogue_frame 2; Gwild Coleford in interpret_action 1; Gharta Kulgarth in narrate 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 2 lines, 11 times; 0 of the game's 11 own lines (0%); most: "You are back at the adventurers' guild house." x6; 'You are back at the Tilted Plough.' x5 |
| Refusals shown / then acted out in the passage / never logged | 1 / 1 / 1 (e.g. turn 36 ['toward', 'tower']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 0 / 1 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 3 of 78 |
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
| populate_place | 9 | 0 | 0 | 1.7 | 120.7 | 670 | 270 | 1693 | 186.5 | 0 | 257 |
| narrate | 44 | 1 | 1 | 2.2 | 2.8 | 2307 | 144 | 2496 | 113.4 | 0 | 99 |
| interpret_action | 57 | 1 | 1 | 1.2 | 1.5 | 3897 | 59 | 4596 | 197.0 | 0 | 72 |
| dialogue_frame | 23 | 4 | 5 | 1.7 | 2.0 | 2027 | 85 | 2151 | 121.3 | 0 | 45 |
| player_line | 60 | 17 | 17 | 0.6 | 0.7 | 515 | 24 | 1458 | 103.1 | 0 | 45 |
| hire_chat | 24 | 3 | 3 | 1.4 | 1.6 | 2679 | 55 | 2750 | 154.8 | 0 | 39 |
| exchange | 17 | 0 | 0 | 1.7 | 1.9 | 2802 | 93 | 2576 | 145.5 | 0 | 29 |
| npc_conversation | 6 | 1 | 1 | 2.4 | 2.7 | 4516 | 131 | 4403 | 109.0 | 0 | 18 |
| audit_compare | 26 | 0 | 0 | 0.3 | 0.4 | 227 | 38 | 1275 | 225.0 | 0 | 9 |
| audit_meaning | 26 | 0 | 0 | 0.3 | 0.4 | 165 | 22 | 1112 | 128.5 | 0 | 8 |
| overheard | 22 | 0 | 0 | 0.3 | 0.4 | 276 | 16 | 973 | 258.4 | 0 | 8 |
| persona_details | 3 | 0 | 0 | 2.0 | 2.1 | 820 | 250 | 1692 | 163.9 | 0 | 6 |
| canon_extract | 8 | 0 | 0 | 0.6 | 0.7 | 890 | 2 | 1498 | 201.6 | 0 | 6 |
| board_stakes | 2 | 0 | 0 | 2.5 | 3.0 | 1100 | 422 | 2276 | 187.2 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.1 | 5.1 | 1093 | 926 | 1555 | 210.8 | 0 | 5 |
| ruling | 2 | 0 | 0 | 0.9 | 1.1 | 1198 | 68 | 2188 | 148.9 | 0 | 2 |
| npc_profile | 2 | 0 | 0 | 0.7 | 0.8 | 606 | 85 | 2027 | 187.4 | 0 | 2 |
| canon_check | 1 | 0 | 0 | 0.2 | 0.2 | 211 | 14 | 1179 | 254.5 | 0 | 0 |

360 attempts for 333 calls, 10.9 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 6 | 83% | 18043 | 21295 | 21295 | 53 | 13% |
| npc_profile | 2 | 100% | 2474 | 2553 | 2553 | 1409 | 0% |
| dialogue_frame | 23 | 87% | 8432 | 9669 | 9863 | 2997 | 4% |
| hire_chat | 24 | 88% | 10786 | 13036 | 13267 | 1822 | 0% |
| canon_extract | 8 | 100% | 3609 | 4347 | 4347 | 977 | 0% |
| canon_check | 1 | 100% | 833 | 833 | 833 | 440 | 0% |
| exchange | 17 | 100% | 11274 | 11884 | 11902 | 67 | 0% |
| overheard | 22 | 100% | 1119 | 1176 | 1255 | 225 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 6 | 83% | 95% | -12 | 21295 | 36345 | 36500 | 21295 | 13% |
| npc_profile | 2 | 100% | 100% | +0 | 2553 | 2774 | 3000 | 2553 | 0% |
| dialogue_frame | 23 | 87% | 86% | +1 | 9669 | 10715 | 11000 | 9863 | 4% |
| hire_chat | 24 | 88% | 98% | -10 | 13036 | 16275 | 16500 | 13267 | 0% |
| canon_extract | 8 | 100% | 100% | +0 | 4347 | 3998 | 4000 | 4347 | 0% |
| canon_check | 1 | 100% | 100% | +0 | 833 | 853 | 1000 | 833 | 0% |
| exchange | 17 | 100% | 90% | +10 | 11884 | 15039 | 15500 | 11902 | 0% |
| overheard | 22 | 100% | 100% | +0 | 1176 | 1326 | 1500 | 1255 | 0% |

Size: 7 of 8 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 21295 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -12; hire_chat -10).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 58 | 226484 | 170455 (75%) | 167347 (74%) |
| narrate | 45 | 105228 | 63893 (61%) | 16164 (15%) |
| hire_chat | 27 | 76974 | 44540 (58%) | 9244 (12%) |
| dialogue_frame | 27 | 55951 | 35386 (63%) | 10618 (19%) |
| exchange | 17 | 46483 | 19256 (41%) | 0 (0%) |
| player_line | 77 | 40701 | 11052 (27%) | 9453 (23%) |
| npc_conversation | 7 | 32852 | 17178 (52%) | 8225 (25%) |
| canon_extract | 8 | 7295 | 5155 (71%) | 0 (0%) |
| populate_place | 9 | 6134 | 2298 (37%) | 0 (0%) |
| overheard | 22 | 6079 | 4855 (80%) | 0 (0%) |
| audit_compare | 26 | 5820 | 3010 (52%) | 0 (0%) |
| audit_meaning | 26 | 4266 | 1821 (43%) | 0 (0%) |
| persona_details | 3 | 2447 | 1091 (45%) | 345 (14%) |
| ruling | 2 | 2396 | 1170 (49%) | 0 (0%) |
| board_stakes | 2 | 2201 | 781 (35%) | 0 (0%) |
| npc_profile | 2 | 1212 | 514 (42%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| canon_check | 1 | 211 | 100 (47%) | 0 (0%) |

The prompts held 623827 tokens; the constant system messages were about 383044 of them (61%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 221396 (35%) and read the rest.
The server's log: 360 prompts; 266 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 898 checkpoints made, 57 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 1 moments, 0 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 1.00 moments, 0.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 1 | 0 | 1 |

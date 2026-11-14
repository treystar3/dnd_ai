# Night run: play_talker_102

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.07 hours; stopped: turn limit (60); starting as green, playing as talker; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| talk | 32 | 2.8 | 5.0 | 2.8 | 5.0 | 2.5 | 3.3 | 0 | 0 |
| move | 13 | 6.2 | 9.6 | 3.7 | 5.5 | 5.8 | 5.5 | 2 | 0 |
| leave | 8 | 2.6 | 3.4 | 2.6 | 3.4 | 2.4 | 3.5 | 1 | 0 |
| wait | 6 | 2.2 | 3.6 | 2.2 | 3.0 | 3.2 | 2.7 | 0 | 0 |
| board | 1 | 4.3 | 4.3 | 4.2 | 4.2 | 6.0 | 4.2 | 0 | 0 |

60 turns in 3.9 minutes; 97% of it in the model; 274 embedding calls taking 1.2 s; 1 calls on background threads.
The budget: 6 optional calls deferred and 3 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.1 s and p90 27.8 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 10.3 s, leave, 3 calls, at the adventurers' guild house: "I appreciate your help today; I'm going to head out now."
- 9.7 s, move, 8 calls, at the adventurers' guild house: "I'm heading toward the south fields now; does anyone know if there's a"
- 9.6 s, move, 9 calls, at the south fields: "I think we should make our way to the Adventurers' Guild House first."
- 8.5 s, move, 9 calls, at the adventurers' guild house: "How does the situation look in the trading square? I want to see what'"
- 8.5 s, move, 8 calls, at the south fields: "Agreed, let's head straight for the Adventurers' Guild House then."

Lines by what read them: interpret 56, hire 4

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 59 of 60 (98%) |
| Lines the model wrote | 56 (template 4; model failed 0, 25 s) |
| Lines picking up the passage before | 16 of 60 (27%); in talk 10 of 32 (31%) |
| Contracts taken / finished | 2 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 2 / 3 (contract 0/1, go 2/0, revisit 0/2) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 6 of 60 (10%) |
| Places visited | 4 |

Turns by goal: idle 38, revisit 10, cont 4, contract 3, go 2, board 2, need 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 1 (json 1) |
| Machinery mended at the screen | 13 (dash 8, stage 3, wrap 2) |
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
| Companion sentences with the other gender's pronoun | 3 (Geir Heyshaw in npc_conversation 1; Geir Heyshaw in interpret_action 1; Yamaku Omari in narrate 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 0 lines, 0 times; 0 of the game's 7 own lines (0%) |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 6 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 1 of 27 |
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
| C6 The false name given: kept by the one told / spread to others / said after it was set straight / in narration | 2 / 0 / 0 / 0 (planted 1, set straight 0) |
| C7 Left the party, then named in narration / in speech before rejoining | nobody left |
| C8 A deed spoken of within 3 days by someone who did not see it / by its witnesses (rough) | 0 / 0 |

## Calls by task

| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 1 | 1 | 1.8 | 3.3 | 5169 | 140 | 6122 | 152.2 | 0 | 94 |
| interpret_action | 59 | 0 | 0 | 0.8 | 0.9 | 4290 | 64 | 9198 | 255.2 | 0 | 43 |
| populate_place | 4 | 0 | 0 | 1.6 | 32.3 | 673 | 255 | 3122 | 234.2 | 0 | 36 |
| narrate | 18 | 0 | 0 | 1.6 | 2.0 | 2207 | 143 | 4342 | 137.3 | 0 | 28 |
| player_line | 56 | 11 | 11 | 0.4 | 0.5 | 504 | 28 | 2836 | 135.7 | 0 | 25 |
| dialogue_frame | 18 | 1 | 1 | 1.0 | 1.2 | 2072 | 69 | 3902 | 144.4 | 0 | 19 |
| exchange | 8 | 0 | 0 | 1.2 | 1.3 | 2374 | 112 | 4398 | 171.9 | 0 | 10 |
| hire_chat | 10 | 0 | 0 | 0.8 | 1.1 | 2353 | 53 | 4321 | 186.6 | 0 | 9 |
| persona_details | 3 | 1 | 1 | 1.6 | 1.6 | 926 | 247 | 3546 | 209.0 | 0 | 6 |
| npc_profile | 6 | 0 | 0 | 0.7 | 0.8 | 622 | 97 | 3353 | 176.3 | 0 | 5 |
| generate_passive_mechanics | 1 | 0 | 0 | 4.5 | 4.5 | 1028 | 972 | 3024 | 232.7 | 0 | 5 |
| audit_compare | 10 | 0 | 0 | 0.3 | 0.3 | 235 | 40 | 2409 | 249.9 | 0 | 3 |
| audit_meaning | 10 | 0 | 0 | 0.2 | 0.2 | 164 | 24 | 1847 | 176.6 | 0 | 2 |
| overheard | 8 | 0 | 0 | 0.2 | 0.2 | 281 | 16 | 2008 | 299.8 | 0 | 2 |
| canon_extract | 2 | 0 | 0 | 0.3 | 1.3 | 860 | 134 | 3094 | 276.6 | 0 | 2 |
| board_stakes | 1 | 0 | 0 | 0.8 | 0.8 | 887 | 102 | 3680 | 203.6 | 0 | 1 |

270 attempts for 256 calls, 4.8 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 20756 | 22557 | 24040 | 114 | 3% |
| npc_profile | 6 | 100% | 2558 | 2680 | 2680 | 1493 | 0% |
| dialogue_frame | 18 | 94% | 8474 | 9825 | 9840 | 3434 | 0% |
| hire_chat | 10 | 100% | 9551 | 12068 | 12068 | 1772 | 0% |
| canon_extract | 2 | 100% | 2746 | 4156 | 4156 | 114 | 0% |
| exchange | 8 | 100% | 9826 | 13015 | 13015 | 63 | 0% |
| overheard | 8 | 100% | 1146 | 1218 | 1218 | 252 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 42 | 98% | 95% | +2 | 22557 | 36345 | 36500 | 24040 | 3% |
| npc_profile | 6 | 100% | 100% | +0 | 2680 | 2774 | 3000 | 2680 | 0% |
| dialogue_frame | 18 | 94% | 86% | +8 | 9825 | 10715 | 11000 | 9840 | 0% |
| hire_chat | 10 | 100% | 98% | +2 | 12068 | 16275 | 16500 | 12068 | 0% |
| canon_extract | 2 | 100% | 100% | +0 | 4156 | 3998 | 4000 | 4156 | 0% |
| exchange | 8 | 100% | 90% | +10 | 13015 | 15039 | 15500 | 13015 | 0% |
| overheard | 8 | 100% | 100% | +0 | 1218 | 1326 | 1500 | 1218 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 22557 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 59 | 252584 | 175534 (69%) | 176456 (70%) |
| npc_conversation | 43 | 218419 | 94622 (43%) | 10927 (5%) |
| narrate | 18 | 39175 | 22013 (56%) | 4436 (11%) |
| dialogue_frame | 19 | 38809 | 22213 (57%) | 1853 (5%) |
| player_line | 67 | 35243 | 9353 (27%) | 6255 (18%) |
| hire_chat | 10 | 24169 | 13850 (57%) | 11 (0%) |
| exchange | 8 | 19807 | 8903 (45%) | 8 (0%) |
| persona_details | 4 | 3752 | 1544 (41%) | 1712 (46%) |
| npc_profile | 6 | 3742 | 1550 (41%) | 6 (0%) |
| populate_place | 4 | 2694 | 1018 (38%) | 4 (0%) |
| audit_compare | 10 | 2317 | 1130 (49%) | 10 (0%) |
| overheard | 8 | 2269 | 1772 (78%) | 8 (0%) |
| canon_extract | 2 | 1720 | 1317 (77%) | 2 (0%) |
| audit_meaning | 10 | 1646 | 671 (41%) | 10 (1%) |
| generate_passive_mechanics | 1 | 1028 | 492 (48%) | 0 (0%) |
| board_stakes | 1 | 887 | 373 (42%) | 1 (0%) |

The prompts held 648261 tokens; the constant system messages were about 356355 of them (55%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 201699 (31%) and read the rest.
The server's log: 270 prompts; 0 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 792 checkpoints made, 249 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

## The world

Over 1 game days: 0 situations started (0 within reach of the player), 0 stages advanced, 0 ended (0 by the player, 0 settled by others, 0 left to their fallout), 0 motive steps; the player met 0 doors (a scene or a summons), 0 moments, 1 lines of the room changing, 1 times people on their routine; re-tellings 0 succeeded, 0 failed.

Per game day within reach: 0.00 situations started, 0.00 doors, 0.00 moments, 1.0 room-changing lines.

| Day | Started (within reach) | Stages | Ended | Motives | Doors | Moments | Room lines | Routine |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 (0) | 0 | 0 | 0 | 0 | 0 | 1 | 1 |

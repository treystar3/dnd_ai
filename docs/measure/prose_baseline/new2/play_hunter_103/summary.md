# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.1 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| wait | 21 | 5.0 | 8.2 | 4.2 | 6.2 | 3.2 | 5.0 | 2 | 0 |
| move | 14 | 7.1 | 12.4 | 5.0 | 8.7 | 5.3 | 6.9 | 1 | 0 |
| forage | 13 | 3.8 | 7.4 | 3.8 | 5.2 | 3.7 | 4.2 | 1 | 0 |
| look | 4 | 4.0 | 4.5 | 4.0 | 4.5 | 3.5 | 3.5 | 0 | 0 |
| board | 2 | 3.7 | 7.2 | 3.7 | 7.1 | 4.5 | 5.3 | 0 | 0 |
| improv | 2 | 1.1 | 10.3 | 7.7 | 7.7 | 3.5 | 5.3 | 0 | 0 |
| talk | 1 | 4.0 | 4.0 | 4.0 | 4.0 | 2.0 | 3.9 | 0 | 0 |
| leave | 1 | 4.2 | 4.2 | 4.2 | 4.2 | 2.0 | 4.1 | 0 | 0 |
| hire | 1 | 3.2 | 3.2 | 3.2 | 3.2 | 3.0 | 3.0 | 0 | 0 |
| search | 1 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 0 | 0 |

60 turns in 5.3 minutes; 96% of it in the model; 171 embedding calls taking 2.2 s; 0 calls on background threads.
The budget: 1 optional calls deferred and 1 dropped; 1 turns told by a stand-in, 1 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 12.1 s and p90 22.3 s, over 60 s in 0 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 15.4 s, move, 11 calls, at the adventurers' guild house: "Stand up and gesture toward the door, telling them we're heading to th"
- 12.4 s, move, 9 calls, at the adventurers' guild house: "I grab my gear and tell everyone we're heading to the watch tower."
- 12.3 s, move, 9 calls, at the adventurers' guild house: "I stand up and tell the others we're heading to the trading square."
- 10.8 s, move, 6 calls, at Parth: "I head straight for the Adventurers' Guild House."
- 10.3 s, improv, 6 calls, at the adventurers' guild house: "I slam a heavy coin onto the counter and gesture at the book."

Lines by what read them: interpret 57, hire 3

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 60 of 60 (100%) |
| Lines the model wrote | 60 (template 0; model failed 0, 42 s) |
| Lines picking up the passage before | 7 of 60 (12%); in talk 0 of 1 (0%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 8 / 0 (contract 7/0, go 1/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 0 |
| Waits | 21 of 60 (35%) |
| Places visited | 6 |

Turns by goal: report 27, contract 18, idle 10, need 3, board 2

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 2 (id 2) |
| Machinery mended at the screen | 8 (wrap 8) |
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
| Companion sentences with the other gender's pronoun | 0 |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 7 times; 7 of the game's 22 own lines (32%); most: 'Gathered: # yarrow.' x7 |
| Refusals shown / then acted out in the passage / never logged | 2 / 1 / 1 (e.g. turn 45 ['tower', 'watch']) |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 0 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 0 of 34 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 0 / 0 / 0 and 0 |
| Fight turns with a foe 10+ levels above the player | not recorded on this night |
| Marks shown from acts (Remembered here) | 3 |
| Captives escaped / handed over or let go | 1 / 0 |
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
| populate_place | 7 | 0 | 0 | 1.7 | 2.0 | 694 | 289 | 1667 | 158.8 | 0 | 139 |
| narrate | 53 | 2 | 2 | 2.2 | 2.8 | 2211 | 127 | 2179 | 104.9 | 0 | 119 |
| interpret_action | 69 | 0 | 0 | 1.1 | 1.7 | 3839 | 45 | 4546 | 164.4 | 0 | 82 |
| player_line | 60 | 7 | 7 | 0.6 | 0.7 | 463 | 22 | 1281 | 93.8 | 0 | 42 |
| dialogue_frame | 12 | 2 | 2 | 1.6 | 2.0 | 1993 | 82 | 2027 | 114.9 | 0 | 24 |
| hire_chat | 14 | 0 | 0 | 1.5 | 1.8 | 2552 | 57 | 2399 | 145.7 | 0 | 22 |
| exchange | 8 | 0 | 0 | 1.8 | 2.0 | 2724 | 72 | 2300 | 144.2 | 0 | 14 |
| npc_conversation | 3 | 0 | 0 | 2.5 | 3.0 | 5106 | 131 | 3613 | 107.7 | 0 | 8 |
| audit_meaning | 20 | 0 | 0 | 0.4 | 0.4 | 156 | 21 | 1020 | 101.5 | 0 | 7 |
| audit_compare | 20 | 0 | 0 | 0.3 | 0.4 | 204 | 37 | 1228 | 221.3 | 0 | 7 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.8 | 5.8 | 1093 | 921 | 1232 | 190.1 | 0 | 6 |
| persona_details | 3 | 0 | 0 | 1.9 | 2.0 | 802 | 243 | 1647 | 171.1 | 0 | 6 |
| overheard | 12 | 0 | 0 | 0.4 | 0.4 | 276 | 16 | 903 | 247.4 | 0 | 5 |
| ruling | 4 | 0 | 0 | 1.1 | 1.3 | 1172 | 64 | 1950 | 128.8 | 0 | 5 |
| board_stakes | 1 | 0 | 0 | 3.3 | 3.3 | 972 | 504 | 2008 | 182.5 | 0 | 3 |
| canon_extract | 3 | 0 | 0 | 0.7 | 1.7 | 948 | 2 | 1514 | 188.8 | 0 | 3 |
| npc_profile | 1 | 0 | 0 | 0.9 | 0.9 | 615 | 83 | 1904 | 149.5 | 0 | 1 |

302 attempts for 291 calls, 8.2 minutes in the model in all.

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 20222 | 20542 | 20542 | 70 | 0% |
| npc_profile | 1 | 100% | 2568 | 2568 | 2568 | 1503 | 0% |
| dialogue_frame | 12 | 83% | 8402 | 9651 | 9673 | 3173 | 0% |
| hire_chat | 14 | 100% | 10281 | 12750 | 13383 | 1665 | 0% |
| canon_extract | 3 | 100% | 3930 | 4109 | 4109 | 1298 | 0% |
| exchange | 8 | 100% | 10987 | 11446 | 11446 | 67 | 0% |
| overheard | 12 | 100% | 1119 | 1194 | 1223 | 225 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 3 | 100% | 95% | +5 | 20542 | 36345 | 36500 | 20542 | 0% |
| npc_profile | 1 | 100% | 100% | +0 | 2568 | 2774 | 3000 | 2568 | 0% |
| dialogue_frame | 12 | 83% | 86% | -3 | 9651 | 10715 | 11000 | 9673 | 0% |
| hire_chat | 14 | 100% | 98% | +2 | 12750 | 16275 | 16500 | 13383 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 4109 | 3998 | 4000 | 4109 | 0% |
| exchange | 8 | 100% | 90% | +10 | 11446 | 15039 | 15500 | 11446 | 0% |
| overheard | 12 | 100% | 100% | +0 | 1194 | 1326 | 1500 | 1223 | 0% |

Size: 6 of 7 tasks at or below the baseline's p95 (dearer: canon_extract); npc_conversation's p95 20542 against the mark of 14000, not held; over their ceiling: canon_extract.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: held.

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 69 | 262659 | 201724 (77%) | 209270 (80%) |
| narrate | 55 | 120398 | 78044 (65%) | 18631 (15%) |
| hire_chat | 14 | 37646 | 22953 (61%) | 0 (0%) |
| player_line | 67 | 31687 | 9597 (30%) | 3466 (11%) |
| dialogue_frame | 14 | 28657 | 18378 (64%) | 3811 (13%) |
| exchange | 8 | 21546 | 9096 (42%) | 0 (0%) |
| npc_conversation | 3 | 15195 | 7383 (49%) | 0 (0%) |
| populate_place | 7 | 4947 | 1791 (36%) | 0 (0%) |
| ruling | 4 | 4738 | 2327 (49%) | 0 (0%) |
| audit_compare | 20 | 4201 | 2322 (55%) | 0 (0%) |
| overheard | 12 | 3325 | 2650 (80%) | 0 (0%) |
| audit_meaning | 20 | 3112 | 1404 (45%) | 0 (0%) |
| canon_extract | 3 | 2788 | 1928 (69%) | 0 (0%) |
| persona_details | 3 | 2401 | 1084 (45%) | 345 (14%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |
| board_stakes | 1 | 972 | 385 (40%) | 0 (0%) |
| npc_profile | 1 | 615 | 255 (41%) | 0 (0%) |

The prompts held 545980 tokens; the constant system messages were about 361810 of them (66%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 235523 (43%) and read the rest.
The server's log: 302 prompts; 212 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 733 checkpoints made, 38 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

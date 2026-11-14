# Night run: play_hunter_103

Ironbound Vanguard, Ironbound Vanguard, level 13, 0 deaths; 60 turns in 0.12 hours; stopped: turn limit (60); starting as green, playing as hunter; model gemma4-12b-bb722270, warm calls +0.15 temperature and +0.1 repeat penalty.

## Turns

| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fight | 17 | 6.3 | 9.7 | 4.1 | 5.6 | 3.5 | 6.4 | 2 | 0 |
| search | 16 | 4.8 | 9.0 | 4.4 | 6.5 | 3.6 | 4.9 | 0 | 0 |
| move | 12 | 7.3 | 12.6 | 5.5 | 7.8 | 6.1 | 8.1 | 3 | 0 |
| wait | 7 | 5.4 | 10.1 | 5.4 | 5.7 | 4.7 | 6.6 | 2 | 0 |
| talk | 2 | 3.0 | 3.9 | 3.0 | 3.9 | 2.0 | 3.3 | 0 | 0 |
| leave | 2 | 6.2 | 7.8 | 5.0 | 6.2 | 6.0 | 6.8 | 0 | 0 |
| hire | 1 | 9.3 | 9.3 | 7.2 | 7.2 | 5.0 | 9.1 | 0 | 0 |
| board | 1 | 17.2 | 17.2 | 17.2 | 17.2 | 5.0 | 17.1 | 0 | 0 |
| improv | 1 | 4.4 | 4.4 | 4.4 | 4.4 | 5.0 | 4.3 | 0 | 0 |
| rest | 1 | 7.1 | 7.1 | 7.0 | 7.0 | 4.0 | 7.0 | 1 | 0 |

60 turns in 6.7 minutes; 97% of it in the model; 140 embedding calls taking 1.8 s; 1 calls on background threads.
The budget: 7 optional calls deferred and 6 dropped; 0 turns told by a stand-in, 0 of them stood without a passage; 0 outcomes told at a load; the required path estimated at p50 16.9 s and p90 33.5 s, over 60 s in 1 turns (apart from the failed turns above); the prompt the server reused not priced (f538), so not comparable with a night before it.

Slowest turns:
- 23.0 s, move, 6 calls, at the Tilted Plough: "I nod to the tavern-master and tell the others we're heading back to t"
- 17.2 s, board, 5 calls, at the adventurers' guild house: "I point at the notice on the board and tell the scribe I'm taking the "
- 12.9 s, fight, 9 calls, at the Greywood: "I use Brutal Strike on wolf 1."
- 12.6 s, move, 7 calls, at the south fields: "I gesture for everyone to follow me as we head toward the adventurers'"
- 11.8 s, move, 10 calls, at the adventurers' guild house: "Let's stop arguing over the pay and head straight for the Temple of Pa"

Lines by what read them: interpret 45, combat 15

## Play

| Measure | Value |
| --- | --- |
| Distinct lines | 56 of 60 (93%) |
| Lines the model wrote | 42 (template 18; model failed 0, 28 s) |
| Lines picking up the passage before | 10 of 60 (17%); in talk 2 of 2 (100%) |
| Contracts taken / finished | 1 / 0 |
| Situations met / followed / ended by the player | 0 / 0 / 0 |
| Goals finished / given up | 5 / 0 (contract 3/0, go 2/0) |
| Deaths (above the level band) | 0 (0) |
| Fights | 17 |
| Waits | 7 of 60 (12%) |
| Places visited | 6 |

Turns by goal: contract 19, fight 15, report 11, idle 7, need 5, go 1, board 1, cont 1

## Consistency

| Measure | Value |
| --- | --- |
| Machinery sent back by the gateway | 2 (id 2) |
| Machinery mended at the screen | 3122 (dash 3111, stage 3, wrap 8) |
| Turns ending on a refusal said at least twice in the last ten | 0 |
| Longest run of one refusal | 1 ("iron longsword is already in hand.") |
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
| Companion sentences with the other gender's pronoun | 12 (Gharta Kulgarth in combat_narrate 5; Gwild Coleford in combat_aftermath 3; Gwild Coleford in narrate 2; Gharta Kulgarth in combat_aftermath 1) |
| Companion sentences naming another people | 0 |

## The page

| Measure (read from what was shown) | Value |
| --- | --- |
| Lines shown 5+ times word for word (digits aside) | 1 lines, 9 times; 9 of the game's 19 own lines (47%); most: 'Victory. +# XP' x9 |
| Refusals shown / then acted out in the passage / never logged | 0 / 0 / 0 |
| Story lines with machinery in them / figure heaps / empty speech | 0 / 1 / 0 |
| City ground in the wilds / rain under a roof / weather out of season | 1 / 0 / 0 |
| Sentences naming one person, with the other gender's pronoun, by kind | hire 9 of 81 |
| Matters the player ended: pursued / by accident | 0 / 0 |
| Fights won / for +0 XP / XP median and most | 9 / 3 / 1 and 5 |
| Fight turns with a foe 10+ levels above the player | 0 of 15, the widest -10 |
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
| populate_place | 5 | 0 | 0 | 1.4 | 124.7 | 648 | 220 | 1710 | 137.4 | 0 | 130 |
| narrate | 43 | 2 | 2 | 2.1 | 2.8 | 2216 | 152 | 2707 | 114.9 | 0 | 95 |
| combat_narrate | 20 | 0 | 0 | 2.5 | 3.4 | 2930 | 187 | 3164 | 112.4 | 0 | 54 |
| interpret_action | 50 | 0 | 0 | 1.0 | 1.3 | 3853 | 59 | 5403 | 188.5 | 0 | 52 |
| npc_conversation | 6 | 1 | 1 | 2.5 | 14.5 | 4866 | 167 | 3994 | 100.9 | 0 | 44 |
| combat_aftermath | 17 | 0 | 0 | 2.0 | 2.3 | 1911 | 187 | 2553 | 151.3 | 0 | 34 |
| player_line | 42 | 6 | 6 | 0.6 | 0.7 | 549 | 24 | 1515 | 106.3 | 0 | 28 |
| combat_opening | 9 | 0 | 0 | 2.4 | 2.5 | 1693 | 170 | 2169 | 113.4 | 0 | 21 |
| dialogue_frame | 9 | 2 | 2 | 1.5 | 1.8 | 1963 | 90 | 2347 | 128.0 | 0 | 17 |
| hire_chat | 10 | 1 | 1 | 1.3 | 1.6 | 2643 | 54 | 2750 | 163.1 | 0 | 15 |
| combat_interpret | 15 | 0 | 0 | 0.8 | 0.8 | 955 | 48 | 1597 | 270.4 | 0 | 12 |
| exchange | 7 | 2 | 4 | 1.2 | 1.6 | 2521 | 60 | 2701 | 152.2 | 0 | 11 |
| audit_compare | 22 | 0 | 0 | 0.3 | 0.4 | 218 | 39 | 1277 | 229.0 | 0 | 8 |
| audit_meaning | 22 | 0 | 0 | 0.3 | 0.3 | 145 | 24 | 1061 | 124.7 | 0 | 7 |
| persona_details | 3 | 0 | 0 | 2.0 | 2.1 | 811 | 248 | 1671 | 163.5 | 0 | 6 |
| generate_passive_mechanics | 1 | 0 | 0 | 5.3 | 5.3 | 1093 | 940 | 1546 | 204.6 | 0 | 5 |
| npc_profile | 3 | 0 | 0 | 0.8 | 1.0 | 616 | 92 | 1887 | 162.5 | 0 | 3 |
| overheard | 7 | 0 | 0 | 0.3 | 0.3 | 271 | 16 | 1045 | 264.2 | 0 | 2 |
| ruling | 2 | 0 | 0 | 1.0 | 1.0 | 1192 | 66 | 2159 | 154.7 | 0 | 2 |
| canon_extract | 3 | 0 | 0 | 0.5 | 0.9 | 864 | 2 | 1768 | 245.7 | 0 | 2 |

310 attempts for 296 calls, 9.1 minutes in the model in all.

## Fights

24 rounds with a fight call; 2.5 fight calls a round; 0.00 operations rolled back a round; 0 fights let go at a load.

| Fight task | Calls | Seconds p50 | p95 | Failed |
| --- | ---: | ---: | ---: | ---: |
| combat_interpret | 15 | 0.8 | 0.8 | 0 |
| combat_opening | 9 | 2.4 | 2.8 | 0 |
| combat_narrate | 20 | 2.5 | 3.6 | 0 |
| combat_aftermath | 17 | 2.0 | 2.3 | 0 |

## Speech tasks (prompt size and first try)

| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 6 | 83% | 19349 | 19976 | 19976 | 64 | 8% |
| npc_profile | 3 | 100% | 2544 | 2609 | 2609 | 1479 | 0% |
| dialogue_frame | 9 | 78% | 8236 | 10359 | 10359 | 3105 | 10% |
| hire_chat | 10 | 90% | 10441 | 12542 | 12542 | 1692 | 0% |
| canon_extract | 3 | 100% | 3518 | 3565 | 3565 | 886 | 0% |
| exchange | 7 | 71% | 10544 | 11232 | 11232 | 62 | 11% |
| overheard | 7 | 100% | 1089 | 1125 | 1125 | 195 | 0% |

## Speech tasks against Bundle D's baseline

| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| npc_conversation | 6 | 83% | 95% | -12 | 19976 | 36345 | 36500 | 19976 | 8% |
| npc_profile | 3 | 100% | 100% | +0 | 2609 | 2774 | 3000 | 2609 | 0% |
| dialogue_frame | 9 | 78% | 86% | -8 | 10359 | 10715 | 11000 | 10359 | 10% |
| hire_chat | 10 | 90% | 98% | -8 | 12542 | 16275 | 16500 | 12542 | 0% |
| canon_extract | 3 | 100% | 100% | +0 | 3565 | 3998 | 4000 | 3565 | 0% |
| exchange | 7 | 71% | 90% | -18 | 11232 | 15039 | 15500 | 11232 | 11% |
| overheard | 7 | 100% | 100% | +0 | 1125 | 1326 | 1500 | 1125 | 0% |

Size: 7 of 7 tasks at or below the baseline's p95; npc_conversation's p95 19976 against the mark of 14000, not held; over their ceiling: none.
Acceptance: first tries within 5 points of the baseline for npc_conversation, npc_parting, hire_chat, exchange, mentor_chat: not held (npc_conversation -12; hire_chat -8; exchange -18).

## Prompt cache

| Task | Attempts | Prompt tokens | System message | Reused |
| --- | ---: | ---: | ---: | ---: |
| interpret_action | 50 | 189652 | 145669 (77%) | 139858 (74%) |
| narrate | 45 | 99076 | 60733 (61%) | 33715 (34%) |
| combat_narrate | 20 | 58397 | 36801 (63%) | 14419 (25%) |
| npc_conversation | 7 | 33793 | 17191 (51%) | 6060 (18%) |
| combat_aftermath | 17 | 32311 | 17595 (54%) | 14862 (46%) |
| hire_chat | 11 | 29101 | 18076 (62%) | 2649 (9%) |
| player_line | 48 | 26089 | 6811 (26%) | 3380 (13%) |
| dialogue_frame | 11 | 22544 | 14053 (62%) | 5759 (26%) |
| exchange | 9 | 20616 | 10128 (49%) | 5427 (26%) |
| combat_opening | 9 | 15269 | 8944 (59%) | 2262 (15%) |
| combat_interpret | 15 | 14357 | 12024 (84%) | 0 (0%) |
| audit_compare | 22 | 4910 | 2559 (52%) | 0 (0%) |
| populate_place | 5 | 3312 | 1270 (38%) | 0 (0%) |
| audit_meaning | 22 | 3274 | 1524 (47%) | 0 (0%) |
| canon_extract | 3 | 2595 | 1943 (75%) | 0 (0%) |
| persona_details | 3 | 2439 | 1084 (44%) | 345 (14%) |
| ruling | 2 | 2384 | 1161 (49%) | 0 (0%) |
| overheard | 7 | 1890 | 1549 (82%) | 0 (0%) |
| npc_profile | 3 | 1861 | 773 (42%) | 0 (0%) |
| generate_passive_mechanics | 1 | 1093 | 489 (45%) | 0 (0%) |

The prompts held 564963 tokens; the constant system messages were about 360377 of them (64%, estimated from their share of the prompts' characters), the reading a kept cache spares; the server reused 228736 (40%) and read the rest.
The server's log: 310 prompts; 214 forced to re-process the whole prompt for want of cache data (a sliding-window model reuses its cache only back to a checkpoint); 736 checkpoints made, 30 restored; 0 prompt-cache updates taking 0.0 s in all (mean 0 ms, the longest 0 ms); 0 entries evicted from the RAM cache.

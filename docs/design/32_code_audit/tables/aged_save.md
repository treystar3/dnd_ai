# Growth of an aged save, measured (finder aged-save, second round)

Everything here was measured on the CPU under simlib's stub, through the game's own line path (`WorldScene.play`), on campaigns named `audit_aged-save*` that the scripts removed when they ended. No model was called, no save or log of the owner's was read. Scripts and raw output are in `C:/Users/tstil/AppData/Local/Temp/claude/dad68772ed0cbd02/d2ae1f65-36c6-4be3-9744-2919d03b2cce/scratchpad/audit/work/aged_save/`.

## What was run

| run | what | lines | game days | level | wall s |
|---|---|---|---|---|---|
| base | the repository's bot (simbot.py, its four known faults mended in memory), warrior, seed 7; a probe every 500 lines | 6,000 | 217 | 35 | 733 |
| second | the same bot, mage, seed 23; a probe every 500 lines | 3,000 | 174 | 41 | 367 |
| third | the same bot, priest, seed 41; a probe every 500 lines | 2,000 | 59 | 19 | 113 |
| talk | one herbalist talked to for 400 lines (talk_aged.py) | 400 | 33 | | |
| pin, unpin | base's play again, twice: as it is, and with the traceback of every exception still alive let go after each line | 3,000 each | 107 | 22 | 251, 288 |
| mem, hold | base's play under tracemalloc (900 lines) and with a report of who holds what (1,500 lines) | | | | |
| recall_check, leak_check | one walk with a road stop; the gateway alone with one refused answer (no campaign) | | | | |

A probe copies the save, opens it in a fresh process the way the game does (`CampaignSession.open`, the scene, `run()` to its first prompt), plays the same plain lines in the start town at ten in the morning, times single store operations, and counts every table, every kv row and every list in the player and world records. The bot's play is the same in every run of one seed (line kinds equal in 3,000 of 3,000 lines between base and pin).

Limits of the method. The stub writes a few words where the model writes paragraphs, so every request size is a floor (the first round's real 42-line session had a townsperson request of 18,051 characters at the median where the stub's is about 14,100 at that age). The suite's stale-save detector is on under the stub and adds about 13% to a world-state read (3.86 ms against 3.35 ms shipped, measured). Times moved by a quarter and more between runs of the same play on this machine. The bot never took a missing-person contract, met a legendary, or used the field marks, so the stores of scenes1-14, scenes1-15 and scenes2-8 were never written and are not ranked.

## The answers in short

### 1. Which stores grow without bound, and how fast

Rates are per hundred typed lines of the base run: over the whole play, then over its second half where they differ.

| store | at 6,000 lines | a hundred lines | cap | note |
|---|---|---|---|---|
| the process's memory (one sitting) | 358 MB from 77 | 4.7 MB (4.5 late) | none | new finding aged-save-1: every answer a contract refuses pins the turn's whole stack, 0.72 MB each under the stub; with the tracebacks let go the same play stays at 96 to 104 MB |
| the page's transcript (one sitting; frontend-shipping-11) | 14,367 nodes | 240 nodes | none | its own measure: 24 ms a turn at 4,340 nodes (line 1,800 of one sitting), 77 ms at 9,940 (line 4,150) |
| logs/pulse.jsonl (engine5-5) | 500 KB | 8.3 KB (13 KB in the second run) | none | reaches the other logs' 5 MB mark near line 40,000 to 60,000 |
| people rows (npcs) | 249 rows, 497 KB; 128 of them gone | 4.0 rows, 8.2 KB (2.3 rows, 5.6 KB late) | none: a row is never deleted | new finding aged-save-7; in the second run the gone are 60 of 186 rows and 45% of the bytes |
| ...stock the people hold | 392 items, 139 KB | 6.5 items, 2.3 KB (9.0, 3.2 late) | none | most of it on road-stop traders who are gone |
| memory rows (npc_memory) | 1,017 rows, 128 KB, 124 holders | 17 rows, 2.1 KB | per person and kind (most for one: 30) | grows with the people; the rows of the gone stay |
| place rows (places table) | 145 rows, 128 KB | 2.3 rows, 2.1 KB | none | a road stop's row stays after the stop leaves the map (63 of 157 rows in the second run) |
| registry rows (entities) | 233 rows, 114 KB | 3.8 rows, 1.9 KB (2.2, 1.1 late) | offers and obligations only | new finding aged-save-8: 92 captive rows and 102 released stock rows are final and stay (194 of 233) |
| carcasses (people-6) | 337 in all, 199 in one place | 5.6 (7.7 late); 3.3 (4.9 late) in the largest | none | 18.6 KB |
| the scene's told news, in memory (world_py-13) | 449 entries, 46 KB | 7.5 entries, 0.77 KB | none (a sitting) | copied at every operation: 0.04 ms |
| the player's row | 23.6 KB from 8.0 | 0.26 KB | | the four below, and the character (one allocation record a level) |
| ...visited (world_py-8) | 100 | 1.6 (2.0 late) | none | one id a road stop |
| ...standing_told, field.towns, last_in, standing | 81, 71, 30 | 1.3, 1.2, 0.5 | none | new finding aged-save-9: the same key a road stop |
| world.spawns (engine3-9) | 10 rows, 2.9 KB | 0.17 rows, 48 B | none | the smallest of the named stores |
| refusals.SESSION, in memory | 137 | 2.3 | none (a sitting) | minor |

Capped, and the cap was reached or holds: the operations record (200 operations from about line 100, 29 to 31 KB, flat: shell2-10 guessed 161 KB), deeds (300 from line 2,500), news (300 from line 3,000), world.history (200 from line 3,500), threads (33 to 36 rows, 150 to 165 KB from line 1,000), the journal (event_log: 48 rows and 9.2 KB a hundred lines, its 6,000-row cap near line 12,500), moments seen (22 of 200), ended parts (118 of 500), the gateway's fallbacks (75 of 200), turns.jsonl (trimmed at 5 MB).

The database file: 220 KB new, 2.8 MB at 6,000 lines (44 KB a hundred lines over the play, 29 KB late; 66 KB in the second run, 49 KB in the third). Bytes are not the cost; what a line reads is (part 3).

### 2. Which request sections grow, and when a request would pass its ceiling or the slot

No request section grows without bound, and no request came near a limit that matters in play.

- The largest request of the three plays was a townsperson's: 21,937 characters in the 6,000-line play and 22,289 in the third (about 5,480 tokens at the played run's 4.07 characters a token); the talk run's largest was 24,595 (about 6,040 tokens). The slot holds 16,384 tokens, about 66,700 characters for the request and its answer. The largest ceiling in data/measured/prompt_ceilings.yaml is npc_conversation's 36,500 and nothing passed it. With the model's own text the same requests would be about 4,000 characters larger: still under both.
- Sections that rise and then stop: a townsperson's YOUR MEMORIES OF THEM (33 to about 470 characters with one person, 908 at the median late in the long play), PEOPLE YOU KNOW (1,490 to 2,150), WHAT THIS TOWN HAS (0 to 3,200, the town's own size), the mentor's WHAT THIS TOWN HAS (1,667 to 3,800), the moment's ALREADY SEEN IN THIS GAME (106 to 2,489 at 22 moments, about 103 characters a moment; the request shows the last 40 at most, so about 4,200), a fight reading's YOUR ABILITIES (387 to 1,265, by level). THIS CONVERSATION SO FAR stays at 2,300 to 2,500 through 400 lines with one person. YOU ALSO KNOW OF (llm-hot-12) is 322 to 1,030 characters with no trend by age. RIGHT NOW YOU ALSO KNOW rises at the median only because later talk is with guild clerks (THE GUILD'S RULES and six rank lines, about 2,100 characters).
- After line 1,000 the largest townsperson request rises by 16 characters a hundred lines in the long play, which is noise around a plateau. Read as a line, it would pass 36,500 after about 89,000 more lines and the slot after about 270,000; I do not think either figure means anything, since every part is windowed.
- The one ceiling passed is mentor_chat's 11,500: all 38 mentor_chat requests of the three plays are over it (12,555 to 16,106 characters; the first at line 67, 76 and 102), and the probe's are 11,324 and 12,109 on a new save. The ceiling is the test fixture's (the file says so) and nothing in play reads a task's own ceiling, so the player sees nothing (finding aged-save-10).
- What the player would see if a request did fill the slot: llm/llama.py:158 turns the server's refusal into a `too_big` failure (and llm/gateway.py:286 does the same for an answer cut off with the slot full); no retry and no looser last pass is sent (too_big ends the tries); the operation is taken back; the line closes with one of data/rules/failures.yaml `turn_not_taken` ("Nothing happens. Try that again.") or, when the reply to the player is what failed, the reply-not-come line; a passage gets its stand-in; a world operation fails without a word; logs/refusals.jsonl gets a `request_refused` row. The same line typed again builds the same request and is refused again: the player is asked to try again each time and is never told to leave it, because the leave-it line (`turn_not_possible`) is kept for the game's own faults (scenes/world.py:1170-1178). No request measured here comes within a third of that.

### 3. When the engine's own time passes 100 ms and 1 s a line

- A plain line on a new save: 8 to 17 ms (look, wait).
- 100 ms: the played search, move and wait lines pass a median of 100 ms between lines 500 and 1,000 (game day 25 to 36; search 119 ms in all three plays of seed 7). The probe's look and wait in the start town pass it between lines 1,500 and 2,000 in the base run (day 65 to 76), between 1,000 and 1,500 in the second (day 49 to 88), and not by line 2,000 in the third (day 59: 51 and 66 ms). The median over every line reaches 100 ms near line 2,500 to 3,000, because half the lines are fight rounds at 24 to 36 ms, which do not age. The cost follows game days, not lines: the talk run reached 184 ms a talk line in 400 lines over 33 days.
- After that it is flat: 100 to 190 ms for a plain line from line 2,000 to line 6,000, because what it reads (deeds, news, history, threads) is at its caps by line 3,500.
- 1 s: no kind of line reaches a median of 1 s in 6,000 lines. Talk lines are the slowest (median 215 to 630 ms, 95th percentile 0.27 to 1.07 s from line 1,000 on). Seven lines of the first 500 passed 1 s (the first line's map layout, and talk in a town still missing its buildings), then three in the next 5,500.
- Where an aged plain line's time goes (cProfile, six look and wait lines on the 6,000-line save, 194 ms a line under the profiler): the world state read whole 14 times a line, 56 ms (trace-save-5 said about 2 ms: finding aged-save-3); the facts for the prompt 54 ms, of which the news window 29 ms (it asks the map for a route for each of up to 300 news rows: finding aged-save-4); the pulse 33 ms; deep copies for the operation snapshots 21 ms; the world tables' own read 14 ms; the JSON schema of the answer built 26 times, 12 ms. One read of the world state: 0.03 ms new, 1.25 ms at line 500, 2.2 at 1,000, 3.0 at 2,000, 3.1 to 3.8 from 2,500 on.
- The budget's own estimate of the model's seconds for the same lines did not move with age: median 5 to 7 s, largest 34 to 49 s, none over 55 s, no line not taken. The engine at 0.1 to 0.2 s is 2 to 3% of a typical turn.

### 4. What opening an aged save costs

Nothing that grows. The store opens in 7 to 14 ms and the game reaches its first prompt in 126 to 245 ms at every age from 0 to 6,000 lines (imports, 0.75 to 1.05 s, and the data check are not in that figure). The first typed line costs 1.2 to 1.9 s whenever the save opens outside a fight, at every age: the map's spring layout (speed-turn-5), 1.07 to 2.06 s cold with 127 to 129 top-level places and no trend by age; inside a fight it is 64 to 164 ms. `#check` (validate_campaign) goes from 1.3 to 18 ms; the panes stay under 22 ms but for one reading of `#places` (151 ms at line 5,500, 14 ms before and after).

### 5. The thirteen first-round findings, ranked by what was measured

| rank | finding | measured | verdict |
|---|---|---|---|
| 1 | trace-save-5 (the world read whole 14 times a line) | 0.03 ms a read new, 3.1 to 3.8 ms from line 2,500: 45 to 55 ms of every plain line, the largest single part of the 100 to 190 ms | re-rated up (aged-save-3) |
| 2 | frontend-shipping-11 (transcript never trimmed) | 240 nodes a hundred lines, no cap, one sitting | stands; the only named store whose cost keeps rising with no cap |
| 3 | speed-turn-5 (first line's layout) | 1.2 to 1.9 s at every age, not growing in 6,000 lines (129 top-level places) | stands as rated; its growth claim was not seen |
| 4 | engine5-5 (pulse.jsonl) | 8.3 to 13 KB a hundred lines; 0.5 MB at 6,000 | stands, low |
| 5 | people-6 (carcasses) | 199 in one place at 6,000 lines, 4.9 a hundred lines there late | stands, low |
| 6 | world_py-13 (_news_seen) | 449 entries, 46 KB a sitting; copy 0.04 ms an operation | stands, low |
| 7 | world_py-8 (visited) | 100 entries, 1.8 KB | stands, low; four more stores of its kind (aged-save-9), and a bug from the same cause (aged-save-2) |
| 8 | shell2-10 (operations record) | flat at 29 to 31 KB from line 100; a read 0.22 to 0.29 ms | lower than estimated (161 KB): the last of the speed items |
| 9 | engine3-9 (spawns) | 10 rows, 2.9 KB at 217 days | stands, the smallest |
| 10 | llm-hot-12 (YOU ALSO KNOW OF) | 322 to 1,030 characters, no trend by age | not a growth finding: its size is by speaker, not by age |
| 11-13 | scenes1-14 (arcs), scenes1-15 (legendaries), scenes2-8 (field marks, item history) | never written in 6,000, 3,000 and 2,000 lines of the bot's play | not measurable this way |

Not on the list and larger than all of them: the pinned stacks (aged-save-1, memory), the rows of the gone (aged-save-7, the largest store with no cap in the save), and the sixteen captive names, used up between lines 1,000 and 1,500 by the warrior and the priest and between 2,500 and 3,000 by the mage (aged-save-5, aged-save-6).

## 6. Every store at every 500 lines (base run: warrior, seed 7)

Counts unless the row says bytes. An empty cell: not there yet.

| store | 0 | 500 | 1,000 | 1,500 | 2,000 | 2,500 | 3,000 | 3,500 | 4,000 | 4,500 | 5,000 | 5,500 | 6,000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| game day | 1 | 25 | 36 | 65 | 76 | 88 | 107 | 131 | 161 | 172 | 179 | 196 | 217 |
| level | 1 | 6 | 9 | 13 | 16 | 19 | 22 | 27 | 29 | 30 | 30 | 32 | 35 |
| database file, KB | 4 | 632 | 836 | 1,104 | 1,476 | 1,732 | 1,952 | 2,176 | 2,352 | 2,516 | 2,568 | 2,684 | 2,788 |
| process memory, MB (a sitting) | 77 | 96 | 107 | 135 | 163 | 195 | 224 | 239 | 270 | 292 | 304 | 328 | 358 |
| things shown on the page so far (frontend-shipping-11) | 0 | 1,071 | 2,214 | 3,395 | 4,634 | 5,733 | 6,909 | 8,086 | 9,263 | 10,580 | 11,888 | 13,209 | 14,367 |
| journal rows (event_log; cap 6,000) | 5 | 205 | 402 | 680 | 1,035 | 1,316 | 1,606 | 1,854 | 2,085 | 2,294 | 2,462 | 2,670 | 2,880 |
| journal bytes | 1,017 | 38,359 | 75,171 | 128,163 | 198,634 | 252,070 | 309,224 | 358,628 | 400,522 | 441,369 | 474,298 | 515,437 | 554,691 |
| people rows (npcs) | 8 | 41 | 48 | 96 | 130 | 157 | 180 | 203 | 220 | 229 | 233 | 241 | 249 |
| ...of them gone | 0 | 1 | 4 | 22 | 55 | 74 | 88 | 97 | 108 | 115 | 116 | 123 | 128 |
| people bytes | 6,261 | 47,764 | 64,619 | 144,192 | 221,202 | 279,588 | 327,759 | 376,663 | 416,756 | 444,017 | 449,901 | 475,801 | 497,011 |
| stock items held by people (all) |  | 16 | 28 | 68 | 68 | 90 | 122 | 176 | 232 | 296 | 304 | 360 | 392 |
| memory rows (npc_memory) | 0 | 75 | 133 | 255 | 322 | 386 | 483 | 597 | 726 | 800 | 823 | 935 | 1,017 |
| ...most for one person | 0 | 8 | 12 | 15 | 17 | 20 | 25 | 26 | 26 | 26 | 26 | 29 | 30 |
| place rows (places table) | 7 | 28 | 34 | 50 | 52 | 58 | 71 | 94 | 103 | 117 | 122 | 141 | 145 |
| registry rows (entities) | 3 | 24 | 40 | 75 | 118 | 141 | 166 | 186 | 205 | 215 | 216 | 222 | 233 |
| ...captives ever (rows of kind captive) | 0 | 0 | 3 | 18 | 52 | 68 | 81 | 85 | 88 | 88 | 88 | 88 | 92 |
| ...stock rows released |  | 12 | 20 | 33 | 40 | 46 | 58 | 69 | 81 | 88 | 90 | 99 | 102 |
| threads rows | 0 | 22 | 32 | 35 | 35 | 36 | 33 | 32 | 35 | 35 | 33 | 34 | 35 |
| deeds rows (cap 300) | 0 | 53 | 119 | 175 | 266 | 300 | 300 | 300 | 300 | 300 | 300 | 300 | 300 |
| news rows (cap 300) | 0 | 56 | 90 | 172 | 198 | 248 | 300 | 300 | 300 | 300 | 300 | 300 | 300 |
| world.history (cap 200) | 0 | 25 | 44 | 92 | 110 | 137 | 172 | 200 | 200 | 200 | 200 | 200 | 200 |
| world.spawns (engine3-9) | 0 | 0 | 1 | 2 | 3 | 4 | 6 | 6 | 7 | 7 | 8 | 10 | 10 |
| world.spawns bytes | 2 | 2 | 233 | 459 | 1,014 | 1,241 | 1,678 | 1,678 | 2,222 | 2,222 | 2,444 | 2,883 | 2,881 |
| world.moments_seen (cap 200) | 1 | 3 | 5 | 6 | 8 | 11 | 13 | 15 | 16 | 18 | 17 | 19 | 22 |
| world.parts_ended (cap 500) |  | 12 | 20 | 34 | 41 | 47 | 60 | 71 | 88 | 97 | 101 | 112 | 118 |
| kv world_state bytes | 508 | 6,401 | 10,640 | 19,674 | 23,471 | 29,294 | 36,258 | 42,085 | 44,452 | 45,737 | 45,779 | 47,370 | 48,269 |
| kv operations bytes (shell2-10; cap 200 operations) | 11,710 | 28,513 | 28,647 | 29,440 | 28,961 | 30,119 | 29,305 | 28,672 | 29,126 | 29,472 | 29,051 | 28,925 | 31,037 |
| kv dungeons bytes | 79,418 | 75,032 | 75,032 | 80,098 | 74,417 | 74,417 | 74,749 | 80,708 | 78,844 | 78,844 | 76,850 | 76,850 | 79,750 |
| kv arcs bytes (scenes1-14) | never written |  |  |  |  |  |  |  |  |  |  |  |  |
| kv legendaries bytes (scenes1-15) | never written |  |  |  |  |  |  |  |  |  |  |  |  |
| player row bytes | 8,017 | 10,362 | 10,352 | 12,351 | 12,951 | 14,895 | 14,470 | 15,313 | 15,982 | 18,415 | 19,875 | 22,437 | 23,562 |
| player.visited (world_py-8) | 2 | 11 | 14 | 27 | 28 | 30 | 41 | 56 | 67 | 77 | 82 | 96 | 100 |
| player.standing_told | 2 | 8 | 10 | 18 | 19 | 20 | 27 | 42 | 48 | 58 | 63 | 77 | 81 |
| player.field.towns | 1 | 4 | 5 | 12 | 13 | 14 | 19 | 32 | 38 | 48 | 53 | 67 | 71 |
| player.last_in | 0 | 4 | 5 | 9 | 11 | 12 | 14 | 17 | 21 | 25 | 27 | 30 | 30 |
| player.character.item_history (scenes2-8) | never written |  |  |  |  |  |  |  |  |  |  |  |  |
| carcasses, all places (people-6) | 0 | 19 | 42 | 52 | 72 | 89 | 107 | 118 | 149 | 205 | 271 | 310 | 337 |
| carcasses, the largest list | 0 | 17 | 35 | 35 | 35 | 41 | 51 | 51 | 51 | 106 | 170 | 199 | 199 |
| board postings, the largest board | 7 | 11 | 16 | 23 | 26 | 30 | 35 | 36 | 36 | 38 | 38 | 40 | 40 |
| scene._news_seen entries (world_py-13) |  | 40 | 64 | 122 | 150 | 183 | 230 | 262 | 326 | 351 | 366 | 397 | 449 |
| scene._news_seen bytes copied an operation |  | 3,582 | 6,183 | 12,079 | 14,915 | 18,375 | 23,242 | 26,611 | 33,787 | 36,066 | 37,732 | 40,939 | 46,407 |
| pulse.jsonl bytes (engine5-5) |  | 42,112 | 77,288 | 136,733 | 193,140 | 238,570 | 290,534 | 334,147 | 391,057 | 415,790 | 431,213 | 469,116 | 500,493 |
| module engine.refusals.SESSION |  | 26 | 32 | 47 | 60 | 75 | 95 | 102 | 111 | 119 | 123 | 132 | 137 |
| module engine.combat._LIFT_CACHE | 0 | 30 | 40 | 58 | 60 | 74 | 100 | 132 | 167 | 167 | 168 | 179 | 210 |

## 7. The save, opening it and a line's time at every 500 lines (base run)

| lines | day | lvl | db KB | open store ms | open run() ms | open total ms | first line ms | map layout ms (cold) | look ms (probe) | wait ms (probe) | talk ms (probe) | played median ms | played mean ms | played p95 ms | played max ms | process MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 1 | 220 | 9.4 | 128.54 | 145.09 | 89.53 | 1068.91 | 7.75 | 14.45 | 12.41 |  |  |  |  | 77 |
| 500 | 25 | 6 | 632 | 10.0 | 110.8 | 127.97 | 1304.46 | 1922.83 | 40.82 | 36.55 | 40.27 | 31.6 | 70.1 | 161.5 | 2055.7 | 96 |
| 1,000 | 36 | 9 | 836 | 9.36 | 125.46 | 142.11 | 110.99 | 1958.65 | 51.33 | 51.49 | 102.52 | 50.3 | 65.5 | 165.1 | 274.7 | 107 |
| 1,500 | 65 | 13 | 1,132 | 8.92 | 136.09 | 152.29 | 64.22 | 1954.64 | 63.79 | 95.31 | 95.5 | 61.1 | 95.9 | 252.6 | 1230.5 | 135 |
| 2,000 | 76 | 16 | 1,480 | 9.23 | 135.56 | 152.59 | 111.48 | 1938.72 | 100.18 | 115.46 | 84.88 | 91.9 | 108.6 | 347.6 | 491.9 | 163 |
| 2,500 | 88 | 19 | 1,732 | 8.3 | 128.64 | 144.08 | 1210.18 | 1901.19 | 69.35 | 110.32 | 116.03 | 90.6 | 113.5 | 307.1 | 981.0 | 195 |
| 3,000 | 107 | 22 | 1,952 | 10.47 | 145.86 | 164.0 | 124.18 | 2000.66 | 112.11 | 120.16 | 132.1 | 103.2 | 115.6 | 311.6 | 1061.6 | 224 |
| 3,500 | 131 | 27 | 2,176 | 9.32 | 144.17 | 161.24 | 121.24 | 1977.63 | 137.75 | 124.19 | 173.46 | 72.2 | 108.1 | 293.8 | 690.9 | 239 |
| 4,000 | 161 | 29 | 2,352 | 8.08 | 123.28 | 139.17 | 1269.08 | 1917.46 | 184.4 | 132.44 | 80.16 | 89.6 | 118.0 | 364.4 | 710.5 | 270 |
| 4,500 | 172 | 30 | 2,516 | 7.13 | 111.97 | 125.8 | 1367.45 | 1984.47 | 191.68 | 126.58 | 178.62 | 101.7 | 111.8 | 305.2 | 494.6 | 292 |
| 5,000 | 179 | 30 | 2,568 | 14.28 | 171.82 | 193.98 | 74.89 | 2011.28 | 73.3 | 80.8 | 83.33 | 98.6 | 103.4 | 205.6 | 785.2 | 304 |
| 5,500 | 196 | 32 | 2,684 | 11.21 | 187.99 | 211.42 | 1854.2 | 1317.64 | 92.73 | 101.53 | 64.28 | 99.4 | 112.7 | 293.3 | 533.0 | 328 |
| 6,000 | 217 | 35 | 2,804 | 7.68 | 139.51 | 153.94 | 1510.24 | 2059.37 | 110.36 | 116.23 | 79.43 | 46.9 | 97.8 | 307.0 | 740.4 | 358 |

Open = CampaignSession.open + the scene + run() to its first prompt, in a fresh process on a copy of the save (imports and the data check not counted). Probe lines are played in that process at the same town at ten in the morning; 'played' is every line of the window before the checkpoint, as the bot played it.

Engine milliseconds a line by what the line was (median / p95 (count)), and the budget's own estimate of model seconds on the 3060 for the same lines:

| lines | fight | search | move | wait | talk | buy | release | sell | attack | est. model s median | max | lines est > 55 s | optional calls dropped | deferred | stand-ins | lines not taken | crashes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | 23.8 / 57.9 (251) | 58.8 / 176.8 (108) | 58.4 / 174.7 (82) | 67.4 / 163.8 (39) | 1040.4 / 1272.5 (10) | 47.6 / 59.0 (10) |  |  |  | 6.0 | 43 | 0 | 7 | 0 | 3 | 0 | 0 |
| 1,000 | 24.4 / 75.1 (299) | 119.2 / 185.6 (96) | 90.1 / 177.9 (70) | 123.5 / 199.9 (25) | 214.8 / 274.7 (6) | 70.4 / 70.4 (1) | 74.5 / 77.0 (2) |  | 73.4 / 73.4 (1) | 5.0 | 42 | 0 | 2 | 0 | 0 | 0 | 0 |
| 1,500 | 26.0 / 92.5 (277) | 138.9 / 221.0 (87) | 117.5 / 250.0 (71) | 149.9 / 280.5 (17) | 298.0 / 1070.3 (23) | 82.8 / 107.0 (7) | 90.6 / 105.4 (7) |  | 93.3 / 154.8 (6) | 6.0 | 39 | 0 | 5 | 0 | 6 | 0 | 0 |
| 2,000 | 28.1 / 131.7 (249) | 140.6 / 230.3 (79) | 128.3 / 294.4 (55) | 155.0 / 261.9 (21) | 367.9 / 485.6 (33) | 89.9 / 176.1 (15) | 113.8 / 129.4 (21) | 97.3 / 177.2 (12) | 111.6 / 182.8 (12) | 7.0 | 35 | 0 | 2 | 0 | 1 | 0 | 0 |
| 2,500 | 28.8 / 109.4 (241) | 143.6 / 295.5 (106) | 141.9 / 299.1 (67) | 167.1 / 271.8 (22) | 404.8 / 863.4 (21) | 106.4 / 128.2 (22) | 119.2 / 210.1 (11) | 83.1 / 85.5 (3) | 121.9 / 234.5 (6) | 6.0 | 41 | 0 | 5 | 0 | 1 | 0 | 0 |
| 3,000 | 29.2 / 126.2 (250) | 142.4 / 311.6 (102) | 146.1 / 275.0 (68) | 172.0 / 289.3 (23) | 394.3 / 1061.6 (17) | 107.8 / 170.6 (17) | 121.3 / 227.6 (5) | 107.3 / 238.9 (10) | 120.4 / 127.5 (7) | 7.0 | 37 | 0 | 6 | 0 | 3 | 0 | 0 |
| 3,500 | 30.1 / 114.0 (291) | 182.0 / 270.9 (51) | 160.4 / 362.2 (74) | 187.8 / 376.2 (25) | 537.1 / 690.9 (13) | 119.7 / 147.8 (28) | 128.5 / 129.7 (3) | 110.7 / 176.8 (7) | 141.2 / 141.2 (1) | 5.0 | 34 | 0 | 1 | 0 | 3 | 0 | 0 |
| 4,000 | 29.9 / 120.0 (269) | 131.1 / 266.7 (110) | 157.5 / 463.5 (59) | 208.0 / 318.8 (28) | 475.4 / 710.5 (20) | 110.0 / 176.3 (3) | 107.4 / 107.6 (3) |  |  | 7.0 | 43 | 0 | 11 | 0 | 6 | 0 | 0 |
| 4,500 | 73.2 / 125.8 (242) | 125.5 / 282.4 (209) | 194.4 / 387.3 (19) | 207.5 / 207.5 (1) | 443.5 / 482.2 (10) | 138.2 / 143.6 (4) |  | 179.4 / 310.2 (4) |  | 7.0 | 40 | 0 | 2 | 0 | 1 | 0 | 0 |
| 5,000 | 36.3 / 131.4 (260) | 127.4 / 172.8 (221) | 231.1 / 466.7 (8) | 428.6 / 563.7 (2) | 630.6 / 785.2 (3) | 127.9 / 137.0 (4) |  | 157.0 / 157.0 (1) |  | 7.0 | 35 | 0 | 4 | 0 | 0 | 0 | 0 |
| 5,500 | 32.0 / 199.3 (265) | 130.7 / 238.7 (128) | 181.5 / 421.0 (36) | 191.5 / 295.6 (26) | 509.8 / 533.0 (6) | 125.3 / 148.8 (7) |  | 130.2 / 501.6 (7) |  | 7.0 | 49 | 0 | 2 | 0 | 1 | 0 | 0 |
| 6,000 | 31.3 / 85.6 (303) | 156.2 / 307.0 (69) | 157.7 / 417.4 (46) | 141.0 / 257.7 (37) | 430.3 / 740.4 (15) | 120.0 / 286.5 (19) | 154.5 / 161.6 (3) | 98.0 / 98.0 (1) | 115.0 / 115.0 (1) | 5.0 | 38 | 0 | 6 | 0 | 4 | 0 | 0 |

Lines of the play whose engine time passed a mark, by window:

| lines | n | mean ms | > 100 ms | share | > 250 ms | > 1 s | slowest ms |
|---|---|---|---|---|---|---|---|
| 1-500 | 500 | 70.1 | 80 | 16% | 10 | 7 | 2,056 |
| 501-1000 | 500 | 65.5 | 115 | 23% | 2 | 0 | 275 |
| 1001-1500 | 500 | 95.9 | 169 | 34% | 26 | 2 | 1,230 |
| 1501-2000 | 500 | 108.6 | 239 | 48% | 44 | 0 | 492 |
| 2001-2500 | 500 | 113.5 | 241 | 48% | 44 | 0 | 981 |
| 2501-3000 | 500 | 115.6 | 257 | 51% | 43 | 1 | 1,062 |
| 3001-3500 | 500 | 108.1 | 217 | 43% | 39 | 0 | 691 |
| 3501-4000 | 500 | 118.0 | 239 | 48% | 50 | 0 | 710 |
| 4001-4500 | 500 | 111.8 | 253 | 51% | 38 | 0 | 495 |
| 4501-5000 | 500 | 103.4 | 246 | 49% | 21 | 0 | 785 |
| 5001-5500 | 500 | 112.7 | 248 | 50% | 38 | 0 | 533 |
| 5501-6000 | 500 | 97.8 | 178 | 36% | 36 | 0 | 740 |

Single store operations on the aged copy (median of 20, ms):

| lines | load_world_state | load_operations | load_player | save_player | load_arcs | begin_turn | refresh_present | validate_campaign |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.03 | 0.06 | 0.06 | 0.12 | 0.0 | 0.07 | 0.15 | 1.32 |
| 500 | 1.25 | 0.23 | 0.15 | 0.32 | 0.01 | 0.16 | 0.3 | 6.07 |
| 1,000 | 2.2 | 0.26 | 0.17 | 0.31 | 0.01 | 0.17 | 0.26 | 8.26 |
| 1,500 | 2.55 | 0.24 | 0.18 | 0.37 | 0.01 | 0.17 | 0.32 | 10.38 |
| 2,000 | 2.99 | 0.23 | 0.19 | 0.39 | 0.01 | 0.18 | 0.35 | 12.73 |
| 2,500 | 3.21 | 0.24 | 0.21 | 0.41 | 0.01 | 0.16 | 0.38 | 13.36 |
| 3,000 | 3.25 | 0.23 | 0.2 | 0.39 | 0.01 | 0.16 | 0.35 | 13.97 |
| 3,500 | 3.45 | 0.23 | 0.2 | 0.4 | 0.01 | 0.16 | 0.37 | 15.56 |
| 4,000 | 3.51 | 0.22 | 0.21 | 0.41 | 0.01 | 0.17 | 0.38 | 15.36 |
| 4,500 | 3.72 | 0.25 | 0.23 | 0.45 | 0.01 | 0.18 | 0.65 | 17.71 |
| 5,000 | 3.81 | 0.22 | 0.26 | 0.49 | 0.01 | 0.18 | 0.36 | 16.56 |
| 5,500 | 1.97 | 0.23 | 0.25 | 0.31 | 0.0 | 0.09 | 0.28 | 10.2 |
| 6,000 | 3.13 | 0.29 | 0.26 | 0.57 | 0.01 | 0.17 | 0.34 | 15.68 |

Pane commands (ms, the quickest of three) and the payload of two panes (characters of JSON):

| lines | #character | #check | #inventory | #journal | #map | #party | #places | #quests | #rumors | #standing | journal payload | places payload |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1.6 | 2.94 | 1.14 | 1.39 | 1.74 | 1.27 | 1.71 | 1.15 | 1.4 | 1.22 | 70 | 1,170 |
| 500 | 3.81 | 9.91 | 3.12 | 4.94 | 4.0 | 2.91 | 7.32 | 2.67 | 6.9 | 4.57 | 1,389 | 1,644 |
| 1,000 | 3.76 | 12.1 | 3.43 | 6.19 | 4.07 | 2.97 | 8.74 | 2.98 | 9.64 | 5.76 | 2,470 | 1,922 |
| 1,500 | 4.24 | 14.83 | 3.71 | 6.75 | 4.59 | 3.34 | 10.51 | 3.27 | 11.26 | 6.33 | 1,932 | 2,179 |
| 2,000 | 5.59 | 16.43 | 4.65 | 8.94 | 5.84 | 3.91 | 13.53 | 4.23 | 14.01 | 7.74 | 2,639 | 2,179 |
| 2,500 | 4.55 | 17.24 | 4.76 | 7.38 | 4.58 | 3.9 | 11.85 | 4.14 | 13.58 | 7.76 | 2,248 | 2,179 |
| 3,000 | 5.63 | 18.61 | 5.16 | 9.37 | 6.03 | 4.2 | 13.91 | 4.63 | 15.04 | 7.93 | 2,054 | 2,749 |
| 3,500 | 6.04 | 20.56 | 5.16 | 9.21 | 6.16 | 4.84 | 13.82 | 4.63 | 14.96 | 8.47 | 2,052 | 3,312 |
| 4,000 | 6.34 | 20.96 | 4.96 | 10.17 | 6.12 | 4.75 | 14.52 | 4.67 | 16.01 | 8.59 | 2,408 | 3,462 |
| 4,500 | 6.13 | 20.61 | 4.78 | 10.02 | 6.18 | 5.25 | 14.31 | 5.2 | 16.31 | 9.38 | 2,909 | 3,759 |
| 5,000 | 5.82 | 21.07 | 5.28 | 9.72 | 5.85 | 6.12 | 13.98 | 4.68 | 17.18 | 8.84 | 2,904 | 3,759 |
| 5,500 | 3.89 | 12.15 | 3.04 | 5.71 | 3.89 | 5.32 | 151.37 | 2.74 | 17.09 | 5.6 | 2,265 | 4,073 |
| 6,000 | 6.74 | 21.74 | 5.49 | 9.83 | 6.74 | 5.35 | 14.52 | 5.71 | 17.01 | 9.05 | 1,651 | 3,909 |

## 8. Requests: every task's size by age, and the sections that moved (base run)

Characters of the whole request (system and user), first tries only.

| task | calls | system chars | first window median | max | last window median | max | largest in the play | largest: chars / 100 lines (whole) | (second half) | ceiling (chars) | calls over it (first at line) | largest in tokens (4.07 chars a token) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| npc_conversation | 342 | 8,857 | 14,079 | 15,820 | 19,242 | 21,372 | 21,937 | 106.1 | 16.4 | 36,500 | 0 | 5,390 |
| pulse_thread | 5 | 6,568 |  |  | 16,549 | 16,549 | 20,079 | 6.0 | 6.0 |  |  | 4,933 |
| interpret_action | 2,857 | 11,976 | 13,214 | 16,040 | 13,524 | 15,370 | 19,951 | 19.4 | -55.0 |  |  | 4,902 |
| mentor_chat | 11 | 6,246 | 14,261 | 14,798 | 13,730 | 13,740 | 14,798 | 0.0 | 0.0 | 11,500 | 11 (102) | 3,636 |
| narrate | 1,614 | 5,185 | 7,200 | 11,438 | 7,597 | 9,804 | 11,438 | -22.2 | 29.1 |  |  | 2,810 |
| mentor_speech | 10 | 6,282 | 10,120 | 10,418 | 9,196 | 9,209 | 11,254 | -7.3 | -7.3 |  |  | 2,765 |
| discovery | 2 | 1,644 |  |  | 10,520 | 10,520 | 10,603 | 0.0 | 0.0 |  |  | 2,605 |
| thread_telling | 93 | 1,366 | 9,760 | 10,363 | 9,885 | 10,211 | 10,383 | -4.1 | -5.7 |  |  | 2,551 |
| combat_narrate | 3,148 | 6,430 | 8,079 | 8,355 | 8,136 | 8,665 | 8,971 | -0.1 | 1.7 |  |  | 2,204 |
| dialogue_frame | 178 | 5,120 | 7,244 | 8,313 | 7,051 | 7,596 | 8,313 | 0.3 | 20.7 | 11,000 | 0 | 2,043 |
| moment | 70 | 3,058 | 5,799 | 6,583 | 7,249 | 7,261 | 7,899 | 26.3 | 62.3 |  |  | 1,941 |
| road_event | 66 | 3,049 | 6,974 | 6,974 | 6,943 | 7,216 | 7,611 | 7.3 | -7.6 |  |  | 1,870 |
| situation_parts | 135 | 3,910 | 6,285 | 6,859 | 6,217 | 6,406 | 7,078 | -3.3 | -22.0 |  |  | 1,739 |
| combat_opening | 902 | 3,543 | 5,086 | 5,291 | 5,372 | 5,709 | 6,077 | 8.5 | -9.9 |  |  | 1,493 |
| mentor_voice | 6 | 2,848 | 5,135 | 5,135 | 5,551 | 5,564 | 5,564 | 0.0 | 0.0 |  |  | 1,367 |
| combat_aftermath | 767 | 3,725 | 4,828 | 5,087 | 4,961 | 5,278 | 5,310 | -0.8 | -3.1 |  |  | 1,305 |
| goddess_line | 30 | 4,009 | 5,017 | 5,017 | 5,018 | 5,020 | 5,056 | -0.2 | 0.1 |  |  | 1,242 |
| combat_interpret | 3,197 | 3,047 | 3,522 | 3,554 | 4,286 | 4,435 | 4,435 | 14.4 | 36.1 |  |  | 1,090 |
| ruling | 8 | 2,321 |  |  | 4,408 | 4,408 | 4,408 | 2.8 | 1.8 |  |  | 1,083 |
| generate_passive_mechanics | 1 | 1,905 |  |  |  |  | 4,071 | 0.0 | 0.0 |  |  | 1,000 |
| populate_place | 68 | 1,027 | 2,591 | 3,763 | 2,128 | 2,128 | 3,763 | -14.1 | -17.6 |  |  | 925 |
| event_judge | 428 | 2,429 | 3,371 | 3,527 | 2,890 | 3,381 | 3,598 | -1.6 | -2.1 |  |  | 884 |
| generate_lessons | 7 | 1,581 |  |  | 3,303 | 3,502 | 3,502 | 0.0 | 0.0 |  |  | 860 |
| npc_profile | 110 | 1,065 | 2,622 | 2,697 | 1,666 | 1,668 | 2,698 | -16.8 | -5.9 | 3,000 | 0 | 663 |
| lesson_want | 5 | 884 |  |  | 966 | 966 | 966 | 0.0 | 0.0 |  |  | 237 |
| stranger_read | 1 | 598 | 698 | 698 | 698 | 698 | 698 | 0.0 | 0.0 |  |  | 171 |
| audit_compare | 61 | 427 |  |  | 583 | 588 | 588 | 0.1 | 0.0 |  |  | 144 |
| situation_agree | 13 | 389 | 540 | 580 | 571 | 571 | 580 | -0.2 | -0.2 |  |  | 143 |
| audit_meaning | 61 | 233 |  |  | 417 | 468 | 542 | 1.0 | 1.0 |  |  | 133 |
| loot_name | 2 | 171 |  |  | 245 | 245 | 296 | 0.0 | 0.0 |  |  | 73 |

The slot holds 16,384 tokens (about 66,700 characters at the played run's 4.07 characters a token) for the request and its answer together.

Sections of the requests, by task: the window's median characters where the section is present, first window, middle, last, and the largest seen. Only sections that grew by 150 characters or more between the first and the last window, or whose largest is 2,000 or more.

| task | section | calls with it | median, first window | middle | last window | largest | median: chars / 100 lines |
|---|---|---|---|---|---|---|---|
| npc_conversation | RIGHT NOW YOU ALSO KNOW | 342 | 1,554 | 4,479 | 4,930 | 5,623 | 61.4 |
| moment | ALREADY SEEN IN THIS GAME | 70 | 232 | 1,367 | 2,329 | 2,489 | 38.1 |
| npc_conversation | YOUR MEMORIES OF THEM | 342 | 33 | 112 | 908 | 1,308 | 15.9 |
| npc_conversation | PEOPLE YOU KNOW | 342 | 38 | 69 | 822 | 1,355 | 14.3 |
| npc_conversation | WHAT THIS TOWN HAS | 18 | 1,208 | 1,635 | 1,970 | 2,362 | 50.8 |
| combat_interpret | YOUR ABILITIES | 3,197 | 387 | 389 | 1,142 | 1,265 | 13.7 |
| mentor_chat | WHAT THIS TOWN HAS | 11 | 2,046 | 2,524 | 2,524 | 2,524 | 95.6 |
| interpret_action | CURRENT PLACE | 2,857 | 500 | 1,491 | 809 | 1,950 | 5.6 |
| npc_conversation | WHAT YOU KNOW | 342 | 42 | 304 | 304 | 1,061 | 4.8 |
| mentor_speech | STATE | 10 | 8 | 132 | 225 | 225 | 4.3 |
| road_event | MUST BE | 66 | 38 | 188 | 219 | 703 | 3.3 |
| thread_telling | PLACES | 93 | 4,207 | 4,207 | 4,229 | 4,229 | 0.4 |
| interpret_action | FOR SALE | 2,857 | 22 | 22 | 22 | 4,915 | 0.0 |
| thread_telling | CREATURES | 93 | 3,311 | 3,331 | 3,311 | 3,393 | 0.0 |

The same lines at every age (the probe: a look, a wait and three lines of talk at the same town): the request's characters, by task.

| line | task | 0 | 500 | 1000 | 1500 | 2000 | 2500 | 3000 | 3500 | 4000 | 4500 | 5000 | 5500 | 6000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| look_home | dialogue_frame | 8,183 |  |  |  |  |  |  | 8,356 | 8,260 | 8,378 | 7,549 | 7,516 | 7,573 |
| look_home | interpret_action |  | 15,028 | 15,077 | 15,178 | 15,288 | 14,998 | 15,060 | 15,010 | 15,020 | 15,246 | 15,193 | 14,986 | 15,033 |
| look_home | mentor_speech | 10,442 |  |  |  |  |  |  | 11,254 | 11,254 | 11,254 | 9,209 |  |  |
| look_home | mentor_voice | 3,853 |  |  |  |  |  |  | 5,564 | 5,564 | 5,564 | 5,564 | 5,176 | 5,162 |
| look_home | moment | 4,987 |  | 6,192 | 6,158 | 6,689 |  |  |  |  | 7,167 |  |  |  |
| look_home | narrate | 7,492 | 9,116 | 9,844 | 9,474 | 10,035 | 10,023 | 9,285 | 9,633 | 9,474 | 9,989 | 9,658 | 9,650 | 9,533 |
| look_home | populate_place | 3,531 |  |  |  |  |  |  |  |  |  |  |  |  |
| look_home | situation_agree |  |  |  |  | 563 |  |  |  | 564 |  |  |  |  |
| look_home | situation_parts |  |  | 6,639 |  | 6,640 | 6,814 |  | 6,717 | 6,703 | 6,561 |  |  |  |
| look_home | stranger_read | 692 |  |  |  |  |  |  |  |  |  |  |  |  |
| look_home | thread_telling |  |  | 10,010 | 10,310 | 9,830 | 10,206 |  | 10,053 | 9,729 | 9,902 |  |  |  |
| talk_home | dialogue_frame |  | 7,591 | 7,586 | 7,586 | 7,683 | 7,616 | 7,552 |  |  |  |  |  |  |
| talk_home | mentor_chat | 11,324 | 11,920 | 12,991 | 13,335 | 13,595 | 13,581 | 12,808 | 13,833 | 13,733 | 13,909 | 13,955 | 13,812 | 13,169 |
| talk_home | mentor_speech |  |  |  |  |  |  |  | 9,178 | 9,178 | 9,178 |  |  |  |
| talk_home | mentor_voice |  |  |  |  |  |  |  |  |  |  | 5,520 | 5,140 | 5,126 |
| wait_home | interpret_action |  | 15,036 | 15,085 | 15,186 | 15,296 | 15,006 | 15,068 | 15,018 | 15,028 | 15,254 | 15,201 | 14,994 | 15,041 |
| wait_home | mentor_chat | 12,109 |  |  |  |  |  |  |  |  |  |  |  |  |
| wait_home | mentor_speech |  |  |  |  |  |  |  |  |  |  |  | 8,836 | 8,822 |
| wait_home | narrate |  | 8,982 | 8,894 | 8,900 | 9,309 | 9,081 | 8,838 | 9,021 | 8,881 | 8,947 | 9,146 | 8,882 | 9,082 |

...and the sections of those requests that moved by 150 characters or more (largest of the line's calls):

| line | task | section | 0 | 500 | 1000 | 1500 | 2000 | 2500 | 3000 | 3500 | 4000 | 4500 | 5000 | 5500 | 6000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| look_home | thread_telling | PLACES | 0 | 0 | 4,207 | 4,207 | 4,207 | 4,207 | 0 | 4,207 | 4,207 | 4,229 | 0 | 0 | 0 |
| look_home | thread_telling | CREATURES | 0 | 0 | 3,336 | 3,377 | 3,315 | 3,352 | 0 | 3,331 | 3,311 | 3,315 | 0 | 0 | 0 |
| talk_home | mentor_chat | WHAT THIS TOWN HAS | 1,667 | 2,145 | 2,922 | 3,459 | 3,388 | 3,457 | 3,214 | 3,539 | 3,460 | 3,473 | 3,678 | 3,801 | 3,531 |
| look_home | moment | ALREADY SEEN IN THIS GAME | 106 | 0 | 610 | 721 | 939 | 0 | 0 | 0 | 0 | 1,949 | 0 | 0 | 0 |
| look_home | interpret_action | CURRENT PLACE | 0 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 | 1,704 |
| look_home | populate_place | PEOPLE TO CREATE | 1,339 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | mentor_speech | WHAT WAS SAID LATELY | 1,328 | 0 | 0 | 0 | 0 | 0 | 0 | 416 | 416 | 416 | 750 | 0 | 0 |
| look_home | narrate | WHAT'S GOING ON HERE LATELY | 0 | 538 | 1,226 | 1,030 | 1,228 | 1,316 | 902 | 1,012 | 970 | 1,280 | 1,032 | 1,064 | 871 |
| look_home | mentor_speech | WHAT THIS IS | 220 | 0 | 0 | 0 | 0 | 0 | 0 | 1,123 | 1,123 | 1,123 | 298 | 0 | 0 |
| look_home | dialogue_frame | RECENT NARRATION | 1,084 | 0 | 0 | 0 | 0 | 0 | 0 | 620 | 529 | 610 | 571 | 536 | 580 |
| look_home | narrate | GAME EVENT | 1,219 | 272 | 272 | 272 | 272 | 329 | 272 | 272 | 303 | 303 | 272 | 272 | 272 |
| look_home | narrate | PEOPLE HERE | 136 | 762 | 730 | 786 | 1,055 | 763 | 686 | 780 | 694 | 835 | 680 | 683 | 732 |
| look_home | interpret_action | PEOPLE HERE | 0 | 661 | 692 | 695 | 901 | 641 | 648 | 649 | 656 | 734 | 642 | 645 | 654 |
| look_home | mentor_speech | COMMANDS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 866 | 866 | 866 | 0 | 0 | 0 |
| look_home | dialogue_frame | THEY WILL SAY | 558 | 0 | 0 | 0 | 0 | 0 | 0 | 846 | 846 | 846 | 100 | 100 | 100 |
| look_home | situation_parts | PEOPLE | 0 | 0 | 823 | 0 | 824 | 822 | 0 | 830 | 837 | 834 | 0 | 0 | 0 |
| look_home | mentor_speech | {WHO} SAID | 812 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | mentor_speech | HIT CHANCE | 767 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | mentor_voice | WHAT WAS SAID LATELY | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 765 | 765 | 765 | 765 | 377 | 377 |
| talk_home | mentor_voice | WHAT WAS SAID LATELY | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 721 | 341 | 341 |
| talk_home | mentor_speech | WHAT WAS SAID LATELY | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 719 | 719 | 719 | 0 | 0 | 0 |
| look_home | situation_parts | ALREADY ESTABLISHED | 0 | 0 | 600 | 0 | 584 | 684 | 0 | 652 | 605 | 524 | 0 | 0 | 0 |
| talk_home | dialogue_frame | RECENT NARRATION | 0 | 578 | 542 | 591 | 563 | 623 | 548 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | moment | TIME | 271 | 0 | 450 | 439 | 566 | 0 | 0 | 0 | 0 | 439 | 0 | 0 | 0 |
| look_home | narrate | WHAT PEOPLE HERE ARE TALKING ABOUT | 0 | 429 | 432 | 392 | 501 | 383 | 333 | 448 | 376 | 444 | 411 | 381 | 506 |
| look_home | moment | THE SHAPE | 252 | 0 | 483 | 443 | 414 | 0 | 0 | 0 | 0 | 238 | 0 | 0 | 0 |
| look_home | moment | ALREADY GOING ON HERE | 136 | 0 | 281 | 267 | 482 | 0 | 0 | 0 | 0 | 253 | 0 | 0 | 0 |
| look_home | narrate | VISIBLE | 130 | 597 | 597 | 458 | 458 | 608 | 458 | 458 | 458 | 458 | 597 | 597 | 458 |
| look_home | narrate | THE TOWN | 0 | 475 | 475 | 475 | 475 | 475 | 475 | 475 | 475 | 475 | 475 | 475 | 475 |
| talk_home | mentor_chat | HAPPENING HERE | 188 | 125 | 343 | 245 | 460 | 300 | 0 | 217 | 286 | 390 | 169 | 264 | 0 |
| look_home | mentor_speech | BOARD | 425 | 0 | 0 | 0 | 0 | 0 | 0 | 424 | 424 | 424 | 425 | 0 | 0 |
| look_home | mentor_voice | BOARD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 425 | 425 | 425 | 425 | 425 | 425 |
| talk_home | mentor_speech | BOARD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 425 | 425 | 425 | 0 | 0 | 0 |
| talk_home | mentor_voice | BOARD | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 425 | 425 | 425 |
| look_home | populate_place | THE TOWN | 417 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | moment | THE TOWN | 417 | 0 | 417 | 417 | 417 | 0 | 0 | 0 | 0 | 417 | 0 | 0 | 0 |
| look_home | mentor_speech | ABOUT YOU | 392 | 0 | 0 | 0 | 0 | 0 | 0 | 392 | 392 | 392 | 0 | 0 | 0 |
| talk_home | mentor_chat | WHAT WAS SAID LATELY | 754 | 498 | 545 | 545 | 545 | 545 | 545 | 879 | 879 | 879 | 881 | 493 | 493 |
| look_home | populate_place | WHAT IS WRONG UNDERNEATH | 379 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | moment | WHAT IS WRONG UNDERNEATH | 378 | 0 | 378 | 378 | 378 | 0 | 0 | 0 | 0 | 378 | 0 | 0 | 0 |
| look_home | thread_telling | STAGE # | 0 | 0 | 265 | 377 | 132 | 316 | 0 | 197 | 105 | 164 | 0 | 0 | 0 |
| look_home | thread_telling | CLUE # | 0 | 0 | 206 | 376 | 210 | 243 | 0 | 214 | 135 | 213 | 0 | 0 | 0 |
| talk_home | mentor_chat | ON THE GUILD BOARD | 469 | 109 | 109 | 109 | 109 | 109 | 109 | 109 | 109 | 109 | 109 | 109 | 109 |
| look_home | situation_parts | GOODS | 0 | 0 | 345 | 0 | 345 | 345 | 0 | 345 | 345 | 345 | 0 | 0 | 0 |
| look_home | mentor_voice | ATTITUDE | 254 | 0 | 0 | 0 | 0 | 0 | 0 | 341 | 341 | 341 | 341 | 341 | 341 |
| look_home | mentor_speech | ATTITUDE | 254 | 0 | 0 | 0 | 0 | 0 | 0 | 338 | 338 | 338 | 341 | 0 | 0 |
| talk_home | mentor_speech | ATTITUDE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 341 | 341 | 341 | 0 | 0 | 0 |
| talk_home | mentor_voice | ATTITUDE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 341 | 341 | 341 |
| talk_home | mentor_chat | WHO IS HERE | 85 | 322 | 259 | 312 | 424 | 343 | 259 | 352 | 259 | 322 | 259 | 259 | 299 |
| look_home | dialogue_frame | THE FRAME SHOWS | 336 | 0 | 0 | 0 | 0 | 0 | 0 | 336 | 336 | 336 | 336 | 336 | 336 |
| talk_home | dialogue_frame | THE FRAME SHOWS | 0 | 336 | 336 | 336 | 336 | 336 | 336 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | situation_parts | PLACES | 0 | 0 | 318 | 0 | 318 | 318 | 0 | 318 | 318 | 318 | 0 | 0 | 0 |
| look_home | mentor_speech | GUILD RANKS | 316 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | mentor_voice | YOU | 314 | 0 | 0 | 0 | 0 | 0 | 0 | 313 | 313 | 313 | 313 | 313 | 313 |
| look_home | dialogue_frame | WAS DOING | 313 | 0 | 0 | 0 | 0 | 0 | 0 | 311 | 311 | 311 | 306 | 306 | 306 |
| look_home | mentor_speech | YOU | 313 | 0 | 0 | 0 | 0 | 0 | 0 | 313 | 313 | 313 | 313 | 0 | 0 |
| talk_home | mentor_speech | YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 313 | 313 | 313 | 0 | 0 | 0 |
| talk_home | mentor_voice | YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 313 | 313 | 313 |
| talk_home | dialogue_frame | WAS DOING | 0 | 311 | 311 | 311 | 311 | 311 | 311 | 0 | 0 | 0 | 0 | 0 | 0 |
| talk_home | mentor_speech | WHAT THIS IS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 298 | 298 | 298 | 0 | 0 | 0 |
| look_home | mentor_speech | MOTIVATION | 272 | 0 | 0 | 0 | 0 | 0 | 0 | 272 | 272 | 272 | 0 | 0 | 0 |
| look_home | situation_parts | ROADS | 0 | 0 | 268 | 0 | 268 | 268 | 0 | 268 | 268 | 268 | 0 | 0 | 0 |
| look_home | mentor_speech | THINGS THEY HAVE TOLD YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 248 | 248 | 248 | 248 | 0 | 0 |
| look_home | mentor_voice | THINGS THEY HAVE TOLD YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 248 | 248 | 248 | 248 | 248 | 248 |
| talk_home | mentor_speech | THINGS THEY HAVE TOLD YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 248 | 248 | 248 | 0 | 0 | 0 |
| talk_home | mentor_voice | THINGS THEY HAVE TOLD YOU | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 248 | 248 | 248 |
| look_home | dialogue_frame | OTHERS PRESENT | 69 | 0 | 0 | 0 | 0 | 0 | 0 | 142 | 149 | 227 | 135 | 138 | 147 |
| look_home | thread_telling | THE PARTS | 0 | 0 | 194 | 210 | 227 | 207 | 0 | 177 | 173 | 201 | 0 | 0 | 0 |
| look_home | mentor_voice | STATE | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 225 | 225 | 225 | 225 | 225 | 225 |
| look_home | mentor_speech | STATE | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 132 | 132 | 132 | 225 | 0 | 0 |
| talk_home | mentor_speech | STATE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 225 | 225 | 225 | 0 | 0 | 0 |
| talk_home | mentor_voice | STATE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 225 | 225 | 225 |
| look_home | interpret_action | YOUR ABILITIES | 0 | 171 | 171 | 171 | 171 | 171 | 171 | 171 | 171 | 223 | 223 | 31 | 31 |
| look_home | narrate | WHAT THE GAME DID THIS TURN | 0 | 0 | 0 | 0 | 0 | 219 | 0 | 0 | 147 | 147 | 0 | 0 | 0 |
| talk_home | dialogue_frame | OTHERS PRESENT | 0 | 154 | 185 | 136 | 215 | 134 | 141 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | populate_place | WORLD | 204 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | moment | WORLD | 204 | 0 | 204 | 204 | 204 | 0 | 0 | 0 | 0 | 204 | 0 | 0 | 0 |
| look_home | narrate | ALREADY SHOWN THIS VISIT | 0 | 199 | 199 | 199 | 199 | 199 | 199 | 199 | 199 | 199 | 199 | 199 | 199 |
| look_home | interpret_action | RECIPES | 0 | 186 | 186 | 185 | 186 | 192 | 186 | 186 | 186 | 185 | 185 | 196 | 196 |
| look_home | mentor_speech | HOW IT ENDS | 180 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | narrate | WHO IS WHO | 0 | 136 | 136 | 136 | 178 | 136 | 136 | 136 | 136 | 136 | 136 | 136 | 136 |
| talk_home | dialogue_frame | WHO IS WHO | 0 | 135 | 135 | 135 | 177 | 135 | 135 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | dialogue_frame | WITHIN REACH | 166 | 0 | 0 | 0 | 0 | 0 | 0 | 138 | 138 | 138 | 138 | 138 | 138 |
| look_home | populate_place | PLACE | 165 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | moment | PLACE | 165 | 0 | 165 | 165 | 165 | 0 | 0 | 0 | 0 | 165 | 0 | 0 | 0 |
| look_home | thread_telling | TRUTH | 0 | 0 | 164 | 145 | 151 | 164 | 0 | 136 | 114 | 135 | 0 | 0 | 0 |
| talk_home | dialogue_frame | ALREADY SHOWN THIS VISIT | 0 | 161 | 161 | 161 | 161 | 161 | 161 | 0 | 0 | 0 | 0 | 0 | 0 |
| look_home | dialogue_frame | ALREADY SHOWN THIS VISIT | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 161 | 161 | 161 | 161 | 161 | 161 |
| look_home | mentor_voice | HOW THINGS STAND | 152 | 0 | 0 | 0 | 0 | 0 | 0 | 152 | 152 | 152 | 152 | 152 | 152 |
| look_home | dialogue_frame | PLACE | 152 | 0 | 0 | 0 | 0 | 0 | 0 | 152 | 152 | 152 | 152 | 152 | 152 |
| look_home | mentor_speech | HOW THINGS STAND | 152 | 0 | 0 | 0 | 0 | 0 | 0 | 152 | 152 | 152 | 152 | 0 | 0 |
| talk_home | dialogue_frame | PLACE | 0 | 152 | 152 | 152 | 152 | 152 | 152 | 0 | 0 | 0 | 0 | 0 | 0 |
| talk_home | mentor_speech | HOW THINGS STAND | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 152 | 152 | 152 | 0 | 0 | 0 |
| talk_home | mentor_voice | HOW THINGS STAND | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 152 | 152 | 152 |
| talk_home | mentor_chat | WHERE | 439 | 438 | 577 | 438 | 442 | 588 | 442 | 439 | 442 | 438 | 578 | 577 | 442 |

## 9. The process's memory: the same 3,000 lines as they are, and with the tracebacks let go

| lines | day | process MB as it is | exceptions alive | frames alive | play() frames alive | objects the collector tracks | process MB, tracebacks let go | exceptions alive | objects |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 77 | 0 | 0 | 0 | 94,390 | 78 | 0 | 94,390 |
| 500 | 25 | 97 | 51 | 272 | 15 | 123,570 | 96 | 0 | 107,001 |
| 1,000 | 36 | 107 | 87 | 485 | 26 | 146,007 | 96 | 0 | 108,137 |
| 1,500 | 65 | 135 | 201 | 1113 | 63 | 198,720 | 98 | 0 | 109,399 |
| 2,000 | 76 | 163 | 318 | 1739 | 102 | 250,519 | 99 | 0 | 115,260 |
| 2,500 | 88 | 194 | 411 | 2255 | 133 | 311,665 | 102 | 0 | 115,537 |
| 3,000 | 107 | 223 | 496 | 2744 | 161 | 369,988 | 104 | 0 | 111,050 |

at line 3,000: 223 MB against 104 MB; the difference over the refused answers still held (exceptions alive / 3 = 165): 0.72 MB each; 4.0 MB a hundred lines
tracebacks let go in the unpinned run: 522

engine ms a line, median by window (all lines / search / move / wait / fight / talk):

| lines | as it is | tracebacks let go | the first run (with probes, beside other work) |
|---|---|---|---|
| 1-500 | 23 (mean 49) / 43 / 46 / 45 / 18 / 576 | 24 (mean 53) / 46 / 46 / 44 / 19 / 613 | 32 (mean 70) / 59 / 58 / 67 / 24 / 1040 |
| 501-1,000 | 47 (mean 64) / 120 / 86 / 116 / 23 / 203 | 47 (mean 64) / 119 / 87 / 121 / 23 / 196 | 50 (mean 65) / 119 / 90 / 124 / 24 / 215 |
| 1,001-1,500 | 58 (mean 93) / 135 / 111 / 149 / 25 / 284 | 54 (mean 89) / 137 / 108 / 143 / 25 / 274 | 61 (mean 96) / 139 / 117 / 150 / 26 / 298 |
| 1,501-2,000 | 58 (mean 75) / 87 / 76 / 107 / 23 / 241 | 54 (mean 63) / 80 / 82 / 89 / 16 / 209 | 92 (mean 109) / 141 / 128 / 155 / 28 / 368 |
| 2,001-2,500 | 62 (mean 79) / 107 / 86 / 121 / 19 / 339 | 70 (mean 96) / 129 / 126 / 132 / 27 / 374 | 91 (mean 114) / 144 / 142 / 167 / 29 / 405 |
| 2,501-3,000 | 98 (mean 113) / 143 / 142 / 184 / 29 / 471 | 96 (mean 107) / 133 / 127 / 171 / 28 / 401 | 103 (mean 116) / 142 / 146 / 172 / 29 / 394 |

the same play? line kinds equal in 3000 of 3000 lines (as it is against the first run); 3000 of 3000 (against tracebacks let go)

The gateway alone, one call (leak_check.py):

```
pydantic 2.13.5 pydantic_core 2.46.5 python 3.14.6

Part A: pydantic alone
  a contract's ValueError, the second answer taken : STILL ALIVE after gc.collect()
  a contract's ValueError, every answer refused    : STILL ALIVE after gc.collect()
  pydantic's own error (a number for the text)     : freed
  broken JSON, then a good answer                  : freed
  no pydantic: a plain ValueError kept the same way: freed
  mended shape (the text kept, not the exception)  : freed
  fifty such turns: ballast objects still alive    : 50 of 50
  the ValueError inside the ValidationError: holders the collector can see: 0 | the ValidationError among them: False

Part B: the game's gateway (llm/gateway.py generate) under simlib's stub
  first answer refused by a contract, second taken  : STILL ALIVE after gc.collect()   (generate gave: 'good')
  every answer refused                              : STILL ALIVE after gc.collect()   (generate gave: LLMError: audit_probe: no valid response after 2 attempts)
  first answer taken                                : freed   (generate gave: 'good')
  forty calls each with one refused answer: callers' ballast still alive: 40 of 40
```

What grew in the traced heap between line 300 and line 900 (tracemalloc, four frames; mem/trace.txt), by the file that allocated it:

```
memory traced: what grew between line 300 and line 900 (600 lines)

by file:
      4958.9 KB  (    8463 B a line)  count   +64012  sers\tstil\AppData\Local\Programs\Python\Python314\Lib\json\decoder.py
      2497.9 KB  (    4263 B a line)  count   +63935  C:\Users\tstil\AppData\Local\Programs\Python\Python314\Lib\random.py
      1480.6 KB  (    2527 B a line)  count    +8788  C:\Users\tstil\AppData\Local\Programs\Python\Python314\Lib\copy.py
       972.1 KB  (    1659 B a line)  count    +8368  ata\Local\Programs\Python\Python314\Lib\site-packages\pydantic\main.py
       927.5 KB  (    1583 B a line)  count       +0  C:\Users/tstil/Projects/dnd_ai\ui\console.py
       781.8 KB  (    1334 B a line)  count    +8504  C:\Users/tstil/Projects/dnd_ai\engine\truth.py
       253.1 KB  (     432 B a line)  count    +5194  -4be3-9744-2919d03b2cce\scratchpad\audit\work\aged_save\aged_common.py
       130.6 KB  (     223 B a line)  count      +85  sers\tstil\AppData\Local\Programs\Python\Python314\Lib\re\_compiler.py
       129.5 KB  (     221 B a line)  count    +1029  C:\Users/tstil/Projects/dnd_ai\llm\gateway.py
       113.5 KB  (     194 B a line)  count    +1305  simbot.py
        90.6 KB  (     155 B a line)  count     +900  C:\Users/tstil/Projects/dnd_ai\scenes\world.py
```

Who was alive after a collection at line 1,500 (hold/holders.txt): the refused answers' exceptions in threes (the contract's ValueError, pydantic's ValidationError, the gateway's LLMError), none of them reachable from any module's global:

```
object counts: dict 70,986, list 52,558, function 17,291, set 10,198, tuple 8,134, cell 5,062, ReferenceType 2,048, getset_descriptor 1,717, wrapper_descriptor 1,374, FieldInfo 1,352, method_descriptor 1,205, frozenset 1,174, builtin_function_or_method 1,138, frame 1,114, type 1,073, AllocationRecord 822, FamilyOption 815, Pattern 702
exceptions alive 201, tracebacks 522, frames 1114

exceptions alive, by type, and the shortest chain to a module global for a few of each:
     30  ValueError: 'quiet enough most days' is how everyone in this town has be
           3 of 3: (no module global found within 1 holders)
     30  ValidationError: 1 validation error for NPCReply   Value error, 'quiet enough
           3 of 3: (no module global found within 13 holders)
     30  LLMError: npc_conversation: no valid response after 2 attempts
           3 of 3: (no module global found within 13 holders)
      9  ValueError: you have opened that way on an earlier return; she remembers
           3 of 3: (no module global found within 1 holders)
      9  ValidationError: 1 validation error for GoddessLine   Value error, you have o
           3 of 3: (no module global found within 31 holders)
      9  LLMError: goddess_line: no valid response after 2 attempts
           3 of 3: (no module global found within 23 holders)
      8  LLMError: moment: no valid response after 3 attempts
           3 of 3: (no module global found within 11 holders)
      8  ValueError: write exactly 1 stages, one for each STAGE given, in order (
           3 of 3: (no module global found within 1 holders)
```

## 10. One person talked to for 400 lines (talk run)

who: {'id': 'robinard_bromford', 'role': 'herbalist', 'name': 'Robinard Bromford'}  at trading_square  switches: None  errors: []
lines 400, days 33, lines that did not stand: 0

| lines | engine ms median | npc_conversation chars median | max | interpret_action median | max | other tasks (median) | est. model s median | max |
|---|---|---|---|---|---|---|---|---|
| 1-12 | 57 | 18,988 | 19,562 | 15,136 | 15,541 | audit_compare 689; audit_meaning 432; dialogue_frame 7108; npc_profile 2418; populate_place 3244; work_offer_read 555 | 15.0 | 40 |
| 13-50 | 93 | 19,703 | 21,486 | 15,167 | 15,602 | audit_compare 678; audit_meaning 427; dialogue_frame 7805; moment 5806; populate_place 2407; situation_parts 6584; thread_telling 9929; work_offer_read 552 | 34.0 | 43 |
| 51-100 | 109 | 20,927 | 23,145 | 15,145 | 15,489 | audit_compare 675; audit_meaning 425; populate_place 2565; situation_agree 527; situation_parts 6625; thread_telling 9717; work_offer_read 558 | 35.0 | 44 |
| 101-150 | 124 | 20,839 | 23,721 | 15,166 | 15,498 | audit_compare 681; audit_meaning 427; dialogue_frame 7912; moment 5546; narrate 9029; populate_place 2567; situation_agree 498; situation_parts 6472; work_offer_read 581 | 35.0 | 45 |
| 151-200 | 162 | 21,334 | 24,595 | 15,261 | 15,658 | audit_compare 683; audit_meaning 439; dialogue_frame 7911; moment 5738; populate_place 2410; situation_agree 541; situation_parts 6648; thread_telling 9993; work_offer_read 562 | 35.0 | 45 |
| 201-250 | 142 | 21,843 | 23,717 | 15,263 | 15,567 | audit_compare 675; audit_meaning 438; dialogue_frame 7724; work_offer_read 559 | 36.0 | 45 |
| 251-300 | 144 | 21,521 | 24,328 | 15,262 | 15,574 | audit_compare 673; audit_meaning 438; moment 5946; situation_parts 5868; work_offer_read 589 | 35.0 | 45 |
| 301-350 | 154 | 21,091 | 24,530 | 15,254 | 15,601 | audit_compare 682; audit_meaning 442; dialogue_frame 7938; work_offer_read 559 | 34.0 | 46 |
| 351-400 | 184 | 21,095 | 24,321 | 15,263 | 15,636 | audit_compare 675; audit_meaning 439; dialogue_frame 7847; populate_place 2408; situation_parts 6640; thread_telling 9804; work_offer_read 558 | 33.0 | 45 |

npc_conversation by section (median characters where present), by window:

| section | 1-12 | 13-50 | 51-100 | 101-150 | 151-200 | 201-250 | 251-300 | 301-350 | 351-400 | largest |
|---|---|---|---|---|---|---|---|---|---|---|
| WHAT THIS TOWN HAS | 0 | 1,794 | 2,073 | 1,973 | 2,287 | 2,133 | 2,476 | 3,088 | 3,162 | 3,181 |
| NEWS THAT HAS REACHED HERE | 0 | 215 | 766 | 738 | 637 | 643 | 730 | 627 | 772 | 889 |
| PEOPLE YOU KNOW | 1,490 | 1,624 | 1,896 | 2,000 | 2,112 | 2,149 | 2,149 | 2,149 | 2,109 | 2,158 |
| RIGHT NOW YOU ALSO KNOW | 1,433 | 1,870 | 1,467 | 1,655 | 2,003 | 1,947 | 2,013 | 1,919 | 1,640 | 2,404 |
| YOUR MEMORIES OF THEM | 33 | 33 | 154 | 223 | 385 | 394 | 398 | 465 | 468 | 468 |
| HAPPENING HERE | 105 | 346 | 530 | 309 | 267 | 495 | 490 | 0 | 373 | 686 |
| HOW YOU TALK | 197 | 197 | 197 | 197 | 197 | 197 | 197 | 359 | 197 | 379 |
| WHERE | 504 | 504 | 654 | 505 | 654 | 647 | 643 | 505 | 504 | 746 |
| THIS CONVERSATION SO FAR | 2,353 | 2,355 | 2,379 | 2,346 | 2,279 | 2,387 | 2,405 | 2,318 | 2,271 | 2,533 |
| WORDS YOU MAY USE THIS TIME, AS THEY ARE | 122 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 122 |

the person's stores:

| after line | person record bytes | lists in the record | memory rows by kind | memory text bytes | kv talk bytes | kv story bytes | player bytes | journal rows |
|---|---|---|---|---|---|---|---|---|
| 1 | 2,231 | {'traits': 3, 'knowledge_groups': 2, 'speech': 8, 'said': 1, 'heard': 1, 'regard': 1} | {} | 0 | 572 | 0 | 4,520 | 1 |
| 25 | 5,013 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {} | 0 | 585 | 1,989 | 4,534 | 10 |
| 50 | 5,074 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 1} | 45 | 895 | 1,950 | 4,534 | 23 |
| 75 | 5,258 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 2} | 91 | 1,411 | 2,023 | 4,534 | 34 |
| 100 | 5,268 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 2} | 91 | 1,648 | 1,916 | 4,534 | 47 |
| 125 | 5,389 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 3} | 136 | 2,144 | 1,980 | 4,534 | 57 |
| 150 | 5,543 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 3, 'knows': 1, 'own_life': 1} | 253 | 2,638 | 2,011 | 4,534 | 66 |
| 175 | 5,533 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 4, 'knows': 1, 'own_life': 1} | 299 | 2,928 | 2,264 | 4,534 | 74 |
| 200 | 5,628 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 4, 'knows': 1, 'own_life': 2} | 390 | 3,332 | 2,275 | 4,534 | 82 |
| 225 | 5,612 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 4, 'knows': 1, 'own_life': 2} | 390 | 3,700 | 2,259 | 4,534 | 89 |
| 250 | 5,553 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 4, 'knows': 1, 'own_life': 3} | 481 | 4,080 | 2,261 | 4,534 | 98 |
| 275 | 5,574 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 4, 'knows': 1, 'own_life': 3} | 481 | 4,509 | 2,233 | 4,534 | 105 |
| 300 | 5,529 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 5, 'knows': 1, 'own_life': 5} | 657 | 5,088 | 2,299 | 4,534 | 115 |
| 325 | 5,468 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 5, 'knows': 1, 'own_life': 5} | 657 | 618 | 2,017 | 4,534 | 123 |
| 350 | 5,373 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 5, 'knows': 1, 'own_life': 5} | 657 | 882 | 1,996 | 4,534 | 129 |
| 375 | 5,360 | {'traits': 3, 'knowledge_groups': 2, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 5, 'knows': 1, 'own_life': 5} | 657 | 1,393 | 1,971 | 4,534 | 138 |
| 400 | 5,461 | {'traits': 3, 'knowledge_groups': 2, 'relations': 1, 'speech': 10, 'said': 8, 'heard': 8, 'regard': 1} | {'experienced': 5, 'knows': 1, 'own_life': 5} | 657 | 1,851 | 2,043 | 4,534 | 147 |

first tries sent back: 271 of 671
   94 'belly' and 'dull' are words everyone here has worn out lately; find o
   72 'dull' and 'heavy' are words everyone here has worn out lately; find o
   46 'pale' and 'slow' are words everyone here has worn out lately; find ot
   42 'belly' and 'quiet' are words everyone here has worn out lately; find 
   34 'belly' and 'heavy' are words everyone here has worn out lately; find 
   34 'dull' and 'pale' are words everyone here has worn out lately; find ot

## 11. What the gone leave in the save (second and third runs; the base run's probes did not count this)

| run | lines | day | people rows | of them gone | bytes of the gone | bytes of the rest | stock items of the gone (bytes) | memory rows of the gone / all | road-stop place rows (bytes) / all place rows | registry rows | of them final (bytes) | import ms | captives ever |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| second | 1,500 | 88 | 125 | 18 | 54,027 | 155,551 | 104 (36,630) | 4 / 465 | 22 (9,787) / 92 | 90 | 56 (22,853) | 883.5 | 5 |
| second | 2,000 | 117 | 151 | 35 | 99,463 | 174,293 | 176 (62,498) | 13 / 619 | 36 (14,858) / 114 | 112 | 73 (28,846) | 912.0 | 12 |
| second | 2,500 | 159 | 174 | 48 | 136,687 | 196,776 | 256 (90,823) | 14 / 865 | 61 (25,855) / 151 | 133 | 88 (34,760) | 981.8 | 15 |
| second | 3,000 | 174 | 186 | 60 | 162,265 | 195,365 | 256 (90,847) | 14 / 932 | 63 (26,810) / 157 | 150 | 106 (42,390) | 1045.6 | 27 |
| third | 0 | 1 | 8 | 0 | 0 | 6,207 | 0 (0) | 0 / 0 | 0 (0) / 7 | 3 | 0 (0) | 796.2 | 0 |
| third | 500 | 21 | 38 | 5 | 8,721 | 42,405 | 0 (10) | 9 / 71 | 0 (0) / 24 | 15 | 7 (2,742) | 771.6 | 2 |
| third | 1,000 | 38 | 51 | 7 | 13,155 | 55,411 | 0 (14) | 9 / 113 | 1 (393) / 29 | 27 | 14 (5,540) | 745.5 | 4 |
| third | 1,500 | 47 | 70 | 19 | 40,094 | 66,457 | 0 (38) | 9 / 159 | 2 (833) / 39 | 48 | 32 (12,880) | 744.9 | 16 |
| third | 2,000 | 59 | 96 | 35 | 78,321 | 79,084 | 24 (8,738) | 9 / 207 | 6 (2,043) / 54 | 71 | 52 (21,162) | 734.6 | 29 |

- base, last probe: people by how they went: {'(here)': 121, 'let go by the stranger': 55, 'put to the sword by the stranger': 34, 'moved on along the road': 32, 'took the road on': 3, 'got away while their captor lay dead': 3, 'a change': 1}
- base, last probe: registry rows by kind and state [rows, bytes]: {'captive|escaped': [3, 1354], 'captive|executed': [34, 15354], 'captive|released': [55, 24276], 'feature|explored': [1, 512], 'feature|known': [11, 6311], 'feature|unseen': [21, 10184], 'obligation|active': [1, 440], 'offer|released': [1, 891], 'offer|taken': [2, 918], 'stock|held': [2, 658], 'stock|released': [102, 39330]}
- second, last probe: people by how they went: {'(here)': 126, 'moved on along the road': 32, 'let go by the stranger': 13, 'put to the sword by the stranger': 10, 'got away while their captor lay dead': 3, 'a change': 1, 'slipped their bonds and got away': 1}
- second, last probe: registry rows by kind and state [rows, bytes]: {'captive|escaped': [4, 1817], 'captive|executed': [10, 4460], 'captive|released': [13, 5694], 'feature|explored': [2, 1038], 'feature|known': [14, 8108], 'feature|unseen': [26, 12412], 'stock|held': [2, 667], 'stock|released': [79, 30419]}
- third, last probe: people by how they went: {'(here)': 61, 'let go by the stranger': 28, 'moved on along the road': 3, 'took the road on': 2, 'left Parth on the work the capital sent her south to do': 1, 'slipped their bonds and got away': 1}
- third, last probe: registry rows by kind and state [rows, bytes]: {'captive|escaped': [1, 446], 'captive|released': [28, 11887], 'feature|explored': [3, 1496], 'feature|known': [5, 2898], 'feature|unseen': [7, 3450], 'obligation|active': [2, 840], 'stock|held': [2, 666], 'stock|released': [23, 8829]}

## 12. The stores at every 500 lines, second run (mage, seed 23)

| store | 0 | 500 | 1,000 | 1,500 | 2,000 | 2,500 | 3,000 |
|---|---|---|---|---|---|---|---|
| game day | 1 | 27 | 49 | 88 | 117 | 159 | 174 |
| level | 1 | 7 | 15 | 22 | 25 | 34 | 41 |
| database file, KB | 4 | 692 | 1,020 | 1,432 | 1,756 | 2,012 | 2,196 |
| process memory, MB (a sitting) | 77 | 100 | 118 | 173 | 220 | 248 | 272 |
| things shown on the page so far (frontend-shipping-11) | 0 | 1,136 | 2,312 | 3,561 | 4,826 | 6,225 | 7,290 |
| journal rows (event_log; cap 6,000) | 7 | 252 | 522 | 847 | 1,134 | 1,425 | 1,663 |
| journal bytes | 1,355 | 46,403 | 98,430 | 162,702 | 218,249 | 274,806 | 322,132 |
| people rows (npcs) | 8 | 58 | 75 | 125 | 151 | 174 | 186 |
| ...of them gone | 0 | 3 | 8 | 18 | 35 | 48 | 60 |
| people bytes | 6,095 | 83,204 | 120,603 | 209,578 | 273,756 | 333,463 | 357,630 |
| stock items held by people (all) |  | 81 | 128 | 212 | 310 | 426 | 425 |
| memory rows (npc_memory) | 0 | 80 | 225 | 465 | 619 | 865 | 932 |
| ...most for one person | 0 | 8 | 17 | 18 | 20 | 28 | 39 |
| place rows (places table) | 5 | 33 | 51 | 92 | 114 | 151 | 157 |
| registry rows (entities) | 3 | 25 | 47 | 90 | 112 | 133 | 150 |
| ...captives ever (rows of kind captive) | 0 | 0 | 2 | 5 | 12 | 15 | 27 |
| ...stock rows released |  | 10 | 26 | 49 | 61 | 73 | 79 |
| threads rows | 0 | 25 | 31 | 35 | 36 | 35 | 32 |
| deeds rows (cap 300) | 0 | 63 | 137 | 192 | 258 | 300 | 300 |
| news rows (cap 300) | 0 | 65 | 161 | 300 | 300 | 300 | 300 |
| world.history (cap 200) | 0 | 29 | 77 | 171 | 200 | 200 | 200 |
| world.spawns (engine3-9) | 0 | 3 | 3 | 3 | 5 | 5 | 5 |
| world.spawns bytes | 2 | 670 | 670 | 670 | 1,452 | 1,451 | 1,451 |
| world.moments_seen (cap 200) |  | 3 | 7 | 8 | 9 | 11 | 11 |
| world.parts_ended (cap 500) |  | 12 | 30 | 59 | 73 | 97 | 105 |
| kv world_state bytes | 304 | 7,939 | 18,612 | 36,894 | 44,425 | 45,781 | 46,495 |
| kv operations bytes (shell2-10; cap 200 operations) | 15,901 | 29,073 | 28,777 | 28,958 | 28,910 | 29,510 | 28,832 |
| kv dungeons bytes | 76,787 | 74,249 | 76,804 | 78,517 | 78,964 | 77,136 | 75,453 |
| kv arcs bytes (scenes1-14) | never written |  |  |  |  |  |  |
| kv legendaries bytes (scenes1-15) | never written |  |  |  |  |  |  |
| player row bytes | 7,936 | 11,709 | 15,284 | 17,430 | 21,210 | 26,143 | 28,900 |
| player.visited (world_py-8) | 2 | 18 | 30 | 61 | 81 | 108 | 112 |
| player.standing_told | 2 | 12 | 19 | 40 | 56 | 83 | 87 |
| player.field.towns | 1 | 8 | 13 | 30 | 44 | 69 | 73 |
| player.last_in | 0 | 7 | 11 | 22 | 28 | 34 | 34 |
| player.character.item_history (scenes2-8) | never written |  |  |  |  |  |  |
| carcasses, all places (people-6) | 0 | 4 | 16 | 24 | 55 | 94 | 127 |
| carcasses, the largest list | 0 | 3 | 11 | 12 | 24 | 25 | 29 |
| board postings, the largest board | 7 | 17 | 22 | 34 | 38 | 42 | 42 |
| scene._news_seen entries (world_py-13) |  | 38 | 95 | 193 | 256 | 334 | 370 |
| scene._news_seen bytes copied an operation |  | 3,793 | 9,858 | 19,496 | 26,242 | 34,334 | 38,134 |
| pulse.jsonl bytes (engine5-5) |  | 41,020 | 99,477 | 212,678 | 290,749 | 366,068 | 391,555 |
| module engine.refusals.SESSION |  | 25 | 46 | 79 | 97 | 111 | 116 |
| module engine.combat._LIFT_CACHE | 0 | 34 | 56 | 98 | 134 | 192 | 230 |

## 13. The stores at every 500 lines, third run (priest, seed 41)

| store | 0 | 500 | 1,000 | 1,500 | 2,000 |
|---|---|---|---|---|---|
| game day | 1 | 21 | 38 | 47 | 59 |
| level | 1 | 5 | 11 | 12 | 19 |
| database file, KB | 4 | 612 | 772 | 984 | 1,200 |
| process memory, MB (a sitting) | 78 | 100 | 115 | 129 | 148 |
| things shown on the page so far (frontend-shipping-11) | 0 | 932 | 1,952 | 3,075 | 4,178 |
| journal rows (event_log; cap 6,000) | 7 | 148 | 322 | 575 | 844 |
| journal bytes | 1,327 | 27,119 | 59,946 | 108,067 | 159,684 |
| people rows (npcs) | 8 | 38 | 51 | 70 | 96 |
| ...of them gone | 0 | 5 | 7 | 19 | 35 |
| people bytes | 6,207 | 51,126 | 68,566 | 106,551 | 157,405 |
| stock items held by people (all) |  | 30 | 37 | 47 | 87 |
| memory rows (npc_memory) | 0 | 71 | 113 | 159 | 207 |
| ...most for one person | 0 | 9 | 9 | 12 | 12 |
| place rows (places table) | 7 | 24 | 29 | 39 | 54 |
| registry rows (entities) | 3 | 15 | 27 | 48 | 71 |
| ...captives ever (rows of kind captive) | 0 | 2 | 4 | 16 | 29 |
| ...stock rows released |  | 5 | 10 | 16 | 23 |
| threads rows | 0 | 24 | 31 | 33 | 33 |
| deeds rows (cap 300) | 0 | 45 | 98 | 195 | 253 |
| news rows (cap 300) | 0 | 56 | 93 | 117 | 144 |
| world.history (cap 200) | 0 | 27 | 49 | 62 | 76 |
| world.spawns (engine3-9) | 0 | 1 | 4 | 4 | 5 |
| world.spawns bytes | 2 | 542 | 1,200 | 1,198 | 1,415 |
| world.moments_seen (cap 200) |  | 2 | 3 | 4 | 5 |
| world.parts_ended (cap 500) |  | 9 | 15 | 21 | 28 |
| kv world_state bytes | 304 | 6,898 | 11,449 | 13,935 | 17,476 |
| kv operations bytes (shell2-10; cap 200 operations) | 15,901 | 29,137 | 29,059 | 29,133 | 29,230 |
| kv dungeons bytes | 75,489 | 75,489 | 75,915 | 75,000 | 75,000 |
| kv arcs bytes (scenes1-14) | never written |  |  |  |  |
| kv legendaries bytes (scenes1-15) | never written |  |  |  |  |
| player row bytes | 7,951 | 10,440 | 14,548 | 18,274 | 18,279 |
| player.visited (world_py-8) | 2 | 6 | 9 | 17 | 26 |
| player.standing_told | 2 | 3 | 6 | 9 | 15 |
| player.field.towns | 1 | 1 | 3 | 5 | 10 |
| player.last_in | 0 | 1 | 3 | 5 | 7 |
| player.character.item_history (scenes2-8) | 0 | 0 | 0 | 0 | 0 |
| carcasses, all places (people-6) | 0 | 34 | 48 | 87 | 102 |
| carcasses, the largest list | 0 | 34 | 48 | 86 | 86 |
| board postings, the largest board | 7 | 9 | 6 | 9 | 9 |
| scene._news_seen entries (world_py-13) |  | 30 | 63 | 81 | 103 |
| scene._news_seen bytes copied an operation |  | 3,130 | 6,181 | 7,895 | 10,529 |
| pulse.jsonl bytes (engine5-5) |  | 33,766 | 56,583 | 83,761 | 114,321 |
| module engine.refusals.SESSION |  | 47 | 89 | 113 | 132 |
| module engine.combat._LIFT_CACHE | 0 | 22 | 32 | 37 | 71 |

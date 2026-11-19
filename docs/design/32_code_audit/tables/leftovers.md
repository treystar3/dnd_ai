# leftovers: the measurements behind the findings

Everything here was read from tracked files only. Nothing was played and no model was called.
The scripts that made the numbers are in `scratchpad/audit/work/leftovers/` (player_line.py, player_line_empty.py,
player_line_names.py, empty_objects.py, party_canon.py, embed_shapes.py).

## 1. The night bot's own line (task `player_line`) in the 44 tracked call logs

Source: `docs/measure/**/llm_calls.jsonl.gz` (44 logs, 14,035 rows, every row Gemma 4 12B). Each run is 60 turns.

| | |
|---|---|
| `player_line` rows | 2,759 |
| calls (a first try and its retry) | 2,251 |
| calls that passed on the first try | 1,743 |
| calls that passed on the second try | 483 |
| calls that ended with no line (the bot typed its template line) | 25 |
| rows sent back | 533 |
| rows sent back in the logs for every task together | 1,089 (so 49% are this one task) |

### Why they were sent back

| Rows | Reason given | What the model wrote |
|---:|---|---|
| 451 | "write the one line the player types" | `{}` or `{ }` every time: 2 to 4 tokens, finish `stop`, always a first try |
| 65 | "the line must name X" | a line without the name as one unbroken run (see below) |
| 13 | "write it in the first person..." | a line that began "You ", "The player" and the like |
| 4 | the narrator's passage message ("write only the passage itself: no JSON, braces...") | a line whose text ended in a stray `" }` |

The 451: `llm/contracts.py:595` is `line: str = ""`. A key with a default is not required in the schema, so the grammar lets the
answer close straight after `{`. The validator (`:600-601`) then refuses the empty line. 442 of the 451 retries wrote a line.

### How often, by run folder (first tries that came back `{}`)

| Run folder | Empty | First tries | Share |
|---|---:|---:|---:|
| prose_a1/both | 53 | 248 | 21.4% |
| prose_a1/control | 42 | 261 | 16.1% |
| prose_a1/dry | 43 | 262 | 16.4% |
| prose_a1/min_p | 49 | 259 | 18.9% |
| prose_a1/xtc | 57 | 264 | 21.6% |
| prose_a2 (five plays) | 42 | 240 | 17.5% |
| prose_baseline/base1 | 22 | 96 | 22.9% |
| prose_baseline/base2 | 16 | 94 | 17.0% |
| prose_baseline/new1 | 64 | 259 | 24.7% |
| prose_baseline/new2 | 63 | 268 | 23.5% |
| all | 451 | 2,251 | 20.0% |

It is the same in every arm, so it is not a sampling setting: it is the grammar.

### What it costs

| | Seconds |
|---|---:|
| All model time in the 44 logs | 21,496 |
| `player_line` in all | 1,291 (6.0%) |
| the 451 empty first tries | 160 |
| the retries those forced | 226 |
| both together | 386 (1.8% of all model time; 8.8 s a run; 0.86 s on one bot line in five) |
| every `player_line` retry, for any reason | 255 |

A six-hour night (nightrun's default) at this mix loses six to seven minutes of model time to it.

It also spends the bot's only retry (`tools/nightbot.py:1222`, `retries=1`). The 25 calls that ended with no line:

| Calls | First try | Second try |
|---:|---|---|
| 13 | name: "the adventurers' guild house" | the same |
| 9 | `{}` | name (7) or first person (2) |
| 1 | name: "the Hollow Tomb (beneath the Willowmead wetlands)" | the same |
| 1 | name: "feature:greywood:deep_thicket" | the same |
| 1 | name: "veteran" | the same |

### The name the line had to carry (1,151 calls asked for one)

| Kind of name | Calls | Calls sent back on the name | Ended with no line |
|---|---:|---:|---:|
| a place name that begins "the" | 554 | 24 | 14 |
| a role or a common word ("veteran", "cook", "girl") | 253 | 13 | 4 |
| a whole title, four words or more | 27 | 9 | 3 |
| two words of a contract's title | 75 | 1 | 0 |
| a place name with a bracketed part | 1 | 1 | 1 |
| an internal id | 1 | 1 | 1 |
| a proper name ("Parth", "Lizardfolk") | 240 | 0 | 0 |

The names sent back most:

| Name asked | Calls | Sent back | No line | What the model wrote |
|---|---:|---:|---:|---|
| "the adventurers' guild house" | 267 | 20 | 14 | "the Guild House", or a name it made up ("the Iron Crown Guild House", "the Golden Lion Guild House") |
| "Hunt 2 lizardfolks in the Willowmead wetlands" | 7 | 6 | 2 | "any sign of the two lizardfolks" (the goal read "search this place for Hunt 2 lizardfolks in the Willowmead wetlands") |
| "veteran" | 7 | 5 | 2 | "the man with the scars" |
| "the Willowmead wetlands" | 51 | 3 | 0 | "those Willowmead wetlands" (only the article differs) |
| "Cheap and then dear in Parth" | 20 | 3 | 1 | "I scan the area for Cheap and then stay alert for any sign of Dear in Parth." |
| "feature:greywood:deep_thicket" | 1 | 1 | 1 | "the Greywood Deep Thicket" |

Where the two bad kinds come from: `tools/nightbot.py:860` (`seek=g["title"]`: a contract's or situation's title as the thing to
search for; the template line types the same title) and `:1151` (a part of a place has no entry in `world.places`, so its id is
used as its name). The check itself is `llm/contracts.py:608`, a plain substring of the whole name.

Also seen in the prompt: "You are you live for the fight" (`tools/nightbot.py:1204`, three of five persona texts begin "you"), and
"Your health: 118%" on 44 first tries (`:1211`).

## 2. `{}` across every task in the same logs

| Task | Rows | Answers that were `{}` | Sent back for it |
|---|---:|---:|---|
| player_line | 2,759 | 451 | yes, all 451 |
| canon_extract | 127 | 86 | no (an empty answer means nothing to keep) |

No other task answered `{}` with Gemma in these logs.

## 3. The update: what proves the file

| Question | What the code does | Where |
|---|---|---|
| A digest? | None. Only the link is kept from the release answer. | core/updates.py:53 |
| A size? | Content-Length is read for the progress bar and never compared (all.json shell1-9). | core/updates.py:122 |
| Where the link points? | Not looked at: any scheme and host urllib opens. | core/updates.py:121 |
| A private place? | The user's own temp folder, under the fixed name Meravia_setup.exe. Never removed, after success or failure. | core/updates.py:119 |
| Closed before it is run? | Yes: Popen comes after the `with` block. | core/updates.py:121-130 |
| When something fails? | The raw exception text goes to the card ("OSError: [WinError 193] ..."). The partial file stays. | core/updates.py:131-132 |
| Can the page start it without the player? | Any POST /update with the page's token starts it. The link is the server's own, not the page's. There is no one-at-a-time guard: each POST starts another thread into the same file. | ui/gui/server.py:220-230 |
| The same in the installer | Setup downloads Microsoft's WebView2 bootstrapper with an empty hash and runs it silently; every other file on that page is checked against its sha256. | installer/meravia.iss:141, :40 |
| The tree's own pattern | `fetch(url, dest, sha, size)`: `.part` file, hash while reading, stop past the size, remove on a mismatch, rename when right. | tools/fetch_runtime.py |

The page's seven `innerHTML` uses (app.js 93, 94, 96, 102, 112, 120, 1127; no `insertAdjacentHTML`): model text reaches 93, 94, 96 and
120 through `decorate()`, which escapes `& < >` first. The two places text lands inside an attribute are :78 (a hit token's id)
and :1128 (the spot's title); both are all.json frontend-shipping-10, and its one-line fix covers both. The player's own echo and
the release notes use `textContent`.

## 4. What `LlamaServer.embed` makes of a wrong-shaped answer (status 200, two texts asked)

Run against tools/sim/fake_llama.py (embed_shapes.py). The first text's vector is `[0.6, 0.8, 0.0]`.

| The second text's embedding | Taken as | Likeness of the two texts |
|---|---|---|
| `[]` | `[]` | 0 |
| the key missing | `[]` | 0 |
| `[1.0]` (short) | `[1.0]` | 0.6 (zip stops at the shorter one) |
| `[0.0, 0.0, 0.0]` | as sent | 0.0 |
| `[null, null, null]` | as sent | TypeError in llm/embed.py:86, outside its try |

Only a wrong number of rows is refused (llm/llama.py:441-442). No test scripts any of these answers.

## 5. The party golden: do the planted claims reach the save?

Read from data/replay/sessions/stub_party (party_canon.py).

| Looked for | Found |
|---|---|
| "militia" in any row any input changed | 0 |
| "next town" in any row any input changed | 0 |
| "commitment" in any row any input changed | 0 |
| CanonCheck calls | 0 |
| the claim in ALREADY KNOWN at the second reading | no |
| `canon.FIRST_PERSON` matches "learned to fight in a town militia up north, before it broke" | no |
| `canon.FIRST_PERSON` matches "will see the player as far as the next town" | no |
| `canon.FIRST_PERSON` matches "I learned to fight in a town militia up north, before it broke" | yes |

## 6. Authored lines that state a number or a rule, held against the data

| Line | Says | Data | Holds? |
|---|---|---|---|
| mentor.yaml:132 (first_blood, caster) | "you can't get mana back in the middle of this" | goods.yaml:35-36 mana tonic, `combat: true`, `restores: {mana: 30}`; engine/combat.py:1561 siphon_mana | no |
| failures.yaml:370 (creation_fail.traits) | "Choose the three you were born with, once more." | the step asked again is the three abilities (scenes/goddess.py:516-519, :241-242) | no |
| mentor.yaml:131 | the draught "doesn't cost your turn, but it's one a turn" | scenes/combat_scene.py:367 | yes |
| mentor.yaml:282 | "There are seven ranks, F at the bottom to S at the top" | guild.yaml ranks | yes (typed, not a slot) |
| mentor.yaml:323 | "You can have three at a time." | party.yaml:10 max_party: 3 | yes (typed, not a slot) |
| mentor.yaml:331, :372 | "about half an hour northwest of Parth" | places.yaml:32 greywood: 30 | yes (typed, not a slot) |
| mentor.yaml:371 | "It has no time limit." | f491 | yes |
| mentor.yaml hires | "You pay them once" | guild.yaml hire price, paid once | yes |
| console.py:731 | "5 spells and 5 techniques at first" | training.yaml loadout.start 5 | yes |
| console.py:732 | "#prepare ... once a day" | engine/loadout.py | yes |
| console.py:742 | "#stash ... (stored at inns with storage)" | also a guild house with the storage perk and the player's own box (scenes/inventory_actions.py:66-68) | narrower than the rule |
| spells.yaml:47-48 | "takes two turns" | cast_turns: 2 beside it | yes (typed twice) |
| goddess_knowledge.json, opening.json, send_off.json | no number and no rule | | nothing to check |

The help list (console.py:720-756) also leaves out #map, #exits (#places), #arc, #home and #gear, which the game handles
(scenes/world.py command()).

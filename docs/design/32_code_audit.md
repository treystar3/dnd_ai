# 32. Code audit: bugs, use of the model, speed, dead code

18 November 2026. Branch play/faults at 6473815 (f730). Asked for by the owner: "an audit of the code base and look for ways
to improve: optimization, better use of the llm, finding dead code and unneeded files, bug fixes".

**Nothing was changed.** No code, no data, no recording, no commit. Every fix named here is a proposal, to be approved and
built as a numbered feature with its test written first. The companion folder `docs/design/32_code_audit/` holds every finding
whole, the tables and the removal list; this file is the ranked reading of them.

## 1. In short

584 findings in two rounds. A second reader tried to disprove 477 of them: 447 confirmed (most by running a script against
the code under the stub), 21 plausible, 9 refuted. The other 107 are small and listed without a check. 204 of the 584 are
already recorded somewhere in the owner's documents; they are marked `known` in the register.

| | Confirmed heavy | Confirmed medium | Confirmed small | Plausible | Refuted | Not checked (small) |
|---|---:|---:|---:|---:|---:|---:|
| Bugs (276) | 13 | 106 | 139 | 16 | 2 | 0 |
| Use of the model (75) | 2 | 16 | 34 | 0 | 0 | 23 |
| Speed (46) | 3 | 10 | 16 | 0 | 1 | 16 |
| Dead code, unneeded files (79) | 0 | 1 | 70 | 3 | 5 | 0 |
| Tests (32) | 0 | 11 | 5 | 0 | 0 | 16 |
| Data (37) | 0 | 3 | 8 | 1 | 1 | 24 |
| Other (39) | 0 | 5 | 5 | 1 | 0 | 28 |

Rows are by the kind each reader gave its finding, so a few file and suite findings sit under Other. The eighteen heavy
rows are thirteen separate things once the same fault found by two readers is counted once (section 3.1 and
the first rows of sections 4 and 5).

The five things I would act on first:

1. **A townsperson's reply writes a journal note nobody asked for** (known, never built). It is about 40% of what the reply
   writes, and it is the one call that breaks the 60 second limit on the minimum card: 9 of the 17 recorded lines priced over
   60 s are a reply that ran to 2,048 tokens inside that field. Leave it out of the grammar unless a note is due.
2. **Seven small, certain bugs with one-place fixes**: asking about the next rank starts the trial; one enchantment eats the
   whole stack of the reagent; a missing-person contract divides by zero once sixteen captives have been taken (about line
   1,500 of a fighter's play); a foe that fled or fell still takes its turn; the player's own summon losing wins a rank trial;
   Word of Recall is refused after any road stop; every refused answer pins its turn's memory for the sitting.
3. **A game built from this tree cannot start**: the startup check reads `.py` sources the build does not carry. No released
   build has this yet (the last tag is 1 November); the next one will.
4. **Three ways a save loses something at a close and reopen**, and no test that would catch the kind: a save opened twice
   with nothing typed cannot be opened again; a fight resumed after a reload has lost what it was for; a talk and the session's
   own memory are not in the save.
5. **The startup check takes 9 to 12 seconds at every launch**, and about 460 of the suite's 1,706 seconds. One loader change
   brings 9 s to about 3.6 s.

## 2. How it was done, and what it does not cover

**Method.** Nineteen readers each read one part of the tracked code in full (4,000 to 7,000 lines), bugs first. Five traced
one path end to end (a turn, a save, a fight, the background lanes, a replay). Twelve looked through one lens each (the
model's hot and cold tasks, the flow of calls, the checks, speed of a turn, health of the tests, speed of the suite, dead
code, dead switches, data, unneeded files, shipping). A skeptic then took each finding of any weight and tried to refute it
against the code, most by writing a script that ran the game's own functions on the CPU under simlib's stub. A critic read
the whole and named fifteen things missed; a second round of fourteen readers covered thirteen of them, checked every
dead-code claim name by name, and built one removal list.

**Measured base.** Three records: the played Gemma session of 18 November (42 lines, 154 calls, today's code, an RTX 4070 Ti
SUPER); the 44 tracked bot runs under docs/measure (14,035 calls, 10 and 11 November, about 130 features back, an RTX 5090);
and stub play made for this audit (about 11,000 bot lines for the aged save, about 5,700 inputs for stale copies, 1,888
logged typed lines replayed through today's repairs, 228 runs with one model task failed at a time).

**Limits. Read these before relying on a number.**

- **No model was run.** The card is shared with the owner's game. Nothing was measured under a changed grammar or prompt;
  every saving is the tokens a thing cost in a record, not a re-run.
- **Nothing was timed on a 3060.** Every minimum-card second is priced from token counts at the two rates in
  `data/measured/card_profile.yaml` (756.8 read, 31.7 written a second). The writing rate agrees with the records within 7%.
  The reading rate does not: the same scaling rule gives the 3060 anywhere from 271 to 935 tokens a second depending on which
  card it is scaled from (min-card-4, plausible). Only a timed night on the card settles it, which GOALS.md already asks for.
- **The full suite was not run, and no coverage map was made.** Which engine code no test reaches is still unknown (the
  critic's gap 12). It needs one full run under coverage, which is the owner's call on a free machine.
- **107 small findings are unchecked.** They are in the register with a blank verdict.
- **`saves/`, `logs/`, `models/`, `runtime/` and `data/runtime/server.yaml` were not read**, as the project's settings require.
  Two things follow that I could not check and the owner should know: (a) the readers made stub campaigns named `audit_...`
  and removed them in a finally block, but I may not list `saves/` to confirm it; any folder there named `audit_*` is from
  this audit and can be removed; (b) stub play appends rows to the game's own logs the way the suite does (tests-health-4),
  so `logs/llm_calls.jsonl` and `logs/turns.jsonl` may hold stubbed rows from this audit's runs.
- **Checks that compare by meaning were not replayed** (they need the helper model). Their send-backs were read by eye.
- **The usage limit stopped the first round twice.** It was resumed from its own record each time and ended complete: no
  reader or skeptic was lost.
- The replays the skeptics ran left a few dozen more `rerun_logs_*` folders in the temp folder (see 6.3).

## 3. Bugs

### 3.1 The heavy ones

| # | What happens | Where | Fix, in a line | Ids |
|---|---|---|---|---|
| 1 | Asking "What do I need for the next rank?" starts the rank trial for a member who has not earned it. | `scenes/trial_actions.py:71` | Delete line 71: the question then falls to the "not ready" answer two lines down. | scenes3-1 |
| 2 | One enchantment consumes the whole stack of the reagent (carry 5, pay 1, lose 5). | `engine/enchanting.py:146` | Spend one unit through `crafting.use_material`, the writer crafting already uses. | engine3-1 |
| 3 | A foe that fled, yielded or fell earlier in the foes' phase still takes its turn. One that ran can wound the player; a dead one "dies" again and the kill, with every kill perk, is credited to the player. Seen in 124 of 400 seeded rounds. | `engine/combat.py:3045` | Ask "is this fighter still in the fight" at the moment of the turn, not when the list is made. | engine2-1, trace-fight-1 |
| 4 | In a trial of rank the player's own summon being beaten wins the trial: promoted without a blow in 4 of 6 seeds. | `engine/damage.py:253` | A duel is decided only on its two duellists; one rule for who may stand in a trial. | trace-fight-3 |
| 5 | A missing-person contract divides by zero once all sixteen captive names are in the save. Measured: that is line 1,000 to 1,500 of a fighter's play, and it is the ordinary path, because the model's arc story is deferred by the budget on the shipped card profile. | `scenes/arc_actions.py:213` | Stop drawing story people and captives from a list of sixteen: name them with `npc/names.py` apart from every name in the save. | scenes1-3, aged-save-6, aged-save-5, people-3 |
| 6 | A save opened twice with no line typed between skips the opening, so the campaign's own places are never put back on the map. Standing at a dungeon entrance, a home, a found place or a road stop the game fails with KeyError at every later open: the save cannot be opened. | `scenes/world.py:943` | Put the campaign's places back on the map at every open, outside the once-per-count check (read only, no store write). Partly known (docs 20 and 27). | trace-save-1 |
| 7 | A fight resumed after a close or a crash has lost what it was for. A dungeon chamber won is not cleared (its foes, XP and loot come again); an arc's camp must be beaten again; the High Keeper fight loses the win; an assault on a town decides nothing. | `scenes/dungeon_actions.py:229`, `scenes/orenna_actions.py:273`, `engine/events.py:1415` | One saved record of what the fight is for, written when it begins and read by the four `*_fight_over` handlers. | scenes1-1, trace-save-2, scenes3-5, engine3-8 |
| 8 | A situation whose own way is met by a kill credits nobody. The same kill ends it won, ends it lost with its fallout, or ends nothing, by what its record happened to hold before. | `engine/situation_parts.py:600` | Record who met a way on the thread, apart from the 40-row window; `touched()` and `contributors()` read it. | situations-1, situations-2 |
| 9 | No find the model proposed has ever been accepted: 4 of 4 discovery calls in the Gemma record and both Qwen runs were refused for a missing name. The grammar lets the name be empty and the validator demands it; the retry repeats the answer. The player reads "a promising lead comes to nothing". | `llm/contracts.py:1943` | Build the call's contract from its context so name, kind and description are required in the grammar. | logs-fields-7, llm-checks-6, logs-sendbacks-7 |
| 10 | A game built from this tree cannot start: six scans of the startup check read `.py` sources the build does not ship. | `engine/data_check.py:1061` | One reader of source in the check that answers None in a built game; the code-side comparisons skip on None. | frontend-shipping-1, speed-turn-2 |

Rows 11 to 13 of the thirteen are the journal note (section 4.1), the startup check's time (5.1) and the quick suite run
that picks 437 of 519 tests (7.2).

### 3.2 The classes behind most of the rest

GOALS.md asks for the fix that covers every case of a kind. Most of the 119 confirmed bugs of weight fall into ten kinds,
each with one piece of infrastructure that would close it and find its remaining members.

**A. State that lives only on the scene object, so a close and reopen loses it.** Rows 6 and 7 above; a talk with someone
who is no resident of the place (world_py-2); what the checks and prompts remember of the session, the worn words and the
voice guard (trace-replay-1); a found place that moves on the map after a reopen (engine4-2); a pending errand that holds the
hire by reference (scenes3-3). *The infrastructure is a
test, and nothing has it today:* play each kept session straight, and again with the game closed and opened part-way, and
compare state and shown lines (trace-replay-2). This audit found the kind eight times by hand.

**B. Two copies of one record: the later save undoes the earlier.** The store has no identity map; every load is a new
object and every save writes the whole row. Under an instrument that watched every load and save over about 5,700 stub
inputs: 45 lost updates in 6 pairs of call sites (one pair is a test script's own doing), every one a real loss, none
harmless (`tables/stale_copies.md`). What a
player meets: a situation's moment is never listed as seen and is not closed for days (35 times, the commonest: stale-copies-1);
a town's memory row wiped (stale-copies-2); the thanks for a job done, trust +5, gone after the asker's reply (scenes2-1); a
dead ally's job back in the journal with nobody to hand it to (engine3-3, engine5-1); a goodbye forgotten (stale-copies-3);
a failed haggle's cooling never saved (stale-copies-4). *Infrastructure:* the stale-save check the world state already has,
widened to every record kind and noted in the suite and night runs (one ratchet list a kind that only shrinks). The larger
step, one live record for each operation, is a design of its own and the owner's to rule on (stale-copies-6, plausible).

**C. A death, a flight or a turn that does not go through the one path.** Row 3 above; a death by a tick, a torn wound, a
rebound or Death's Door skips what a death sets off (trace-fight-4, engine2-2, engine7-3); `start_turn` treats every dead
foe as dead of an affliction (trace-fight-5); a floor that holds a killing blow is undone by the torn wound in the same blow
(trace-fight-2); Spell Echo repeats onto the foe it just killed, so every kill perk pays twice (fight-abilities-1); the rest
of an area spell strikes foes who broke and ran at its first kill, who end both fled and dead (fight-abilities-2); a fleeing
foe killed by the parting strike is told as fled (engine1-3); Dominate on the last foe wins at once (trace-fight-6); taming
leaves the engagement standing (trace-fight-7). *Infrastructure:* one `fell()` and one `left()` that every way out of a
fight goes through, and one "may this fighter act" asked at the moment of acting. The player's abilities held up well
otherwise: 668 checks over every rider, shape, buff, command, heal, summon and maneuver passed (`tables/fight_abilities.md`).

**D. The typed line read again by a pattern after the model has read it.** The owner's census counts 324 places in 166
functions. Replayed on 1,888 real typed lines with the plan the model gave, today's repairs change the model's reading on 26%
of lines. Most of that is right. The readers wrong most often are the ones that overrule a field the plan already filled:
with a hire having just spoken, the follow-up takes 178 of the 1,888 lines as chat to the hire, and the model had read 169
of those as something else (typed-patterns-1); "The guild hall feels warm tonight." pays the joining fee (typed-patterns-3); "I can't sleep, so I
whittle a stick" sleeps fifteen hours (typed-patterns-4); "wait until two guards pass" is two o'clock (engine2-4); "twenty
five silver" is 5 (scenes2-3); "fine, take me to jail" pays the fine (scenes2-4); a threat is recorded as a promise of mercy
(scenes1-6); `inventory.find` matches by substring over every word of the line (engine4-1); "I sit down and give Odly the
draught" has the player drink it (engine1-6). *Infrastructure, and it is the measure plan 29 was waiting for:* a handler is
given its step, not the line. `tables/typed_patterns.md` sorts all 166 functions: 62 to replace by a field of the plan, 93 to
keep as eight shared readers with a corpus test, 11 to remove. The corpus today pins repairs that never fire in play and has
no case for the ones that fire most (typed-patterns-7).

**E. What the player reads when a model task fails.** 228 runs, each failing one task one way over the kept scripts
(`tables/task_failures.md`). The turn machinery holds: nothing is half written. What does not: a lost passage is stood in for
by "No trouble. It's done." or "You see it through." whatever the deed came to, a failed theft and a refused deed included
(task-failures-1, dead-families-1); a fight round whose telling fails shows no figure at all, so the player can die reading
"The round is over." (task-failures-2); a once-only writing that fails is never asked again, so a hire keeps no details and
an arc its plain story (task-failures-4); at a road stop an act still waiting for its ruling is paid as help done
(task-failures-3); the starting companion's call has no fallback and stops the game at the first waking (people-8); a failed
rewrite throws away the good draft (scenes3-4); a silent line's telling asked inline loses the line (world_py-1).
*Infrastructure:* a stand-in is filled from the ledger's own facts of how the deed ended (only 8 of 33 ledger rows carry
them today, and none carries how a roll went); the deferral queue takes model failures of once-only writings as it takes the budget's; and one test that fails
each task in turn through a played session (task-failures-9).

**F. The fighter is a copy of the character, and pane commands change only the character.** Gear and enchant commands are
taken in the middle of a fight; the sheet shows bare hands and the next round still strikes with the longsword
(pane-commands-1). An attribute point spent in a fight is lost at the next typed line (pane-commands-2). The command path
itself is sound: every `#` command is one operation, replays, and cannot reach the game while a turn is being answered.
*Fix:* a command's default in a fight is "locked" (today's list is a deny list, which is how one was missed); whether gear
may change in a fight, and what it costs, is the owner's rule.

**G. Situations: who did it.** Row 8; the same line said again stands on its kept ruling and applies its changes again,
trust +10 a repeat with no model call (situations-8, known in part); a change that rests on an earlier one is kept or
dropped by the wrong rule in three places (situations-5, -6, -7). The machinery is otherwise steady: 30,000 random chains
never raised and never wrote where they should not (`tables/situations.md`).

**H. Long saves.** An aged save was grown to 6,000 lines under the stub (`tables/aged_save.md`). No request section grows
without bound and no request came near the slot. What does grow: row 5; Word of Recall refused in the town reached after any
road stop, because the stop is remembered as the town behind and is off the map (aged-save-2); half the people rows of an
aged save belong to nobody left in the world (aged-save-7); captive and released-stock rows are never trimmed (aged-save-8);
four of the player's stores gain a key at every road stop (aged-save-9); the process's memory grows 4.7 MB a hundred lines
(section 5.2). *Fix for the kind:* one helper for "this place is a road stop", asked by every writer that records a town.

**I. Faults swallowed without a record.** 68 broad handlers whose whole body is `pass`, `continue` or a constant; 27 in game
code either skip a state change or answer for the fault ("There is no lock here that you can find." for any error at all)
with nothing in crash.log, against decision f449 (`tables/silent_excepts.md`). None of the 27 caught anything in 91 watched
tests, so none hides a live fault on those paths today. *Fix:* crashlog has no record-and-carry-on helper; give it one and
route the 27 through it. Eight of them also catch a cancelled call as an ordinary failure (silent-excepts-4).

**J. Shipping.** Row 10; in the built game crash.log, refusals.jsonl and the audit log land inside `_internal`, not in the
logs folder the player is pointed to (shell1-8, dead-switches-2); `UPDATE_CHECK = False` does not stop the window's update
check (shell1-7, dead-switches-1); a start that fails is told under the home page and the window closes itself, so the
player never learns why (frontend-shipping-2); a line the server refuses leaves the page locked (frontend-shipping-3); the
self-update downloads an installer to the shared temp folder and runs it silently with no digest, size or look at where the
link points (leftovers-1, shell1-9); a deleted game moved back is never listed and an unreadable index hides every game
(shell2-1); an update removes no old data files (frontend-shipping-6). *Infrastructure:* nothing builds or starts the
packaged game in CI or in the hooks (frontend-shipping-7). A step that builds it and reaches the home page would have caught
row 10 the day it was written.

### 3.3 Other confirmed faults of weight, one line each

- `gendered()` adds -s to any word after he, she or it, so prompts read "keepses" (engine3-2); `first_person()` writes "I hums" into the lines that feed the canon checks (engine2-5).
- A struck companion is told it happened "yesterday" the minute it happens (engine6-2); the return greeting gets the person's newest memory of anything as their last memory of the player (engine6-3).
- Another arc's captive completes this arc's step (scenes1-5); one beaten foe counts twice for a bounty (scenes1-4); at an arc's last fight the dead leader is made a walking captive (scenes1-2).
- A yes to a person's request, said where a guild clerk stands, goes to the board and can take an unrelated contract (scenes2-2).
- Every gift of any size moves bond +1 and trust +2 with no bound: 45 coppers make a hire devoted (scenes2-5, known).
- A stale rank offer takes the teacher's fee and teaches nothing (scenes3-2).
- Overcast buys through a named spell's once-a-fight and day locks and through any ability's cooldown (fight-abilities-4); a charged spell loses every bonus fixed when it was begun (fight-abilities-5); Blood Summons charges mana as well as health (fight-abilities-6); a Bound summon recast in a fight is gone at the next (fight-abilities-3).
- A reforge rolls spell power at full size on gear that a drop halves (engine4-3).
- People who flee a fallen town leave no vacancy behind (engine3-4).
- Traits and the speech profile are rolled from the same seed, so a person's culture decides which traits they can have (people-1).
- A walk to where the character already stands says nothing and is recorded as a walk done (trace-turn-1); a few handlers refuse with a bare note, so the step is recorded done and the narrator is never told NOT DONE (trace-turn-2).
- A typed line in a fight that is no fight action is resolved as an improvised gamble and costs the round (trace-fight-8, known).
- Helping at a road stop reached from another stop raises KeyError (stale-copies-5; 5 times in 4,800 bot inputs).
- 'humanoid' is not a creature category, so one war in three draws its hosts from every category (data-1).
- `nightrun --save NAME` deletes `saves/NAME` unasked, whatever it is: a player's own game, or a path outside saves (tools2-3). `tools/prose_baseline.sh` removes the game's own call log twice (leftovers-3).

## 4. Better use of the model

### 4.1 Where the time goes, and what would give it back on the minimum card

In the played session: 154 calls, 397 seconds of model time, 268 seconds of turn time over 42 lines, a median of four calls
a line. In the 44 runs writing is 62% of line time at the minimum card's rates and reading 38%. Priced there, the recorded
lines come to:

| Record | Median line | 95th | Longest | Over 45 s | Over 60 s |
|---|---:|---:|---:|---:|---:|
| Played session, today's code (41 lines) | 17.5 s | 36.5 s | 45.0 s | 0 | 0 |
| 44 tracked runs (2,620 lines) | 18.1 s | 47.0 s | 93.5 s | 6.5% | 0.65% (17 lines) |

The savings the first round found, each applied alone to every recorded line (`tables/min_card.md`, part d):

| Saving | Off a line, mean | What it does for the worst lines | State |
|---|---:|---|---|
| **journal_note out of the reply unless a note is due** | 0.9 s | The only one that removes a single call over 60 s. Longest line 93.5 to 72.0 s; lines over 60 s 17 to 6. On a 3060 a reply that runs to 2,048 tokens cannot finish (64.6 s of writing): it is cut, the tries end, and the player waits about 55 s for nothing. About 1 talk in 80. | Known since the settings trial; not built. llm-checks-1, min-card-2, logs-sendbacks-1 |
| **The shared slot's prompts cached** | up to 4.9 s (3.4 s for the system messages alone) | The largest saving on an ordinary line: 92 of 105 requests in the played session had nothing cached. Lines over 45 s 6.5% to 2.0%. Little for the longest line, which is writing. | Known (f536). The one saving with no built answer: the RAM cache was measured and lost (f537); a third slot for the narrator is unmeasured on 12 GB. llm-flow-1, llm2-1, min-card-6 |
| **Compact layout in the grammar** | about 0.9 s | Indented layout is 5 to 34% of what structured answers write, about two tokens for each line break. 1.9 s on a first arrival's people. | One `space` rule from data in `llm/llama.py grammar_of()`; `llm/gbnf.py` stays the faithful port. Must be measured with the live gate: it changes what the model may write between fields. llm-hot-5 |
| **A place's first people and a person's profile written outside the turn** | 0.9 s | All of it on lines already long: 9.6 s on a first arrival, 3.8 s on a first talk. | llm-flow-6 |
| **No whole rewrites by `fresh()`** | 0.4 s | 5.4 s on each of the 204 rewritten passages (16% of first narrations). 24 of 82 stale-phrase rewrites were for a run of little words ("at the far end of"). | llm-flow-8, logs-sendbacks-14 |

All five together: median 18.1 to 11.4 s, 95th 47.0 to 32.3 s, longest 93.5 to 54.4 s, no line over 60 s (with the layout
priced at one token a line break, which the check showed is about half its cost). The two that are
grammar only (the note and the layout) need no prompt rule, no sampling change and no new call.

### 4.2 The budget's own arithmetic has two holes

These decide what happens on the day a line does run long, whatever its usual length.

- **A retry is never asked of the budget** (min-card-1). `allow()` is asked once before a call's first try; every later try
  and the looser last pass is handed at least the 8 s floor however far over the turn already is. Shown on the game's own
  gateway: with 8.1 s left one required call made 5 tries and the budget's own count ended at 101 s of 55.
- **A try cut at the deadline is charged its expected size, not the time it ran** (min-card-3), so the budget counts room
  that is gone. Also: people a place still lacks are asked for before the line's budget opens (min-card-7); the first line
  after every launch is charged about 35 s for a 1 s embed (engine1-1); embed calls carry no turn deadline, so a stalled
  embedder holds the turn for 120 s (llm2-2, trace-threads-3).

### 4.3 Answers sent back that needed no second call

In the 44 runs the game sent 556 answers back; the second and third tries and the rewrites are 5.4% of the game's model
time, and 41 requests were lost outright (`tables/logs_sendbacks.md`). About 320 of the 556 are things the page's own
cleaning already mends, or a sentence that could be dropped in place:

| Reason | Count | What the reading found |
|---|---:|---|
| A word joined with an underscore ("mud_slick") | 171 | The largest single reason. None is a game label. `hygiene.clean()` already turns the underscore into a space; it needs a full stop where a capital follows (about 50 of them are a lost full stop). |
| A dialogue frame shows them going back to work | 71 | Half of all frame send-backs. 42 right, 15 false alarms ("returns their gaze"). Dropping the sentence that carries the hit settles all 71. |
| A carriage return before a line break, told as "a character came out broken" | 43 | The reason quotes an invisible character, so the retry repeats it: 39% of these requests are lost. |
| A literal backslash-n; a stray JSON tail; a request heading echoed after a good frame | 15, 4, 11 | `clean()` mends the first two already; the frame can be cut at the heading. |

One mend pass before the gate, built from the cleaning the page already does, would cover them. A foreign word in
mid-sentence (54, 31 of them the same Korean word) is better stopped at the source: a character rule in the grammar makes 46
of the 54 impossible to write (logs-sendbacks-6).

### 4.4 Checks that are wrong more often than right

- The amounts check on party talk: 21 of 24 send-backs are false alarms, 16 of them the hire's own oath "By the Nine Winds",
  which the engine offered in the same request; "twice as hard", "half-asleep" (logs-sendbacks-2). Six exchanges lost.
- Ability text refused on substrings: "individual" as "dual", "amount of" as a mount, "Cold Steel" on a plain technique as
  cold damage (engine1-2, unmeasured-tasks-2). One badly worded ability sends all fifteen back, up to five whole answers,
  though the check knows which slots failed (unmeasured-tasks-3).
- The clarify line's "game word" list: 4 of 4 false alarms on "intent" and "action" (logs-sendbacks-13). The stock-opener
  and no-question checks: 9 of 16 ("See you then.", "Trouble? Well, ...") (logs-sendbacks-8). Maren's speech sent back for
  "game trail", "half a mind", "double back" (unmeasured-tasks-5). `truth.coined` rejects "Maren'll" (engine7-1). The hire
  check fires on "I have a staff" (llm-checks-10).
- The content guard's list holds bare words with innocent senses and no allow list: "it cocks its head toward you" was sent
  back, and "a naked blade" would be today (logs-sendbacks-12).
- The looser last pass let the player's own line be printed as the innkeeper's answer in one Qwen run (llm-checks-7).

### 4.5 Fields the model writes and nobody reads

Per task and per field in `tables/logs_fields.md`. The heaviest:

- A townsperson's reply has 12 fields, 7 never filled in the played session, all written after the speech (llm-hot-3);
  `reveals` was written 10 times and none kept (llm-hot-2).
- A hire's reply writes `impression` and `they_promised` on every line: impression filled 0 times in 1,182 replies, the
  promise 7 times, 4 of them on a line that promised nothing (logs-fields-2).
- The fight's reader writes a `summary` that is half its answer and unread in all 291 fight lines (logs-fields-1);
  `camp_intent` writes a summary nothing reads (unmeasured-tasks-10); `audit_compare`'s reason is nine tenths of its answer
  and only logged (logs-fields-4).
- The interpreter's `summary` is 46% of what it writes and ran away to the 700 token ceiling 4 times in 2,481 readings
  (logs-fields-8, logs-fields-9).

One rule covers the kind, and it is llm-hot-7's: every string that is neither spoken nor narrated gets a `maxLength` from
data through one helper, a field the engine knows it will not keep this call is left out of that call's grammar, and the
startup check refuses a contract with an unbounded unspoken string. It puts no length limit on a narrator or a speaker.

Two real losses hide in the same tables: a hire's detail weights are thrown away for one hire in three, because the model
gives seven and the contract keeps five (logs-fields-5); and the model picks each starting perk's number while the request
shows it only the higher of the two values (logs-fields-6).

### 4.6 Ids the engine knows, left as free strings

`situation_parts` is asked with free-string ids and 1 of 11 parts was kept (engine6-9). About sixteen more answer fields are ids
the engine holds the whole valid set for at the time of the call; a wrong one sends the answer back or is silently lost
(logs-fields-11, unmeasured-tasks-9). Build the enum into the call's grammar from its context, as `engine/act.py shape()`
already does. A test over every contract would hold the kind: a field a validator demands is required in the schema that
call sends (llm-checks-5). The night bot's own line is that kind's worst case: `{}` on 20% of first tries, a fifth of the
bot's model time (logs-sendbacks-15).

### 4.7 What the prompts carry

- The interpreter's PLACES list is filled to 32 with the insides of other towns on every line, about 200 tokens, and sits
  second from the top, so about 885 tokens are read again each line (llm-hot-8, llm-flow-3). Order the blocks by how often
  they change.
- `dialogue_frame` reads 2,200 tokens to write two sentences (llm-hot-13).
- Three requests are mostly a whole-world list: `arc_story` sends every person's name in the save with no cap, 81% of the
  request (unmeasured-tasks-8).
- Every guild contractor in all 13 halls is told they know the Greywood from their own jobs (world_py-5); every profile of a
  town takes the same concern (llm-rest-3).

### 4.8 Calls and waits

- **The audit of a reading.** A correction to the first round: it said no audit changed a plan in the played session. In the
  tracked logs 173 of 917 audits led to a second reading and about 131 came back different, so it does work. Its word test
  is the weak part: it sends 43.7% of real lines to two more model calls, and `unmatched_verb` fires on nouns
  (typed-patterns-9, typed-patterns-10, llm-rest-1). Before plan 29 drops the calls, those 131 pairs are worth reading by a
  person and turning into corpus cases.
- **From New Game to the first typed line: ten model calls, 150 to 181 s of model time on the minimum card**, about 66 s of
  it one foreground wait for the fifteen abilities (unmeasured-tasks-1). Creation is outside the turn budget by rule.
  19 of the 23 tasks this part looked at have never been in a recording, and their budget sizes are first guesses
  (unmeasured-tasks-12).
- In Maren's lesson the walk to the hall carries five required calls, 45 to 97 s on the minimum card (unmeasured-tasks-7);
  a line her free speech fails is asked for twice more before the written line shows (unmeasured-tasks-6).
- A situation's birth is asked in the foreground after the passage, about 20 s each on the 3060 (llm-flow-5; doc 14 plans
  the background lane). A background job starts 120 s late beside a turn: the 132 s `populate_place` of the played session
  was 120 s of waiting to be let in (llm-flow-4).

## 5. Speed

### 5.1 The startup check

9 to 12 seconds on every launch before the home page, and the suite pays it about 50 times: 460 of 1,706 seconds of test
time (speed-turn-1, engine3-7, data-6, suite-speed-1). It parses 143 files 240 times with PyYAML's pure-Python loader and
re-reads source for each scan. Three steps, each safe alone: base the strict loader on `CSafeLoader`, which
`core/yamlio.py` already picks (9 s to about 3.6 s, one line); parse each file once a check; read each source file once.

### 5.2 The engine's own time in a turn

Small beside the model (2 to 3% of a turn), but it ages. A plain line is 8 to 17 ms on a new save and 100 to 190 ms from
about line 2,000, flat after that because the stores it reads are at their caps.

- The world state is read whole 13 or 14 times a line: 45 to 55 ms of every plain line on an aged save (trace-save-5,
  aged-save-3, shell2-10).
- The news window asks the map for a route for each of up to 300 news rows every time the facts are built: 21 to 29 ms a
  line (aged-save-4).
- Every stand-down for a model call throws away the map's caches though nothing on the map changed (speed-turn-3). The route
  cache recomputes its signature on every call, 144,000 times in 46 turns: fixing it took 46 stubbed turns from 7.5 to 10 s
  down to 5 to 6.5 s (speed-turn-4, people-10).
- The first line of a session pays a 1.2 to 1.9 s map layout at every age (speed-turn-5).
- **Memory.** Every answer a contract refuses pins the whole stack of its turn for the rest of the sitting, because the
  gateway keeps the ValidationError: 358 MB from 77 at 6,000 lines, against 96 to 104 MB with the mend, which is one line
  (`last_error = LLMError(reason)`) and was run (aged-save-1). The page's transcript is never trimmed: 240 nodes a hundred
  lines, 77 ms a turn at 9,940 nodes (frontend-shipping-11).

### 5.3 The suite

See 7.2: the quick run picks 437 of 519 tests, the suite uses 4 of 28 logical processors, and start-up is about 40% of test
time.

## 6. Dead code and unneeded files

The removal list is `docs/design/32_code_audit/removal_list.md` (560 lines). It holds only what a skeptic confirmed, with
every range opened in today's code, the tests that exist only for each item, and one line on why it is safe.

### 6.1 Totals

| Group | Entries | Lines | Bytes |
|---|---:|---:|---:|
| Whole files and modules | 5 | 782 | 44,538 |
| Functions, classes and methods | 60 | 708 | 45,075 |
| Constants, parameters, imports, data keys | 36 | 250 | 9,748 |
| Code behind a switch that has never been on | 2 | 92 | 6,880 |
| Tracked files that are not code | 5 | 3,523 | 215,268 |
| **Tracked, in all** | **108** | **5,355** | **321,509** |
| Outside git, left behind by tools | 6 | | about 3.5 GiB |

### 6.2 The larger items

- **Whole files:** `character/history.py` (imported by nothing since the first commit); `tools/runstats.py`;
  `tools/scratch/` (neither probe runs); `tools/sim/simreport.py` (an older copy that fails at import); four dead scripts
  in `tools/sim` (`tune_party.py`, `tune_camps.py`, `matrix.py`, `cc.py`).
- **Across files, one change each:** the retired stat-passives creation step (205 lines in six files: the contract, both
  prompts, the request builder and the stub's answers for a request no code makes); the old one-call abilities flow kept as
  a fallback nothing reaches (66 lines); the mentor's rank check that no call can run (25); seven test-only wrappers on
  CombatScene (34); the typed hiring path, while `party_notice` still tells the player to say "recruit help" (scenes3-10).
  One trap the list records: the tuple of names at `llm/prompts.py:320` is read through `globals()`, so a prompt and its
  name there must go in the same change or the game stops at import.
- **Imports:** 106 unused `import yaml` lines in 105 files, 19 others.
- **Data nothing reads:** 45 lines of authored text in `data/world/mentor.yaml`; five rule keys that promise a rule the
  engine does not apply; three ledger kinds with no adder. Fifteen more "stood" lists in `data/rules/failures.yaml` can
  never be shown, which is a fault to wire, not text to delete (dead-families-2). `behaviors.text_for()` has no caller, so 48
  `text:` lines of `data/world/families.yaml` never reach the narrator: held as the owner's call (wire or delete).
- **Switches:** `conditional_rolls` has been false since the first commit; the model's motive step has been the engine's own
  since f360 (65 lines, a contract and a budget row for a call asked 0 times in the record).
- **Not code:** four root scripts that begin `cd /home/claude/r56` and `sim_report_full.txt`, all tracked against
  `.gitignore`; both files in `docs/patches`, already applied; `docs/tests/improv_dice_repro_test.py`, a byte copy of the
  test the suite runs.

### 6.3 Outside git: about 3.5 GiB that tools leave behind

Nothing was deleted. These are the owner's to remove.

| What | Made by | Size |
|---|---|---|
| `rerun_logs_*` in the temp folder, one for each replay, never removed (about 11,740 folders in nine days) | `tools/rerun.py:359` | 2.1 GiB |
| `meravia_base_<commit>` worktrees in the temp folder, one for each commit the Stop hook has seen (46) | `.claude/hooks/quick_suite.sh:9` | 1.3 to 1.4 GB |
| A second copy of the repository at `.claude/worktrees/intelligent-saha-40633a` (branch merged) | a past session | 105 MB |
| About 2,070 small temp folders from 17 test prefixes | `tools/sim` | not measured |
| `logs/audit`, one file a session with no cap; `logs/pulse.jsonl`, no cap | `llm/audit.py:45`, `engine/pulse.py` | not read |

The fixes that stop the growth are small: a finally block in `tools/rerun.py`; the quick run taking the old text from
`git show` instead of a worktree (suite-speed-2's fix removes the worktrees altogether); a cap on the two logs, which the
owner's rule that every store gets a cap already asks for.

### 6.4 Do not remove: claims the check refuted

- **`decide_then_speak`** (494 lines) is a finished feature behind the owner's switch, waiting on the blind reading.
- **A1's sampling arms** are paused, not closed (GOALS.md line 179); the rule that sampling settings stay covers them.
- **`docs/measure`** (37.3 MB of the 58.5 MB tracked tree) is the kept record on purpose; GOALS.md cites it as evidence.
  What could change is the format: the gzipped call logs weigh 31 MB in git's history (unneeded-files-4).
- **`docs/research`** holds the sources of the shared-world report.
- **The dormant server start** in `llm/runtime.py` is a guarded fallback that runs when `data/rules/launch.yaml` is missing.
- **Needs (hunger and fatigue)** are off, but parts are live with the switch off and no document says the systems are
  abandoned: plausible only, the owner's call.

The opposite of a removal: eight documents that tracked files cite are not in git (`docs/play`, cited on 69 lines; doc 26;
five dated measure reports) (unneeded-files-5).

## 7. Tests and the suite

### 7.1 Tests that cannot catch what they are for

- 15 checks end in `or True`; 5 of them hide a claim that is false today (tests-health-2). `party_test` has no check, no
  assert and no exit code, and has been writing a real error to a temp file nobody reads (tests-health-3).
- Four window tests skip their page checks and print a pass wherever node with playwright is missing, which is the owner's
  machine and CI: `follow_test` runs none of its 10 checks (tests-health-5).
- A replay passes when the game stops short of the recording: calls left unserved and lines never asked are not compared
  (tools3-1).
- The party golden keeps none of the claims its script plants, so the recording pins no kept claim, no promise and no canon
  check (leftovers-4). No golden sends a pane command in a fight and plays on (pane-commands-6).
- The balance bot has drifted from the engine five times with the suite green: no bot fight is ever recorded, every purchase
  raises, and a run ends at level 1 (shell1-1, -2, -3, -5, tests-health-1). The night bot never works a situation's contract
  (tools2-1).
- The suite writes its stubbed model calls into the game's own `logs/llm_calls.jsonl` and the turn, pulse and crash logs
  (tests-health-4). The fake llama-server takes any command line, so a flag the pinned build does not know passes every
  launch test (leftovers-7).
- Missing as a kind: the close-and-reopen comparison (3.2 A), a test that fails each model task in turn (3.2 E), and a build
  that is started (3.2 J).

### 7.2 The suite's own speed and trust

- **A quick run counts every untracked file as changed and picks tests by the bare word of its name: 437 of 519 tests
  today, with no tracked change in the list** (suite-speed-2). It also never picks the fence tests that read code as text
  (suite-speed-3), and does not see a change to a `.json`, `.html`, `.css` file or the page's script (suite-speed-4).
- The push marker trusts any summary: a run of one test, of none, or of an earlier commit marks HEAD as passed
  (suite-speed-7).
- The suite uses 4 of this machine's 28 logical processors, in name order with a 39 s test among the last twelve
  (suite-speed-8). Start-up is about 40% of test time (suite-speed-9), most of it the data check (5.1).
- The default `--outdir /tmp/meravia_suite` is two different folders on Windows, and the failure line sends a reader to the
  other one (suite-speed-6).
- CI sees only pull requests and main, on Python 3.12, without requirements.txt (frontend-shipping-7).

## 8. Data

- 22 code defaults differ from the data's value, 3 keys are set nowhere, and 43 of 129 data files have no startup check
  beyond parsing (data-2, known in part).
- About 60 roster creatures can be met by no road in play, and 172 of 549 fit no place's wild roster; nothing at startup
  says so (data-5).
- Fourteen rule keys nothing reads, some of which promise a rule the game does not have, such as heavy armour's stamina
  recovery (data-3). Two are to be wired, not deleted: `needs.yaml sleep_after_minutes` and
  `dungeons.yaml rest_in_chamber_only`, which the code holds as its own copies.
- `mentor_chat`'s prompt ceiling (11,500) is under every such request play builds (aged-save-10).
- Authored lines that read wrong where they are shown: Maren tells a new caster mana cannot be got back in a fight while a
  mana tonic is sold in town (leftovers-8); a stand-in opens a sentence on a lower-case creature name, and says "Here they
  come" when the player struck first (task-failures-8). These are the owner's to reword.
- The minimum card's reading rate rests on one scaled night (section 2). `tools/card_profile.py` could fit reading as a
  fixed cost a request plus a rate, which is what the records show (min-card-4).

## 9. A proposed order

Each line is one or a few numbered features, test first. Plans 29 and 31 both wait on the owner and both claim f731 onward;
where this order sits beside them is the owner's call.

1. **The journal note and the unspoken-string rule** (4.1, 4.5). Grammar only. It was already named as the next feature in
   the settings trial. With it, the discovery contract (row 9), which is the same kind of fix.
2. **The seven small certain bugs** (rows 1 to 5, Word of Recall, the pinned memory). One place each, and each test is a
   few lines. The two fight fixes may move the fight golden; that is settled a fix at a time with the rebless skill, never
   by re-recording to pass.
3. **Before the next release:** the built game that cannot start, the logs' place, the update switch, a failed start that
   says why, and a CI step that builds and starts the game (3.2 J).
4. **The close-and-reopen test, then the two save faults it would have caught** (rows 6 and 7).
5. **The startup check's loader and the quick run's picking** (5.1, 7.2): they give time back on every launch and every
   Stop from then on. With them the temp-folder leaks (6.3).
6. **The mend pass before the gate, the false-alarm checks, the compact layout** (4.3, 4.4, 4.1), each measured with the
   live gate before it is kept.
7. **The removal list**, in five or six changes by group.
8. **Designs that need a plan first:** the step and not the line (plan 29 has the measure it was waiting for); one path for
   a death; stand-ins that know how the deed ended; the stale-save check over every record kind; pane commands in a fight;
   the shared slot's cache on 12 GB, which needs the card.

## 10. The companion folder

`docs/design/32_code_audit/` (about 4.5 MB, untracked like this file):

- `register.md`: one row for each of the 584 findings, with its verdict.
- `findings_bugs.md`, `findings_llm.md`, `findings_speed.md`, `findings_dead_code.md`, `findings_tests_data_other.md`:
  every finding whole, with its evidence, what a player meets, the fix and the skeptic's check.
- `removal_list.md`: section 6 in full.
- `tables/`: the fourteen tables of the second round (the minimum card, the send-backs, the fields, the aged save, typed
  patterns, stale copies, task failures, silent handlers, situations, fight abilities, pane commands, the tasks never
  measured, dead families, leftovers).
- `repro_scripts.zip`: the 1,204 scripts the readers and skeptics wrote (not their outputs). Paths in the findings that
  begin `work/` are inside it. Many are most of the way to the test a fix needs.

Given the weight the audit itself found in docs/measure, I would commit this file and `removal_list.md` and decide about the
rest of the folder separately.

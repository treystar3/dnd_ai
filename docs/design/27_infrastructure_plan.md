# 27. The five infrastructure changes: plan

Date: 2026-11-17. Follows docs/design/26_approach_review.md (section 5.4, items 1 to 5) and the owner's answer of the same day:
"let's do your 5 infrastructure changes now then begin with phase 4". This is the plan CLAUDE.md asks for before anything that
touches more than two modules. Nothing below is built yet.

Six features carry the five changes (the turn driver is split in two, so its risky half can be checked alone), in build order:

| Feature | Change | Touches | Behaviour the player sees | Goldens |
|---|---|---|---|---|
| f717 | The suite loop | tools/run_suite.py, a tracer beside it, test markers | none | do not move |
| f718 | The data hash in two parts | storage/statehash.py, tools/rerun.py, engine/recording.py | none | re-blessed once: the hash's meaning changes, nothing else |
| f719 | The live gate | tools/live_gate.py (new), data/rules/gate.yaml (new), tools/interp_eval.py, tools/latency.py | none | do not move |
| f720 | Rollback by declaration | engine/actor.py, engine/session.py, scenes/world.py | none intended; any real gap it finds is reported, then fixed | must not move |
| f721 | One turn driver | scenes/world.py (run, turn, the opening) | one fix: exactly one closing line an input | must not move, but for that line |
| f722 | One ordered page | engine/operation.py, scenes/world.py, ui/console.py | the order of notes and passages in a turn | move, each change explained |

Order: the suite loop first (every later feature is checked faster and never collides with the stop hook's run), then the hash
(f720 to f722 would each force a re-bless without it), then the gate (phase 4 needs its numbers as the "before"), then the three
that change the turn's own code, the least risky first.

## f717. The suite loop

**What is wrong today** (tools/run_suite.py, read 17 November):
- `--changed` picks tests whose text mentions a changed file's name. The ten most central files (`BROAD`: world, main, loader,
  console, simlib, models, rules...) are skipped with a note, so the stop hook checks nothing for the file changed most often.
  Picking by imports alone would not help: nearly every test imports simlib, which imports the whole game.
- `changed_files` walks the whole folder, into `.claude/worktrees/intelligent-saha-40633a` (a second copy of the repo on another
  branch), so that copy's files count as changed and its tests are found.
- Five tests that start processes of their own fail now and then beside others (gui_test, determinism_439, layers_517,
  registration_545, nights_529).
- Only a full run takes the lock (saves/.suite_running), and nothing waits on it: two full runs, or a full run begun during the
  hook's quick one, share saves/ and fail each other. On 16 November that cost about 55 false failures.

**The change (as built, 17 November):**
1. **Picked by what a test ran.** Every run records, for each test, the functions of the game it entered (Python's
   `sys.monitoring`, one event the first time a function starts and none after: no measurable cost) and the data files it opened
   (tools/suite_ran/sitecustomize.py). The record is kept in tools/sim/.ran.json, which git ignores. `--changed` then picks:
   - a test that ran a function whose code changed, is new or is gone (comments, docstrings and line endings do not count);
   - a test that ran a method a new method of a subclass now stands in front of;
   - every test that loaded a module or a class whose own lines changed (a table, a class attribute, a decorator);
   - a test that opened a data file that changed and names one of its changed keys, and the tests that compare the data hash;
   - a test that is itself changed, or that no run has recorded;
   - for any change to code, the nine tests that start a Python process the record cannot follow.
   With no record (a fresh checkout) it falls back to the old word match, `BROAD` and all, and says so.
   What it does not see, by design: a new handler found only by its name, and a number a test reads without naming its key.
   The full suite before a commit stays the rule.
2. **The stray copy is skipped:** any folder that is a checkout of its own (it holds a `.git`), and `.claude/`. A file that is gone
   counts as changed.
3. **A serial lane:** a test with the line `# suite: serial` runs alone, after the others. The five above have the line.
4. **One lock for every run,** the operating system's own lock on saves/.suite_running: a run that dies or is killed lets go of
   it at once, so there is nothing to go stale. A full run waits for it (`--wait SECONDS`, 1200); a `--changed` run waits two
   seconds and then leaves with exit code 75 and one line saying which process holds it. `--busy` stays, so the stop hook's
   script is not edited.

**Measured:** the full suite, 506 of 506, in 429 seconds with the record kept (439 and 431 on the two runs before; about eight
minutes before f717). The five tests that used to fail now and then passed in the serial lane on all three runs. A quick run
for f717's own change: 8 changed files, 14 tests, 76 seconds. A change inside `part_line` in scenes/world.py would pick 12
tests; inside `turn`, 112; a table in engine/actor.py, 484, since every test loads it.

**Left for the owner:** the stop hook reads a run that was turned away (exit code 75) as "the run did not finish" and blocks.
It can only happen if a run starts in the instant between the hook's `--busy` check and its own run. The hook is the owner's file.

**Test:** tools/sim/suite_loop_717_test.py, on a small made-up tree in a temporary folder, with the real runner.

**Risk:** low. The full suite is the same suite. The record can be stale between full runs; a full run still precedes every commit.

## f718. The data hash in two parts

**What is wrong today:** `statehash.data_hash` (storage/statehash.py:140) is one digest over every file in data/. A recording is
refused when it differs (tools/rerun.py:341). So any edit to a told line, a failure line or a prompt forces all three goldens to be
re-blessed even when, as in f715/f716, "no state, call, outcome or shown word differs". The re-bless that changes nothing teaches
everyone to skim re-blesses.

**The change:** two digests. `data` (rules: every file as today, less the wording) and `words` (the wording alone). What counts as
wording is declared in one new file, data/rules/wording.yaml: whole files, or keys of a file. Anything not listed is rules, so a new
file is on the strict side until someone says otherwise. A recording keeps both. Replay refuses on `data`, as today; when only
`words` differs it replays, and the replay itself says whether a shown word or a call changed, and at which input.
budget_data_459 and isolation_456 hold the rules digest.

**Test:** datahash_split_718_test.py: a changed told line moves `words` and not `data`; a changed number moves `data`; a file nobody
listed is rules; a recording whose words moved is replayed and passes when nothing it showed changed, and fails at the right input
when something did. The seven existing hash tests are updated to the two names.

**Goldens:** re-blessed once, for the new meaning of `data` and the new `words` field; no input, state, call or shown word differs.

**Risk:** low. The list of wording is decided at build from what forced the last ten re-blesses, and shown to the owner in the commit.

## f719. The live gate

**What is wrong today:** every measure the suite runs is against the stand-in model. The four things a person meets first are
measured only by a person playing: whether lines are read right, what the narrator invents, how speech reads, how long a turn takes.
The corpus's live pass rate had never been recorded before 17 November.

**The change:** one command, `python tools/live_gate.py`, on the real model and this card:
1. **Reading:** the corpus through `tools/interp_eval.py --live`: the share right, by kind.
2. **A played script:** a fixed list of about forty typed lines (data/replay/gate_script.yaml: travel, talk, explore, camp, a
   fight, lines of several steps), played through the real turn from a fixed save and seed. From its logs:
   - **inventions:** passages sent back for a creature not there (f701), and names in a passage that the scene does not hold, per
     hundred passages (rough by design, as tools/page_measures.py is);
   - **stiff speech:** the share of spoken replies sent back as stiff on the first try (f714);
   - **time:** the median and the 95th percentile of seconds by the turn's shape (talk, walk, explore, a fight's round, several
     steps), the inputs over the limit, and the stand-ins shown.
3. **Held against kept numbers:** data/rules/gate.yaml holds the floors (the owner's numbers). The run writes
   data/measured/live_gate.yaml and a dated report under docs/measure/, and exits non-zero under a floor. Until the owner sets
   floors it reports only; the first run is the baseline.
4. `--quick`: sixty cases drawn evenly by kind and fifteen lines, for before a playtest. The full run is for before a push that
   touches llm/, the prompts or the reading data.

The script's typed lines are shown to the owner before they are kept (pre-written player lines are the owner's to read first).

**Not in it:** a line in CLAUDE.md saying when the gate is run. That file is the owner's; the wording is proposed when f719 lands.

**Test:** live_gate_719_test.py with the stand-in model: the script plays, each measure is counted from a log made by hand with
known counts, a number under its floor fails the run, and nothing is written outside data/measured and the report.

**Risk:** low (tools only). The full run takes about forty-five minutes of the card.

## f720. Rollback by declaration

**What is wrong today** (engine/session.py:155-207, scenes/world.py:1165, engine/actor.py:71-118):
A failed operation puts the scene back by three means: every `_` attribute is copied and restored wholesale; the names in the
hand-kept tuple `WorldScene.ROLLED` (36) are copied and restored; `reload_after_rollback` rebuilds a few by hand (the player, the
fight, the residents, who is present). The comment on the tuple says what happens to a name nobody added: "the next failing
operation shows it".

Measured 17 November: the scenes' code sets 125 different names on `self`. 44 are in no list. About twenty of those are the world
scene's own, and about ten are written while a line is played with no declared treatment: `pending_clarify` (the question that is
waiting), `repairs`, `last_interpret`, `dropped_steps`, `line_text`, `learn_request`, `camp_events`, `revisit`, `first_arrival`,
`visitors`. Whether any of them survives a rollback wrongly is not known; nothing checks. (f633's test covers names held by
modules, not a scene's own attributes.)

**The change:**
1. **Every attribute of the world scene is declared once,** in engine/actor.py, beside FIELDS: its treatment (put back; kept, with
   the reason; rebuilt from the save; set once and never written in a turn; a cache) and its home for multiplayer (the turn's, one
   character's view, the scene's). `ROLLED`, `HOMES` and `UNLISTED` are read from that one table and keep their names, so the
   existing tests pass unchanged.
2. **Checked two ways.** A census: every name the scenes' code sets on `self` is in the table. And by running: a new test replays
   a golden and, at each operation in turn, makes it fail, then compares everything the scene holds with what it held before the
   operation. A name that differs and is not declared "kept" fails the test with its name.
3. `Session.begin_turn` and `rollback` read the table. `reload_after_rollback`'s hand resets become the table's "rebuilt" rows.

**Test:** rollback_declared_720_test.py (the two checks above). rollback_fields_579, turn_fields_628, turn_context_631 and
moving_parts_628 must pass unchanged.

**Goldens:** must not move. A name found to leak is a real fault: each is listed for the owner with what a player would have seen,
and fixed by its declaration.

**Risk:** medium. The table is mechanical; the second check may find several leaks, each needing a decision of "put back" or "kept".

## f721. One turn driver

**What is wrong today** (scenes/world.py:1057-1114 and 1734-1840): an input is played by three stretches of code that each open
the log's row, the line's fields, the fence, the dice and the budget, and each close them in their own way: a typed line (`turn`),
a pane button (inline in `run`), and the opening after a load. What is said at the end is decided in two places: the tail says
"Nothing comes of that here" (`said_nothing`) and `run` then prints the part line, which is how both were printed on 17 November.
The load's opening retold the last typed line as if it had happened.

**The change:** one driver, `play(input)`, with the same steps for all three kinds of input: open (log row, line fields, fence,
dice, budget), the body (a typed line's steps, a command, or the opening), its passages, the world's own operations, the tail, and
one close. The close is the only place that chooses the last line, and it chooses one: the turn failed, it stood in part, it was
silent, or nothing. The budget's close, the log's row and the header are written there once.

**Behaviour:** one fix, the closing line (a silent-turn line never beside a part line). The opening's retelling is looked at here:
fixed if the cause is the driver's, else given a feature of its own.

**Test:** turn_driver_721_test.py: a typed line, a pane button and an opening each leave the same things closed (no fence armed, no
budget open, one log row); a turn that stands in part shows the part line and no silent line; a failed pane button reads as a failed
line does.

**Goldens:** must not move (none of the three holds a part turn; checked first).

**Risk:** the highest of the six. `turn()` carries the order of twenty features (f463 to f498). It is moved, not rewritten: the
steps keep their order and their comments, and the goldens and the 500 tests say whether they still do.

## f722. One ordered page

**What is wrong today:** what a turn shows comes by two roads. An operation's notes are held and released when it commits; the
line's passage is written after all its steps. So "You find a level patch of ground and make camp there." was printed above the
passage that walks to the rise.

**The change:** everything an input shows (notes, told lines, passages, speech) goes onto one list with the step it belongs to,
and is released in one order: a step's passage, then that step's notes; what must come first (a question, a refusal with no
passage) says so when it is queued. The stand-in for a lost passage takes the passage's place in the order.

**Behaviour:** the order of lines in a turn. No new wording.

**Test:** page_order_722_test.py: a walk, a camp and a sleep in one line read in that order; a refusal still comes before anything
it stops; a question is last.

**Goldens:** move where a note came before its passage. Each moved line is listed in the commit with the reason, by the rebless rule.

**Risk:** medium. It builds on f721's close.

## What follows these

- The travel line read as speech (17 November) goes into the corpus as a case, with no repair rule.
- Phase 4 begins with decide then speak and the smaller prompt (doc 09, B4 and B5) and the change to f410 (voice in every line; the
  engine decides for each reply whether a slip of grammar shows). The gate's numbers before and after are its proof.

## When the one reader is built (the owner's question of 17 November)

Building it after phase 4 breaks nothing. Phase 4's combat step changes how an improvised act in a fight is ruled, not how a line is
read; its speech work changes the briefs for speaking, not the reader's prompt. So a baseline taken now is still the right
comparison then.

What waiting costs:
- Lines go on being misread through phase 4. Each is kept as a case in the corpus, not patched.
- A fight keeps its own reader of one action.
- The audit's extra calls go on costing seconds on the path the player waits on.
- The handlers are opened twice (once for beats, once for typed slots), each a re-bless.

The baseline (docs/measure/2026-11-17_reading_baseline.md): 216 of 252 right with the real model reading, 86%, against 252 of 252
offline. That is on the lines the repairs were written for, so new lines will do worse. 21 of the 36 wrong are one class: one line
read as two steps made from the same words.

Recommendation: build the contained half of the reader (ids chosen from the engine's list by the grammar, and each step naming the
words it covers; the contract, the grammar and the audit, no handler) after the five changes and before phase 4, behind its
switch, and measure it on the same 252. It aims at that one class, and every playtest of phase 4's speech work is otherwise
broken up by misread lines. The rest of the reader (typed slots, intercepts as offers, fights) waits until after phase 4. The
owner's to decide.

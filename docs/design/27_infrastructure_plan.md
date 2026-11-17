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

**The change (as built, 17 November):** two digests. `data` is the rules: every file as before, with a mark where each string
of wording stood. `words` is the wording alone. What counts as wording is declared in one new file, data/rules/wording.yaml: whole
files, or keys of a file. Anything not listed is rules, so a new file is on the strict side until someone says otherwise. A
recording keeps both. Replay warns on `data`, as before; when only `words` differs it replays, and the replay itself says whether
a state, a call or a shown word changed, and at which input. budget_data_459 and isolation_456 hold the rules digest.

**Narrower than first planned, after the goals review:** only a line's words are wording. Its place is a rule: the key it is
found by, how many lines its list holds (a line is drawn by the count, so one more line changes the draws), whether it is empty.
So a reworded line moves `words` alone and no recording is made again; a new line or a new kind of line still moves `data`.
Of the last twenty re-blesses this would have spared the rewording passes (f711/f712), not the features that added lines.

**The list:** rules/told.yaml, rules/failures.yaml, rules/launch.yaml (every string); rules/stay.yaml `lines`;
rules/questions.yaml `dropped`; rules/voice.yaml `frame_stand_in`, `no_words`; rules/moments.yaml `shapes.*.ends`;
rules/body.yaml `fall.died`, `kinds.*.past`, `kinds.*.nearly`. Left as rules: words the engine reads a line by, words a
memory keeps, the prompts' own text, and the story content of data/world (its files mix lines with ids; it can be listed by key
later).

**Test:** tools/sim/datahash_split_718_test.py.

**Goldens:** re-blessed once, for the new meaning of `data` and the new `words` field; no input, state, call or shown word differed.

## f719. The live gate

**What is wrong today:** every measure the suite runs is against the stand-in model. The four things a person meets first are
measured only by a person playing: whether lines are read right, what the narrator invents, how speech reads, how long a turn takes.
The corpus's live pass rate had never been recorded before 17 November.

**The change (as built, 17 November):** one command, `python tools/live_gate.py`, on the real model and this card:
1. **Reading:** the corpus through tools/interp_eval.py on the real model: the share right, and each kind's.
2. **A played script:** typed lines (data/replay/gate_script.yaml: forty, a draft until the owner has read them) played through
   the real turn from one fixed save and seed. tools/nightrun.py plays it (`--script`), with the script as its player, so the
   gate reads the same turn rows and transcript a night run leaves. From them:
   - **inventions:** of the passages checked for a creature not there (f701), those sent back, per hundred; and, roughly,
     capitalised words inside a sentence that are no name of the run's or of the game's data, per hundred passages shown (a
     count to watch move, not a verdict);
   - **stiff speech:** of the spoken replies checked (f714 checks while the turn has room for another try), the share sent back;
   - **time:** the median and the 95th percentile of seconds by the turn's shape (the script's word for each line; "fight" for
     any line played inside one), the lines over the limit, the stand-ins shown, the lines the model failed.
   The two send-backs had been flags inside one call and counted nowhere: llm/gateway.py now keeps four counts (`CHECKED`:
   passages checked, of them sent back for a creature; spoken replies checked, of them sent back as stiff), each counted when
   it happens, so a call that fails after its send-back is still counted.
3. **Held against kept numbers:** data/replay/gate.yaml holds the floors (the owner's numbers; none is set yet). A whole run
   on the real model, played to the script's last line, writes data/measured/live_gate.yaml and a dated report under
   docs/measure/, and leaves 1 under a set floor (a set floor with nothing measured under it counts as missed). A floor not
   set is reported and held to nothing. A script that ended early (the server died, the model failed twelve lines running)
   is no measure: nothing is kept and the gate leaves 2.
4. `--quick`: sixty cases drawn evenly by kind and the script's first fifteen lines, for before a playtest; it writes only to
   its own folder. `--stub` is the test suite's.

**Changed from the plan:** the floors are in data/replay/gate.yaml, beside the script, not in data/rules: they are what the
game is tested against, not the game, and a file in data/rules would have moved the data hash and every kept recording with it.

**For the owner:** the script's forty lines, to read before they are kept; the floors, once the first whole run is in; and a
line for CLAUDE.md, proposed: "Before a push that touches llm/, the prompts or the reading data: `python tools/live_gate.py`
(the whole gate, about forty minutes); before a playtest, `--quick`."

**Test:** tools/sim/live_gate_719_test.py, on the stand-in model.

**Goldens:** not moved.

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

**As built (17 November):** the table is `actor.ATTRS` (54 rows: 37 put back, 5 kept with a reason, 4 written only outside
operations, 3 read again from the save, 5 set once; a property of the scene, such as its name for the character's record,
holds nothing of its own and has no row); `HOMES`, `UNLISTED` and `WorldScene.ROLLED` are read from it. Changed from the plan:
- The run is not a golden replayed: a failed operation ends a golden's line, so the rest of the recording no longer applies. The
  test plays a session of the stand-in model's bot (forty typed lines, about 210 operations) and fails every third operation at
  its end. After each it compares everything the scene holds (every attribute, the turn's fields, the character's record, who
  is here, the fight, the rows told) with what the operation found; a name that differs fails unless it is declared kept or is
  the line's own record of the failure.
- turn_context_631_test changed in one check: it pinned `UNLISTED` to four names; it now holds that those four are among the
  names a failure leaves standing and that every such name has a reason.
- The census also reads names another module sets on a scene (`ws.x = ...`), which is how `assault` was found.

Found and fixed by declaring each "put back" (what a player would have seen):
- `first_arrival`, `revisit`: after a walk that failed, the chance of meeting something where the player still stood was worked
  out as for a place just reached for the first time, until the next walk.
- `visitors`: someone who came looking for the player inside an operation that failed stayed in the room as a visitor.
- `assault` (set by engine/events.py): a host reaching the gate inside an operation that failed left the next fight's end to
  decide whether that town held.
- `learn_request`: what was asked of an instructor stayed when the lessons offered for it went back.
- `repairs`, `camp_events` (the goals review): each is appended to inside an operation, so an operation run again for its answer
  appended twice. Nothing a player reads; the turn log and the sim's bot read them.
- The ledger's told marks: three callers untold the rows by hand when a passage failed; the world's own operations (the tail,
  the arrival, a pane command) did not, so a deed could be marked told by a passage nobody read. Now part of every rollback of
  one operation (engine/session.py), and the three hand calls are gone.

- Where the opening stands the player (the part of the place, set by the entry at the game's start) was in memory only until
  the first operation stood. A first operation that failed read the record back without it, and the player stood nowhere in
  the place until they next walked. scenes/world.py `run` now saves the record after the opening's entry. Found by the run's
  comparison of the character's record, which the first version of the test did not make (the goals review asked for it).

Seen by the run and left: two things are filled in on the character's record by whoever reads them, in memory and outside any
operation, as a merchant's stock is laid out: the loadout (engine/loadout.py `prepared`) and the pronoun worked out from the
character's own words (engine/truth.py `player_pronoun`). A failed operation's reload undoes that and the next read does it
again, to the same result. Nothing shows; the test leaves those four fields out of its comparison and says so.

Not fixed here, for the owner: `assault` is not in the save, so a game closed during the fight at the gate and opened again
decides nothing about the town when the fight ends. `camp_events` (read by the sim's bot alone) has no cap.

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

### As built (17 November)

Four things in scenes/world.py, each the only one of its kind (the test reads the code and fails on a second):

- `input(text, kind)` opens and closes an input: the line's fields and the write fence (`begin_line`), no question read inside it,
  and for a typed input its count, its dice and its budget. It is the only caller of `begin_line`, `new_input` and the budget's
  close. Three kinds: a typed line, a pane's command, and what the world owes the save as the game opens (`open_world`). When a
  typed input has run to its end, it says the input's one closing line.
- `closing_line(text)` chooses that line by how the input stood (a new field of the turn, `stood`, set where the outcome is
  settled): not taken, stood in part, showed nothing, or none.
- `play(text)` is the loop's one path: the log's row opened, the input played (`turn` for a line, `command_input` for a command),
  then `close_input`. The loop in `run` is now the prompt, the quit words and `play`.
- `close_input(...)` writes the log's row and redraws the header.

`turn` was moved, not rewritten: its body is the same lines in the same order, four columns to the left, under `with
self.input(text, "line")`.

**The fix.** The tail no longer prints "Nothing comes of that here": it marks the line `silent` (a new field of the turn, put back
by a failed operation), and the close says it only when the line has no other closing line. A turn that stood in part shows the
part line alone, whatever fails after the tail.

**The closing line is said where the input closes, not in the loop** (the goals review). The suite and the acceptance tool play a
turn without the loop (64 tests call `turn`). Said in the loop, the silent line never reached them, and a scene's "this line must
not say Nothing comes of that" could not fail. Said by the input's close, whoever plays a turn reads the line the player reads:
those callers now also read the line for a turn not taken and for one that stood in part, which only the loop printed before.

**What moved on the page:** the silent line is now the last line of its input. It used to come from the tail, so it came before
the tail's quiet line of places first heard of and before anything a deed taken up after the line showed. The same lines, in a
different order, in that case alone; no recording holds it.

**Older tests changed, each for the reason it exists:** turn_fields_628 and turn_context_631 hold the list of a line's
fields (two more); tutorial_stages_461 counted four fences in the file and now holds that the one place and the arrival after a
command have one each and that a turn, a command and the opening go through that place; turn_record_416 called the tail's
check by hand and read the note there (it now reads the mark and the close's choice). channel_580 and turn_survives_449 played a
turn and then asked for the not-taken line by hand, as the loop did; they now read the one the turn says.

**Changed from the plan:** the floors are in data/replay/gate.yaml, beside the script, not in data/rules: they are what the
game is tested against, not the game, and a file in data/rules would have moved the data hash and every kept recording with it.

**For the owner:** the script's forty lines, to read before they are kept; the floors, once the first whole run is in; and a
line for CLAUDE.md, proposed: "Before a push that touches llm/, the prompts or the reading data: `python tools/live_gate.py`
(the whole gate, about forty minutes); before a playtest, `--quick`."

**Test:** tools/sim/live_gate_719_test.py, on the stand-in model.

**Goldens:** not moved.

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

**As built (17 November):** the table is `actor.ATTRS` (54 rows: 37 put back, 5 kept with a reason, 4 written only outside
operations, 3 read again from the save, 5 set once; a property of the scene, such as its name for the character's record,
holds nothing of its own and has no row); `HOMES`, `UNLISTED` and `WorldScene.ROLLED` are read from it. Changed from the plan:
- The run is not a golden replayed: a failed operation ends a golden's line, so the rest of the recording no longer applies. The
  test plays a session of the stand-in model's bot (forty typed lines, about 210 operations) and fails every third operation at
  its end. After each it compares everything the scene holds (every attribute, the turn's fields, the character's record, who
  is here, the fight, the rows told) with what the operation found; a name that differs fails unless it is declared kept or is
  the line's own record of the failure.
- turn_context_631_test changed in one check: it pinned `UNLISTED` to four names; it now holds that those four are among the
  names a failure leaves standing and that every such name has a reason.
- The census also reads names another module sets on a scene (`ws.x = ...`), which is how `assault` was found.

Found and fixed by declaring each "put back" (what a player would have seen):
- `first_arrival`, `revisit`: after a walk that failed, the chance of meeting something where the player still stood was worked
  out as for a place just reached for the first time, until the next walk.
- `visitors`: someone who came looking for the player inside an operation that failed stayed in the room as a visitor.
- `assault` (set by engine/events.py): a host reaching the gate inside an operation that failed left the next fight's end to
  decide whether that town held.
- `learn_request`: what was asked of an instructor stayed when the lessons offered for it went back.
- `repairs`, `camp_events` (the goals review): each is appended to inside an operation, so an operation run again for its answer
  appended twice. Nothing a player reads; the turn log and the sim's bot read them.
- The ledger's told marks: three callers untold the rows by hand when a passage failed; the world's own operations (the tail,
  the arrival, a pane command) did not, so a deed could be marked told by a passage nobody read. Now part of every rollback of
  one operation (engine/session.py), and the three hand calls are gone.

- Where the opening stands the player (the part of the place, set by the entry at the game's start) was in memory only until
  the first operation stood. A first operation that failed read the record back without it, and the player stood nowhere in
  the place until they next walked. scenes/world.py `run` now saves the record after the opening's entry. Found by the run's
  comparison of the character's record, which the first version of the test did not make (the goals review asked for it).

Seen by the run and left: two things are filled in on the character's record by whoever reads them, in memory and outside any
operation, as a merchant's stock is laid out: the loadout (engine/loadout.py `prepared`) and the pronoun worked out from the
character's own words (engine/truth.py `player_pronoun`). A failed operation's reload undoes that and the next read does it
again, to the same result. Nothing shows; the test leaves those four fields out of its comparison and says so.

Not fixed here, for the owner: `assault` is not in the save, so a game closed during the fight at the gate and opened again
decides nothing about the town when the fight ends. `camp_events` (read by the sim's bot alone) has no cap.

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

### As built (17 November)

Four things in scenes/world.py, each the only one of its kind (the test reads the code and fails on a second):

- `input(text, kind)` opens and closes an input: the line's fields and the write fence (`begin_line`), no question read inside it,
  and for a typed input its count, its dice and its budget. It is the only caller of `begin_line`, `new_input` and the budget's
  close. Three kinds: a typed line, a pane's command, and what the world owes the save as the game opens (`open_world`).
- `play(text)` is the loop's one path: the log's row opened, the input played (`turn` for a line, `command_input` for a command),
  and closed. The loop in `run` is now the prompt, the quit words and `play`.
- `closing_line(text, stood)` chooses the one line that closes an input: not taken, stood in part, showed nothing, or none.
- `close_input(...)` says that line, writes the log's row and redraws the header.

`turn` was moved, not rewritten: its body is the same lines in the same order, four columns to the left, under `with
self.input(text, "line")`.

**The fix.** The tail no longer prints "Nothing comes of that here": it marks the line `silent` (a new field of the turn, put back
by a failed operation), and the close says it only when the line has no other closing line. A turn that stood in part shows the
part line alone. A pane's command that fails now reads by the same choice as a failed line (it did before; it is now the same code).

**Changed from the plan:**

- The opening is opened by the same place but is **not counted as an input**: nothing was typed, so it has no count, no budget
  and no row, and its dice stay its caller's ("#start"). Making it a counted input would move every recording's dice and the
  row counts the night tools read. What the plan called "the opening after a load" as a third stretch of code was `open_world`
  doing its own `begin_line`, fence and `arm(False)`; those are gone from it.
- The rest of what `run` does before the loop (the entry, the opening passage, a saved fight, a question asked again) is not an
  input and is left where it is.
- `collecting` (a telling asked for now is a passage of its own) is cleared whenever an input closes. A line that ended early
  used to leave it set until the next line began; nothing read it in between.

**Seen and left:**

- A pane's command does not open and close the ledger's turn as a typed line does. Left as found: a recording holds a pane command.
- **The load's retelling of the last typed line** (the play journal of 16 November: "You move into the Cinder Mug" on opening the
  save) is not the driver's: the opening passes no typed line to the narrator. It needs a trace on a real save and a feature of
  its own.

**Goldens:** not moved.

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

### As built (17 November)

**The cause, read in the code.** A single action's passage already had a place on the page (f464): where it is asked for, a
marker is put among the lines its operation holds, and what the operation says after the marker waits behind the passage. The
one passage of a line of several actions had no place: its events were set aside (`pending`) and told after all the steps, while
each step's lines were shown as that step committed. So there was one road with a place and one without.

**The change:** the line's one passage is given a place by the same marker (scenes/world.py `owe_place`): where its first event
is set aside (`narrate`), and, for every later operation of the line while it is still to tell, before anything that operation
says (`hold`). What is said after that place waits (`waiting`, a field of the line, put back by a failed operation) and is shown
after the passage, in the order it was said:

- told by the line's passage operation, or early by a later step (a talk tells what came before it; a fight's opening does):
  the telling takes the place, then what earlier steps said after it, then what the telling step itself had said (`flush`);
- stood in for: the stand-in takes the place and what waited follows it;
- a step that told it and then did not stand shows nothing: its lines go with it and the wait is put back;
- a passage of its own asked for by a later step (the goddess's words) waits until the line's is told and is told straight
  after it (`run_passages`), before the notes time raised and the world's own lines (review Q36);
- what waits is still owed by its operation in the save until it is shown, so a game closed in between tells it at the next
  load (f467). A step whose wait was taken up by a telling that stood is told at that load by the telling, not by its rows
  as well (engine/operation.py keeps whose wait a telling took up; `recover_unshown` reads it).

**Found by the goals review and fixed here:** "several actions told in one passage" (`buffering`) was put back to on when the
first action of such a line did not stand, and nothing turned it off: the next input, if it was taken whole (an answer, a
fight's round) or was a pane's command, set its passage aside and never told it. It is now a field of the line, started fresh
by every input. Older than this feature, but this feature would have made it cost more (the lines after it would have waited
to the input's close).

**Changed from the plan:**

- **Within one action the order is left as the code says it** (a line said before the passage is asked for is read before it).
  The plan said "a step's passage, then that step's notes" for every step. Read in the code, the lines said before a passage
  are shown the moment the action stands, while the passage is still being written: moving them below it would make the player
  wait the length of the model's call before reading anything. So the rule built is "nothing is read above a passage that tells
  what came before it", which is the fault. For the owner: say if every note should sit below its passage even so.
- **No recording moved.** None of the three holds a line of several actions (checked), and a line of one action reads as it did.
- No new list type: the marker and the wait are the ones f464 made. ui/console.py is not touched.

**Behaviour:** in a line of several actions, a later step's lines are read after the passage. In a line that hands work in and
then speaks, what the hand-in said after its telling was asked for is read after that telling. The first lines of such a line
are no longer read while the passage is being written, since they now follow it.

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

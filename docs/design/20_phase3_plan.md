# 20. Phase 3: the groundwork, planned against the code as it stands

Written 2026-11-14 against `main` at 84fc7cd (f627, with the prose branch merged). Approved by the owner the same day ("Approve as
recommended"), with the recommendations of section 7 taken.

**Built so far:** f628 and f630. **Changed since approval:** f629 moved from section A to after f632 (the owner, 2026-11-14:
"Yes, move it"), because three of its logs are written where there is no scene to ask who acted (see f629 below).

This is not a new design. Two designs the owner has already taken stand behind it:

- docs/design/13_foundations_design.md (2026-11-10): the turn's context, the actor's context, the world's lists in tables, one
  migration and one re-record. Its feature numbers (f584 to f592) were used by other work, and its line references are from before
  phase 2.
- docs/design/17_multiplayer_survey_and_plan.md (2026-11-12): its milestone M0 is this phase, and it asks more of it than doc 13 did.

What this plan does: checks both against today's code (five read-only surveys on 2026-11-14, the claims below taken from them),
puts the two together in one build order with new numbers, and says what has changed and what is the owner's to decide.

**Pillar:** infrastructure, for checklist item 8 (multiplayer) and for phase 4, whose rewrites cut through the same turn code.
**What the player sees:** nothing, but for one decided change (a pane click no longer takes a dice step, section 5).
**The model:** no live model is needed. Every feature but one replays the three goldens exactly.

## 1. What is already built

| The design's step | Built as | State |
|---|---|---|
| The settled deed kept | f578 | on `main` |
| Pins the goldens do not hold | f579 | on `main`; needs widening before anything moves (f628) |
| The output channel under the console | f580 | on `main`; text only (doc 17 asks for the whole seam, f635) |
| The dice as an object | f581 | on `main`; f585 added a count of inputs begun to it |
| The world's state behind one seam | f589 | on `main`, as storage/worldrow.py `RowWorld` |
| One append path for effects and matters | f590 | on `main` |
| The start's deed numbered | f591 | on `main` |
| Objects as entities (doc 05 step 2) | f592 | on `main` |

The stale-save detector of f589 holds no known site today (its RECORDED list is empty), so there is nothing for the owner to rule
on there.

## 2. What has changed since the designs

Each of these changes what a feature below must do. None overturns the design.

1. **The file name is taken.** engine/context.py is the prompt's scene records, an unrelated module. The contexts go in a new
   module, engine/actor.py.
2. **The rolled-back names are 36, not 5.** `WorldScene.ROLLED` (scenes/world.py:1130) has grown with the fight, the camp, the
   lessons and phase 2. Twenty-two of them are never set in `__init__` and exist only once written; the rollback depends on
   "absent means remove".
3. **A line resets twelve fields, not nine.** `begin_line` (scenes/world.py:1148) also resets `line_from`, `line_log` and
   `line_losses`; the last is rolled back as well.
4. **Two caches are swept that the design did not know:** `_wrote_turn` and the prose work's `_exemplars`.
5. **The fight and the party hold a player of their own.** services/fight.py and services/party.py each keep `self.player`
   (61 uses). A view on the scene alone would leave those two pointing at an old record after a reload.
6. **The scene's player is rebound at five places and one in the arcs**, all moved: scenes/world.py:101, 655, 1385, 1503, 1777
   and scenes/arc_actions.py:791. `self.player` is read 1,096 times (scenes 1,031, services 61); the acting id 551 times.
7. **The five entries stand** (open_world, run, turn, handle, command), and the act path adds none. Tools reach in past them:
   tools/acceptance.py calls `turn`, tools/eventrun.py calls `run_pulse`. Tests call the entries about 284 times in 101 files,
   so the binding must sit inside the entries, where no caller changes.
8. **State nobody owns has grown.** engine/session.py's table owns 19 names. Outside it today: `turnlog.SHOWN` and `COUNTS`,
   `asked._LOCAL`, the dice's count of inputs begun (`streams.BEGUN`), the gateway's per-call place for a seed (`_SEEN`) and its
   tallies, two counters of mended answers (`names.REPAIRS` and `BY_TASK`, `hygiene.REPAIRS`), the crash and refusal lists, the
   audit's state, the background job list and the recent events. The design named three places that tie a turn to a thread;
   there are about a dozen thread-local and thread-id sites now, most of them the model layer's own.
9. **One more tool reads a moved name:** tools/live_check.py (`canon.EVENTS`).
10. **The world row is busier, the four lists are as designed.** Phase 2 added `parts`, `heart`, `changes` and a consequence
    to a thread, and `by` to a settled deed. Every field a table column was to be derived from still exists. The row's other
    keys (about 25: history, spawns, camps, assaults, the doors, the cooldowns) stay in the row, as the owner decided.
11. **Whole loads and saves are more than counted:** about 80 loads and 44 saves in engine and scenes. They do not change: save
    still means "the stored world is this dict" (the design's rule 3).
12. **The save is still version 16.** No migration has been added since, so the planned one is still v17.
13. **`long_campaign_test` is about people, not the world's lists.** The cap test the design leaned on has to be written.

## 3. The features, in build order

Fourteen features, f628 to f641. The design's five rules hold (one of everything while there is one actor; a pin before the
thing it pins moves; a save replaces the whole world; storage proven before it is switched on; old names removed, not aliased).
Each feature has its test first, replays the three goldens exactly unless it says otherwise, and passes the suite.

### A. No turn code (can start at once)

**f628: the pins, widened (tests only).**
- All 36 rolled-back names, the twelve line fields and the swept caches are read through `getattr` around a failed operation, an
  asked stand-down and a line whose second operation fails. A name never set stays absent after a rollback.
- tools/sim/scene_rollback_465_test.py reads `ws.__dict__` and would pass blind for a moved field: it reads through `getattr`.
- A pin of what every output function sends that is not text (the line asked for, the panes, the status block, the busy light,
  the fight's pane), taken through the window's bridge, before f635 moves them.
- A pin of each log's row shape, before f629 adds to it.

f629 (the operation and every log row name who acted) was planned here and is built after f632: see section B.

**f630: one helper for the acting character, and no literal `"player"` id.** Code that takes a character id but still reads the
scene's player for the place and the sheet (engine/act.py, engine/ruling.py, engine/targets.py) reads them through one helper by
id. The literal id (the journal's "lately", a memory's default subject, the quirks) becomes the character's id; a fight's side
named "player" is a side, not an id, and stays. A fence counts what is left and only falls. The saved id stays `player`.

### B. The turn code (while no other branch touches scenes/world.py)

**f631: the turn's context.** A `TurnContext` in engine/actor.py with a declared table of fields, each LINE (reset by
`begin_line`), ROLLED or KEPT. It takes the turn's own fields: the twelve line fields; `step`, `ran`, `interpret_calls`,
`buffering`, `line_done`, `line_losses`; and `pending`, `halted`, `last_failure`, `last_budget`. The operation's snapshot moves
onto it from the session. The scene keeps one descriptor per field, so no call site changes and `getattr(self, "ran", [])` means
what it did.
- What f628 found of today's behaviour, which the table has to say: a failed operation puts `pending` back to what it found by
  its own hand (it is not kept as set), writes `halted` and `last_failure` itself, and leaves `last_budget`, `broken`,
  `last_text`, `crash_after_commit` and `recovered_at_load` as they stand.
- **Every one of the 36 rolled-back names is declared** as the turn's, the actor's view or the scene's, in a table a test holds,
  whether or not it moves now. Only the turn's move. This is the list M1's split of the scene starts from.
- The four scene fields no list holds today (`broken`, `last_text`, `crash_after_commit`, `recovered_at_load`) are declared too.
- Proof: f628's pins unchanged. Each golden holds a call that fails every try, so the rollback over the moved fields is replayed.

**f632: the actor's context and the clock's view.** `ActorContext(player, dice, out, clock, turn)`. The scene's `player` becomes a
view over it, and so does the fight's and the party's, so the six rebinds cannot leave any of them stale. The clock is a view
with no state over the store's meta; its `advance` is the one writer in play (scenes/world.py:480, 488; engine/starts.py:67).
The actor is bound inside the five entries and `run_pulse`, and the one before is restored on the way out; with none bound, the
process's own dice and screen answer, as today.
- A count of `self.player` per directory (scenes 1,031, services 61) that only falls.
- Proof: two stub campaigns taken in turn on one thread each see their own actor; after each rebind the acting id is the new
  one; the clock follows a reload and an asked restore.

**f629: the operation and every log row name who acted** (moved here from section A). `Operation` gains `actor`, written by
its record, the presentation entry and the recorder's input row; the turn log, the call log, the refusals, the audit and the
crash log gain it too. The call log, the gateway's refusals and the crash log are written where there is no scene to ask, so
every one of them reads who acted from the actor f632 binds, the one source. A row without one reads as the save's one
character. No recording moves: the replay compares id, kind and rows, and both kept rows are outside the state digest. The
fields first appear in the goldens at f640. The lines of f628's log pin that say "no actor yet" are the ones this changes.

**f633: the turn's registers, one owner, and no state without a home.** The operation's, the ledger's, the budget's, the turn
log's and the asked call's module state go onto one `Registers` object the context points at (one for the process while there is
one actor). The three ways a thread owns a turn become one field. The old module names are removed, and every user changes in the
same commit, the tools the suite never runs among them (tools/rerun.py, nightrun.py, live_check.py).
- **The class fix:** every module-level name in the game's code that is written after import is declared in one table as the
  turn's, the actor's, the campaign's or the process's, with what resets it. A scan of the syntax tree fails the suite on one
  that is not declared. Those found unowned today (item 8 of section 2) are the first rows it adds; the next one someone
  writes cannot arrive unnoticed.
- The thread-local and thread-id sites are held in an allow-list of those that exist, each with its reason.
- Proof: the replay compares the ledger's outcomes, what was presented and the committed operations at every input.

**f634: the actor's caches.** The journal sink, the name map and the events of engine/canon.py, the cast's pronouns, the last
failure, the last question and the price discount move to an object on the actor, shared with the process's default while there
is one actor. The fence of f633 covers assignment, so `canon.IDS = {...}` cannot quietly make a dead name again.

**f635: the whole output seam under the channel (doc 17).** The line asked for, the scope, the status block, the busy light, the
panes, the home page, creation and the fight's pane become methods of the channel. The window's bridge supplies a channel and no
longer swaps eleven module attributes (ui/gui/bridge.py:269-290). Holding an operation's lines, the turn log's tap, the
recorder's wrap and the question fence wrap the channel, never the `console` module. Until this is done a second player's turn
would print to the first player's window.
- Proof: f628's pin of what the bridge is sent, unchanged; console_bytes_579 unchanged; a fence that nothing assigns to a
  `console` attribute.

**f636: a player's preferences on the actor.** `#dialogue`, `#numbers` and `#debug` flip flags on `config` today
(scenes/world.py:2693-2699). They move to the actor; `--debug` at start sets the first actor's.

### C. The storage (last, with no other change to data/ or the save pending)

**f637: the world's tables, built and proven, not yet used.** `TableWorld` in storage/worldtables.py beside `RowWorld`, over four
tables (threads, deeds, news, effects), each row's JSON kept exactly as today and the columns derived from it when written. The
row keeps every other key. A seeded world is played once over the row and once over the tables and compared after every step:
the loaded dict equal with its order, every other table's digest equal, outcomes and shown lines equal.
- New, since `long_campaign_test` does not cover it: after 1,000 days each table is within its cap, and rows written per save
  stay flat.
- Kept at the last v16 commit: the world script's end database and the three goldens' start databases, as fixtures the
  migration is tested on afterwards.

**f638: the players table, built and proven, not yet used.** One row for each character, holding today's player record; the
first keeps the id `player`. A port with load, save, exists and the raw text.

**f639: only a story input takes a dice step.** The owner's answer of 2026-11-12 (doc 17, question 17): a pane's command no
longer counts as an input for the dice (scenes/world.py:1121). This changes the dice that follow a pane click, so it is the one
feature here that changes play. It is committed with f640, because the owner asked that it ride in the one re-record and the
suite must pass at every commit.

**f640: the one migration (v17) and the one re-record.** The tables and the players table go live; `migrations.CURRENT` becomes
17. With it: the scene's raw compare of the player row asks the store (scenes/world.py:652-654); the old migrations v6 and v8
get frozen readers of the old row; the save list and the export read the new table.
- **Before anything is kept**, a new `tools/rerun.py --as-schema 16` replays each old recording under a v16 view of the new
  storage. The prediction is every input of all three (41, 15 and 27) with outcomes, operations, presented entries and shown
  words equal. A miss stops the feature.
- Then f639's change is replayed and read: which inputs part, and that each follows a pane click.
- Then one re-record, by the `rebless` process. Predicted to change: the data hash (the schema's number is in it), the start
  database, every input's state digest, f629's actor fields, and the dice after a pane click. Predicted not to change: any
  request, outcome or shown word that f639 does not account for.
- A save that fails the migration is refused in a clear line and offered a new game; the line is the owner's to word.

**f641: narrow reads read one table.** The readers f589 put on the seam (an effect at a place, the threads of a status, the deeds
since a minute, the news) become one indexed query each. Writes stay load, change, save. A count of whole-world loads per golden
input that only falls.

## 4. How it lands

| Pull request | Features | Why together |
|---|---|---|
| 1 | f628, f630 | No turn code; the pins everything after rests on |
| 2 | f631, f632, f629 | The two contexts, then the logs that read who acted from them; scenes/world.py and the session |
| 3 | f633, f634 | The module state; wide and mechanical, with the fence |
| 4 | f635, f636 | The screen |
| 5 | f637, f638 | Storage nothing reaches yet |
| 6 | f639, f640, f641 | The switch and the one re-record |

While pull requests 2 to 4 are open, no other branch should touch scenes/world.py, engine/session.py or ui/console.py. While 5
and 6 are open, nothing else should change data/ or the save, or the proof of f640 has to be run again. The rest of prose
section A (A4, A5) changes data/ and prompts, so it fits before pull request 5 or after 6, not between.

Where a build finds one of these features wrong in a way that changes its shape, the build stops and the owner is asked.

## 5. Risks

1. **A field drops out of the rollback without a sound.** The guard is f628's pins, written on today's code and unchanged through
   f631, and the table that declares all 36 names.
2. **A missing bind hides while there is one actor.** Everything shares the process's default, so code outside an entry works
   today and would reach the wrong player in M1. M1 must turn the default into an error for story output; f632 lists where it
   is reached.
3. **f633 and f635 touch many files and tools outside the suite.** A missed site is caught only by the fences, which must cover
   assignment as well as reads, and the tools named above are run by hand once each.
4. **The goldens are thin for the world's lists** (6 of 83 inputs). The proof of the storage move rests on the world script's
   fifteen coverage checks and the step by step comparison. Weakening those hollows it.
5. **Two unused implementations drift** if other work lands between f637 and f640. They are built close together.
6. **f639 clouds the proof of f640** if the two are read together. They are read apart: the storage move on the old recordings
   first, then the dice step.
7. **The actor's view is not split here.** Thirty of the 36 rolled-back names stay on the scene. That is M1's work; this phase
   only declares which is which.

## 6. Not in this plan

- **Doc 05 steps 3, 4, 5 and 7** (parts of settled places, one resolver, the narration read back, `seen_by`): see question 1.
- **The single saved rows keyed by character** (the talk, the open question, the notices): see question 2.
- The scene's split in three, a second actor, per-actor dice, a clock per place, row versions: M1 and M2.
- A night run. Nothing here needs the model; the first night after pull request 6 is where a slip in play would show.

## 7. Questions for the owner (answered 2026-11-14: "Approve as recommended")

Questions 1 and 2 are settled as recommended (GOALS.md holds them). Question 3 stays open until the owner has looked.

1. **Doc 05's steps 3, 4 and 7 are not groundwork.** The roadmap lists them in phase 3 under "no behaviour change", but parts of
   settled places and the one resolver change what a player can do, and doc 05's three questions (leave or a key for a private
   building's parts; people named in passing; when the read-back runs) are unanswered. Doc 17 has since put knowledge by
   character in M1. Recommended: take them out of phase 3. Steps 3 and 4 get a plan of their own after pull request 6, as
   single-player depth (pillar 1); step 7 goes with M1.
2. **The single rows keyed by character.** Doc 17 lists them in M0. The decision of 2026-11-10 says the one migration holds the
   players table and the four lists "and nothing else". Recommended: keep to that decision. M1 has a migration and a re-record
   of its own in any case (the dice key takes the character's id there), and the rows can be keyed then at no extra cost.
3. **data/runtime/server.yaml** is still unread: this session is refused that folder, as the earlier ones were. The plan treats
   it as untouched. Still the owner's to confirm that it holds nothing about saves, the turn, the dice or the screen.

Needed later, not now: the wording of the line a player reads when a save cannot be migrated (f640).

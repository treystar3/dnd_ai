# 33. The fix plan for the code audit

18 November 2026. Branch play/faults at 6473815 (f730). Asked for by the owner: "can you come up with a plan to fix all of
the issues you found and note down all of your findings".

**This is a plan. Nothing is built.** No code, data or recording changed, and nothing is committed. Each feature here is
proposed for approval and, once approved, is built by the project's own process: a numbered feature (fNNN, given in the
order they are built), its test written first in tools/sim, the checklist of GOALS.md, the full suite before a push.

## 1. In short

- **All 584 findings of the audit are placed.** 575 are fixed by one of **341 features**; each finding stands under exactly
  one feature. The other 9 get no action: they are the claims the audit's own check refuted (listed at the end).
- **Sizes:** 165 small (under about 50 lines in one or two modules), 161 medium (larger; the feature's entry is its plan),
  15 large (each needs a design document of its own before it is built: section 5).
- **22 phases**, in the order they can be built: first what stops the game, loses a save or the player's progress, or
  breaks the 60 second turn; then what must be right before the next release; then the instruments, the smaller fixes,
  the savings in what the model writes (each measured on the card before it is kept), and last the work that changes no
  behaviour (a long campaign kept flat, removals, data, the suite, the tools).
- **48 questions for the owner**, gathered in one list after the phases. Most features carry a recommended answer and can be
  built on it; the features that wait are named on each question.
- **Recordings:** about 45 features move a kept recording on purpose and about 50 may. Each says why. None is re-recorded to
  make a test pass; REMOVALS_2-2 (phase 1) makes each re-bless a small change in git instead of a new copy.
- **The card:** five phases (5, 13, 14, 15, 16) end in one session of the live model on the card each, where the changes to
  what the model writes are measured together before they are kept. Everything else is built and tested under the stub.
- **New lines:** about 30 features add a line the player reads. None is drafted here: the owner reads each phase's lines in
  one sitting before it is built (question 46).

## 2. Where every finding is noted down

| File | What it holds |
|---|---|
| [32_code_audit.md](32_code_audit.md) | The audit's report: what was found, ranked, and how it was checked. |
| [32_code_audit/register.md](32_code_audit/register.md) | All 584 findings, one row each, with the check's verdict. |
| `32_code_audit/findings_*.md` | Every finding whole: evidence, what a player meets, the proposed fix, the check. |
| [33_audit_fix_plan/coverage.md](33_audit_fix_plan/coverage.md) | All 584 findings again, each with the feature that fixes it, its phase and its workstream file. |
| `33_audit_fix_plan/<workstream>.md` | The 22 workstream plans: every feature in full. |
| `33_audit_fix_plan/order_reasoning.md` | The ordering's reasoning, phase by phase. |

The plans cite the scripts that showed each fault and checked each plan. A path beginning `audit/work/` is inside
`32_code_audit/repro_scripts.zip` (as `work/...`); one beginning `plan/work/` is inside `33_audit_fix_plan/plan_scripts.zip`.
Many of them are most of the way to the test a feature needs.

## 3. Before approving: where this sits beside the owner's order of 17 November

GOALS.md line 148 records the owner's answer to the approach review (doc 26): the review's five infrastructure changes
first, then phase 4's speech work, which "goes ahead of more fault rounds"; fix rounds for misread lines stop, and a misread
found in play becomes a case of the corpus, never a repair of its own; the one reader is built behind a switch and kept
only if the measure improves.

This plan pulls against that in two places, and so asks first (question 1 and question 3):

- **Order.** Phases 1 to 7 alone are about 120 features. They are not rounds of misread lines: they are a save that cannot
  be opened, a fight that pays a kill twice, a trial won by losing, a build that cannot start, a reply that cannot finish
  inside the minute. The recommendation (question 1, option a) is phases 1 to 7 before more phase 4 work, and the rest
  interleaved with phase 4 and plans 29 and 31, the savings phases sharing their card sessions. The other options are
  phase 4 and plan 29 first, this plan after; or phase by phase as each is approved.
- **Phase 10 (the typed line).** Its features narrow or replace the engine's own reading of the player's words; none adds a
  repair for a misread line, and every logged misread they found goes into the corpus. Whether that still counts as a fix
  round is the owner's to say (question 3).

Plans 29 and 31 and CONTRACTS-1 each claim f731 (question 2). Phase 22 says where each design here sits beside plan 29's
steps.

CLAUDE.md asks for a plan, approved, before anything touching more than two modules. The proposal is that approving a phase
approves its small and medium features as written in their workstream files, and that each large feature still has its own
design read first.

## 4. How the plan was made, and how far it was checked

The findings were sorted into 21 workstreams by where the fix would be built (dead code split in two, so 22 files). For each
workstream one planner read every finding whole and the code at each place, searched GOALS.md's decisions and the design
documents for what already covers it, and grouped the findings into features, one piece of infrastructure for each kind of
case where there is a kind. A second reader for each workstream then tried to find what was wrong with the plan: opened the
code again, checked the owner's rules and decisions, the test, the recordings and the size, and amended the file. The changes
each made, and the doubts it could not settle by reading, are at the end of each workstream file under "Review". A last
reader ordered every feature into phases, found where workstreams meet, and gathered the questions.

Checked by script, not by reading: every finding stands under exactly one feature or under no action; every feature is in
exactly one phase; no need a feature states is broken by the order. The usage limit stopped the run once, after the
planners; it was resumed from its own record and nothing was lost.

What is not checked: nothing was built or run against a changed tree, so a plan can still be wrong in the build. The
reviewers' open doubts are listed in each file with what would settle them. The minimum card's seconds are still estimates
from token counts, as in the audit.

## 5. The large features: a design first

| Feature | Phase | What its design must settle |
|---|---:|---|
| FIGHT_CORE-1 | 2 | One fall step on every damage path: its order on each path, where each kill is credited, the die for paths that have none. |
| BUDGET_FLOW-2 | 5 | The card profile as a fixed cost a request plus a rate, and a profile the game can always load. |
| TESTS-3 | 9 | Every model task failed in turn through a played session, and what each task's failure must leave. |
| GATE-7 | 13 | One reader for amounts and game words, reading what the request gave, its lists in data. |
| GATE-23 | 13 | A word in another script made impossible to write, only if the measure shows an English word takes its place. |
| CONTRACTS-17 | 14 | One step that shapes a call's schema from what the call holds (doc 29's R2 is built on it). |
| BUDGET_FLOW-10 | 16 | Every model call of play asked outside its operation's transaction, with a ratchet over what play reaches. |
| BUDGET_FLOW-20 | 16 | A place's first people written ahead when the engine knows it is next. |
| STARTUP_DATA-3 | 19 | A rules key no code reads stops the start, and no rule is read with a default that stands in for the data. |
| BUDGET_FLOW-13 | 22 | The interpreter's request ordered by what changes least, places listed by what the words are about (with plan 29 R2). |
| TYPED_LINE-12 | 22 | A handler is given its step and not the line; an intercept is an offer to the reader (after plan 29 R1 to R3). |
| FIGHT_CORE-8 | 22 | One test for who may leave where they stand (phase 4's can_take in narrow form). |
| FIGHT_SCENE-6 | 22 | A line typed in a fight that is no fight action, answered from the fight's facts (plan 29 R4). |
| STALE_COPIES-13 | 22 | One live record for each operation; only if the stale-save lists of STALE_COPIES-1 ask for it. |
| LONG_SAVE-17 | 22 | People long gone leave the save by how they left (with multiplayer M1). |

## 6. The workstreams

| File | What it fixes | Features | Findings | Small / medium / large |
|---|---|---:|---:|---|
| [contracts](33_audit_fix_plan/contracts.md) | What the model is asked to write | 17 | 33 | 4 / 12 / 1 |
| [gate](33_audit_fix_plan/gate.md) | Checks on what the model wrote | 24 | 47 | 11 / 11 / 2 |
| [budget_flow](33_audit_fix_plan/budget_flow.md) | When and how the model is called | 27 | 52 | 9 / 14 / 4 |
| [typed_line](33_audit_fix_plan/typed_line.md) | The typed line read by patterns | 12 | 23 | 3 / 8 / 1 |
| [reload](33_audit_fix_plan/reload.md) | What a close and reopen loses | 13 | 18 | 6 / 7 / 0 |
| [stale_copies](33_audit_fix_plan/stale_copies.md) | Two copies of one record | 13 | 16 | 5 / 7 / 1 |
| [fight_core](33_audit_fix_plan/fight_core.md) | The rules of a fight | 9 | 18 | 2 / 5 / 2 |
| [fight_abilities](33_audit_fix_plan/fight_abilities.md) | Abilities, spells, perks and summons in a fight | 14 | 17 | 9 / 5 / 0 |
| [fight_scene](33_audit_fix_plan/fight_scene.md) | The fight as the scene and the player meet it | 6 | 6 | 2 / 3 / 1 |
| [situations](33_audit_fix_plan/situations.md) | Situations, acts, events, arcs and jobs | 17 | 22 | 13 / 4 / 0 |
| [task_failure](33_audit_fix_plan/task_failure.md) | When a model task fails or a fault is swallowed | 17 | 26 | 8 / 9 / 0 |
| [long_save](33_audit_fix_plan/long_save.md) | What grows or slows over a long campaign | 18 | 29 | 12 / 5 / 1 |
| [startup_data](33_audit_fix_plan/startup_data.md) | The startup check and the data files | 16 | 31 | 6 / 9 / 1 |
| [shipping](33_audit_fix_plan/shipping.md) | The game as the player installs and runs it | 17 | 31 | 5 / 12 / 0 |
| [suite](33_audit_fix_plan/suite.md) | The test runner and the hooks | 14 | 29 | 10 / 4 / 0 |
| [tests](33_audit_fix_plan/tests.md) | Tests and recordings that cannot catch what they are for | 13 | 18 | 2 / 10 / 1 |
| [tools_bots](33_audit_fix_plan/tools_bots.md) | Tools that play or measure | 23 | 39 | 10 / 13 / 0 |
| [people_talk](33_audit_fix_plan/people_talk.md) | People and talk outside a fight | 16 | 16 | 11 / 5 / 0 |
| [town_services](33_audit_fix_plan/town_services.md) | What a character does in a town | 9 | 10 | 6 / 3 / 0 |
| [travel_places](33_audit_fix_plan/travel_places.md) | Travel and places | 10 | 11 | 7 / 3 / 0 |
| [removals_1](33_audit_fix_plan/removals_1.md), [removals_2](33_audit_fix_plan/removals_2.md) | Dead code and unneeded files | 36 | 83 | 24 / 12 / 0 |
| **All** | | **341** | **575** | **165 / 161 / 15** |

Each feature in a workstream file has the same parts: what it fixes (finding ids), the pillar, the kind of case it covers,
what is built and where, the test written first and its second case, whether a recording or the data hash moves, the
measure, the size, what must come first, which other workstreams it meets, and what the owner decides.

## Phase 1 as built

19 November 2026, branch play/faults, f731 to f747 (`git log 6473815..d581cc7`). The owner approved phase 1 with "Start
phase 1", which took the plan's recommended answer on each question the phase waited on. **All 18 features landed; no key
was left out.** REMOVALS_1-17 and REMOVALS_2-4 were built as one change (f744), as the plan said. Each was checked by the full
suite on this branch when it landed.

| Feature | The commit that built it | The owner's answer it was built on |
|---|---|---|
| TESTS-1 | b3d4d5e f731: a replay parts when the game stops short of its recording (infrastructure; checklist 4, 7) | none asked |
| REMOVALS_2-2 | 44c5bb7 f732: a kept recording's call log is plain text behind one reader, so a re-bless adds a delta to git and not a new blob (infrastructure; checklist 5, 7); follow-up 88c3412 (below) | Question 42 (a): the kept recordings' call logs are plain text behind one reader |
| RELOAD-2 | d0bfda5 f733: a save opened again with nothing typed opens, the campaign's own places back on its map (pillar 7, 1) | none asked |
| TRAVEL_PLACES-1 | 0b51e65 f734: a road stop's ways and its record name only places on the map, so every walk from a stop goes on (pillars 1, 7) | none asked |
| TRAVEL_PLACES-4 | 4c17f4a f735: the towns a character has stood in hold only places that count as settled, so Word of Recall finds the town behind (pillars 1, 6) | none asked |
| TRAVEL_PLACES-3 | a6cfacb f736: a stop is left one way whatever ends the stay, and no character stands or wakes at a place off the map (pillars 1, 7); follow-up 140063c (below) | Question 23 (a): a night slept at a road stop is no last rest; the rest note names where they would wake |
| SITUATIONS-3 | 2621ca6 f737: the plain arc story names its people from the name builder, so taking an arc never fails for want of a name (infrastructure; pillar 7) | none asked |
| LONG_SAVE-2 | 390e3bc f738: a refused answer lets its line go, so a long sitting no longer grows in memory (infrastructure, pillar 7; checklist 4, 5) | none asked |
| TOWN_SERVICES-1 | dc30c5c f739: a trial of rank begins only for a member the register says has earned it, and a question about rank is answered (pillars 6, 2) | none asked |
| TOWN_SERVICES-2 | 0b618aa f740: an enchantment spends one of its reagent, and a stacked thing leaves the pack only through a writer that counts (pillars 1, 6) | none asked |
| RELOAD-5 | 40b5f8c f741: a game's folder says it is the player's game, so a deleted game moved back is listed again and a lost index hides nothing (pillar 7); follow-up 5f9a232 (below) | Question 19 (a): any folder carrying the game's mark is listed, one copied in from another install included |
| RELOAD-13 | d6fa085 f742: a game left during creation leaves no dead row, and discard never erases a game that has a character (pillar 7) | Question 19 (a), through RELOAD-5's mark: discard never touches a marked folder |
| TOOLS_BOTS-1 | 53d2f50 f743: a tool clears only a save it made itself, and says so when the clearing did not happen (pillar 7) | Question 19 (c): a folder with no mark is refused when its name was typed on a tool's command line, and adopted when a tool or test names it in its own code |
| REMOVALS_1-17, REMOVALS_2-4 | fce33ac f744: a save folder from before the database is refused and left as it was, never marked current and then read (pillar 7, infrastructure) | Question 20 (a): the import of the old one-file-per-record layout is retired; such a folder is refused and left as it was |
| TASK_FAILURE-4 | 6fc5f56 f745: no call on the way to a new game's first input can stop it; the starting companion has an engine answer (pillars 7, 2) | Question 29: a starting companion the engine had to choose is called by its kind |
| LONG_SAVE-3 | 86e6740 f746: a captive is named for their people by the name builder, apart from every name in the save, so captive names never run out (pillar 4) | none asked |
| TASK_FAILURE-15 | d581cc7 f747: an old save whose player's record does not read is refused at the step that reads it, never stepped past (pillar 7, infrastructure) | none asked |

**Three follow-ups**, found by the phase's review across its commits. Each reuses the number of the feature it completes:

- 88c3412 f732: a re-bless writes anew only what really moved, so an unchanged recording keeps its call log and start save as
  they were (infrastructure; checklist 5, 7). The clock's values (a call row's seconds, the start save's creation time) made
  every re-bless rewrite about half the log and the whole start save, which undid f732's aim.
- 140063c f736: a character standing off the map is stood wherever a scene is built and written inside the opening, for every
  saved character (pillar 7; checklist 8). f736's guard ran outside any operation, missed scenes built without run(), and
  moved only the scene's one player.
- 5f9a232 f741: no test reaches the player's games, index or records through the saves folder's default; one source names
  the folder and one predicate says whose a folder is (pillar 7, infrastructure). A follow-up to f741, f742, f743 and f744:
  every test ran in the owner's own saves folder, which f741's marks made writable by reading the Load page.

Notes. None of the owner's answers above is yet a row of GOALS.md's decisions table: GOALS.md holds the owner's own
uncommitted edit, so it was left alone. f744 reverses what docs/design/20_phase3_plan.md (lines 370 and 459) planned for the
old layout. SITUATIONS-3 was built before LONG_SAVE-3, so the captives kept arcs.yaml's sixteen names until f746 took the list
and its startup check out.

## Phases 2 and 3 as built

19 November 2026, branch play/faults, f748 to f767 (`git log 711d2cd..05f6313`), on the owner's "continue on to phase 2 and
3". Phase 2's seven features that do not wait on FIGHT_CORE-1's design and all thirteen of phase 3 landed, in the order they
were ready; RELOAD-10 and BUDGET_FLOW-9 were built as one change (f753), as the plan said. Each was checked by the full suite
when it landed. Every suite from f748 to f767 failed the same two tests, rename_meravia_test and rename_lethoria_test, on the
old world and capital names quoted in this audit's documents; the docs commit after f767 rewords those quotes.

| Feature | Phase | The commit that built it | The owner's answer it was built on |
|---|---|---|---|
| FIGHT_CORE-9 | 2 | 9bae0e7 f748: the fight's rules gain no new read of the first player fighter: combat.player is counted per engine file and only falls (infrastructure; checklist 8) | none asked |
| FIGHT_ABILITIES-3 | 2 | 87ff83c f749: a Bound summon made anew in a fight walks into the next one (pillars 6, 1) | none asked; the trial's case waits on FIGHT_CORE-4 |
| FIGHT_SCENE-4 | 2 | 52e0f77 f750: the passage after a fight is told only of the player's own who died in that fight (pillars 1, 4) | none asked |
| RELOAD-1 | 3 | 6313947 f751: an opening by declaration: every name the scene holds says what an opening does with it, and a session closed and opened part-way is held to the same session played straight (infrastructure; checklist 4, 7, 8) | the plan's default for each name neither saved nor rebuilt: what a check, a prompt or the next line's routing reads is kept; what only spaces out chatter inside one sitting is declared forgotten, each with its reason (the list is in f751's commit) |
| FIGHT_SCENE-1 | 3 | 07d40d5 f752: a fighter is rebuilt from the character by one step that keeps what the fight took, so a point spent in a fight leaves an ooze's wear on the armour (pillar 6, infrastructure) | none asked |
| RELOAD-10, BUDGET_FLOW-9 | 3 | 24b65fb f753: an input keeps its count when an operation fails before the line's first commit, and the count reaches the save with whichever operation stands first (infrastructure; checklist 4, 7) | none asked |
| RELOAD-7 | 3 | c9fe910 f754: a place made in play sits in the same spot on the map, with the same direction word, in every session (pillars 1, 7) | none asked |
| LONG_SAVE-18 | 3 | 10bcc63 f755: a stop left takes only its own people: a captive walked through it goes on, and a companion is never let go there (pillars 1, 7) | none asked |
| FIGHT_ABILITIES-12 | 2 | 8acb095 f756: each summon casting has its own serial, whoever has left the fight since (pillar 6) | none asked |
| FIGHT_CORE-5 | 2 | 87f3112 f757: the line of a blow comes before what the blow set off, in the story and in the fight's log (pillars 5, 1) | none asked; one live gate run on the card is owed before it is kept |
| RELOAD-9 | 3 | 3806a35 f758: what waits on the next line after a fight is in the save: a yielded foe's question and the walk to take up after a road fight survive a close (pillars 2, 1) | none asked |
| RELOAD-4 | 3 | 2b3f36d f759: a talk in progress, the companion who spoke last and someone who came looking are all there when the save is opened again (pillar 4) | none asked |
| FIGHT_SCENE-2 | 3 | c04835b f760: the fight's row is written with every operation's commit, so a point spent in a fight stays spent through the next line and a reopen (infrastructure, pillar 6) | none asked |
| RELOAD-6 | 3 | c896dc4 f761: what the checks and prompts remember of the telling is kept in one capped row of the save, so a close no longer lets worn words and a town's stock phrases through again (pillars 5, 3) | (a) what the checks and prompts remember of the telling is kept across a close, as planned. |
| REMOVALS_2-12 | 3 | 4b92ced f762: a commit saves the campaign's meta once, with its player, and the comments say so (infrastructure; checklist 4, 7) | none asked |
| FIGHT_ABILITIES-1 | 2 | d259e35 f763: an ability lands only on a fighter still in the fight, and no blow fells anyone twice (pillars 1, 6) | none asked |
| RELOAD-8 | 3 | 15859f9 f764: opening a save puts the scene back and rolls nothing, since an opening is not an arrival (infrastructure, pillar 1) | (a) a period's moment is rolled on arriving only, as data/rules/moments.yaml says. |
| RELOAD-3 | 3 | 337680a f765: what a fight is for is saved with the fight, so a fight resumed after a close or a crash ends with its consequences (pillars 1, 6) | none asked |
| FIGHT_CORE-6 | 2 | 4f3661e f766: a fighter leaves a fight one way, released first, and a runner cut down is told fallen, never fled (pillars 1, 6) | none asked |
| FIGHT_ABILITIES-6 | 3 | 05f6313 f767: a two-turn ability lands with what was settled when it was begun: its bonuses, its recipient and its repeats (pillar 6) | none asked |

Left for later in phase 2: FIGHT_CORE-1 (a design first: docs/design/34_one_fall_step.md, with its questions for the owner),
and the six that wait on it: FIGHT_CORE-2, FIGHT_CORE-3, FIGHT_CORE-4, FIGHT_ABILITIES-2, FIGHT_ABILITIES-4 and
FIGHT_ABILITIES-5.

Owed on the card, none run yet: one live gate run for f757 (tools/live_gate.py: the order of what the fight's narrator is
handed changed), to be shared with FIGHT_CORE-1 and FIGHT_ABILITIES-5; tools/acceptance.py --live for f751, whose reopen now
runs the whole opening; and, offered by f761, a live gate run with the save closed and opened part-way.

Found by the review across these commits and left for a later change:
- Three rows are each written at the commit by a call placed by hand in WorldScene.operation (f759 the visitors, f760 the
  fight, f761 the telling, beside the older talk row); nothing ties a name engine/actor.py declares kept to its writer.
- f736 and f765 each run an extra world:open operation from the opening, written twice.
- The `target.alive else enemies[0]` fallbacks f763 left for FIGHT_ABILITIES-6 (engine/spellcraft.py targets and control,
  engine/martial.py control) are still there after f767.
- f764 restores a character f736 has just moved off a vanished place as if they had stood there at the close; no test covers
  the two together.
- f749 updates every character's Bound summon bond and saves only the first player.
- Tests still name the real saves folder by a literal path (turn logs, crash logs and `rmtree("saves/<name>")` of their own
  folders); f741's fence only stops new ones.
- stub_fight was re-blessed four times in the run (f746, f757, f759, f760) and stub_short three, where note 9 asks for one
  re-bless a phase; each reason was checked against the later commits and none is undone.
- f759 makes GOALS.md's f711 row ("Keeping a summoned person in the save waits for a later fix") out of date.

## The phases

Each phase opens with why it is there. The ordering's criteria, in this order: (a) what stops the game, loses a save or the
player's progress, or breaks the 60 second turn on the minimum card; (b) what must be right before the next released build;
(c) a small instrument ahead of the fixes it would find; (d) small certain fixes; (e) savings in what the model writes and
reads, batched so that one session on the card measures several; (f) work with no change in behaviour; (g) designs that need
a document first. "Heavy row N" is row N of the audit's table of heavy bugs (32_code_audit.md, section 3.1).

A row is one feature. `Size`: S is under about 50 lines in one or two modules; M is larger and its entry in the workstream file is its plan; L needs a design document of its own first. `Weight` is the heaviest finding it fixes. `Golden` says whether a kept recording is expected to move (never re-recorded to pass). `Measure`: `card` needs the model on the card before it is kept, `measure` is measured without it. `Owner`: a question waits on the owner (section after the phases).

### Phase 1. Stops the game or loses a save

Criterion (a): heavy rows 5 and 6 and the audit's seven small certain bugs (rank question, reagent stack, Word of Recall, pinned memory), a road stop that strands a player, saves that will not open, a tool or the Load list losing a game, a failed call stopping a new game. TESTS-1 leads so every 'goldens do not move' is true; REMOVALS_2-2 leads so this phase's re-blesses and all later ones cost a delta (skipped if the owner answers c). Stub only.

18 features (12 S, 6 M), fixing 23 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TESTS-1 | A replay parts when the game stops short of its recording | S | medium | 1 | no |  |  |
| REMOVALS_2-2 | A kept recording's call log is plain text behind one reader, so a re-bless adds a delta to git and not a new blob | M | small | 1 | yes |  | yes |
| RELOAD-2 | The campaign's own places are back on the map at every open, so a save opened twice with nothing typed opens | S | heavy | 1 | no |  |  |
| SITUATIONS-3 | The plain arc story names its people from the name builder, apart from every name in the save, so taking an arc never fails for want of a name | S | heavy | 2 | no |  |  |
| LONG_SAVE-3 | A captive is named for their people, apart from every name in the save, from a source that cannot run dry | M | small | 2 | yes |  |  |
| TRAVEL_PLACES-1 | A road stop's ways and its record name only places on the map, so every walk from a stop goes on | M | medium | 2 | no |  |  |
| TRAVEL_PLACES-4 | The towns a character has stood in hold only places that count as settled, so Word of Recall finds the town behind | S | medium | 1 | yes |  |  |
| TRAVEL_PLACES-3 | A stop is left one way whatever ends the stay, and a character is never left standing, or due to wake, at a place off the map | M | medium | 1 | no |  | yes |
| LONG_SAVE-2 | A refused answer no longer pins its turn's stack in memory | S | medium | 1 | no |  |  |
| TOWN_SERVICES-1 | A trial of rank begins only for a member the register says has earned it, and a question about rank is answered | S | heavy | 1 | no |  |  |
| TOWN_SERVICES-2 | An enchantment spends one of its reagent, and a thing that stacks leaves the pack only through a writer that counts | S | heavy | 1 | no |  |  |
| RELOAD-5 | A game's folder says it is the player's game, so a deleted game moved back is listed again and an unreadable index hides nothing | M | medium | 1 | no |  | yes |
| RELOAD-13 | A game left during creation leaves no dead row, and discard never erases a game that has a character | S | small | 2 | no |  |  |
| TOOLS_BOTS-1 | A tool clears only a save it made itself, and says so when the clearing did not happen | M | medium | 2 | no |  | yes |
| REMOVALS_1-17 | A save from before the database is no longer imported by a path that skips every migration step | S | small | 1 | no |  | yes |
| REMOVALS_2-4 | A folder in the old file layout is never marked current and then read: the import is retired with a plain refusal, or it comes in through the migrations (one change with REMOVALS_1-17) | S | small | 1 | no |  | yes |
| TASK_FAILURE-4 | The starting companion has an engine answer, and no call on the opening path can stop the game | S | medium | 1 | no |  | yes |
| TASK_FAILURE-15 | An old save whose player row cannot be read is refused, not stepped past | S | small | 1 | no |  |  |

### Phase 2. The fight: a fighter out of the fight acts no more, and a death happens once

Criterion (a): heavy rows 3 and 4 (a fled or dead foe still strikes and pays kills; a rank won by a summon losing), a fight won without a blow, a summon lost. The fence first so new code is counted; FIGHT_CORE-5 then -1 so stub_fight is re-read once; one live gate run for FC-1, FC-5, FA-5.

14 features (7 S, 6 M, 1 L), fixing 22 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| FIGHT_CORE-9 | The fight's rules gain no new uses of "the first player" before multiplayer rewrites them | S | small | 1 | no |  |  |
| FIGHT_CORE-5 | The line of a blow comes before what the blow set off | M | medium | 1 | yes | card |  |
| FIGHT_CORE-1 | A death happens once, whatever killed: one fall step on every damage path releases, tells and credits it | L | medium | 3 | yes | card | yes |
| FIGHT_CORE-2 | One turn a fighter a round, and none for a fighter who is out of the fight | S | heavy | 3 | maybe |  |  |
| FIGHT_ABILITIES-1 | An ability lands only on a fighter still in the fight, and no blow fells anyone twice | S | medium | 1 | no |  |  |
| FIGHT_CORE-6 | A fighter leaves a fight one way: released first, and never told as gone when it fell | M | medium | 4 | maybe |  |  |
| FIGHT_CORE-3 | A floor that holds a killing harm holds the whole blow, and the floors are declared once for every damage path | M | medium | 1 | maybe |  | yes |
| FIGHT_CORE-4 | A trial of rank is decided only by its duellists, and one rule says who may stand in it | M | heavy | 1 | no |  | yes |
| FIGHT_ABILITIES-4 | A kill outright goes down a declared path: the floors hold, and the death sets off what a death sets off | S | medium | 1 | no |  | yes |
| FIGHT_ABILITIES-5 | Who breaks at a death is settled when the action that caused it has finished | M | medium | 1 | yes | card |  |
| FIGHT_ABILITIES-2 | A turned foe is on the player's side to every rule of harm, and turning a foe never wins a fight by itself | M | medium | 2 | no |  | yes |
| FIGHT_ABILITIES-3 | A Bound summon made anew in a fight walks into the next one | S | medium | 1 | no |  |  |
| FIGHT_ABILITIES-12 | Each summon casting has its own serial, whoever has left the fight since | S | small | 1 | no |  |  |
| FIGHT_SCENE-4 | The passage after a fight is told only of the player's own who died in that fight | S | medium | 1 | no |  |  |

### Phase 3. Close and reopen: what a save keeps

Criterion (a) with its instrument first (c): RELOAD-1's close-and-reopen test is what would have caught heavy row 7; then a fight's purpose after a reload, the attribute point spent in a fight, the talk in progress, the yield question, the input's count, the telling's memory, an escorted captive lost at a stop.

14 features (6 S, 8 M), fixing 17 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| RELOAD-1 | Every name the scene holds says what an opening does with it, and a session closed and opened part-way is held equal to the same session played straight | M | medium | 1 | no |  | yes |
| RELOAD-3 | What a fight is for is saved with the fight, so a fight resumed after a close or a crash ends with its consequences | M | heavy | 4 | no |  |  |
| FIGHT_SCENE-1 | A fighter is rebuilt from the character by one step that keeps what the fight took (an ooze's wear stays through an attribute click) | M | small | 1 | no |  |  |
| FIGHT_SCENE-2 | The fight's row is written with every operation's commit: the fight in memory equals its row when an operation ends | S | medium | 1 | yes |  |  |
| RELOAD-4 | A talk in progress, the companion who spoke last and someone who came looking are all there when the save is opened again | M | medium | 2 | yes |  |  |
| RELOAD-9 | What waits on the next line after a fight is in the save: the yielded foe's question and the road walk to resume | M | small | 1 | maybe |  |  |
| RELOAD-8 | Opening a save puts the scene back and rolls nothing: an opening is not an arrival | M | small | 1 | maybe |  | yes |
| RELOAD-10 | An input's count reaches the save with the first operation of the line that stands, whichever it is | S | small | 1 | no |  |  |
| BUDGET_FLOW-9 | An input keeps its count when an operation fails before the line's first commit | S | small | 1 | no |  |  |
| REMOVALS_2-12 | A commit saves the campaign's meta once, and the comments say what the code does | S | small | 1 | no |  |  |
| RELOAD-6 | What the checks and prompts remember of the telling is kept in one capped row of the save | M | medium | 1 | no | card | yes |
| RELOAD-7 | A place made in play sits in the same spot on the map, with the same direction word, in every session | S | medium | 1 | maybe |  |  |
| FIGHT_ABILITIES-6 | What is settled when a two-turn ability is begun reaches the turn it lands | M | medium | 1 | no |  |  |
| LONG_SAVE-18 | A stop that leaves the map takes only its own people: whoever is there with a character goes on, and a companion is never let go at a stop | S | small | 0 | no |  |  |

### Phase 4. Progress lost outside a fight: second copies, situations, coin

Criterion (a): the stale-copy check first so each fix takes its site off a list; heavy row 8 (a situation won by its own way ends lost); coin paid for an errand or a rank never given; jobs, thanks, commissions and trust moves lost; dungeon postings naming what is gone (TS-7 and TP-8 as one build).

17 features (10 S, 7 M), fixing 21 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| STALE_COPIES-1 | The suite and the night runs name every save over a newer write, every change nobody saved and every record held apart, for every record kind | M | medium | 1 | no |  |  |
| STALE_COPIES-2 | The #enchant question keeps the item, the enchantment and the quoted fee by id, and a yes binds that or nothing | S | medium | 1 | no |  |  |
| STALE_COPIES-3 | A companion's errand waits in the save by id: the answer reaches the hire after a rollback, a stand-down or a reopened game | M | medium | 1 | maybe |  |  |
| STALE_COPIES-4 | When someone dies or leaves, what a character had with them is tied off on the record the scene holds, whichever path removed them | M | medium | 2 | maybe |  | yes |
| STALE_COPIES-5 | A situation's moment is listed as seen, is closed from afar when its minutes run out, and its town keeps the memory of it | M | medium | 3 | maybe |  |  |
| STALE_COPIES-7 | Code that is handed the scene takes a person from the scene, so the asker's thanks for a job done is not written on a second copy and lost | M | medium | 1 | maybe |  |  |
| STALE_COPIES-6 | A person here is one object from one reading of the room to the next, so time passing cannot orphan what a handler holds | S | small | 1 | maybe |  |  |
| STALE_COPIES-8 | A trust move made in a scene is saved by the one way scenes move trust, so a failed haggle cools the seller in the save | M | small | 1 | maybe |  |  |
| STALE_COPIES-9 | What finishing someone's request is worth to them is stated in data, each amount once | S | small | 1 | no |  | yes |
| SITUATIONS-4 | Who a situation's end credits is kept on the situation, and every kind of way met makes its certain change through one writer | M | heavy | 2 | maybe |  | yes |
| SITUATIONS-5 | A captive answers only for a step of its own arc | S | medium | 1 | no |  |  |
| SITUATIONS-8 | At an arc's last fight a leader who fell is no captive, and one who yielded is taken | S | medium | 1 | no |  |  |
| SITUATIONS-6 | A beaten foe counts once toward a hunt or bounty, whichever way it was beaten | S | medium | 1 | no |  | yes |
| LONG_SAVE-5 | A memory with no minute is trimmed by its day, not first | S | small | 1 | no |  |  |
| TOWN_SERVICES-3 | A rank a teacher offered is taught for the fee quoted, or the offer is withdrawn in words and nothing is taken | S | medium | 1 | no |  |  |
| TOWN_SERVICES-7 | A posting made from a dungeon as it was leaves every board when the dungeon is remade, and a posting struck is struck in the save | S | small | 1 | no |  |  |
| TRAVEL_PLACES-8 | A dungeon's remaking lets go of the contracts that name what it lost, on every board and in words | S | small | 1 | no |  | yes |

### Phase 5. The 60 second turn on the minimum card (card session 1)

Criterion (a), the minute: the journal note (the only single call over 60 s), tries not asked of the budget, the embed with no deadline, the profile that misprices the first line, the 114 s one-call abilities flow, a lesson costing up to five answers. Row 9 (no find ever accepted) rides with the journal note as the audit's order asks. Small instruments lead because the phase is judged on the card: the gate's exit code, the logs' one folder (which also stops a suite run trimming the owner's play logs), a run's own rows, the call-row reader and wait times. REMOVALS_1-6 follows REMOVALS_2-3 so CONTRACTS-5 never floors a dead contract.

24 features (8 S, 15 M, 1 L), fixing 48 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TOOLS_BOTS-19 | A gate that could not run leaves 2, on every path | S | small | 1 | no |  |  |
| SUITE-9 | Tools that read the tree read git's list of it, not every copy under the folder | S | small | 2 | no |  |  |
| SUITE-1 | The suite's output folder is one folder to Python, Git Bash and the Read tool, each checkout has its own, and no tracked Python names /tmp | S | medium | 2 | no |  |  |
| SUITE-2 | One place says where the game's logs go, and a test's process is told: under the suite, by hand, and in the tools | M | medium | 2 | no |  | yes |
| TOOLS_BOTS-2 | A measuring run writes into a folder and logs of its own | M | small | 2 | no |  |  |
| TOOLS_BOTS-4 | One reader says what a row of the call log means: a call, a first try, a token read | M | small | 2 | no |  |  |
| TOOLS_BOTS-5 | Every call row says how long the call waited for the card, and model time is counted without the wait | M | small | 2 | no |  |  |
| CONTRACTS-1 | A townsperson's reply is asked for a journal note only when one is due, the note has an end, and a reply can point only at the things it was shown | M | heavy | 6 | yes | card | yes |
| CONTRACTS-11 | Whether a townsperson gave their name is read from their words on every reply path | S | small | 1 | yes | card |  |
| GATE-3 | What a reply leaves behind, the line to remember and the journal note, is checked, bounded and kept in one place | M | small | 2 | maybe |  |  |
| CONTRACTS-2 | Structured answers are written without layout, and a contract change is measured by replaying a task's recorded requests under both forms | M | medium | 1 | no | card | yes |
| CONTRACTS-3 | A find is never lost to a missing name: an answer's shape follows its deciding field, declared on the contract | M | heavy | 3 | no | card |  |
| BUDGET_FLOW-1 | Every try of a model call is asked of the budget, and a try cut at its deadline is charged what it was handed | M | medium | 2 | maybe |  |  |
| BUDGET_FLOW-3 | An embed call has a deadline, and its answer is checked before it is kept | M | medium | 4 | no |  |  |
| BUDGET_FLOW-2 | The card profile prices a request as a base plus a rate, and the tool cannot write a profile the game cannot load | L | medium | 3 | no | measure |  |
| GATE-2 | A checked draft is never thrown away because its rewrite failed | S | medium | 1 | no |  |  |
| REMOVALS_2-3 | A fault in the engine's plan of a class's abilities is written down and told as the gifts line, and the one-call flow in which the model chose every mechanic is gone | S | small | 1 | no |  | yes |
| REMOVALS_1-6 | The retired stat-passives step is gone from creation, and no prompt is reached by a built name | S | small | 2 | no |  |  |
| GATE-5 | Every word list a check reads is matched as whole words with their endings, by one matcher | M | medium | 3 | maybe | measure |  |
| GATE-6 | A set answer that fails in some entries keeps the entries that passed and asks again only for the rest | M | medium | 1 | no | card |  |
| BUDGET_FLOW-4 | A pane walk's arrival runs inside the command's input, and a ratchet names every main-thread call or wait made with no budget open | M | medium | 1 | no |  |  |
| BUDGET_FLOW-27 | A place's missing first people are asked for inside an input, and a wait on a background job is bounded and charged | M | small | 2 | no | card | yes |
| BUDGET_FLOW-7 | One of Maren's lines takes one ladder: free speech once, the written line re-voiced only while there is room, else as written | S | medium | 1 | no |  |  |
| REMOVALS_2-14 | No switch in config.py is one that nothing can set: the two mentor switches go, and the written lines are tested through a model that fails | M | small | 1 | no |  | yes |

### Phase 6. Before the next release (1): a build that starts, its logs and its check

Criterion (b): heavy row 10, a built game cannot start (SHIPPING-1 with STARTUP_DATA-1's shared reader, which also gives 6 to 9 s back a launch); logs beside the exe and capped (one order on llm/audit.py); the update switch; faults written down; the embedder after Try again; what the hash and the name vocabulary read. SUITE-12 first because this plan and docs 26 to 32 are untracked.

13 features (10 S, 3 M), fixing 25 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| SUITE-12 | Every file a tracked document or an agent's instructions cite is in git | S | medium | 2 | no |  | yes |
| SHIPPING-1 | A built game passes its own startup check, and a build that cannot is never handed over | M | heavy | 2 | no |  |  |
| STARTUP_DATA-1 | The startup check parses each data file once, on the fast loader, and reads the source once a process | M | heavy | 4 | no |  |  |
| SHIPPING-3 | The files written under the code's own folder are placed by core.paths, so the logs land beside the exe | S | medium | 3 | no |  |  |
| REMOVALS_1-12 | The audit log has one switch, and no config read falls back to a data table | S | small | 1 | no |  |  |
| LONG_SAVE-6 | Every log the game writes has a cap, and the audit folder keeps a window of sessions | S | small | 4 | no |  |  |
| SHIPPING-7 | The update switch is asked in one place and every path obeys it | S | medium | 2 | no |  |  |
| TASK_FAILURE-2 | A fault the game carries on past is written down, and a fence stops a new silent handler | M | small | 1 | no |  |  |
| TASK_FAILURE-13 | The gateway's own bookkeeping never costs an answer or leaves it half mended | S | small | 2 | no |  |  |
| TASK_FAILURE-14 | Closing a campaign runs every stage, whatever the one before it did | S | small | 1 | no |  |  |
| SHIPPING-12 | Try again brings the embedder back with the model | S | small | 1 | no |  |  |
| STARTUP_DATA-8 | Files only tools read leave the game's data hash | S | small | 1 | no |  |  |
| GATE-20 | Name mending reads its ordinary words from the game's own files only | S | small | 1 | maybe |  |  |

### Phase 7. Before the next release (2): CI, the window, leaving, the installer

Criterion (b): CI builds, installs and starts the game (TESTS-2 and TESTS-7 first, which the page checks need); a failed start told; a refused line that locks creation; one way of leaving; the installer proven and holding exactly this release; game text that could become markup. SHIPPING-17 last, lowest weight.

17 features (3 S, 14 M), fixing 29 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TESTS-2 | One check helper in simlib, and the runner fails a test that checked nothing | M | medium | 3 | no |  |  |
| TESTS-7 | A skipped check is counted and shown, and the page's checks run in CI | M | medium | 1 | no |  | yes |
| SHIPPING-2 | CI builds, installs and starts the packaged game | M | medium | 1 | no |  |  |
| TESTS-11 | The fake llama-server refuses a flag the pinned build does not take | M | small | 1 | no |  |  |
| SHIPPING-4 | An end the player did not choose is told over whatever page is up, and the window stays | M | medium | 2 | no |  | yes |
| SHIPPING-5 | One sender for the page: only the page on top answers the prompt, and a refused line puts it back | M | medium | 2 | no |  |  |
| SHIPPING-6 | One way of leaving: every exit cancels the calls in flight and stops the server, whichever start made it | M | small | 5 | no |  | yes |
| REMOVALS_1-18 | The dormant server start is kept with its reason written, or retired once there is one stop | S | small | 1 | no |  | yes |
| SHIPPING-8 | The installer the game downloads is proven before it is run | M | small | 2 | no |  | yes |
| SHIPPING-9 | The installer moves the model files, checks them and asks for the room | M | medium | 1 | no |  | yes |
| SHIPPING-10 | A build and an install hold exactly this release's files | M | small | 2 | no |  | yes |
| SHIPPING-11 | The launcher knows whether its page is there: a blank window falls back, a closed tab ends the game | M | small | 2 | no |  | yes |
| SHIPPING-13 | What is a view is the bridge's to say, and the page keeps no list | S | small | 1 | no |  |  |
| SHIPPING-14 | Text from the game cannot become markup in the page | M | small | 1 | no |  |  |
| SHIPPING-15 | The Python the game needs is stated once and checked where it starts; requirements are bounded and a build is pinned | M | small | 2 | no |  |  |
| SHIPPING-16 | The built game offers no start that cannot work | S | small | 1 | no |  | yes |
| SHIPPING-17 | The page's transcript has a cap, and a line's cost stays flat over a long sitting | M | small | 1 | no | measure | yes |

### Phase 8. Instruments the rest is measured by

Criterion (c): what phases 9 to 16 are measured by. The bench that puts things back, zeros never measured, the typed-line counts and owed cases, creation and the lesson recorded, the slots measured (answers GOALS.md's f536 question), the contract floor test, fences that see too little, the typed-number count, the first-player counts (one fence, see overlaps).

19 features (8 S, 11 M), fixing 31 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TOOLS_BOTS-3 | A tool's bench puts back everything it replaced, so the next bench starts clean | M | medium | 2 | no |  |  |
| TOOLS_BOTS-22 | interp_eval reads only the rows a case wrote | S | small | 1 | no |  |  |
| TOOLS_BOTS-7 | A night's harness keeps its record at the edges: a character the console cannot print, an event that never started | S | small | 2 | no |  |  |
| TOOLS_BOTS-11 | A measuring tool never reports a zero or an empty result it did not measure | M | small | 1 | no |  |  |
| TOOLS_BOTS-8 | The night's Fights section counts rolled-back operations and fights let go from the game's own rows | S | medium | 1 | no |  |  |
| TOOLS_BOTS-12 | The divergence yardstick counts every situation that started, not only the last thirty finished | S | medium | 1 | no | measure |  |
| TOOLS_BOTS-16 | Every speech row in the call log says who spoke | M | small | 1 | no |  |  |
| TOOLS_BOTS-20 | A blind reader's file is read line by whole line: a remark is no vote | S | small | 1 | no | measure |  |
| TYPED_LINE-1 | Every repair, intercept and risk flag is counted on lines people typed, and every repair has a case it gets right | M | medium | 1 | no |  | yes |
| BUDGET_FLOW-6 | A recording walks character creation and Maren's lesson, and mentor_chat's ceiling is written from it | M | small | 2 | no | measure | yes |
| BUDGET_FLOW-12 | Every night says what each slot kept, so the f536 question is answered from numbers | M | medium | 5 | no | card | yes |
| CONTRACTS-5 | The smallest answer a contract's grammar allows is never refused for being empty | M | small | 3 | yes | card |  |
| TESTS-8 | No check ends in `or True` or passes a constant | M | small | 2 | no |  | yes |
| TESTS-10 | The write-path and pure-module fences read the syntax tree, and name a listed file that is missing | M | small | 2 | no |  | yes |
| TESTS-12 | A reworded line fails no test whose behaviour did not change | M | small | 1 | no |  |  |
| STARTUP_DATA-11 | A tuning number typed in game code is counted, and the count only falls | M | small | 1 | no |  |  |
| SITUATIONS-17 | Engine code's reads of the scene's first player are counted and only fall, and a job's thanks and a stay read the character who is acting | S | small | 1 | no |  |  |
| TOWN_SERVICES-9 | Every memory made in play says whom it is about: none is built by hand with the subject left to a default | S | small | 1 | no |  |  |
| STALE_COPIES-12 | The files that still act on the scene's first player, and the store that saves under the first row, are put on M1's list | S | small | 2 | no |  |  |

### Phase 9. What a failed model call leaves, built against the task matrix

(a) and (c) together: these lose a passage, a step or a search, rarely a save, and the matrix that fails each task in turn (TESTS-3, on TESTS-6's script) is their test, so it leads. The outcome field and ledger facts first, then the stand-ins that never tell a no as done.

18 features (6 S, 11 M, 1 L), fixing 27 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TESTS-6 | A kept recording's census reads what the game did, and the party recording keeps the claims its script plants | M | medium | 2 | yes |  | yes |
| TESTS-3 | Every model task is failed in turn through a played session, and each task says what its failure does | L | small | 1 | no |  | yes |
| TASK_FAILURE-1 | What a step came to is kept on its operation, and a road stop pays only for help that worked | M | medium | 1 | no |  | yes |
| TASK_FAILURE-3 | Every ledger row carries the facts its stand-in list names, and startup fails a list no writer can fill | M | small | 1 | yes |  | yes |
| TRAVEL_PLACES-2 | A step that asks for what is already so is answered as such: no journey told, no refusal logged, and the rest of the line goes on | M | medium | 1 | no | card | yes |
| TASK_FAILURE-5 | Every telling of a line is a passage: a silent line and a creature sighted survive a failed narrator | M | medium | 2 | yes |  |  |
| TASK_FAILURE-6 | A lost passage's stand-in says what the engine decided: a no or a failed deed is never told as done | M | medium | 2 | no |  | yes |
| TASK_FAILURE-7 | A stand-in is shown as its passage would have been, with the engine's own record: a round prints its figures, the goddess speaks as herself | M | medium | 2 | yes |  | yes |
| TASK_FAILURE-8 | A once-only writing that fails on the model is asked again from the deferred queue | M | medium | 1 | no |  |  |
| BUDGET_FLOW-8 | A companion's new quirk queues its details for the tail and never asks at the line's first touch of the party | S | small | 1 | yes |  |  |
| TASK_FAILURE-9 | A step the game said no to is never recorded as done: bare-note refusals go through refuse() | M | medium | 1 | no |  | yes |
| TASK_FAILURE-10 | Inside a turn a fault rolls the operation back instead of being answered for, and an Interrupt passes every guard | M | small | 6 | no |  | yes |
| TASK_FAILURE-11 | A failed audit call is a line not taken, never the player's words called unclear | S | small | 1 | no |  | yes |
| TASK_FAILURE-12 | A companion's reply that cannot be written is the line not taken, as a townsperson's is | S | small | 1 | no |  | yes |
| TASK_FAILURE-16 | A background batch of townspeople lands whole or leaves a record | S | small | 1 | no |  |  |
| STALE_COPIES-10 | People written in the background are applied whole or not at all, and a fault in applying them is written to the crash log | S | small | 1 | no |  |  |
| SITUATIONS-11 | Health lost outside a fight is taken by one writer that holds the floor, writes the row and tells the player what was taken | M | small | 1 | maybe |  |  |
| TASK_FAILURE-17 | The goddess's line for traits that cannot be written names what is on the page | S | small | 1 | no |  | yes |

### Phase 10. What the engine reads of a typed line, and of carried things

(a) and (d): coin and standing taken on a suspicion, a fine on a misread answer, a number in words read wrong, the wrong thing sold or dropped. After TYPED_LINE-1's counts (phase 8) and GATE-5's matcher (phase 5). Subject to the owner's word on the 17 November stop.

18 features (11 S, 7 M), fixing 25 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TYPED_LINE-3 | A repair never takes coin or changes standing on a suspicion: it reads the player's words only, and what it only suspects is asked first | M | medium | 1 | maybe |  | yes |
| TYPED_LINE-4 | An answer to the game's own question settles only when it names exactly one choice | M | medium | 1 | maybe |  |  |
| TYPED_LINE-6 | A pattern over the whole line gives way to the step the plan already holds | M | medium | 3 | maybe |  | yes |
| TYPED_LINE-5 | A number said in words is read whole and belongs to what follows it: a sum, a count, an hour | M | medium | 3 | maybe |  |  |
| TYPED_LINE-8 | A check that is only a manner of doing never replaces a handler that makes its own roll | M | medium | 1 | no |  | yes |
| TYPED_LINE-7 | Taking a thing oneself is read only from the first person's own verb | S | medium | 2 | no |  | yes |
| TYPED_LINE-11 | A command with no name is an unknown command, never a crash | S | small | 2 | no |  |  |
| TYPED_LINE-10 | What a line did not get to is told to the narrator before its passage | S | small | 1 | no |  |  |
| TRAVEL_PLACES-5 | A part this place has is walked to before the words are read for leaving | S | small | 1 | no |  |  |
| TRAVEL_PLACES-7 | A dungeon chamber gives up its overlooked coin once | S | small | 1 | no |  | yes |
| TRAVEL_PLACES-9 | The fork's question and the reader of its answer count the branches in one order | S | small | 1 | no |  | yes |
| TRAVEL_PLACES-10 | A numbered name is found in a line only as a whole name | S | small | 1 | no |  |  |
| TOWN_SERVICES-4 | One resolver says which carried thing the words mean: whole words, the pack, the key items and the things in hand together, and never a guess from a letter | M | medium | 2 | maybe |  | yes |
| TRAVEL_PLACES-6 | A find is told by what the pack kept and what it left lying | S | small | 1 | no |  |  |
| TOWN_SERVICES-6 | Only a thing with a slot can be worn: equipment holds the slots data names and nothing else | S | small | 1 | no |  |  |
| TOWN_SERVICES-5 | A yes goes to whoever asked: a request and the board are weighed together, and the clerk's presence decides nothing | M | medium | 1 | no |  |  |
| SITUATIONS-10 | A captive's deal is recorded only when mercy was offered and not denied | S | medium | 1 | no | card | yes |
| PEOPLE_TALK-14 | Sworn Enemy's subject is read at word starts from a table in data, held to the bestiary's kinds | S | small | 1 | no |  | yes |

### Phase 11. The fight's remaining faults: steps, prices, locks, commands, captives

Criterion (d): medium and low fight faults that wait on owner answers (prices, locks, gear in a fight, captives' labels). TESTS-4 walks every command through a fight once FIGHT_SCENE-3's table exists.

10 features (5 S, 5 M), fixing 13 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| FIGHT_CORE-7 | A step on the battlefield is told as what happened, and "you" takes its own verb | M | medium | 2 | yes |  | yes |
| FIGHT_ABILITIES-7 | One function knows what an ability costs and one takes it, so a free or blood-paid cast is never refused for a pool it does not use | M | medium | 2 | no |  | yes |
| FIGHT_ABILITIES-8 | A once-a-fight or once-a-day lock is a lock, not a cooldown, and nothing passes it unless the owner says so | M | medium | 1 | no |  | yes |
| FIGHT_ABILITIES-9 | Gear's spell power is scaled in the one place every roll passes, so a drop, a reforge and a cache agree | S | medium | 1 | no |  | yes |
| FIGHT_ABILITIES-10 | A command with nobody to obey is refused before it is paid for | S | small | 1 | no |  | yes |
| FIGHT_ABILITIES-11 | A heal's card states the numbers the engine uses | S | small | 1 | no |  | yes |
| FIGHT_ABILITIES-14 | A fight's binding, taming, items and spell dice act for the fighter who is acting | S | small | 2 | no |  | yes |
| FIGHT_SCENE-3 | Every `#` command and every standing question is declared in one table that says what it may do in a fight, and one not declared for a fight is locked | M | medium | 1 | no |  | yes |
| TESTS-4 | Every command that changes the character is played in a fight, then a round, then a reopen | S | medium | 1 | maybe |  |  |
| FIGHT_SCENE-5 | Captives taken in one fight are told in one note, and each bears a label of their own | M | small | 1 | yes | card | yes |

### Phase 12. Small certain fixes: situations, people, town, field abilities

Criterion (d): one place each, stub tests. PEOPLE_TALK-4 before -6 (one day base); SITUATIONS-7 and PEOPLE_TALK-6 share one trust bound in regard.step; TOWN_SERVICES-8 before RELOAD-11 (same function, one cooldown answer).

18 features (13 S, 5 M), fixing 21 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| SITUATIONS-1 | On an act rolled on talk nothing of the world moves by the act's own hand, whatever cause the ruling gives | S | medium | 1 | no |  |  |
| SITUATIONS-2 | An act's changes are checked in the ruling's order by one pass, each against its own situation, and a person named by their code is that situation's own part | M | medium | 4 | no |  | yes |
| PEOPLE_TALK-4 | A companion's memory is kept under the calendar day of its minute and read from the same clock | M | medium | 1 | yes |  |  |
| SITUATIONS-7 | A ruling stood on again moves nobody's trust or feeling a second time | M | medium | 1 | no |  | yes |
| PEOPLE_TALK-6 | A gift moves trust and bond through the one writer, bounded by the day and by its worth | M | medium | 1 | no |  | yes |
| SITUATIONS-9 | People who flee a fallen town leave their post vacant in the town they left | S | medium | 1 | no |  | yes |
| SITUATIONS-12 | A situation that ends inside a scene ends one way, and the people here are read again whichever ending it was | S | small | 1 | no |  |  |
| SITUATIONS-13 | A condition says whether an effect of it was ever laid, so one that has run out reads the same before and after its row is pruned | S | small | 1 | yes |  | yes |
| SITUATIONS-14 | A ruling's word on a good ends that part's own stock, so goods the record calls lost are not still on sale | S | small | 1 | no |  | yes |
| SITUATIONS-15 | A queued follow-on whose pressure the world lacks starts from its place, and data cannot queue one that cannot start | S | small | 1 | no |  |  |
| PEOPLE_TALK-11 | Every companion picked can bring up what drives them | S | small | 1 | maybe |  |  |
| PEOPLE_TALK-12 | A hire who is sent away is recorded as departed and their promises are let go | S | small | 1 | no |  |  |
| TOWN_SERVICES-8 | A field ability used as an edge is spent in one step: what it costs, whether it then rests, and whether it was used at all are decided once | M | small | 1 | no |  | yes |
| RELOAD-11 | A crafting ability's boost is kept with the character and its numbers are in data | S | small | 1 | no |  | yes |
| RELOAD-12 | The daily cap on people ruled into a place is counted in the save | S | small | 1 | maybe |  |  |
| STARTUP_DATA-9 | A ware that is a good takes the good's price | S | small | 1 | no |  |  |
| BUDGET_FLOW-24 | A pane command told to be quiet reaches no model call, whatever hook it passes | S | small | 1 | no |  |  |
| BUDGET_FLOW-25 | A waiting claim with no room is passed over before the model is asked about it | S | small | 1 | no |  |  |

### Phase 13. Savings (a): the speakers' checks and the narrator's rewrites (card session 2)

Criterion (e), the largest saving first: GATE-1 removes about 215 of 556 second calls (8 to 10 s each on the minimum card). False alarms, one set of speaker checks, every fault told at once; Maren's files together (GATE-7, -22, STARTUP_DATA-10, REMOVALS_1-8); the narrator's worn words. GATE-23 last: its measure decides whether it is built. One live gate session.

20 features (10 S, 8 M, 2 L), fixing 41 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| GATE-1 | A fault with one certain mend is mended before the gate, counted, and never costs a second call | M | medium | 8 | no | card | yes |
| GATE-4 | A dialogue frame with one bad sentence or an echoed heading is mended in place, and the going-back check reads its object | M | medium | 3 | no | card | yes |
| GATE-8 | Every speaker's words pass one set of checks, and a check stays on for the last pass unless it is named as loosened | M | medium | 3 | maybe | card |  |
| GATE-9 | The speaker checks let ordinary speech stand: a word that opens a sentence, an echoed question, owning a thing | S | medium | 2 | maybe | measure | yes |
| GATE-24 | Every fault of a draft is told at once, and no fault once told is forgotten on a later try | M | small | 1 | maybe | card |  |
| GATE-7 | A check on amounts or game words reads what the request gave, through one reader with its lists in data | L | medium | 3 | maybe | card | yes |
| STARTUP_DATA-10 | Maren's lines take the fee and the wolf count from the keys the engine reads, and her word to a caster about mana is true | S | small | 2 | no |  | yes |
| REMOVALS_1-8 | Maren's unreachable rank check is gone, and the figures check that does run reads every level | S | small | 2 | no | card |  |
| GATE-22 | Maren's first appearance is kept when it shows her sword, her crest and her rank in any plain wording, and falls back when it leaves one out | S | small | 1 | no |  |  |
| GATE-10 | One reader decides whether a model coined a name, wherever its text can name someone | M | medium | 3 | maybe | measure |  |
| GATE-11 | A speaker's own gestures are always checked for a repeat, however many others are present | S | medium | 1 | maybe |  |  |
| GATE-15 | The content guard knows the innocent senses of its words, and can never refuse a word the game itself offered | S | small | 1 | no | measure | yes |
| GATE-16 | A reason sent back to the model is the same in every process | M | small | 2 | no |  |  |
| GATE-18 | A name the model gives a thing is checked by one validator before it replaces the engine's name | S | small | 1 | no |  |  |
| GATE-14 | The stock phrases the narrator is shown and the ones a draft is checked for are one list in data | S | small | 1 | no | card | yes |
| GATE-21 | When a request itself speaks of a building the town lacks, the speaker is told so, and a complaint never points at a list they were not shown | S | small | 1 | maybe | card | yes |
| GATE-12 | fresh() never counts the request's own names and facts as a worn word | M | medium | 2 | maybe | card |  |
| GATE-13 | A shared run of words is stale only when it carries more than names and little words | M | small | 1 | no | measure |  |
| GATE-19 | The narrator's prose tasks are one list, and a prose task neither tuned nor declared untuned fails at startup | S | small | 1 | no |  | yes |
| GATE-23 | A word in another script cannot be written, if the measure shows an English word takes its place | L | small | 2 | maybe | card | yes |

### Phase 14. Savings (b): what the contracts let the model write (card session 3)

Criterion (e): bounds in the grammar, the shaping step (which doc 29 R2 should then use), ids taken from the call, fields nobody reads. One re-bless of every golden with BUDGET_FLOW-11, back to back with CONTRACTS-6; one stub_party re-bless for the small readers.

13 features (4 S, 8 M, 1 L), fixing 21 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| CONTRACTS-6 | No string that is neither spoken nor narrated is without an end: its length comes from data and is in the grammar | M | heavy | 2 | yes | card | yes |
| CONTRACTS-17 | One step shapes a call's schema from what the call holds, and the fixed sets come from data | L | small | 1 | no | card |  |
| CONTRACTS-7 | A situation's parts can name only the people, places and goods its request lists, and no person where none can be cast | M | medium | 1 | yes | card |  |
| CONTRACTS-9 | An id or a count the call holds is taken from it, never written free | M | small | 1 | yes | card |  |
| CONTRACTS-12 | What the engine has already decided is not asked back: a road event's kind, a perk's strength | S | small | 2 | yes | card | yes |
| CONTRACTS-13 | A small reader of a typed line writes no summary that nobody reads | M | small | 2 | yes | card | yes |
| REMOVALS_2-6 | The reading of a line at a camp carries only what the engine reads, and every field of a small reader's answer is read | S | small | 1 | no | card |  |
| PEOPLE_TALK-8 | The hiring note names the way that works, and the typed hiring path nothing can reach is gone | M | medium | 1 | no |  | yes |
| CONTRACTS-14 | A ruling call asks only for what its caller reads: the road hazard and the event judge | M | small | 2 | no | card | yes |
| GATE-17 | No speaker is sent back for the length of what they say, and the suite holds it for every reply contract | S | small | 2 | no |  | yes |
| BUDGET_FLOW-11 | Answer ceilings come from the engine's count, and the budget's expected sizes from recordings | M | medium | 2 | yes | measure |  |
| BUDGET_FLOW-17 | No request carries a whole-world list: names come from near the matter, under a cap, and a clash is named by the check | M | small | 3 | yes | measure |  |
| LONG_SAVE-12 | A naming request shows the newest taken names, and the engine holds the rest | S | small | 1 | no | card | yes |

### Phase 15. Savings (c): what a speaker is asked and handed (card session 4, with doc 31 if approved)

Criterion (e): the townsperson's and the companion's requests and answers, measured by the live gate's leaks and sizes in one run with doc 31's f731 if it is approved. Needs CONTRACTS-17 and -6 from phase 14.

16 features (9 S, 7 M), fixing 20 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| PEOPLE_TALK-1 | The engine's pronoun fill changes only its own lines, and only the pronoun and the verb it governs | M | medium | 1 | yes |  |  |
| PEOPLE_TALK-5 | A companion's details are written with their pronoun and once in their own voice, so nothing converts them | M | medium | 1 | yes | card |  |
| CONTRACTS-4 | A hire's five details get exactly five weights, so the weights are never thrown away whole | S | medium | 1 | yes | card | yes |
| PEOPLE_TALK-2 | What a person is told they last remember of a character is a memory of that character | S | medium | 1 | no |  |  |
| PEOPLE_TALK-16 | The default reply request lists under YOUR MEMORIES OF THEM only rows of that character | S | small | 1 | no | card | yes |
| PEOPLE_TALK-3 | A person's traits, speech, goal and town trouble each roll on a die of their own | S | medium | 1 | yes |  |  |
| PEOPLE_TALK-9 | The engine draws which of a town's troubles colours a person's concern | S | small | 1 | yes | measure |  |
| PEOPLE_TALK-10 | Only the drift hands a person a new goal; the profile only words the goal the engine gave | S | small | 1 | no |  |  |
| CONTRACTS-15 | Making a person asks only for what is kept: no copied name, no activity, no voice | M | small | 2 | yes | card |  |
| CONTRACTS-8 | A field the engine will not keep this call is not in the call's grammar, and one it will keep is required | M | small | 1 | yes | card |  |
| CONTRACTS-10 | A hire's reply is asked only for what its caller keeps, and the impression line is the engine's | M | medium | 2 | yes | card | yes |
| BUDGET_FLOW-14 | A party member's description is kept in parts, and each reader is given its own | M | small | 1 | yes | card |  |
| BUDGET_FLOW-15 | A townsperson's request says each thing once, and the line of what else they know has a cap | M | small | 2 | yes | card | yes |
| BUDGET_FLOW-16 | The speakers' system text is short and stable, and the frame's request carries no line for what was not given | S | medium | 2 | yes | card |  |
| PEOPLE_TALK-15 | A deed's witness remembers it in plain words: each deed names its verb once for its three lines | S | small | 1 | yes |  |  |
| PEOPLE_TALK-7 | A guild contractor knows the wilds of their own hall; role lines and rank weights live in data | S | medium | 1 | no |  |  |

### Phase 16. Savings (d): the background lane and what a line waits on (card session 5)

Criterion (e): the worker's withdraw, creation's abilities written while the class is read, model calls out of transactions (STALE_COPIES-11 as BUDGET_FLOW-10's arrival family), births and people ahead only on the owner's word, the cache settings. Measured on the card with BUDGET_FLOW-6's recording.

10 features (4 S, 4 M, 2 L), fixing 14 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| BUDGET_FLOW-5 | The worker can withdraw one job, and the save's one background job follows the player | M | small | 1 | no | card |  |
| BUDGET_FLOW-18 | Creation's abilities are written while the player reads the class, not after they confirm | M | medium | 1 | no | measure |  |
| STALE_COPIES-11 | The arrival's telling of a situation and its moment are asked outside the arrival's transaction | M | small | 1 | maybe |  |  |
| BUDGET_FLOW-10 | Every model call of play is asked outside its operation's transaction, and the ratchet reads what play reaches | L | small | 4 | yes |  | yes |
| BUDGET_FLOW-19 | A situation's birth is written on the background lane and taken up at the next input's edge | M | small | 1 | maybe |  | yes |
| BUDGET_FLOW-20 | The first people of a place the engine knows is next are written ahead, and dropped when not wanted | L | medium | 2 | maybe | measure | yes |
| BUDGET_FLOW-21 | One-time loads run behind the loading line when a campaign opens | S | small | 1 | no |  | yes |
| STARTUP_DATA-7 | The server's settings say what the server runs: idle slots are saved only when there is a RAM cache | S | small | 1 | no |  | yes |
| BUDGET_FLOW-26 | A thinking call's room is worked out against the slot it runs in | S | small | 1 | no |  |  |
| REMOVALS_1-13 | DND_NUM_CTX and the comment that says it sets the model's context are gone | S | small | 1 | no |  |  |

### Phase 17. A long campaign stays flat: stores bounded, reads narrowed

Criterion (f) (GOALS.md 'Nothing grows without bound'): the store registry and census first, then caps, the route cache beside the map's version, the narrow reads beside their counter.

14 features (9 S, 5 M), fixing 24 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| LONG_SAVE-1 | Every store names what bounds it in one registry, and a census fails on one that does not | M | small | 1 | no |  | yes |
| LONG_SAVE-4 | A stop that leaves the map takes its keys with it | M | small | 2 | yes |  | yes |
| LONG_SAVE-7 | Each kind in the entity registry says whether its final rows are trimmed or kept, and the trim obeys | S | small | 1 | no |  | yes |
| LONG_SAVE-8 | Carcasses past their hours leave the place where they are written | S | small | 1 | no |  |  |
| LONG_SAVE-9 | What a matter holds is bounded, and leaves the world's row with it | S | small | 2 | no |  |  |
| LONG_SAVE-10 | A character's per-day marks keep today only, and item history has a cap | S | small | 1 | no |  | yes |
| LONG_SAVE-11 | Ended arcs are kept small, and to a number | S | small | 1 | no |  | yes |
| BUDGET_FLOW-23 | Putting back a map that did not move leaves its version alone | S | medium | 1 | no |  |  |
| LONG_SAVE-13 | A route question costs one search from its start, and the cache trusts the map's version | M | small | 4 | no |  |  |
| BUDGET_FLOW-22 | A plain line's whole reads are counted, and the count only falls | M | small | 3 | no |  |  |
| LONG_SAVE-14 | A plain line reads the world's lists only where it needs them | M | small | 3 | no |  |  |
| LONG_SAVE-15 | The store asks its schema once and holds the operations record in hand | S | small | 2 | no |  | yes |
| LONG_SAVE-16 | The drift is handed each character's standing by its caller, and loads no player | S | small | 1 | maybe |  |  |
| SITUATIONS-16 | A summons that cannot be sent waits before it tries again, and loads only the one it picks | S | small | 1 | maybe |  |  |

### Phase 18. Removals (1): the census, then the code nothing reaches

Criterion (f): the one census is the failing test of every removal; the sweeps under it; the temperature arguments (REMOVALS_2-7 with PEOPLE_TALK-13's pair line); the saved fields in one planned re-bless last.

15 features (6 S, 9 M), fixing 45 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| REMOVALS_2-1 | The suite holds one census of what nothing reads, for both parts, and no tracked file imports a name it never uses | M | small | 1 | no |  |  |
| REMOVALS_1-1 | No import in the game or its tools binds a name the file never uses, and the suite holds it | M | small | 3 | no |  |  |
| REMOVALS_1-2 | Every function, class and constant of the game is reached by the game, or is declared with the reason it is kept | M | small | 11 | no |  | yes |
| REMOVALS_1-3 | No test passes through a helper the game does not call | S | small | 2 | no |  | yes |
| REMOVALS_1-5 | No parameter is handed that nothing reads, and the count of unread ones can only fall | M | small | 2 | no |  |  |
| REMOVALS_2-10 | Names nothing in the game reads are gone from the engine, the model layer, the store, the shell, the stub and the tools | M | small | 14 | no |  | yes |
| REMOVALS_1-4 | The fight scene's tests go through the round the game runs | M | small | 1 | no |  |  |
| REMOVALS_2-11 | The fight scene's seven pass-through methods are gone, and their tests call the service the game calls (one change with REMOVALS_1-4) | M | small | 1 | no |  |  |
| REMOVALS_2-8 | Every contract and stub answer belongs to a request some call makes: the retired stat-passives step is gone whole (one change with REMOVALS_1-6) | S | small | 3 | no |  |  |
| REMOVALS_1-9 | An error row from before the new failure kinds parts the replay, and the translation kept for it is gone | S | small | 1 | no |  |  |
| REMOVALS_2-9 | Every declared name of the scene is read and can change: the passage weight nothing reads and the exits flag nothing sets are gone | M | small | 2 | no |  |  |
| REMOVALS_2-7 | No call states a temperature the sampling table decides, and startup names one that does | S | small | 1 | no |  |  |
| PEOPLE_TALK-13 | A pair's line stays owed until the model has written it, and no call passes a temperature the table overrides | S | small | 1 | no |  |  |
| REMOVALS_1-19 | Saved fields that nothing reads go in one planned re-bless | M | small | 1 | yes |  | yes |
| REMOVALS_2-17 | The LoRA score's kit breaks are read from the voice kit in data, so a reworded option cannot go dead | S | small | 1 | no |  |  |

### Phase 19. Data is the source of truth: keys checked, numbers out of code (one data-hash batch)

Criterion (f): the key check first (STARTUP_DATA-2's war hosts is the one fault met in play), then every move that edits the same rules files in one pull request and one re-stamp of the three kept sessions; STARTUP_DATA-15 after the contracts and gate cuts.

17 features (8 S, 8 M, 1 L), fixing 29 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| STARTUP_DATA-2 | An id named in data is held to the table that defines it, and a war draws its hosts only from the categories its kind names | M | medium | 1 | no |  | yes |
| STARTUP_DATA-3 | A key in a rules file that no game code reads stops the start, and no rule is read with a default that stands in for the data | L | medium | 1 | no |  |  |
| STARTUP_DATA-4 | Each key that promised a rule the engine does not apply is wired, deleted or marked reserved | S | small | 2 | no |  | yes |
| REMOVALS_1-11 | Authored lines and keys that no code reads leave the world and rules files | S | small | 2 | no |  | yes |
| STARTUP_DATA-5 | The start names every roster creature no road reaches and every creature biome with no wild place | M | medium | 1 | no |  | yes |
| STARTUP_DATA-6 | What the game plays by leaves config.py: the sampling shift and the thresholds are data, hashed, checked and kept with a recording | M | small | 3 | no |  | yes |
| REMOVALS_1-7 | A known person's motive step is the engine's alone | S | small | 1 | no |  |  |
| REMOVALS_2-5 | A known person's goal moves by the engine alone: the model's motive step, its contract, prompt, stub answer and table rows are gone (one change with REMOVALS_1-7) | S | small | 1 | no |  | yes |
| REMOVALS_1-14 | The loot table says what an item is given, and the switch for conditional properties is kept with its reason or removed | S | small | 1 | no |  | yes |
| REMOVALS_1-15 | The families' fight lines are wired, held with a true header, or deleted: one answer for all 48 | S | small | 1 | no |  | yes |
| REMOVALS_1-16 | Hunger and fatigue have a written answer: they return with a played day under test, they go, or they stay off and GOALS.md says so | M | small | 1 | no |  | yes |
| STARTUP_DATA-12 | The engine's and the store's numbers, tables and fixed lines outside the fight are data | M | small | 4 | no |  |  |
| STARTUP_DATA-13 | The scenes' numbers, tables and fixed lines are data | M | small | 4 | no |  | yes |
| STARTUP_DATA-14 | Character creation's numbers and the companion roster's rule are data, and the townsfolk prompt quotes the wage the data holds | M | small | 1 | no |  | yes |
| STARTUP_DATA-15 | The contracts' word lists and field limits are data | S | small | 1 | no |  |  |
| STARTUP_DATA-16 | The fight's numbers are data, and a creature's health is worked out in one place | M | small | 3 | no |  | yes |
| FIGHT_ABILITIES-13 | A cap that is in data is read from data by every effect that uses it | S | small | 1 | no |  | yes |

### Phase 20. The suite and the balance bot

Criterion (f): the quick run from git (the heaviest suite fix), what a test leaves behind, the fences at every Stop, the push marker, the width; the balance bot playing again; the 292-file fold last when no feature has tests open. The owner may pull SUITE-3 and SUITE-14 to just after phase 7, since they speed every later Stop.

14 features (6 S, 8 M), fixing 32 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| SUITE-3 | A quick run takes what changed from git, against the tree its record describes: no baseline checkout, every tracked file, scratch picks nothing | M | heavy | 7 | no |  | yes |
| SUITE-14 | What a test leaves behind is removed, and a write into the repository fails it: temp folders, saves, stray files | M | small | 2 | no |  | yes |
| SUITE-4 | The record keeps every file a test read and every folder it listed, so a test that reads the code as text is picked when that code changes | M | medium | 1 | no |  | yes |
| SUITE-5 | The push marker believes only a full run of this commit on a clean tree | S | medium | 2 | no |  | yes |
| SUITE-6 | The suite uses the machine: a width it works out, the longest tests first | S | medium | 2 | no | measure | yes |
| SUITE-7 | A replay puts back what it changed and removes its scratch | S | medium | 3 | no |  |  |
| SUITE-8 | A stopped run keeps the record of what it ran, and its tests die with it if a lone kill of the runner is ever seen | S | small | 1 | no |  | yes |
| SUITE-10 | The line census reads each function once | S | small | 1 | no |  |  |
| TESTS-9 | The arrival split is played in the suite and replayed | M | small | 1 | maybe |  | yes |
| TOOLS_BOTS-6 | The balance bot plays again: its taps pass the game's call through whole, and it reads offers, trust and contracts as the game holds them | M | medium | 5 | no |  |  |
| TESTS-5 | The balance bot's loop runs in the suite, bounded, with no noted exception | M | medium | 1 | no |  |  |
| TOOLS_BOTS-23 | The bot's switches are one written table, and the suite shields its tests from them | S | small | 1 | no |  | yes |
| TOOLS_BOTS-17 | Every hand tool is run by the suite under the stub, or is listed with the reason it cannot be | M | small | 4 | no |  | yes |
| TESTS-13 | The copied check helper and the copied groups of tests are folded into one of each | M | small | 1 | no |  |  |

### Phase 21. The night tools, and the tree tidied

Criterion (f): the night bot works situations and gives up by moving on; capped-list readers; files that cannot run or are kept twice leave; the design index; the owner's one clean-up last, when nothing grows back.

13 features (9 S, 4 M), fixing 30 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TOOLS_BOTS-9 | The night bot works a situation's contract, and counts a path or a report done only when the game shows it | M | medium | 2 | no |  |  |
| TOOLS_BOTS-10 | The event bot gives up by moving on to something else, and seeks a contract at the hall that posts it | M | small | 2 | no |  |  |
| TOOLS_BOTS-18 | The bot's goal carries only names a player could know, and its line is checked by the game's own name matcher | M | small | 1 | no | card |  |
| TOOLS_BOTS-13 | Every pulse-log row written in a session carries its minute, and the world report opens a day only for a row it counts | S | small | 1 | no |  |  |
| TOOLS_BOTS-14 | A tool says what is new in a capped list by what the rows are, not by how long the list was or where they sit in it | M | small | 2 | no |  |  |
| TOOLS_BOTS-15 | The pulse preview carries on its scratch world: a second run does not crash | S | small | 1 | no |  |  |
| TOOLS_BOTS-21 | think_ab sends the request the game sends: the game's sampler list, and only rows whose grammar it can rebuild | S | small | 1 | no |  | yes |
| REMOVALS_1-10 | No tracked file is ignored, kept twice, already applied or named by nothing | S | small | 7 | no |  | yes |
| REMOVALS_2-13 | Files that cannot run, stale copies and applied patches leave the tree, and nothing tracked is ignored (one change with REMOVALS_1-10) | S | small | 7 | no |  | yes |
| SUITE-11 | What a tool generates is ignored, and the test asks git | S | small | 1 | no |  |  |
| REMOVALS_2-15 | docs/design/README.md is the folder's index, and no design document says "nothing built" for work that is built | S | small | 3 | no |  | yes |
| REMOVALS_2-16 | The second copy of the repository under .claude/worktrees is removed by git's own command, and the branches it leaves with it | S | small | 1 | no |  | yes |
| SUITE-13 | One clean-up of what the tools have already left on disk, run by the owner | S | small | 1 | no |  | yes |

### Phase 22. With plan 29, and the designs that need a document first

Criterion (g). TYPED_LINE-2 parts 1-3 and CONTRACTS-16's measures fold into doc 29 R1 whenever R1 runs (it can share card session 1 or 2); TYPED_LINE-9 part 2 after R1; BUDGET_FLOW-13 with R2 (after CONTRACTS-17); FIGHT_SCENE-6 is R4; TYPED_LINE-12 after R1 to R3, before or after roadmap phase 4 by the owner; FIGHT_CORE-8 is phase 4's can_take in narrow form; STALE_COPIES-13 and LONG_SAVE-17 feed multiplayer M1 (roadmap phase 5), STALE_COPIES-13 only if STALE_COPIES-1's night lists ask for it.

9 features (1 S, 2 M, 6 L), fixing 17 findings.

| Feature | What is true after it | Size | Weight | Findings | Golden | Measure | Owner |
|---|---|---|---|---:|---|---|---|
| TYPED_LINE-2 | The audit's second reading is counted by flag and its changed readings are read by a person, before plan 29 takes its model calls away | M | small | 5 | no | card | yes |
| CONTRACTS-16 | The one-reader plan carries the audit's two measures: the summary's share of a reading, and a second reading that writes a reason only when it differs | S | small | 2 | yes | card | yes |
| TYPED_LINE-9 | After a hire speaks, the next line is read by the reader with that hire offered: the follow-up no longer takes the line | M | medium | 1 | maybe | card | yes |
| BUDGET_FLOW-13 | The interpreter's request puts what does not change first and lists places by what the words are about | L | medium | 3 | yes | measure | yes |
| FIGHT_SCENE-6 | A line typed in a fight that is no fight action is answered from the fight's facts and spends no round | L | medium | 1 | no | card | yes |
| TYPED_LINE-12 | A handler is given its step, not the line, and an intercept is an offer to the reader (a design first) | L | medium | 2 | yes | card | yes |
| FIGHT_CORE-8 | One test says who may leave where they stand, and a hold ends with the holding | L | small | 2 | no |  | yes |
| STALE_COPIES-13 | One live record for each operation: the design that would remove the kind and the hand-made repairs | L | small | 0 | yes |  | yes |
| LONG_SAVE-17 | People long gone leave the save by a rule for how they left, and a stop's place row goes with its people | L | small | 1 | yes |  | yes |

## Questions for the owner

Each is asked once here; the features named wait on the answer.

1. **Where does this plan sit beside roadmap phase 4 (doc 28 Part B) and plans 29 and 31?** Options: (a) Phases 1 to 7 (faults in today's game and the next build) before any more phase 4, 29 or 31 work, the rest interleaved (recommended); (b) phase 4 and plan 29 first, this plan after; (c) phase by phase as approved. Waiting: all.
2. **Plans 29, 31 and CONTRACTS-1 (the model-settings trial's note) all claim f731. Which gets it?** Options: Number in the order approved; renumber the others. Waiting: CONTRACTS-1, TYPED_LINE-2, GATE-21, TASK_FAILURE-9.
3. **Are the typed-line fixes a 'fix round for misread lines', which the 17 November decision stopped?** Options: (a) Build them: they narrow or replace the engine's own reading of the player's words and add no repair (recommended); (b) record the lines as owed corpus cases and leave all to TYPED_LINE-12. Waiting: TYPED_LINE-3, TYPED_LINE-4, TYPED_LINE-5, TYPED_LINE-6, TYPED_LINE-7, TYPED_LINE-8, TRAVEL_PLACES-5, TRAVEL_PLACES-9, TRAVEL_PLACES-10, TOWN_SERVICES-4, TOWN_SERVICES-5.
4. **Timing of the plan-29 parts and the step-not-line design.** Options: TYPED_LINE-2 parts 1-3 with R1; if R3 slips past phase 4, (a) leave the two audit calls or (b) one request (TYPED_LINE-2 part 4) or CONTRACTS-16's two-shape verdict, not both; R3 with clause numbers or copied words; TYPED_LINE-9 part 2 (a) straight after R1 (recommended), (b) after R2-R3, (c) after phase 4; BUDGET_FLOW-13 with R2 (recommended) or alone ahead; FIGHT_SCENE-6 in R4 or Part B; TYPED_LINE-12 before or after phase 4; typed hiring (PEOPLE_TALK-8) pane-only now, as a reader target with plan 29; SITUATIONS-10 shared reader now (recommended) or a field of the one reader. Waiting: TYPED_LINE-2, CONTRACTS-16, TYPED_LINE-9, BUDGET_FLOW-13, FIGHT_SCENE-6, TYPED_LINE-12, PEOPLE_TALK-8, SITUATIONS-10.
5. **Are changes that touch the sampler chain or the server's slots within 'keep sampling as it is' (GOALS.md:249)?** Options: CONTRACTS-2's compact-space grammar rule treated as a contract change kept task by task on the measure (recommended); GATE-19 (a) declare combat_aftermath and road_event untuned (recommended) or (b) give them the prose guard; GATE-23 after its measure (a) build behind a switch or (b) keep the send-back; STARTUP_DATA-6 (a) correct GOALS.md's row to the values in force (recommended) or (b) fold the shift into the table; STARTUP_DATA-7 (a) settings say what runs (recommended) or (b) turn the RAM cache on; BUDGET_FLOW-12 after the measure (a) two slots stay or (b) a third slot (about 1 GiB). Waiting: CONTRACTS-2, GATE-19, GATE-23, STARTUP_DATA-6, STARTUP_DATA-7, BUDGET_FLOW-12.
6. **What may data/runtime hold, and may builders change server.yaml, which the project forbids reading?** Options: Window numbers and lines in data/runtime/window.yaml outside the hash (recommended; widens GOALS.md:192) or under data/rules inside it; embed limits in server.yaml (BUDGET_FLOW-3) and slot_ctx read from it (BUDGET_FLOW-26) only with the owner confirming the file's contents. Waiting: SHIPPING-4, SHIPPING-17, BUDGET_FLOW-3, BUDGET_FLOW-26, STARTUP_DATA-7.
7. **Code-held fight numbers: move now or wait for the balance pass (decision of 2026-11-04)?** Options: (a) Keep waiting, parts 1-3 only; (b) move now with values unchanged (recommended). Same answer for FIGHT_ABILITIES-13 (three readers ignore a number in data; Barkskin's card printed from its key or in words) and REMOVALS_1-14's halving; and are conditional properties on rolled gear still wanted. Waiting: STARTUP_DATA-16, FIGHT_ABILITIES-13, REMOVALS_1-14.
8. **Which floors hold against a poison or burn tick, a torn wound, and a kill outright?** Options: (a) By their own words: Deathless, Lifeline and a yielding foe hold against any harm, Deathward, Last Breath, a boss's last stand and Soul Tether a blow only (recommended); (b) every floor holds any harm; (c) only the duel and the first hunt. Kill outright: all refusals of death answer it (recommended) or none. Waiting: FIGHT_CORE-3, FIGHT_ABILITIES-4.
9. **A foe killed by a poison or burn a companion laid: whose kill is it?** Options: (a) The one who laid it, from status_from (default, needed by multiplayer); (b) always the player's, as today. Waiting: FIGHT_CORE-1.
10. **Summons in a trial of rank.** Options: (a) Allowed, a beaten one simply unmade, and whether the Bound summon walks in; (b) refused like draughts. The wrong win is fixed either way. Waiting: FIGHT_CORE-4.
11. **Turned foes (Dominate, Dread Regent).** Options: Last unturned foe gone: (a) the will lifts and the fight goes on (recommended) or (b) it flees and the fight is won; a turned foe an ally for blessings (a no, recommended); may its old side strike it (a yes, recommended). Waiting: FIGHT_ABILITIES-2.
12. **Fight prices, locks and cards.** Options: FIGHT_ABILITIES-7 echoing's weapon card: own id and code (recommended), reword, or out until balance; FIGHT_ABILITIES-8 Overcast through a named spell's locks (neither, recommended), reaching stamina techniques (no), reset relics clearing locks (no); FIGHT_ABILITIES-9 a cache's gear rolls as a drop's (recommended) or keeps its wider list; FIGHT_ABILITIES-10 refuse an order with nobody to obey before the cost (recommended) or keep it; FIGHT_ABILITIES-11 the transfer heal's price as the engine takes it (recommended), from what landed, or the card's 60%, and with no ally refuse or mend the caster. Waiting: FIGHT_ABILITIES-7, FIGHT_ABILITIES-8, FIGHT_ABILITIES-9, FIGHT_ABILITIES-10, FIGHT_ABILITIES-11.
13. **Fight movement and holds.** Options: FIGHT_CORE-7: a step that changed nothing is no move (default) or an attempt counts, and whether a refused step gets its own line; FIGHT_CORE-8: build a narrow hold rule now shaped for phase 4 (recommended) or wait for can_take, and which movement abilities break a hold (a, b or c). Waiting: FIGHT_CORE-7, FIGHT_CORE-8.
14. **Gear, quests and renaming during a fight.** Options: (a) Locked, as #prepare already refuses (recommended); (b) free; (c) as the round's action, which needs a design. Waiting: FIGHT_SCENE-3, TESTS-4.
15. **Captives: labels, choices, guards.** Options: Told apart by order or by a word of their look; the four choices with every capture or once a save (needs a saved mark and a re-record); a boss's guard by the creature's name (recommended) or its own noun; whether guards are numbered in the fight. Waiting: FIGHT_SCENE-5.
16. **A look or a question typed in a fight, and an improvisation that names no effect.** Options: (a) A game note from the engine's facts (cheapest) or (b) the narrator in place of the round's telling; the effectless improvisation rolled as 'distract' (recommended) or asked back. Waiting: FIGHT_SCENE-6.
17. **Out-of-fight ability cooldowns ('Cooldowns stay').** Options: RELOAD-11: (a) hold crafting and healing abilities to their cooldown before the cost (follows 'Cooldowns stay') or (b) start none; brews and meals spend the craft boost (b, as today) or only gear (a). TOWN_SERVICES-8: a picklock's edge starts no cooldown (recommended) or rests like any use. Waiting: RELOAD-11, TOWN_SERVICES-8.
18. **What is kept across a close and reopen.** Options: RELOAD-1: for each scene name neither saved nor rebuilt, keep or declare forgotten (default: what a check, prompt or routing reads is kept; chatter spacing forgotten), the owner reading the list; RELOAD-6: the telling's memory (a) kept across a close (planned) or (b) forgotten. Waiting: RELOAD-1, RELOAD-6.
19. **Should the home page list a save folder copied in from another install (GOALS.md open question)?** Options: (a) Yes, any marked folder (built unless told otherwise); (b) no, the marker carries the install's id. With it, TOOLS_BOTS-1's unmarked folder rule: (a) refuse always, (b) adopt names the game never gives, (c) refuse a typed name, adopt a coded one (recommended). Waiting: RELOAD-5, RELOAD-13, TOOLS_BOTS-1.
20. **Retire the import of the old one-file-per-record layout (reverses doc 20)?** Options: (a) Retire with a plain refusal (recommended); (b) keep and mend into the migrations. Waiting: REMOVALS_1-17, REMOVALS_2-4.
21. **A period's moment when the period turns while the character stands still.** Options: (a) No, rolled on arriving only (planned); (b) yes, a design change with its own feature and measure. Waiting: RELOAD-8.
22. **A remade dungeon's postings and held contracts whose floor survives.** Options: (a) Only lost floors let go; (b) everything naming the old making let go (TOWN_SERVICES-7's text already does this for 'Slay' postings); (c) kept and retitled. Waiting: TOWN_SERVICES-7, TRAVEL_PLACES-8.
23. **Road stops: settled or not (review Q15), and what outlives one.** Options: LONG_SAVE-4: does standing land at a stop, (a) no or (b) yes as today (default); TRAVEL_PLACES-3: a night at a stop is (a) no last rest (recommended), (b) the nearer real end, (c) as today; STALE_COPIES-4: a job from someone at a stop (a) struck with a history line (recommended), (b) never offered, (c) kept, which needs f711's later work. Waiting: LONG_SAVE-4, TRAVEL_PLACES-3, STALE_COPIES-4.
24. **Where a bound captive counts toward a hunt or bounty (review Q28 against doc 21 D7).** Options: (a) At the win, the hand-over only for a contract not yet counted (recommended, as built); (b) at the hand-over, as Q28 is written. Waiting: SITUATIONS-6.
25. **Situation rules.** Options: SITUATIONS-2 a present doer who is no part: (a) stays the act's hand (recommended) or (b) dropped; SITUATIONS-4 clear, find and contract ways make the situation touched only (recommended) or resolve their threats, and every threat resolved with nobody credited: lost as today or settled by others; SITUATIONS-9 the refuge's extra post for the dead too, or only the fled; SITUATIONS-13 an adopted condition lasts the situation's span (recommended) or its own clock; SITUATIONS-14 given_up stock stays at the fair price (recommended) or is released. Waiting: SITUATIONS-2, SITUATIONS-4, SITUATIONS-9, SITUATIONS-13, SITUATIONS-14.
26. **One cause's day bound on trust, and gifts to companions (review Q20 'memory only' against f420's +1 bond).** Options: SITUATIONS-7: build the reuse rule now and leave the bound to balance (recommended) or take the bound now; PEOPLE_TALK-6: a gift moves bond not at all, +1 once a day, or by worth; the least worth that earns trust; Campfire Cook once a day or unbounded. If both bound, one bound in regard.step. Waiting: SITUATIONS-7, PEOPLE_TALK-6.
27. **What finishing a personal request is worth in trust.** Options: (a) Keep 3 + 3 + 5 in data (recommended); (b) one amount; (c) drop the code's 3. Waiting: STALE_COPIES-9.
28. **Write the stale-save design (one live record per operation) or keep the ruling of 2026-11-10?** Options: Build STALE_COPIES-1 to -8 first and decide with a night's lists (recommended); design now. Waiting: STALE_COPIES-13.
29. **Failed model calls: what the player is told.** Options: TASK_FAILURE-11 a failed audit is the line not taken (recommended, turns round f332) or keep the ask-back; TASK_FAILURE-12 one rule for every speaker (recommended) or a quip list per temperament; TASK_FAILURE-10 a fault in the journal or a town's thanks costs the turn (recommended) or is carried; TASK_FAILURE-7 a stand-in round prints its figures even with numbers off (recommended), and {foe} by kind or by name; TASK_FAILURE-3 drop the ended, gathered and worked ledger kinds (recommended) or wire them; TASK_FAILURE-1 a half success pays no helper (recommended) and any act that worked deals with a hazard (recommended) or the hazard is given to the ruling; TASK_FAILURE-4 a companion the engine chose is called by its kind (recommended) or by names in data. Waiting: TASK_FAILURE-11, TASK_FAILURE-12, TASK_FAILURE-10, TASK_FAILURE-7, TASK_FAILURE-3, TASK_FAILURE-1, TASK_FAILURE-4.
30. **'Already so' answers.** Options: TRAVEL_PLACES-2: coin already in the purse and a camp where there is shelter move to the already-so answer (a, recommended) or stay refusals; TASK_FAILURE-9: 'You're not down in a dungeon' a refusal or already so. Waiting: TRAVEL_PLACES-2, TASK_FAILURE-9.
31. **Typed-line rules.** Options: TYPED_LINE-1 the owed ceiling (a) re-based to added cases, each owed to a feature (recommended) or (b) none, and whether the owner reads the typed cases first; TYPED_LINE-3 a suspected coin-taking step asked first with the price (recommended) or left; TYPED_LINE-8 a performance or recollection keeps its own mechanic (recommended) or goes to the one ruling, and stealth on a search counted for the fight or not rolled; TRAVEL_PLACES-7 one search a chamber (recommended) or until it finds; TRAVEL_PLACES-9 fork branches left to right (recommended) or nearest first; TOWN_SERVICES-4 two equal carried things: ask which (recommended) or ask only where the thing leaves the pack, and the goods' extra words; TESTS-8 a refused lesson ask closes the earlier offer (a) or leaves it open (b). Waiting: TYPED_LINE-1, TYPED_LINE-3, TYPED_LINE-8, TRAVEL_PLACES-7, TRAVEL_PLACES-9, TOWN_SERVICES-4, TESTS-8.
32. **The output gate's order (f391, f431) and the speakers' checks.** Options: GATE-1 (a) all exact mends, each kept only if its logged cases read right (recommended), (b) only carriage return and backslash-n, (c) as is; GATE-4 drop the bad frame sentence in place and narrow (recommended) or narrow only; GATE-9 an echoed question mended to a full stop (recommended) or sent back; GATE-7 cardinals strict, half and twice only before a unit (recommended) or a number only before a unit for everyone; GATE-14 move the stock list to data, five shown and ten checked (recommended), show all ten (measured), or check only what is shown; GATE-21 give the town line for kinds the request names (recommended) or leave the send-back; GATE-17 a town moment's line is a kept fact line with its bound in the grammar (recommended) or prose with no bound. Waiting: GATE-1, GATE-4, GATE-9, GATE-7, GATE-14, GATE-21, GATE-17.
33. **The content guard's lists.** Options: The allow phrases for cock, cocks and naked (owner reads them); 'fuck' as a strong curse: (a) pass only for the speaker offered it (recommended), (b) off the sexual list, (c) out of the strong curses. Waiting: GATE-15.
34. **Contract shape choices.** Options: CONTRACTS-1 the pinned grammars kept as frozen proof of the port (recommended) or remade by hand, and the note's bound (240 or another); CONTRACTS-4 a hire's secrets carry weights (seven) or not (five); CONTRACTS-6 a ratchet first (recommended) or every leaf at once with its own design; CONTRACTS-10 the impression line set by the engine from data (recommended), dropped, or asked only when the bond moved; CONTRACTS-12 a creation perk's tier light, drawn by weights, or picked by the player; CONTRACTS-13 the fight's summary kept for kind other only (recommended) or removed; CONTRACTS-14 the hazard keeps its own small call (recommended) or moves onto the act's ruling. Waiting: CONTRACTS-1, CONTRACTS-4, CONTRACTS-6, CONTRACTS-10, CONTRACTS-12, CONTRACTS-13, CONTRACTS-14.
35. **What a speaker is handed.** Options: BUDGET_FLOW-15 the faith paragraph in every reply (a) or only when the line bears on it (b); PEOPLE_TALK-16 mend the old request now (b, against f726's switch-off rule) or wait for the switch (a); PEOPLE_TALK-14 Sworn Enemy for six kinds of foe or all seventeen (words read first); STARTUP_DATA-14 the companion roster rule moved to data only (recommended) or limited to the waking biome. Waiting: BUDGET_FLOW-15, PEOPLE_TALK-16, PEOPLE_TALK-14, STARTUP_DATA-14.
36. **Background-lane choices.** Options: BUDGET_FLOW-27 a place's missing first people (a) on the background lane (planned) or (b) asked at the head of the input; BUDGET_FLOW-10 a failed residents call on a walk (a) takes the walk back or (b) the walk stands and people come later; BUDGET_FLOW-19 births (a) after the line as decided (f597, f599) or (b) on the background lane once the numbers say so; BUDGET_FLOW-20 people written ahead: build or not after the hit rate; BUDGET_FLOW-21 the place-name embed at the opening (b, re-bless stub_party) or left (a). Waiting: BUDGET_FLOW-27, BUDGET_FLOW-10, BUDGET_FLOW-19, BUDGET_FLOW-20, BUDGET_FLOW-21.
37. **Caps on the long campaign's stores.** Options: LONG_SAVE-1 each unbounded store found: cap, window or declared open, and code caps to data now or when touched (default); LONG_SAVE-7 keep escaped captives' rows until a return is built (default) or trim; LONG_SAVE-10 item history newest 200 (default) or all, declared open; LONG_SAVE-11 cap ended arcs now (default) or leave open until arcs become situations; LONG_SAVE-12 taken names a window of 400 (default) or all, declared open; LONG_SAVE-15 the operations record one row in memory (default) or a table (a migration); LONG_SAVE-17 a deleted person's journal line under its cap, a window on the people list, or never delete anyone known by name; SHIPPING-17 the page's transcript drops the oldest text past a cap or keeps everything. Waiting: LONG_SAVE-1, LONG_SAVE-7, LONG_SAVE-10, LONG_SAVE-11, LONG_SAVE-12, LONG_SAVE-15, LONG_SAVE-17, SHIPPING-17.
38. **Release choices.** Options: SHIPPING-6 a window closed mid-turn: cancel and roll back the operation, gone at once (recommended) or finish unseen; SHIPPING-8 the installer proven by size and sha256 now (recommended), a build-time signature, or a bought certificate; SHIPPING-9 the WebView2 bootstrapper downloaded or carried (about 2 MB); SHIPPING-10 Setup removes only listed retired model files (recommended), every unnamed file, or nothing; SHIPPING-11 a page gone this many minutes ends the game (recommended) or never; SHIPPING-16 drop --terminal from the built game (recommended) or give it a console; REMOVALS_1-18 keep the dormant server start with its reason (recommended) or retire it after SHIPPING-6. Waiting: SHIPPING-6, SHIPPING-8, SHIPPING-9, SHIPPING-10, SHIPPING-11, SHIPPING-16, REMOVALS_1-18.
39. **node and playwright on the owner's machine.** Options: (a) Install them so the suite before a push runs the 32 page checks (recommended by SHIPPING-2); (b) leave it, CI runs them and every local summary says they were skipped. Waiting: TESTS-7, SHIPPING-2, SHIPPING-4, SHIPPING-5, SHIPPING-13, SHIPPING-14, SHIPPING-17.
40. **The go to edit the owner's own files, and the suite's rules.** Options: One go for .claude hooks, agents, skills, settings and CLAUDE.md; SUITE-2 a test by hand is a *_test.py script (recommended) and a night's audit files move into its folder; SUITE-3 baseline the record's tree (recommended) or HEAD; SUITE-4 fences at every Stop (about 35 s, recommended) or at the full run; SUITE-5 untracked files refuse the push mark (recommended) and a run before the commit cannot mark; SUITE-6 the width cap 12 or 8 after three runs; SUITE-8 the tie only if a lone kill is seen (recommended) and a Stop hook time limit; SUITE-14 a write into the repository fails the run and a passed test's saves are removed (both recommended). Waiting: SUITE-1, SUITE-2, SUITE-3, SUITE-4, SUITE-5, SUITE-6, SUITE-8, SUITE-9, SUITE-12, SUITE-14.
41. **Which untracked documents go into git, and the design index.** Options: The eight cited ones (recommended), docs 29 to 31 and this audit once read, blind-pair keys only after their reading (or an ignore line saying why); finished docs marked in place (recommended) or moved to done/, and the owner reads the roadmap's new state column. Waiting: SUITE-12, REMOVALS_2-15.
42. **Recordings: their form and when to re-make them.** Options: REMOVALS_2-2 (a) plain text behind one reader (recommended), (b) gzip with zero time, (c) leave; TESTS-6 re-make stub_party so it holds a kept claim, a promise and a canon check (yes) or correct its docstring; TESTS-9 make stub_short with the arrival split at its next intended re-make (a) or not; REMOVALS_1-19 the saved-field re-bless taken once with another planned change of saved shape (recommended), and whether scope_places is wanted; TESTS-3 task failures declared in data/replay (recommended) or budget.yaml. Waiting: REMOVALS_2-2, TESTS-6, TESTS-9, REMOVALS_1-19, TESTS-3.
43. **Removals that need a yes.** Options: reindex_npcs removed (recommended) or declared; export_json and words_hash kept declared or removed; presence.hearers removed (recommended) or declared; tools/scratch and tools/runstats.py deleted (recommended); sim_report.md moved and the bot reports (TOOLS_BOTS-17) (a) both mended (recommended), (b) simreport kept, (c) both retired; tools/sim/matrix.py deleted (recommended); root scripts untracked only (recommended); docs/patches confirmed applied; troll.scenes wired or deleted, and a yes to the list of unread lines; the families' 48 fight lines (a) held with a true header (recommended), (b) wired and measured, (c) deleted; REMOVALS_2-3 stop at the first step (recommended) or remove about 125 more lines; REMOVALS_2-5 retire the model's motive step (recommended) or keep as a measuring arm; REMOVALS_2-14 remove VOICED_MENTOR and FREE_MENTOR (recommended) or keep one as a setting; TOOLS_BOTS-23 keep all twelve bot switches written (recommended) or only those used; TOOLS_BOTS-21 leave per-call grammars out of think_ab (recommended) or record them; TESTS-10 hold the four Bundle D modules pure (recommended) or drop the three names. Waiting: REMOVALS_1-2, REMOVALS_2-10, REMOVALS_1-3, REMOVALS_1-10, REMOVALS_2-13, TOOLS_BOTS-17, REMOVALS_1-11, REMOVALS_1-15, REMOVALS_2-3, REMOVALS_1-7, REMOVALS_2-5, REMOVALS_2-14, TOOLS_BOTS-23, TOOLS_BOTS-21, TESTS-10.
44. **Do hunger and fatigue come back?** Options: (a) Yes, with a played day under test; (b) no, removed in a planned change; (c) undecided, they stay off and GOALS.md says so (recommended). Waiting: REMOVALS_1-16.
45. **Data keys that promise unbuilt rules, and data facts.** Options: STARTUP_DATA-4 for each of six keys build, delete or keep reserved (reserved for stamina_recovery and siege_danger, delete the other four, recommended), and curses three or four (four); STARTUP_DATA-2 'humanoid' meant monstrous race (a) or nothing (b); STARTUP_DATA-5 the 60 unreachable creatures listed as waiting (recommended), eight homed now, or four biomes given a danger place; STARTUP_DATA-13 the two wrong lines get a data slot or new words; STARTUP_DATA-10 and TASK_FAILURE-17 the wording of one line each. Waiting: STARTUP_DATA-4, STARTUP_DATA-2, STARTUP_DATA-5, STARTUP_DATA-13, STARTUP_DATA-10, TASK_FAILURE-17.
46. **Every new line a player reads: one reading sitting per phase, in a human author's voice.** Options: Read before each phase's build: the enchant and rank offer notes (STALE_COPIES-2, TOWN_SERVICES-3), the stand-in lists (TASK_FAILURE-5, -6 incl. the act-not-yet-decided list needed before it lands), the refused-line note (SHIPPING-5), launcher messages (SHIPPING-15), the lesson script (BUDGET_FLOW-6), the night bot's templates (TOOLS_BOTS-18), the not-wearable note (TOWN_SERVICES-6), the request-or-posting question (TOWN_SERVICES-5), the hiring note (PEOPLE_TALK-8), the caster's mana line (STARTUP_DATA-10), and the fight cards and refusals that change. Waiting: STALE_COPIES-2, TOWN_SERVICES-3, TASK_FAILURE-5, TASK_FAILURE-6, SHIPPING-5, SHIPPING-15, BUDGET_FLOW-6, TOOLS_BOTS-18, TOWN_SERVICES-6, TOWN_SERVICES-5, PEOPLE_TALK-8, STARTUP_DATA-10, FIGHT_ABILITIES-10, FIGHT_ABILITIES-11.
47. **Build the multiplayer counts and moves ahead of M1?** Options: Build now since the ratchets only shrink (recommended) or leave for M1 as doc 20 planned. Waiting: FIGHT_ABILITIES-14, SITUATIONS-17, STALE_COPIES-12.
48. **Clean-up timing.** Options: When to run git worktree remove and branch -d (no session working; after play/faults is pushed); SUITE-13 run once with its saves part if TOOLS_BOTS-1 chose (a), then the script removed (recommended). Waiting: REMOVALS_2-16, SUITE-13.

## Where two workstreams meet

| Features | What they share | How it is settled |
|---|---|---|
| TASK_FAILURE-16, STALE_COPIES-10 | Both put npc/life.py _apply in one transaction and backfill collect under crashlog: the same two changes. | STALE_COPIES-10 builds them; TASK_FAILURE-16 adds only its case of a job's own error to the same backfill_test.py. Adjacent in phase 9, after TASK_FAILURE-2. |
| TOWN_SERVICES-7, TRAVEL_PLACES-8 | The same fault from two sides: void_dungeon_contracts over every board and one predicate for a posting that still stands. Their defaults disagree on postings whose floor survives a remake (TS-7 already removes 'Slay' postings, option b; TP-8 asks a, b or c). | TOWN_SERVICES-7 owns the predicate and the board helper; TRAVEL_PLACES-8 adds the telling and every character. One answer from the owner for both. Adjacent in phase 4. |
| REMOVALS_2-7, PEOPLE_TALK-13 | Both remove the temperature arguments the sampling table overrides at the same sites (banter_actions 112 and 839, mentor_actions, party_actions, quirk_actions, canon). Not declared by either. | REMOVALS_2-7 owns it with its startup check; PEOPLE_TALK-13 keeps only the owed pair line and its retry count. Adjacent in phase 18. |
| SITUATIONS-17, FIGHT_CORE-9, STALE_COPIES-12, FIGHT_ABILITIES-14, TOWN_SERVICES-9 | Five ratchets on reads of the first player. SITUATIONS-17 says engine/'s 128 ws.player reads are counted by nothing, but tools/sim/acting_character_630_test.py READS already counts them per engine file (events 28, truth 26, matters 17...). | One fence, acting_character_630_test.py: FIGHT_CORE-9 adds the fight's .player half there; SITUATIONS-17 drops its fence half and keeps the stakes.py and stay.py moves; STALE_COPIES-12 stays text in doc 20's M1 list; FIGHT_ABILITIES-14 lowers actor_632's per-directory counts; TOWN_SERVICES-9 adds its Memory count to 630. |
| STALE_COPIES-11, BUDGET_FLOW-10 | BUDGET_FLOW-10 lists moment and thread_telling among its sixteen families to move into asked_outside; STALE_COPIES-11 moves exactly those two for the arrival. | BUDGET_FLOW-10 owns the mechanism and the ratchet over the goldens' rows; STALE_COPIES-11 is built inside it first as the arrival family with its door_loc test, and BUDGET_FLOW-10's list loses those two tasks. Adjacent in phase 16. |
| TOWN_SERVICES-8, RELOAD-11 | The same function in scenes/world.py (about lines 4100 to 4152): TS-8 makes one cost and spend step for a field ability; RELOAD-11 keeps the craft boost set at 4133 and asks about the cooldown started at 4151. Both ask an out-of-fight cooldown question. | TOWN_SERVICES-8 owns the spend step; RELOAD-11 then moves the boost onto the record, with RELOAD-12's data move. Ordered TS-8, RELOAD-11, RELOAD-12 in phase 12; the two cooldown questions are answered once. |
| GATE-20, STARTUP_DATA-8 | Both define in storage/statehash.py which data folders are the game's: GATE-20 one helper listing the game's files for data_hashes and names vocab, STARTUP_DATA-8 one named exclusion list with data/tools. | STARTUP_DATA-8 owns the named list; GATE-20's vocabulary reads it. STARTUP_DATA-8 before GATE-20 in phase 6. |
| CONTRACTS-16, TYPED_LINE-2, TASK_FAILURE-11 | All three change the intent audit's model calls while doc 29 (whose R3 removes them) is pending; CONTRACTS-16's two-shape verdict and TYPED_LINE-2's part 4 (one request in place of two) are rival changes to the same calls. | Doc 29 R1 and R3 own the calls. TYPED_LINE-2 parts 1-3 are R1's measure; build at most one of CONTRACTS-16's verdict and TYPED_LINE-2 part 4, and only if R3 slips past phase 4. TASK_FAILURE-11's handler mend holds either way (phase 9). |
| GATE-21 | Doc 31 f731 (proposed) moves the building search of engine/truth.py:421-436 into engine/elsewhere.py and gives its line when the player's line names a lacking kind; GATE-21 adds a trigger on the request's own text. | If doc 31 is approved, its engine/elsewhere.py owns the search and GATE-21 is one more trigger inside it; built first, GATE-21 is moved there. |
| BUDGET_FLOW-9, RELOAD-10, REMOVALS_2-12 | The input's count kept across give_back: the same change seen from the budget and from the save; REMOVALS_2-12 edits the same lines' comments. | RELOAD-10 owns it; BUDGET_FLOW-9 adds its test case; REMOVALS_2-12 follows in the same pull request. Adjacent in phase 3. |
| BUDGET_FLOW-26, REMOVALS_1-13 | think_room against the slot's size, and NUM_CTX and DND_NUM_CTX going. | BUDGET_FLOW-26 owns it; REMOVALS_1-13 is the deletion in the same change (phase 16). |
| SHIPPING-1, STARTUP_DATA-1 | One reader of source in engine/data_check.py: SHIPPING-1's that answers None in a build, STARTUP_DATA-1's that reads once a process. | SHIPPING-1 builds the reader and 'this is a build'; STARTUP_DATA-1 adds the per-check cache and the C loader. Adjacent in phase 6. |
| GATE-5, TYPED_LINE-3, TYPED_LINE-4, PEOPLE_TALK-14 | A whole-word matcher with endings: GATE-5 builds engine/wordlist.py, TYPED_LINE-3/-4 say 'or makes it', PEOPLE_TALK-14 plans a third matcher reading at word starts. | GATE-5 owns engine/wordlist.py (phase 5); TYPED_LINE-3 and -4 read it; PEOPLE_TALK-14 uses it with a word-start mode, not a matcher of its own. |
| TYPED_LINE-5, GATE-7, STARTUP_DATA-10 | One number-word table (engine/numbers.py, data/rules/numbers.yaml), 'whichever lands first'. | TYPED_LINE-5 (phase 10) makes it; GATE-7 and STARTUP_DATA-10 (phase 13) read it. |
| RELOAD-5, RELOAD-13, TOOLS_BOTS-1 | Marker files in storage/saves.py: the game's marker and a tool's scratch marker, each read by the other. | RELOAD-5 owns the game's marker; RELOAD-13's discard and TOOLS_BOTS-1's scratch read it. Ordered RELOAD-5, RELOAD-13, TOOLS_BOTS-1 in phase 1. |
| REMOVALS_1-1, REMOVALS_2-1, REMOVALS_1-2, REMOVALS_2-10, REMOVALS_1-4, REMOVALS_2-11, REMOVALS_1-6, REMOVALS_2-8, REMOVALS_1-7, REMOVALS_2-5, REMOVALS_1-10, REMOVALS_2-13, REMOVALS_1-17, REMOVALS_2-4 | The two removals workstreams split one census and several changes between them. | REMOVALS_2-1 owns the census, 1-1 is its import sweep; 1-2 owns the names fence and KEPT table, 2-10 its sweep; 2-11 owns the seven wrappers with 1-4's tests; 1-6 removes the stat-passives step (phase 5, before CONTRACTS-5's floors) and 2-8 adds its census rule later; 2-5 owns the motive step with 1-7; 1-10 and 2-13 one change; 1-17 and 2-4 one change and one answer. |
| CONTRACTS-13, REMOVALS_2-6, PEOPLE_TALK-8 | The small readers' summary fields and party_intent's dead kinds and handlers. | CONTRACTS-13 owns PartyIntent and CombatIntent; REMOVALS_2-6 the camp half and the field fence; PEOPLE_TALK-8 deletes the handlers. One stub_party re-bless in phase 14. |
| LONG_SAVE-12, BUDGET_FLOW-17 | A helper for names near here under a cap. | BUDGET_FLOW-17 owns it; LONG_SAVE-12 uses it, after it in phase 14. |
| SUITE-7, TOOLS_BOTS-3 | simlib swap(), one stack of undoings for replays and benches. | TOOLS_BOTS-3 (phase 8) builds it; SUITE-7 (phase 20) uses it. |
| TESTS-7, SHIPPING-2 | node, playwright and the CI jobs. | TESTS-7 owns the harness and the counted skips; SHIPPING-2 the package job. One owner answer on node. |
| TOOLS_BOTS-4, REMOVALS_2-2 | Each makes 'one reader' of the call log: REMOVALS_2-2 of the file's form (read_calls), TOOLS_BOTS-4 of a row's meaning, through the same tools (card_profile, latency). | REMOVALS_2-2 (phase 1) builds read_calls; TOOLS_BOTS-4 (phase 5) builds the row reader beside it and reads files only through read_calls. |
| FIGHT_CORE-2, FIGHT_ABILITIES-1 | in_fight(f), one predicate. | FIGHT_CORE-2 owns it in engine/combat.py; FIGHT_ABILITIES-1 reads it. |
| FIGHT_CORE-3, FIGHT_ABILITIES-4 | The floors table in stages.yaml. | FIGHT_CORE-3 owns it; FIGHT_ABILITIES-4 is one more column and asks with it. |
| STARTUP_DATA-16, FIGHT_ABILITIES-13, REMOVALS_1-14 | Code-held fight numbers into data now or at the balance pass. | One owner answer; STARTUP_DATA-16 owns the move; all three in phase 19. |
| CONTRACTS-4, PEOPLE_TALK-5 | PersonaDetails: its count of details and a new list of said forms held to the same count. | CONTRACTS-4 sets the count from data first; PEOPLE_TALK-5 adds the said list on it. Adjacent in phase 15. |
| CONTRACTS-15, PEOPLE_TALK-10, REMOVALS_1-19 | The person-making request, its goal branch and its saved columns. | PEOPLE_TALK-10 owns has_motive; CONTRACTS-15 the fields; REMOVALS_1-19 the stored columns, last. |
| CONTRACTS-17 | Doc 29 R2 builds plan_contract(offered) per call by hand, as decision_contract was; CONTRACTS-17 builds the general shaped(contract, ctx) step but names only act.shape, decision_contract, many_reply and reply_contract as forms to move onto it. | CONTRACTS-17 owns per-call shaping; its design lists plan_contract too, and R2 is built after it, or the game keeps two shaping mechanisms. |

## What must come first across workstreams

| Feature | Needs | Why |
|---|---|---|
| GATE-20 | STARTUP_DATA-8 | Both define the game's data files in storage/statehash.py; the vocabulary must exclude data/tools, which STARTUP_DATA-8 creates. |
| PEOPLE_TALK-14 | GATE-5 | Its word-start matching should be a mode of engine/wordlist.py, not a third matcher. |
| SITUATIONS-17 | FIGHT_CORE-9 (acting_character_630_test.py READS) | The engine count it would add already exists there; its new code is the stakes.py and stay.py moves only. |
| STALE_COPIES-12 | acting_character_630_test.py's per-file table | Its per-file table for scenes belongs in the same one fence, not a second count in actor_632. |
| RELOAD-11 | TOWN_SERVICES-8 | Same function in scenes/world.py; the cost and spend step first, and the cooldown question answered once. |
| STALE_COPIES-11 | BUDGET_FLOW-10's asked_outside mechanism (built together) | It is that feature's arrival family; BUDGET_FLOW-10's list must drop moment and thread_telling. |
| BUDGET_FLOW-27 | BUDGET_FLOW-10 (option b only) | Option b asks populate_place outside its operation, which is BUDGET_FLOW-10's work, four phases later. |
| doc 29 R2 (f732 of plan 29) | CONTRACTS-17 | plan_contract(offered) should be built on the one shaping step, or CONTRACTS-17's design must name it. |
| BUDGET_FLOW-13 | CONTRACTS-17 | It is built with doc 29 R2, which should stand on the shaping step. |
| TOOLS_BOTS-4 | REMOVALS_2-2 | The row reader reads files through read_calls; otherwise two readers of the call log. |
| TYPED_LINE-3, TYPED_LINE-4, TYPED_LINE-5, TYPED_LINE-8, TRAVEL_PLACES-5, TRAVEL_PLACES-9, TRAVEL_PLACES-10, TOWN_SERVICES-4, TOWN_SERVICES-5 | The owner's answer to TYPED_LINE-6's question on the 17 November stop | Each changes how a repair or handler reads the typed line; only TYPED_LINE-6 and -7 ask. |
| TOWN_SERVICES-4 | A plan for doc 05 step 4 (the one resolver) | Doc 20 left step 4 for a plan of its own; this builds its carried-things half and touches more than two modules. |
| TASK_FAILURE-9 | doc 31 f732 (coordination) | Both change scenes/world.py:3665-3682, the lines about someone absent. |
| BUDGET_FLOW-15 | doc 31 f731 (one gate run) | Both change the townsperson's request and brief.yaml; measured once, before and after. |
| CONTRACTS-1 | doc 30 Part 3 (awareness) | reply_contract is where the reply in two fields would go; the f731 number is claimed by CONTRACTS-1's trial note, plan 29 R1 and plan 31. |
| BUDGET_FLOW-3 | The owner's confirmation on data/runtime/server.yaml | It adds embed numbers to a file the project forbids reading; GOALS.md still has the owner confirming what that file holds. |
| BUDGET_FLOW-26 | The owner's confirmation on data/runtime/server.yaml | It reads server.slot_ctx from that file. |
| TRAVEL_PLACES-4 | LONG_SAVE-4 (same re-bless, or accept two) | Both move stub_short and want one pass; the order puts the Word of Recall fix in phase 1 and LONG_SAVE-4 in phase 17. |
| FIGHT_SCENE-5 | LONG_SAVE-3 (same recording, or accept two) | FIGHT_SCENE-5 asks to be recorded with LONG_SAVE-3; the crash fix lands in phase 1 and the labels wait on the owner's lines. |
| TESTS-10 | FIGHT_ABILITIES-4 (sequence) | Both edit tools/purity.py; FIGHT_ABILITIES-4 lands first (phase 2) and the new write reader must keep its declared path. |
| FIGHT_SCENE-3 | RELOAD-9 | RELOAD-9 makes the yielded foe's question a standing question; FIGHT_SCENE-3's table must declare it. |
| CONTRACTS-12 | PEOPLE_TALK-14 (sequence) | Both change Sworn Enemy at creation (its tier, then its subject) in character/creation.py. |
| LONG_SAVE-6 | SUITE-2, SHIPPING-3, REMOVALS_1-12 (order) | Four features edit llm/audit.py: the logs' folder, the path helper, the one switch, then the caps. |
| STARTUP_DATA-6 | GATE-19 and REMOVALS_2-7 (order) | All three edit data/rules/sampling.yaml; one sequence avoids three hash moves colliding. |
| SUITE-1, SUITE-3, SUITE-5, SUITE-6, SUITE-8, SUITE-9, SUITE-12 | The owner's go on .claude hooks, agents, skills and CLAUDE.md | Those files are the owner's; one go for the set. |

## Findings with no action

| Finding | What it said | Why nothing is planned |
|---|---|---|
| dead-switches-12 | A1's sampling arms were measured and none kept, but the arms, DND_SAMPLING_ARM and their plumbing are still in | Refuted by the audit's own check: The verdict is in, but the owner's own row says the instrument is used again. GOALS.md:179: 'A1 measured: no arm is kept and the model-sampling row is unchanged ... so the next arm is that pair with min_p's floor under… |
| dead-switches-17 | decide_then_speak is off as shipped and awaits the owner: 386 lines and three call sites run only in tests and measuring runs | Refuted by the audit's own check: Nothing here is dead code; it is a finished feature behind a switch the plan records as waiting for the owner. The finding's facts hold: reply.yaml:8 `decide_then_speak: false`; engine/reply.py:21 on(); the npc_decide c… |
| leftovers-2 | Setup downloads Microsoft's WebView2 bootstrapper with no hash and runs it silently: the one unpinned file on a page whose header says each is checke… | Refuted by the audit's own check: The two code lines are as quoted: meravia.iss:141 adds the bootstrapper with an empty hash and :40 runs it with /silent /install. But the finding's ground, that the header says every file is checked, is a cut quote. The… |
| llm-flow-9 | think_room measures a thinking call against both slots' context (32,768) where one slot holds 16,384 | Refuted by the audit's own check: The arithmetic is as stated and I saw it: with DND_THINK_TASKS=npc_conversation and a 36,500-character request (its ceiling, data/measured/prompt_ceilings.yaml:16), think_room gave 8,192 and the body carried n_predict 1… |
| min-card-5 | The second minimum card has no profile: a Vulkan machine is priced at the 3060's rates, and by the game's own cards table the RX 7600 XT writes a fif… | Refuted by the audit's own check: The facts hold: engine/budget.py:36 reads the one profile, cards.yaml:14-15 and :19 are as quoted, no commit subject is f530, and 288/360 of 31.7 is 25.4 tokens a second (2,048 tokens = 80.8 s). But it is the owner's re… |
| min-card-8 | RE-RATE llm-hot-5: layout in the grammar is the smallest of the five savings on the minimum card, 0.46 s a line (2.1% of line time), and does nothing… | Refuted by the audit's own check: The arithmetic reproduces (2,620 lines, 0.46 s a line, 2.1%, over 45 s 171 to 146, over 60 s 17 to 15, longest 93.5 to 92.7 s, played 0.55 s and 3.0%), but only because the script prices each newline-and-indent run at O… |
| trace-threads-9 | start_for_game, stop_for_game and _GAME (the 'dormant' start before the home page) cannot run while data/rules/launch.yaml is in the tree | Refuted by the audit's own check: Not dead: a guarded fallback that runs. The script printed: launch.yaml as tracked -> screen_on()=True, reached ['Screen.begin']; missing -> screen_on()=False, reached ['start_for_game'], startup problems []; one line b… |
| unneeded-files-13 | docs/research: six sets of raw reading notes (414 KB) kept beside the report they were written for, after the decision they fed was taken | Refuted by the audit's own check: NOT DEAD: the six notes are the report's sources and are referenced as kept on purpose. docs/design/17_multiplayer_survey_and_plan.md:228 cites '(docs/research/shared_world_time/report.md, with its notes beside it)'. re… |
| unneeded-files-3 | docs/measure is 37.3 MB of the 58.5 MB tracked tree (230 of 1,349 files) and no tool or test reads any of it | Refuted by the audit's own check: The sizes are right: 230 of 1,349 tracked files, 37.3 MB of 58.5 MB (35.6 of 55.8 MiB), 54 gzipped logs 32.0 MB; no code path names them (tools/prose_measure.py takes its paths on the command line, tools/live_gate.py on… |

## Notes from the ordering

Full reasoning is in 33_audit_fix_plan/order_reasoning.md. The phase lists are in plan/work/phases.py (inside 33_audit_fix_plan/plan_scripts.zip) (it confirms all 341 keys, each exactly once). Every feature's stated Needs was parsed and checked against the order by plan/work/depcheck.py: no stated need is broken. The 13 lines it still prints are needs the features themselves call soft ('nothing', 'whichever lands first', 'option b only').

New overlaps found by reading the code: SITUATIONS-17's 'no count sees engine/ws.player' is wrong, because tools/sim/acting_character_630_test.py READS already counts them per file. TOWN_SERVICES-8 and RELOAD-11 edit one function in scenes/world.py (about lines 4100-4152). PEOPLE_TALK-13 and REMOVALS_2-7 remove the same temperature arguments. STALE_COPIES-11 is one of BUDGET_FLOW-10's families. GATE-20 and STARTUP_DATA-8 define the same statehash list.

Ways the plan pulls against GOALS.md or the ROADMAP:
(1) GOALS.md (17 Nov) says phase 4 comes next, and this plan's phases 1-7 alone are about 120 features.
(2) The 17 Nov stop on fix rounds bears on phase 10.
(3) 'Keep sampling as it is' bears on CONTRACTS-2, GATE-19(b), GATE-23, STARTUP_DATA-7(b) and BUDGET_FLOW-12(b), which also departs from GOALS.md:192's two slots.
(4) The 2026-11-04 rule that code-held fight numbers wait bears on STARTUP_DATA-16(b), FIGHT_ABILITIES-13 and REMOVALS_1-14.
(5) Other recorded decisions: births after the line (f597/f599) against BUDGET_FLOW-19(b); the f332/GOALS.md:182 ask-back against TASK_FAILURE-11; f726's switch-off rule against PEOPLE_TALK-16(b) and half of BUDGET_FLOW-15.
(6) data/runtime holds only the server's launch settings (GOALS.md:192), against SHIPPING-4 and -17. Also BUDGET_FLOW-3 and -26 touch server.yaml, which no builder may read.
(7) Doc 20 left doc 05 step 4 for a plan of its own, against TOWN_SERVICES-4. REMOVALS_1-17 and 2-4 reverse doc 20's plan for the old layout.
(8) Earlier review answers: Q28 against D7, Q20 against f420, Q15 and Q30.
(9) About 45 features move goldens on purpose and about 50 may. Batch them per phase with REMOVALS_2-2 first, and never re-record to pass.
(10) About 30 features add lines a player reads. The owner reads them first.
(11) CLAUDE.md asks for a plan first for work across more than two modules. Approving a phase can stand for its M features. The 15 L features each need a design read first.
(12) The minute on the 3060 stays an estimate from token counts until a timed night is run on a real minimum card.

Some feature pairs want one re-bless, but the crash fixes come first, so each pair costs two re-blesses unless the owner reorders: TRAVEL_PLACES-4 with LONG_SAVE-4 (stub_short), and FIGHT_SCENE-5 with LONG_SAVE-3.

The order puts the 130-file import sweep (REMOVALS_1-1) in phase 18 by the criteria. Its own workstream wanted it first, and the owner may prefer that. SUITE-3 and SUITE-14 could also be pulled to just after phase 7, since they speed every later Stop.

## What stays open after this plan

- **The minute on the 3060** is priced from token counts until a timed night is run on a real minimum card (GOALS.md asks
  for it before the budget is revisited). The card sessions of phases 5 and 13 to 16 measure on the card this machine has.
- **No coverage map.** Which engine code no test reaches is still unknown; it needs one full suite run under coverage, the
  owner's call on a free machine. Several features in phases 8 and 9 add the instruments that would show it in part.
- **The reviewers' open doubts**, each with what would settle it, are at the end of every workstream file.
- **Leftovers of the audit itself:** any folder in `saves/` named `audit_*` or `audit_plan_*` is from the audit or this
  plan and may be removed; `logs/` may hold rows from their stub runs. Neither could be checked from here.

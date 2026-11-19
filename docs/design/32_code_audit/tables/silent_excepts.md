# Silent exception handlers: every one, sorted

Second round of the audit, part `silent-excepts`. Nothing in the repository was changed. Scripts and raw output are in the audit's `work` folder (`silent_excepts_*`, `check_silent_excepts_*`).

## The scan

An ast walk over the Python files git tracks outside `tools/sim` (323 files): a handler that catches `Exception`, `BaseException` or everything, whose whole body is `pass`, `continue`, `break` or a `return` of a constant, with no call in it.

**68 handlers in 42 files**: 47 in 31 game files (core, engine, llm, npc, scenes, storage), 3 in simbot.py, 18 in 10 files under tools/. (The critic's count was 44 in 29 game files; this scan also takes a `return` of an empty list, tuple or string as a constant.)

| Sorting | game | simbot | tools | all |
|---|---|---|---|---|
| leave | 20 | 3 | 6 | 29 |
| state change, no record | 10 | 0 | 2 | 12 |
| hides a fault | 17 | 0 | 10 | 27 |

- **leave**: a guard around logging, display, an optional probe of the machine, or clean-up on the way out. A fault there costs nothing the player or the save can see.
- **state change, no record**: something the turn was writing is skipped or left half done, the turn commits, and neither crash.log, the refusals log, the turn log nor a debug line says so.
- **hides a fault**: a read or a model call that fails for any reason is taken as an answer (no lock, level 1, nobody here, an empty pack), so a programming error or a broken row looks like the world's own reply for ever.

GOALS.md line 207 (decision f449): whatever fails inside a turn is rolled back whole and *"the fault is written to logs/crash.log so it still surfaces"*. The S and H handlers are the places where neither happens.

## What was measured

Each scanned handler was watched with `sys.monitoring` (EXCEPTION_HANDLED) while 91 existing tests ran one at a time under the stub, child processes included (so the three golden sessions replayed by `golden_replay_test`, 83 typed lines, are in it): 102 processes, 3,237,391 handled exceptions in all. The list of tests is in `work/silent_excepts_trace_run3.sh`.

| Handler | times | what it caught | where |
|---|---|---|---|
| `core/updates.py:47` latest_release | 1 | OSError x1 | updates_test.py |
| `llm/audit.py:141` _record | 1 | JSONDecodeError x1 | log_rows_628_test.py |
| `storage/statehash.py:208` data_hashes | 2 | ParserError x1, TypeError x1 | datahash_split_718_test.py |

Only these three fired, all of the *leave* kind and all on purpose (a test feeds the bad input: updates_test's offline case, a non-JSON answer, datahash_split_718_test's unclosed list and its date; `check_silent_excepts_5_hash.py` shows no real data file falls back at statehash:208). **None of the 27 game handlers sorted S or H caught anything**: on the paths these tests and the goldens walk, none is hiding a live fault today, and none of the 91 tests makes one catch, so the first fault each one meets is likely to be met in play. The other 428 test files were not watched (the full suite was out of bounds for this audit). (The first two versions of the monitor also showed `llm/gateway.py:352` catching `Cancelled`; that was the monitor mistaking the lineless clean-up block of the `except ... as e` at line 251 for the handler laid out after it. The exact rule shows nothing there.)

The wider set (below) fired at three more places, all by design: `engine/asked.py:151`, `services/fight.py:320`, `storage/statehash.py:53`.

## One of each kind, made to happen under the stub

### A state change with no record (`check_silent_excepts_1_state.py`)

```
(a) engine/events.py:397-400, a job done that settles an uncommon matter at Parth
  control: matter resolved (result player); town memory ['Sheep gone from the hill (a_ok): settled by Ironbound Vanguard']; reputation at Parth 4; new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 1}; shown []
  reputation_add raises: matter resolved (result player); town memory ['Sheep gone from the hill (a_bad): settled by Ironbound Vanguard']; reputation at Parth 0; new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 1}; shown []
(b) engine/deeds.py:38-45, a persuasion that is the matter's one way to end
  control: deeds.log returned seq 3; persuade deeds kept in the save 1; matter resolved (result player); new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 1}
  save_world_state raises inside deeds.log: deeds.log returned seq 5; persuade deeds kept in the save 0; matter active (result None); new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 0}
  fence armed, no operation open: deeds.log raised None; deeds in the save 3 -> 3; the same save made directly raises WriteOutsideOperation; new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 0}
(c) storage/migrations.py:126-129, step v8 on a save whose player cannot be loaded
  player unreadable: the step raised None -> run() would mark the save v8 and report it done; the hire's pronoun in the save: (none); new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 0}
  control: the step raised None -> run() would mark the save v8 and report it done; the hire's pronoun in the save: she; new records {'crash.log entries': 0, 'refusals': 0, 'debug lines': 0}
```

### A fault hidden as an answer, an Interrupt caught, a mend half done (`check_silent_excepts_2_hidden.py`)

```
(a) scenes/law_actions.py:398-401, the typed line: 'I pick the lock on the cellar door'
  the judging answers (a lock is plausible):
    the player reads: ['Lock: strong success']
    locks at the place: ['the cellar door']; turn() returned True; new records {'crash.log entries': 0, 'refusals': 0}
    debug lines naming a fault: []
    turn log row: {'text': 'I pick the lock on the cellar door'}
    refusal rows filed: []
  the judging raises AttributeError:
    the player reads: ['There is no lock here that you can find.']
    locks at the place: []; turn() returned True; new records {'crash.log entries': 0, 'refusals': 1}
    debug lines naming a fault: []
    turn log row: {'text': 'I pick the lock on the cellar door'}
    refusal rows filed: [('refused', 'unlock: There is no lock here that you can find')]
    crash.log on disk: 0 characters
(b) an Interrupt (llm.errors.Cancelled) raised inside the guarded call
  invent_lock: returned None (the Interrupt did not pass; the caller goes on to refuse 'There is no lock here that you can find.')
  is_challenge('Face me, one on one.') with the embed call cancelled: returned True (by the word list; the Interrupt did not pass)
  is_challenge('Lovely weather for it.') with the embed call cancelled: returned False (by the word list; the Interrupt did not pass)
(c) llm/gateway.py:368-372, the dash mend raising on the second prose field of a taken answer
  control: text 'The gate, old oak, stands shut.'; detail 'A latch, rusted, holds it.'; new records {'crash.log entries': 0, 'refusals': 0}
  undash raises on the second field: text 'The gate, old oak, stands shut.'; detail 'A latch — rusted — holds it.'; new records {'crash.log entries': 0, 'refusals': 0}
```

### A failed read taken as an answer (`check_silent_excepts_4_reads.py`)

```
(a) engine/events.py: the player's saved row cannot be read
  control: player_level 9; _player_in('parth') True
  load_player raises: player_level 1; _player_in('parth') False; crash.log entries 0
(b) scenes/audit_actions.py:66-71, the scene lines the audit's reader is given
  control: 'Pack: copper dagger.'
  inventory.label raises: 'Pack: empty.'; crash.log entries 0
(c) scenes/road_actions.py:252-258, who walks the road with the player
  control: road_company() ['Brannoch Vale: she - a hired striker, travelling with the player']
  who_is_who raises: road_company() []; crash.log entries 0
  the same call as scenes/world.py:3074 makes it, with no guard: raises AttributeError (the operation rolls back and crash.log has it)
```

### A guard around logging or display (leave) (`check_silent_excepts_3_display.py`)

```
(a) engine/pulse.py:777-780, an effect whose pulse-log row raises
  effects in the state before 0, after 1; crash.log entries 0
(b) llm/gateway.py:411-415, the debug line of a rejected try raises
  tries 2; the answer taken: 'The gate stands shut.'; crash.log entries 0
```

In every faulted case the count of crash.log entries is unchanged and no debug line names the fault. In check 2a the refusals log does gain a row, but it is the ordinary `refused: unlock: There is no lock here that you can find`, the same row a true 'no lock' writes.

## The fix for the class

One helper in `engine/crashlog.py`, beside `record()` (the module's first line is already 'where a fault goes when the game goes on without it'):

```python
@contextmanager
def carried(where: str, **context):
    """What is guarded may fail without costing the turn: the fault is written down and the game goes on."""
    try:
        yield
    except Interrupt:                 # core/interrupts.py: a cancel, a replay that parted: never a fault
        raise
    except Exception as e:
        once(e, where, **context)     # record(), but one entry per (where, error type) a session, then a count
```

- `once` matters: crash.log keeps the last 50 entries (config.CRASH_KEEP), and a fault in a mend that runs on every model call would push every other entry out in one turn. A small capped dict of (where, type) seen this session, with a count, keeps the store bounded.
- It lets `Interrupt` through, which eight of today's handlers do not (silent-excepts-4). `NeedAnswer` and `Drift` are BaseException and pass any of this already.
- A replay already counts the growth of `crashlog.SESSION` as `crashed` (tools/rerun.py:372 and 468), so a carried fault shows in a golden's result with no further work.
- crashlog imports only `config` and `engine.actor`, so `llm/gateway.py`, `storage/migrations.py` and `npc/backfill.py` can import it (the gateway already imports engine modules inside its functions).

Sites that need more than the helper (the *fix* column says which):

- **remove the try**: inside an operation the executor already does the right thing with a fault (rolled back, crash.log, a line to the player). `engine/deeds.py:44`, `engine/canon.py:296`, `scenes/dungeon_actions.py:191`, the three `relevance.pick` guards (the fallback they exist for is inside `pick`), `engine/events.py:102` and `:1207`, `engine/moments.py:53` and `:86`, `scenes/road_actions.py:257`, `scenes/quirk_actions.py:256`, `scenes/audit_actions.py:70`, `scenes/banter_actions.py:432`.
- **narrow to the one expected error**: `scenes/law_actions.py:249` and `:400` and `engine/field.py:98` to `LLMError` (the gateway has filed it); `scenes/law_actions.py:475` and `scenes/audit_actions.py:58` to `FileNotFoundError`; `engine/mentor.py:218` and `:229` to `KeyError`.
- **ask first**: `storage/migrations.py:101` and `:128` (`store.player_exists()`), `engine/events.py:399` (`th['place'] in world.places`, as line 719 does).
- **the helper as it is**: `engine/events.py:399`, `:723`, `:1443`; `llm/gateway.py:371`, `:379`; `engine/phantoms.py:102`; `scenes/passive_hooks.py:361`; `npc/backfill.py:91` (with people-7's transaction); and, from the wider set, `engine/pulse.py:773`, `engine/session.py:169` and `:179`, `llm/embed.py:79`.
- **tools**: no helper; a measuring tool should stop or print, never report a zero it did not measure.

A test for the class, on a case other than the ones that found it: a tools/sim test that walks the same ast scan and fails on any broad handler whose body neither records nor re-raises, with the *leave* list written out as its allowed exceptions (each with its reason).

## Every handler

`fired` is the count from the 91 watched tests. `first round` names a finding already in all.json.

### Game files

| # | handler | body | what the try guards | what can raise | what is skipped or already changed | sorting | fix | fired | first round |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `core/updates.py:47` latest_release | `return None` | the release check's download and JSON, on a daemon thread | network, bad JSON | nothing | **leave** | leave (could narrow to OSError, ValueError) | 1 |  |
| 2 | `core/updates.py:107` _leave | `pass` | runtime.stop_for_game() just before os._exit(0) | anything in stopping the server | the installer is about to run; a fault leaves the server to the OS job object | **leave** | helper is free here (one record before the exit) | 0 | llm2-5, trace-threads-7, dead-switches-5 (what it stops) |
| 3 | `engine/canon.py:296` journal | `pass` | the journal row's write | TypeError from json.dumps, WriteOutsideOperation, sqlite | the fact is not journaled; towns.py, truth.py and world.py read the journal later | **state change, no record** | remove, or helper | 0 | engine2-7 |
| 4 | `engine/combat_perks.py:695` is_challenge | `pass` | relevance.pick (an embed call) for 'is this a challenge' | Interrupt (Cancelled, Parted); KeyError on perks data. Never 'no helper model': pick falls back to words by itself | nothing; the word list answers | **hides a fault** | remove the try | 0 |  |
| 5 | `engine/deeds.py:44` log | `pass` | load world state, add the deed, save | TypeError (a value json cannot write), WriteOutsideOperation, sqlite | the deed is lost; the caller is handed a deed with a seq that is not in the save, and after_deed runs on it | **state change, no record** | remove (the operation rolls back), see silent-excepts-2 | 0 |  |
| 6 | `engine/events.py:102` player_level | `return 1` | store.load_player().character.level | a player row that does not validate | the pulse sizes a cataclysm and a boss for level 1 | **hides a fault** | remove (player_exists is asked on the same line) | 0 |  |
| 7 | `engine/events.py:399` after_deed | `pass` | ws.reputation_add for a job that settled a normal or uncommon matter | KeyError when the matter's place is not on the map (the one expected case); any fault in reputation_add or doors.yaml memory.reputation | the matter is ended and remembered; the town's thanks are skipped | **state change, no record** | ask (`if th['place'] in world.places`, as line 719 does) then helper | 0 |  |
| 8 | `engine/events.py:723` finish | `pass` | ending_share lookup and ws.reputation_add, per town hit | KeyError on a kind missing from doors.yaml ending_share; any fault in reputation_add (a Famous character's spread can stop half way) | the event is ended, the deed and news written; thanks skipped for that town | **state change, no record** | helper | 0 |  |
| 9 | `engine/events.py:1207` _player_in | `return False` | town_of(store.load_player().location) == town | a player row that does not validate | False: the town's fate is rolled instead of fought at the gate (lines 1153, 1225, 1401) | **hides a fault** | remove | 0 |  |
| 10 | `engine/events.py:1443` assault_over | `pass` | ws.reputation_add(town, held_reputation) after a gate held | any fault in reputation_add | town_outcome and the save are done, GateHeld noticed; the player reads 'You kept the gate.' with no thanks | **state change, no record** | helper | 0 |  |
| 11 | `engine/mentor.py:218` build_of | `pass` | items.base_of(weapon).reach | KeyError for a base the catalog lacks | Maren takes the character for a melee fighter | **hides a fault** | narrow to KeyError | 0 |  |
| 12 | `engine/moments.py:53` _town_last | `pass` | store.load_place(pid).moment_last, per place of the town | nothing expected: load_place returns an empty state for a missing row | the town's gap between moments is not kept for that place | **hides a fault** | remove the try | 0 |  |
| 13 | `engine/moments.py:86` choose | `continue` | law.current_heat(ws.player, ...) for a shape that needs heat | any fault in current_heat | the shape is never chosen | **hides a fault** | remove the try | 0 |  |
| 14 | `engine/phantoms.py:102` found | `return ''` | the scene's roster callback (creatures_here) | any fault in the scene's read | the check that a passage shows no creature the place lacks is skipped for that passage, and every one after | **hides a fault** | helper | 0 |  |
| 15 | `engine/pulse.py:779` apply_effects | `pass` | the pulse log's row for an effect | OSError, a describe() fault | nothing: the effect is already applied (shown: check 3a) | **leave** | leave | 0 |  |
| 16 | `engine/recording.py:66` commit | `return ''` | git rev-parse HEAD for a recording's meta | no git, timeout | nothing | **leave** | leave | 0 |  |
| 17 | `engine/threads.py:608` problems | `pass` | importing engine.moments inside the startup data check | an import fault (the game would not start anyway) | the 'scene is a moment shape' check is skipped | **leave** | leave | 0 |  |
| 18 | `engine/turnlog.py:210` _trim | `pass` | trimming the turn log | OSError (trim_log already catches it) | nothing | **leave** | leave | 0 |  |
| 19 | `engine/turnlog.py:222` session_stats | `pass` | reading the gateway's tallies for the session's stats row | an import fault | nothing | **leave** | leave | 0 |  |
| 20 | `engine/turnlog.py:229` session_stats | `pass` | reading the refusals for the session's stats row | an import fault | nothing | **leave** | leave | 0 |  |
| 21 | `engine/world_improv.py:29` read_effect | `pass` | relevance.pick (an embed call) for the improvised effect | Interrupt; re.error on a `needs` pattern. Never 'no helper model' | nothing; the word fallback answers | **hides a fault** | remove the try | 0 |  |
| 22 | `llm/audit.py:141` _record | `pass` | pretty-printing the raw answer as JSON for the audit page | JSONDecodeError (expected: fired once in log_rows_628_test) | nothing | **leave** | leave (narrow to ValueError) | 1 | llm1-2 (the function around it) |
| 23 | `llm/backend.py:475` _source_has | `return None` | making the source to ask whether it has a method | a malformed DND_LLAMA_URL (written down as the reason, f523) | nothing: the calls themselves then fail loudly | **leave** | leave | 0 |  |
| 24 | `llm/gateway.py:212` generate | `pass` | filing the refusal row for a call that gave up | a refusals-log fault | nothing: the LLMError is raised right after | **leave** | leave | 0 |  |
| 25 | `llm/gateway.py:352` _generate | `pass` | filing the 'guarded' refusal row | a refusals-log fault | nothing: the reason is already set | **leave** | leave | 0 |  |
| 26 | `llm/gateway.py:371` _generate | `pass` | hygiene.undash_answer on an answer already taken (the owner's no-dash rule) | any fault in the mend, on any field | fields mended before the fault keep the mend, the rest go to the player as written (shown: check 2c) | **state change, no record** | helper | 0 |  |
| 27 | `llm/gateway.py:379` _generate | `pass` | names.mend_answer and the per-task count of mends (A1 reads it) | any fault in the mend | names half mended; the count not taken | **state change, no record** | helper | 0 |  |
| 28 | `llm/gateway.py:414` _debug | `pass` | the debug line of a rejected try | a console fault | nothing (shown: check 3b) | **leave** | leave | 0 |  |
| 29 | `llm/runtime.py:270` _pdeathsig | `pass` | prctl on Linux | no libc, not Linux | nothing | **leave** | leave | 0 |  |
| 30 | `llm/runtime.py:958` _load | `pass` | the load screen's on_ready callback (the slow-machine warning) | a page fault | the model is loaded; the warning may not show | **leave** | leave (helper is free here) | 0 |  |
| 31 | `llm/runtime.py:1022` _wait_ready | `pass` | the loading line callback | a page fault | nothing | **leave** | leave | 0 |  |
| 32 | `llm/setup_check.py:23` ram_gb | `return 0.0` | reading the machine's memory | platform call missing | 0.0, which the caller reads as unknown | **leave** | leave | 0 |  |
| 33 | `llm/worker.py:78` _strict | `return False` | importing engine.streams to read STRICT | an import fault | False: background calls are let run as in live play | **leave** | leave | 0 |  |
| 34 | `npc/backfill.py:91` collect | `pass` | life._apply of a finished background batch | any fault part-way through the residents | people saved who stand in no place's residents; the place asks again | **state change, no record** | helper plus one transaction (people-7) | 0 | people-7, trace-threads-1 |
| 35 | `scenes/audit_actions.py:58` people_at | `continue` | store.load_npc of a resident | FileNotFoundError for a row that is gone; a row that does not validate | that resident is left out of who can be aimed at | **hides a fault** | narrow to FileNotFoundError | 0 |  |
| 36 | `scenes/audit_actions.py:70` pack_names | `return []` | the labels of the pack, for the audit reader's scene lines | any fault labelling ONE item | the reader is told 'Pack: empty.' (shown: check 4b) | **hides a fault** | remove the try | 0 |  |
| 37 | `scenes/banter_actions.py:432` party_news | `return []` | pulse.news_for with a stand-in person | AttributeError when the world state is None or news_for reads a field the stand-in lacks | the party never brings up news | **hides a fault** | remove (load `or {}`) | 0 |  |
| 38 | `scenes/combat_scene.py:140` read_effect | `pass` | relevance.pick (an embed call) for the fight's improvised effect | Interrupt. Never 'no helper model' | nothing; effect_by_words answers | **hides a fault** | remove the try | 0 |  |
| 39 | `scenes/dungeon_actions.py:191` void_dungeon_contracts | `pass` | load, filter and save the board where the player stands | nothing expected (load_place cannot fail on a missing row); WriteOutsideOperation | the held contracts are already closed; the stale posting stays | **state change, no record** | remove (scenes1-13) | 0 | scenes1-13 |
| 40 | `scenes/law_actions.py:400` invent_lock | `return None` | judge_object (the plausible_object model call, made inside the operation) | LLMError (already filed by the gateway); Interrupt; any fault building the request | the player is told 'There is no lock here that you can find.' (shown: check 2a) | **hides a fault** | narrow to LLMError | 0 |  |
| 41 | `scenes/law_actions.py:475` on_answer_law | `return None` | store.load_npc of the guard who asked | FileNotFoundError; a row that does not validate | the watch's question is let go; `confronted[town]` is already set for the day, so no guard asks again | **hides a fault** | narrow to FileNotFoundError | 0 |  |
| 42 | `scenes/passive_hooks.py:361` tavern_ear | `pass` | ensure_board (may post the board anew) for Tavern Ear | any fault in the board's refresh; Interrupt when the refresh asks the model | nothing half written (the save is the refresh's last line); the paid-for talk leaves the board out | **hides a fault** | helper | 0 |  |
| 43 | `scenes/quirk_actions.py:256` gesturers | `pass` | whether Maren is with the party, and her gestures | any fault in mentor_with_you | her gestures do not count against a new one | **hides a fault** | remove the try | 0 |  |
| 44 | `scenes/road_actions.py:257` road_company | `return []` | entities.who_is_who for the road's telling | any fault in who_is_who (six other callers have no guard) | the telling is given nobody (shown: check 4c) | **hides a fault** | remove the try | 0 |  |
| 45 | `storage/invariants.py:32` known_places | `pass` | reading the discoveries for the checker's list of known places | a save from before discoveries (written down as the reason) | the checker then reports more, not less | **leave** | leave (narrow) | 0 |  |
| 46 | `storage/migrations.py:128` _v8_hire_pronouns | `return` | store.load_player in step v8 | ValidationError: no player yet (expected), or a player row that does not read | the step returns; run() marks the save v8 (shown: check 1c) | **state change, no record** | ask (`if not store.player_exists(): return`) | 0 |  |
| 47 | `storage/statehash.py:208` data_hashes | `pass` | splitting a wording-listed data file for the two hashes | a file that is not YAML (expected: fired twice in datahash_split_718_test) | the file is hashed whole instead, the stricter way | **leave** | leave | 2 |  |

### simbot.py

| # | handler | body | what the try guards | what can raise | what is skipped or already changed | sorting | fix | fired | first round |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `simbot.py:570` gear_pass | `continue` | items.base_of for a pack item (the balance bot) | KeyError | the item is skipped | **leave** | leave (narrow to KeyError) | 0 |  |
| 2 | `simbot.py:630` buy_pass | `continue` | items.base_of for a ware (the balance bot) | KeyError | the ware is skipped | **leave** | leave (narrow to KeyError) | 0 |  |
| 3 | `simbot.py:1752` run | `pass` | a recovery wait after a fault the bot has already noted | the same fault again | nothing | **leave** | leave | 0 | shell1-5 (the loop has no test) |

### tools/

| # | handler | body | what the try guards | what can raise | what is skipped or already changed | sorting | fix | fired | first round |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `tools/acceptance.py:144` made | `return 0` | ledger.count('made') | any fault in the ledger read | 0: a step expecting 'nothing made' passes without looking | **hides a fault** | remove the try | 0 |  |
| 2 | `tools/event_eval.py:148` evaluate | `pass` | model_calls(gateway.OUTCOMES) for the summary | any fault (it hid one until f519: the docstring at line 41 says so) | the summary lacks model_calls | **hides a fault** | remove the try | 0 |  |
| 3 | `tools/eventrun.py:294` zone_for | `continue` | encounters.ensure_roster for a zone | any fault | the zone is skipped | **hides a fault** | narrow or remove | 0 |  |
| 4 | `tools/eventrun.py:631` main | `pass` | reload_after_rollback after an error the run already printed | the same fault | nothing more | **leave** | leave | 0 |  |
| 5 | `tools/eventrun.py:638` main | `pass` | the run's last save of the player, in finally | any fault | the run's final state is not saved, and the summary is written as if it were | **state change, no record** | print the fault | 0 |  |
| 6 | `tools/latency.py:162` _yaml | `return {}` | reading a YAML file for the report | missing file, bad YAML | {}: the report shows no ceilings | **hides a fault** | narrow to OSError, YAMLError | 0 |  |
| 7 | `tools/lora_eval.py:98` score | `pass` | schema.model_validate_json, to score 'does it fit' | ValidationError (the thing measured) | fits stays 0 | **leave** | leave (narrow to ValidationError) | 0 |  |
| 8 | `tools/nightbot.py:205` state | `return {}` | store.load_world_state() | any fault | {}: the bot sees no matters | **hides a fault** | remove the try | 0 |  |
| 9 | `tools/nightbot.py:755` goal_follow | `pass` | events.path_met for a goal | any fault in path_met | the path is taken as not met and pursued again | **hides a fault** | remove the try | 0 |  |
| 10 | `tools/nightbot.py:803` path_done | `return False` | events.path_met for a goal | any fault in path_met | False: the goal never counts as done | **hides a fault** | remove the try | 0 |  |
| 11 | `tools/nightbot.py:913` where_lives | `continue` | encounters.ensure_roster for a zone | any fault | the zone is skipped | **hides a fault** | narrow or remove | 0 |  |
| 12 | `tools/nightbot.py:960` contract_to_take | `return None` | ws.ensure_board() (may ask the model) | any fault; Interrupt | None: the bot takes no contract | **hides a fault** | remove the try | 0 |  |
| 13 | `tools/nightrun.py:260` last_outcomes | `return []` | ledger.last() for the night's turn row | any fault | []: the row says the engine did nothing that turn | **hides a fault** | remove the try | 0 |  |
| 14 | `tools/nightrun.py:714` main | `pass` | reload_after_rollback after an error the run already printed | the same fault | nothing more | **leave** | leave | 0 |  |
| 15 | `tools/nightrun.py:719` main | `pass` | the night's last save of the player, in finally | any fault | the night's final state is not saved, and the summary is written as if it were | **state change, no record** | print the fault | 0 |  |
| 16 | `tools/suite_ran/sitecustomize.py:53` opened | `pass` | the suite's own audit hook | anything | nothing: a hook must never break the test it watches | **leave** | leave | 0 |  |
| 17 | `tools/think_ab.py:297` card_seconds | `return None` | a division by the card profile's speeds | a missing key, zero | None in the report | **leave** | leave | 0 |  |
| 18 | `tools/voice_report.py:47` load | `continue` | json.loads of a logged answer | bad JSON | the row is skipped | **leave** | leave | 0 |  |

## The wider set: broad handlers that set a default or write only a debug line

Not in the scan's definition, but the same question. 39 in game files and simbot.py. Sorted in one line each; only the ones marked S or H belong with the class.

| handler | body | sorting | note | fired |
|---|---|---|---|---|
| `character/creation.py:108` _run | `self.error = e` | leave | keeps the error for the thread's reader | 0 |
| `core/updates.py:131` install | `return f'{type(e).__name__}: {e}'` | leave | returns the error text to the page | 0 |
| `engine/asked.py:151` call | `result, error = (None, e)` | leave | by design: kept and raised again by kind (fired 3 times in the tests watched) | 3 |
| `engine/data_check.py:372` check | `broken.append(f'{f.relative_to(ROOT).as_posix()}: {e}')` | leave | reported as a startup problem | 0 |
| `engine/data_check.py:543` check | `need(False, f'the scene cannot be imported to check the action registr` | leave | reported as a startup problem | 0 |
| `engine/data_check.py:831` check | `need(False, f'name_sounds.yaml {people} {kind}: {e}')` | leave | reported as a startup problem | 0 |
| `engine/events.py:955` _leaders | `console.debug(f'war leaders: could not populate {spot.id} ({err})')` | hides a fault | a debug line only; also catches an Interrupt around populate_place's model call (silent-excepts-4) | 0 |
| `engine/field.py:98` classify | `answers = {}` | hides a fault | answers = {}: any fault, and an Interrupt, become the keyword fallback (silent-excepts-4); narrow to LLMError | 0 |
| `engine/mentor.py:229` empty_handed | `return weapon is None` | hides a fault | unknown base: narrow to KeyError | 0 |
| `engine/pulse.py:773` apply_effects | `console.debug(f"pulse: dropped effect {e.get('kind')} ({err})") ; resu` | state change, no record | 'an effect the world can't honor is simply dropped': kept in the pulse log row and a debug line, never in crash.log; the helper would add it | 0 |
| `engine/session.py:169` begin_turn | `held[k] = v` | hides a fault | a scene cache that cannot be deep-copied is kept by reference, so a rollback does not put it back; never fired in the tests watched; record it once | 0 |
| `engine/session.py:179` begin_turn | `rolled[k] = home[k]` | hides a fault | the same for the scene's declared state (ROLLED) | 0 |
| `engine/stakes.py:224` _open_matter | `paths = []` | hides a fault | an invalid path from the model becomes no path: narrow to ValidationError | 0 |
| `engine/threads.py:283` _effect | `console.debug(f'threads: dropped a templated effect ({err})') ; return` | leave | a debug line; data_check covers the template before play | 0 |
| `llm/audit.py:38` enabled | `return bool(A.get('enabled', True))` | leave | falls back to the data file's switch | 0 |
| `llm/embed.py:79` vectors | `_state['failed'] = True ; return None` | hides a fault | one failed embed call turns the helper off for the session, with no record anywhere (pinned by embed_test.py:56; docs/design/17:130): record it once | 0 |
| `llm/launch.py:277` run | `self.error = e` | leave | keeps the error for the load screen | 0 |
| `llm/launch.py:368` _could_not_wake | `ram = 0.0` | leave | memory unknown | 0 |
| `llm/runtime.py:113` runtime_problems | `known = set()` | leave | the slot_of check is skipped when the budget table cannot be read | 0 |
| `llm/runtime.py:181` needed_context | `chars = 36500` | hides a fault | the server's context is sized from 36500 characters when the measured ceilings cannot be read, with no record | 0 |
| `llm/runtime.py:185` needed_context | `cpt = 4.0` | hides a fault | the same for chars_per_token (4.0) | 0 |
| `llm/runtime.py:319` _run | `box['error'] = e` | leave | keeps the error for the caller | 0 |
| `llm/runtime.py:1047` _died | `self.state = 'failed'` | leave | marks the runtime failed | 0 |
| `main.py:87` play | `console.out(f'The llama-server at DND_LLAMA_URL could not be reached (` | leave | told to the player | 0 |
| `npc/backfill.py:51` run | `job['error'] = err` | state change, no record | kept on the job, which collect() then drops (people-7) | 0 |
| `scenes/audit_actions.py:200` ask_back | `console.debug(f'clarify: no question ({e})')` | hides a fault | a debug line; also catches an Interrupt around the clarify call (silent-excepts-4) | 0 |
| `scenes/goddess.py:218` show | `console.debug(f'creation page: {e}')` | leave | a creation page that cannot be drawn: debug line | 0 |
| `scenes/law_actions.py:249` create_object | `verdict = ObjectVerdict(plausible=False, reason='nothing turns up')` | hides a fault | 'nothing turns up' for any fault (silent-excepts-5): narrow to LLMError | 0 |
| `scenes/world.py:1497` asked_operation | `serve.answers.append((need.key, None, e))` | leave | by design: kept and served back to the operation | 0 |
| `scenes/world.py:3887` reach_of | `ground = []` | hides a fault | what lies on the ground reads as nothing when one label fails: a prompt input | 0 |
| `scenes/world.py:3891` reach_of | `heat = ''` | hides a fault | the town's heat reads as none | 0 |
| `services/fight.py:320` resume | `return (None, '', f'{type(e).__name__}: {e}')` | leave | returns why; the caller writes crash.log 'fight row' (scenes/combat_scene.py:306). Fired 5 times in fight_service_503_test | 5 |
| `simbot.py:559` score | `return float(items.price(it))` | leave | the balance bot | 0 |
| `simbot.py:1726` check_invariants | `self.violation('unknown_item_base', it.name)` | leave | the balance bot notes a violation | 0 |
| `simbot.py:1852` finish | `summary['survey_error'] = repr(e)` | leave | kept in the summary | 0 |
| `storage/migrations.py:101` _v6_maren_voice | `player = None` | state change, no record | step v6 goes on with player None when the row does not read (silent-excepts-7) | 0 |
| `storage/statehash.py:53` dump | `rows = []` | leave | 'an older save without that table': fired 130 times in 3 tests (no such table: players); narrow to sqlite3.OperationalError | 130 |
| `storage/statehash.py:237` wording_problems | `bad.append(f'wording.yaml {rel}: cannot be read as data ({e})') ; cont` | leave | reported as a wording problem | 0 |
| `ui/gui/__init__.py:64` _window | `reason = f'could not open a window: {e}'` | leave | the reason is shown | 0 |


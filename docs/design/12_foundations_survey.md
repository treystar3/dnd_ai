# Map: the foundations bundle (M0 + TurnContext, world_state steps 1 and 6)

Read-only survey check. I re-read the code behind every HIGH site below; where I only carry the survey's line numbers I say "survey". No test was run.

## 0. Four findings that shape the plan

1. **M0 as written cannot "replay exactly" if it adds the players table.** The data hash includes the schema version (storage/statehash.py:124; owner's decision GOALS.md:145), golden_replay_test fails on "data hash differs" (tools/sim/golden_replay_test.py:31-32), and two more tests pin the golden's hash (tools/sim/budget_data_459_test.py:94, tools/sim/isolation_456_test.py:126). Any new migration (storage/migrations.py:297-316) forces a re-bless of all three metas, and moving kv['player'] also moves the `kv` and `all` digests (storage/statehash.py:20-27). Everything else in M0 and step 1 can be done with no migration and no data/ edit.
2. **The goldens are a thin gate for the world_state work.** Across all three recordings world_state changes in 6 of 83 inputs (stub_short 4, stub_fight 1, stub_party 1); threads move in 2, deeds in 2, effects in 3, news in 4. All three start with 0 threads, deeds, news and effects, and stub_short has no world_state row at start (read from data/replay/sessions/*/start.db and turns.jsonl `rows`). "Recordings exact" proves little for step 1 or step 6; the 44 tools/sim files that touch world_state are the real gate, and none compares old against new storage.
3. **A live lost write sits in the path step 6 changes.** events.finish logs the 'settled' deed through deeds.log, which loads and saves its own copy of the row (engine/events.py:547, engine/deeds.py:29-36); both callers of finish return into after_deed, which then saves its older copy over it (engine/events.py:416, 494-495, 422). The settled deed and its seq tick are lost in play. consequences.yaml's renown_campaign rule counts exactly those deeds (data/rules/consequences.yaml:33-34, engine/consequences.py:47). A deeds table would silently start keeping them.
4. **The rollback contract is "lives in WorldScene.__dict__".** begin_turn deep-copies every `_` key and every ROLLED name found in scene.__dict__ (engine/session.py:183-199); rollback deletes and restores the same (engine/session.py:215-222). A field moved behind a facade property drops out of both without any error.

## 1. Survey claims checked and corrected

| Claim | Result |
|---|---|
| data/rules/card_profile.yaml | Wrong path. It is data/measured/card_profile.yaml, outside the data hash (storage/statehash.py:120). data/rules has cards.yaml only. |
| session._owned() lists 21 bindings | 19 entries (engine/session.py:53-78). |
| "A deed has no actor" | Half wrong. Bus deeds carry `by` since f547 (engine/reactions.py:133-134). Only the two 'settled' writers lack it (engine/events.py:547, engine/starts.py:149). |
| combat.yaml effects_keep clashes with a v15 table | No SQL table exists. v15 only drops an old fight row (storage/migrations.py:255-261); the save has six tables (storage/campaign.py:167-204). The clash is in names only (engine/effects.py against a world `effects` table). |
| world_state keys beyond empty_state: seq, road_marks, moments_seen, rulings | More than listed. Also assaults (engine/events.py:988, 1186), fallen (events.py:1072), queued and pressure_heat (engine/threads.py:379, 389), consequence_last (engine/consequences.py:85), drift_cursor (engine/drift.py:91), door_log (engine/matters.py:236), motive_last (engine/pulse.py:705), reach_quiet_since (pulse.py:228), situation_people and parts_ended (engine/situation_parts.py:54, 1480). |
| advance_quiet writes the clock | It only calls advance (scenes/world.py:218-219). The in-play writers are scenes/world.py:363, 371 and engine/starts.py:67. |
| "ContextVar not inherited by threads in 3.12" | True here too: the interpreter is 3.14.6 with sys.flags.thread_inherit_context = 0. It flips on free-threaded builds, so pass the context explicitly. |
| simbot is unpinned | Wrong, as the survey itself found: tools/sim/simbot.py:1-11 loads the root module for nine tests. |
| Counts | Confirmed by grep: self.player 1,141, ws.player 173, console calls 907, .acting 281, WorldScene( 133. Doc 08's 1,078 and 670 are stale (docs/design/08_multiplayer_implementation_plan.md:85, 91). |
| pulselog trim after a stood-down attempt cannot work when full | Confirmed: deque(maxlen=400) (engine/pulselog.py:8) trimmed by length (scenes/world.py:1237-1239). Diagnostic only. |
| data/runtime/server.yaml | Still unread: permission to data/runtime is denied in this session too. Outside the data hash. |

Nothing was dropped as wrong beyond these corrections.

## 2. The map, by what the sites are

### A. The replay gate (what "exactly" is measured by) — HIGH
- Per input the replay compares: state digest, ledger.LAST, the committed operations by meta.steps, operation.PRESENTED, and the shown-words hash (tools/rerun.py:399-418; recorder side engine/recording.py:269-275).
- The shown hash is taken from the arguments passed to `console.<name>` module attributes, replaced by rerun (tools/rerun.py:372-374) or wrapped by the recorder (engine/recording.py:173-188). It never sees stdout.
- Replay opens a copy of start.db through CampaignSession.open, so migrations run on it (tools/rerun.py:385-391; storage/campaign.py:285). All three start.db are at v16.
- Rollback coverage in the goldens: one failed-every-try call each (ActionPlan in stub_short, NPCReply in stub_party, CombatIntent and Narration in stub_fight, one stand_in presented).
- Pins on the table list: tools/sim/isolation_456_test.py:124, tools/sim/operation_record_462_test.py:171-172 (also pins "operation.CURRENT" in _owned at :175).
- rerun leaves console bindings, config paths and life.FIRST_BATCH changed after a replay (tools/rerun.py:354-361, 440, 447-458).

### B. Console and output — HIGH
- Bodies print to sys.stdout (ui/console.py:13-72). Six layers stack by setattr on the module: the hygiene gate (ui/console.py:649-670), the recorder (engine/recording.py:171-188), turnlog.tap (engine/turnlog.py:162-173), the operation hold (scenes/world.py:1088-1109), questions.fence (survey: engine/questions.py:75-88), the GUI bridge (ui/gui/bridge.py:263-276).
- The bridge and several tools capture stdout whole (ui/gui/bridge.py:268; survey: simbot.py:67, tools/interp_eval.py:211).
- Safe shape for M0: keep module-attribute dispatch, change only what `print` writes to, and have the default channel resolve sys.stdout at call time. Anything that bypasses the module attribute moves the shown hash.
- Writes with no actor: start-up, home page, creation and crash lines (main.py:81, 100, 105, 113-115, 137, 147, 183-202); creation runs under an open session before a player exists (main.py:145-156).
- Held calls replayed by name (scenes/world.py:1123; survey: 802-805, 1164); saved presentation entries carry no actor (storage/campaign.py:549-551).
- turnlog.SHOWN is a process counter that decides the "silent turn" refusal (scenes/world.py:1466, 1577-1580; engine/turnlog.py:146-153). It is not in _owned.
- Process flags read by the game: console.damage_tags, console.WIDTH (ui/console.py:9, 75; scenes/world.py:1101).

### C. Dice — HIGH
- One process key `seed:step:said` for every stream, plus a reseed of the global random module (engine/streams.py:33-40); snapshot and restore include the global state (streams.py:86-102).
- Seeded at scenes/world.py:760 ("#start") and :974; snapshotted around asked re-runs (scenes/world.py:1212, 1228).
- Held references that a per-actor object would strand: WorldScene.rng (scenes/world.py:132), engine/spellcraft.py:25 (import time, used at 606-1107), and per survey scenes/combat_scene.py:128, 151, services/fight.py:187, npc/life.py:345.
- Operation ids draw from the "ops" stream (engine/operation.py:101).
- No test pins the key string; the goldens and the fight fixtures do it indirectly (survey: tools/sim/fight_fixtures.py:148, 204).
- Clock-keyed seeds that read ws.minutes or ws.player.location: survey list (engine/matters.py:256, engine/stakes.py:63, engine/ruling.py:214, engine/moments.py:121, engine/battlefield_builder.py:109, engine/doings.py:76, engine/events.py:1200, scenes/arc_actions.py:392). They stay byte-identical only while the facade returns meta.minutes and the same location.
- World seeds from world_state scalars: `last` and `drift_last` (engine/pulse.py:250, 309). They must stay Python ints, and drift_last must not be defaulted by a migration.
- Entropy fallbacks reached if an rng argument is dropped: engine/lessons.py:309 (sole play caller scenes/training_actions.py:148), and per survey engine/ability_traits.py:213, engine/ability_slots.py:82, engine/field.py:156. The fence exempts these files (tools/sim/determinism_439_test.py:104).

### D. Turn state and rollback — HIGH
- About 40 turn fields on the scene (scenes/world.py:101-133); line fields reset in begin_line (:998-1003); ROLLED, HELD, PANE declared at :978-987; `step` is a class attribute (:1596).
- One snapshot call (scenes/world.py:1031); restores at give_back and reload_after_rollback (survey :1339-1367; read :1617-1631).
- asked_operation keeps its own snapshot: streams, people by identity, store.meta, ledger told, store._later, refusals.SESSION, pulselog.LOG (scenes/world.py:1208-1239).
- Underscore state written through `__dict__` from other modules, which a facade property would never see (survey, spot-checked scenes/world.py:145, 516): engine/stay.py:38-84, engine/voices.py:192-219, engine/ruling.py:232, engine/matters.py:302 and engine/moments.py:205 (`_arrival_lines`, four writers), scenes/combat_scene.py:1099-1116, scenes/banter_actions.py:115, scenes/quirk_actions.py:146-157, scenes/party_actions.py:596.
- `_truth` is special-cased by name (engine/session.py:183).
- Tests write scene fields and replace instance methods directly (survey: 68 and 64 files), and 133 sites build WorldScene with four arguments with no turn open, so every moved field needs a setter and a default context.

### E. The actor — HIGH
- `self.player` is rebound in six places: scenes/world.py:101, 511, 1232, 1350, 1622, scenes/arc_actions.py:791. asked_operation also restores it in place by identity (scenes/world.py:1213-1232).
- Seams that already exist: acting (scenes/world.py:153-158), characters() (:1299-1301), party_service (:173-177), place (:179-181), minutes (:183-185), name_ids (:958-966).
- The player row is saved at every operation commit, with the meta (scenes/world.py:1044; storage/campaign.py:444-454).
- The pulse writes the player behind the scene and the scene detects it by comparing the raw kv text (scenes/world.py:508-511; survey: engine/pulse.py:923-940).
- The saved id "player" is load-bearing: goldens' character id is "player" (start.db), and per survey core/models.py:250, npc/models.py:25, 84, engine/memory.py:72, 94, engine/reactions.py:73, services/fight.py:197, 873, engine/domain_events.py:80-167, engine/truth.py:270, 520, llm/contracts.py:1938. The migrated row's key must stay "player". The fight side "player" is a different meaning and must not be touched (survey: engine/combat.py:422, engine/damage.py:253).
- Single-player kv rows: talk, question, deferred, combat, story, presentation, notices (survey: storage/campaign.py:484-516, 628-660, 637; presentation read at :549-560). Home page reads kv['player'] with raw SQL (storage/saves.py:87, 99).
- Per-player notice state in the world row: player_events (engine/pulse.py:36; survey: engine/events.py:997, 1075, 1179-1200); `touched`/`revealed`/result="player" inside thread JSON (engine/events.py:394, 544-546).

### F. Clock and counters — HIGH
- One CampaignMeta: minutes, day, turn, steps, seed (storage/campaign.py:38-45), saved with the player (:454), with the first operation of a line (:547-548), reloaded after rollback (:362-366), and rebound whole by asked_operation (scenes/world.py:1216, 1233).
- Writers: minutes at scenes/world.py:363 and engine/starts.py:67; day at world.py:371; steps at :973; turn at :1543, :1945, :2145.
- Recorder and replay key operations on meta.steps (engine/recording.py:163-164, 270; tools/rerun.py:407).
- 109 test files set store.meta.minutes directly and read ws.minutes (survey); tools set it by hand (survey: simlib.py:773, tools/acceptance.py:86, tools/nightrun.py:599, tools/rerun.py:548).
- GOALS.md:237 leaves the multiplayer clock open, so M0 can only mirror the campaign clock.

### G. Module bindings and where each belongs
| Binding | Site | Belongs to | Risk |
|---|---|---|---|
| operation.CURRENT, PRESENTED, LEGACY | engine/operation.py:68-73, 98-113 | turn (CURRENT already thread-owned) | HIGH: PRESENTED is recorded |
| ledger.ROWS, LAST, TOTALS | survey engine/ledger.py:41; world.py:1550 | turn | HIGH: LAST is recorded |
| budget.CURRENT, LAST | engine/budget.py:189-190 (owner thread at :122-130) | turn | HIGH |
| budget.PROFILE, SLOW, CACHED | survey budget.py:63-69; rerun.py:342-348 | process (card) | stays |
| turnlog._open, SHOWN, COUNTS | engine/turnlog.py:146-153 | turn and channel | HIGH (SHOWN drives play) |
| streams | engine/streams.py:24-26 | actor; STRICT and global random stay process | HIGH |
| canon.JOURNAL, IDS, EVENTS, _SINK; names.CAST | scenes/world.py:961-966 | actor | HIGH |
| failures._last, questions._last, enchanting.DISCOUNT | engine/session.py:57-62 | actor | medium |
| asked._LOCAL | survey engine/asked.py:64 | turn (thread-local today) | low |
| pulse.LAST, pulselog.LOG/_tick, domain_events bus | engine/session.py:59, 99-100; engine/pulselog.py:8, 31 | campaign (world) | medium |
| refusals.SESSION, crashlog.SESSION, hygiene/names REPAIRS, gateway TALLY, audit._turn, embed._state | survey | not in _owned today; process residue | low to medium |
| config toggles from #settings | survey scenes/world.py:2538-2544 | per player later | medium |

residue() is asserted empty by 33 tests and named in session_453 (survey: tools/sim/session_453_test.py:66); if it stops looking into the context they pass without checking.

### H. Threads
- The window runs the whole game on a new thread (ui/gui/__init__.py:36); backfill and creation start their own (npc/backfill.py:57; survey: character/creation.py:100).
- The model path on any thread reaches budget, operation, audit and console.debug (llm/gateway.py:141-142, 212-229, 340; llm/embed.py:83). Budget and operation already ignore other threads (engine/budget.py:13, 122-130; engine/operation.py:106-113), so "no context on a background thread" matches today's behaviour if the default is "no turn".
- Two campaigns interleave turns on one thread in a test (survey: tools/sim/simlib_campaign_450_test.py:21-42), and CampaignSession.open resets every owned binding (engine/session.py:115). The context therefore has to be set per scene entry (turn, handle, run, open_world), not per session open.

### I. world_state — HIGH
- Root: one JSON row read and written whole, each read a fresh copy (storage/campaign.py:341-344, 404-408). Game code: 84 loads, 40 saves; tools/sim: 214 and 162; other tools 15 and 6.
- Heaviest files: engine/events.py 20, engine/matters.py 17, engine/situation_parts.py 13, scenes/road_actions.py 9, scenes/arc_actions.py 8, engine/pulse.py 8, engine/standing.py 6, scenes/world.py 5; then stakes, moments, world_improv, starts, mentor, deeds, ambient, truth, towns, situations, passive_hooks, explore_actions, dungeon_actions, field_actions, storage/invariants.py.
- The pulse holds one dict across the whole tick loop and saves once (engine/pulse.py:245-311); every helper mutates that dict. A table writer inside the loop would be doubled or overwritten.
- Load/save pairs held across a model call (survey): scenes/road_actions.py:318-539, scenes/explore_actions.py:105-147, engine/threads.py:488 inside engine/matters.py:253-284.
- Three deed writers: engine/reactions.py:134 (through deeds.log), engine/events.py:547 (lost, see 0.3), engine/starts.py:149 (direct append, no seq, no trim). deeds.log returns without writing when the row is empty and swallows every exception (engine/deeds.py:28-38).
- Order is behaviour. News folding moves a retold row to the end (engine/pulse.py:973-984) and cap_news drops the oldest non-deed rows first (pulse.py:946-958); history trims at append (pulse.py:315-318); thread ids are random hex, so no natural order (survey: pulse.py:375, 564). Tests pin list order (survey: roads_closed_540_test.py:91-95, town_memory_484_test.py:101, events_test.py:74).
- Hidden effects readers that never name world_state: price_factor, danger_factor, closed_reason, closed_until, one whole-row parse each (survey: engine/pulse.py:83-105); price quotes fan out per ware during interpret (survey: scenes/shop_actions.py:31).
- Older migrations read the JSON shape and must run before the move (storage/migrations.py:230-252, 264-294).
- Tools that slice lists by remembered length (survey: tools/event_trial.py:198-210, tools/pulse_preview.py:98-118, simbot.py:258).

### J. Saves, migrations, digest — HIGH
- A fresh save skips migrations and is built from SCHEMA_V1-3 (storage/campaign.py:266-271); new tables must be in both.
- Migration list ends at v16, each step in its own transaction with one backup (storage/migrations.py:297-332).
- Digest queries are fixed per table with ORDER BY a key (storage/statehash.py:20-27); new tables need a stable order column and their JSON columns named.
- export_json and _import_legacy write kv rows (survey: storage/campaign.py:918-950).
- Precedent for a schema-only re-bless: f547's v16, "no input's state, request, outcome or shown word moved" (git show 7d9ffe1).

### K. Tests and tools that pin
- Source-text fences on scenes/world.py that move with the code (survey: rollback_455_test.py:147, tutorial_stages_461_test.py:171, bus_454_test.py:106, brief_486_test.py:95-99, turn_survives_449_test.py:220-222).
- Ratchets with fixed directory lists; new packages are unscanned: determinism over engine, scenes, npc, services, storage, world (tools/sim/determinism_439_test.py:109-110); questions_460_test.py:130, turn_record_416_test.py:146, tutorial_stages_461_test.py:176 use non-recursive glob; tools/purity.py:217, 251, 305.
- regard_480 SITES pins `player.character.id` counts (tools/sim/regard_480_test.py:136); one_constructor_450 pins 124 scene-building tests (tools/sim/one_constructor_450_test.py:18).
- Old-save tests that the new step will run over (survey: circumstances_483b_test.py:160-172, storage_test.py:24-35, situation_ruling_547_test.py:800).
- Harnesses that rebind console per name or set the clock by hand (survey: tools/nightrun.py:104-119, simbot.py:58-67, 131-134, tools/acceptance.py:72-92, data/replay/scripts/stub_fight.py:73-91, stub_party.py:66-87).

### L. Data
- No data/ file may change before the re-bless step (storage/statehash.py:118-124).
- Caps that become SQL limits have no startup check: keep_deeds (engine/deeds.py:14), history_keep (engine/pulse.py:318), news.keep and keep_days (pulse.py:943, 972). Deed kinds are hardcoded in the check (engine/data_check.py:579) and 'gift' is read but not listed (engine/situation_parts.py:1243).

## 3. What the plans did not foresee

1. Doc 08 M0 promises the players table and exact replay together (docs/design/08_multiplayer_implementation_plan.md:168); the data hash rules that out (0.1).
2. Doc 05's "recordings exact" as the proof for step 1 (docs/design/05_world_objects_design.md:111-115) rests on recordings that barely touch threads and deeds (0.2). A same-seed pulse run compared old against new storage is missing.
3. Doc 05's schema does not fit the rows: news uses `origin`, not `place`, and old rows lack certainty (engine/pulse.py:986; survey: storage_test.py:24); threads lack tier, place, made on old saves; no table has an order column; fold-to-end and gossip-first eviction are not expressible as "DELETE WHERE over an index" (05:108).
4. Doc 05 says the row keeps four scalars (05:110). About 20 other keys live there, several unbounded or per player (section 1 table; engine/pulse.py:34-36).
5. The lost 'settled' deed (0.3) and the unnumbered start deed (engine/starts.py:149) change behaviour the moment deeds get their own writer.
6. Doc 08 calls the binding move "mechanical" (08:86-88). It is not: the rollback sweep (0.4), `__dict__` writers, tests assigning fields, residue() going blind, and held stream references each need a decision.
7. Console through ACTOR.out has to keep module-attribute dispatch and stdout capture, and needs a channel before any actor exists (section B).
8. The per-actor dice key cannot hold a character id and stay equal to today's key. Either "player" keeps the bare key forever or the id enters the key with a later re-bless.
9. Thread identity already plays the actor's role in five places (budget, operation, asked, recorder.asking at engine/recording.py:158, 209, gateway thread-locals); M0 should fold these, not add a sixth mechanism.
10. save_player writes the meta (storage/campaign.py:454). A players row with its own clock splits that write unless both stay in one transaction, and rollback must reload the actor clock with reload_meta (scenes/world.py:1621-1622).
11. Every operation commit rewrites the player row (scenes/world.py:1044) and many turns rewrite the whole world row; step 6 only helps the 60 s budget if save_world_state stops composing whole tables, which breaks the 33 tests that mutate the dict and save it.

## 4. Questions only the owner can answer

1. **Players table and the re-bless.** Fold the players table into the one step-6 migration (one re-bless, M0 stays hash-neutral and holds its clock and player in memory over today's rows), or accept a separate M0 re-bless of all three goldens? I recommend the first.
2. **The lost 'settled' deed.** Is it a bug to fix (its own feature before step 1, with a re-bless if any golden moves, and renown_campaign starts firing from the player's own endings), or must the table copy today's loss exactly?
3. **The dice key with several characters.** Keep `seed:steps:said` for the character "player" for good, or accept a re-bless when the character id enters the key in M1?
4. **The clock.** GOALS.md:237 is still open. Confirm M0 only mirrors the campaign clock and does not adopt doc 06's per-character model yet.
5. **Old saves.** Does "migrated with the least work" (GOALS.md:165) cover step 6, so legacy rows get defaults and world deeds get a stand-in actor, or must old saves keep every field?
6. **Per-player knowledge inside world rows** (thread touched and revealed, player_events, notices): split per character in this bundle, or carried whole and left for doc 05 step 7?
7. **data/runtime/server.yaml** could not be read in either pass. Someone with access should confirm it holds nothing this bundle touches.

## 5. An order that keeps the gate honest (for the planner)

Hash-neutral first, each its own feature: tests that pin what the goldens do not (stream key string, rollback over moved fields, old-against-new world_state run); the output channel under console; TurnContext with the snapshot re-homed; ActorContext with a process default equal to today's module state; streams as an object behind the module API; the clock view; the step-1 access layer. Then one migration (players plus threads, deeds, news, effects, with statehash.TABLES, both table pins, fresh-save schema, export/import, saves.py, cap checks in data_check) and one deliberate re-bless.

Relevant files: C:\Users\tstil\Projects\dnd_ai\GOALS.md, C:\Users\tstil\Projects\dnd_ai\docs\design\08_multiplayer_implementation_plan.md, C:\Users\tstil\Projects\dnd_ai\docs\design\05_world_objects_design.md, C:\Users\tstil\Projects\dnd_ai\scenes\world.py, C:\Users\tstil\Projects\dnd_ai\engine\session.py, C:\Users\tstil\Projects\dnd_ai\engine\streams.py, C:\Users\tstil\Projects\dnd_ai\storage\campaign.py, C:\Users\tstil\Projects\dnd_ai\storage\statehash.py, C:\Users\tstil\Projects\dnd_ai\storage\migrations.py, C:\Users\tstil\Projects\dnd_ai\engine\events.py, C:\Users\tstil\Projects\dnd_ai\engine\deeds.py, C:\Users\tstil\Projects\dnd_ai\engine\pulse.py, C:\Users\tstil\Projects\dnd_ai\ui\console.py, C:\Users\tstil\Projects\dnd_ai\engine\recording.py, C:\Users\tstil\Projects\dnd_ai\tools\rerun.py

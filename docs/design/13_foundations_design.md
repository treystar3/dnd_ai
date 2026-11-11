# Foundations bundle: one plan (M0 + TurnContext, world state steps 1 and 6)

Built on the replay design, with grafts from the other two where the judges found them sound. Nothing was run; every claim is from reading the code. Feature numbers are provisional (phases 1 and 2 will take numbers first); the order is what matters.

## 1. Shape

Fifteen features, f578 to f592. Fourteen move no recording and no data hash. One (f591) is the single migration (v17) and the single re-record of the three goldens (owner decision 1).

Five rules the whole bundle follows:

1. **One of everything in M0.** A scene's contexts hold the process's own dice, channel and registers, not copies. This is forced by the code: the replay and the recorder read `ledger.LAST` and `operation.PRESENTED` after the scene entry has returned (tools/rerun.py:402-413, engine/recording.py:265-270), so a per-scene register would read empty there. Separate objects per actor arrive in M1.
2. **A pin exists before the thing it pins moves.** f579's tests are written on today's code and must pass unchanged through f592.
3. **Save still means "the stored world := this dict".** After the tables exist, `save_world_state(dict)` replaces the whole logical state and `load_world_state()` composes it back exactly. No narrow writer is added, so each mutation keeps one writer (rebuild plan principle).
4. **Storage is proven before it is switched on.** The table storage is built unreachable and compared against the old row storage step by step; the switch is then small.
5. **Old module names are removed, not aliased.** A missed site fails loudly.

Rejected from the other designs, with the reason:
- "Contexts installed into module globals" (smallest): M2 would have to redo every binding (GOALS.md:133-134).
- A recorded world fixture with stored checkpoints (player): every phase 2 world change would have to re-record it. The dual run in f589 gives the same gate with nothing stored.
- A narrow deed insert (player f590): a second write path for one list.
- Rerouting all 75 loads and 40 saves through a new module (replay f582): the store's two methods are already the one path (storage/campaign.py:404-408).
- Rerouting the start's deed inside f578 (player): beyond decision 2; it is owner question 3.

## 2. Features in build order

### f578: the 'settled' deed is kept (pillar 1; decision 2). Build now.
- **Fault:** `after_deed` loads the row (engine/events.py:378); `finish` logs the deed through `deeds.log`, which loads and saves its own copy (engine/events.py:547, engine/deeds.py:25-39); both callers (events.py:416, :494) return into `after_deed`, which saves its older copy over it (events.py:422-423). `renown_campaign` counts those deeds (data/rules/consequences.yaml:33-34, engine/consequences.py:47).
- **Fix:** new `deeds.add(state, kind, minute, place, **data)` does tick, append, trim on the dict it is given. `deeds.log` becomes load, add, save. `finish` calls `deeds.add` on its caller's state with `by=ws.acting`. engine/starts.py:149 is left as it is.
- **Files:** engine/deeds.py, engine/events.py, tools/sim/settled_deed_578_test.py.
- **Test:** (a) a thread ended by a path leaves one 'settled' deed with the next seq, `state['seq']` ticked, `by` the acting id; (b) the same through the judge's 'resolved' verdict; (c) two endings in one region within 42 days make `consequences.tick` pick renown_campaign; (d) a JudgeVerdict failing every try rolls the operation back, the row text is byte-equal, the failure line shows, the next line plays; (e) `deeds.log` on an empty row still writes nothing (deeds.py:30-31).
- **Replay:** no recording moves. All three turns.jsonl hold 0 'settled' and 0 '- ended;' (checked). A move is a stop, not a re-record.
- **Leaves for M1:** the deed names its character, so consequences can count per player.

### f579: pins the goldens do not hold (tests only). Build now.
- **(1) Dice key:** `streams.begin(7, 3, 'look')` gives key `7:3:look`; each stream seeds `<key>:<name>`; global module `<key>:global`; `keyed()` and `fixed()` seed strings; `reset()` returns to `unseeded` (engine/streams.py:28-40, 43-50, 72-83).
- **(2) Rollback by reach:** every ROLLED name (scenes/world.py:982-987), every line field (:998-1003) and every underscore cache is read through `getattr`, never `__dict__`, around a failing operation, an asked stand-down (:1228-1239) and a line whose second operation fails. tools/sim/scene_rollback_465_test.py:36 reads `ws.__dict__` and would pass blind for a moved name.
- **(3) Console bytes:** stdout text of every output function for fixed arguments (131 `print` calls; one with `end=`/`flush=` at ui/console.py:115). The shown hash never sees stdout (tools/rerun.py:372-374).
- **(4) World script** (tools/sim/world_script.py): a seeded stub campaign through real turns and `pulse.catch_up`, with coverage asserted: a thread ended by the player, a settled deed, a news fold and an eviction (engine/pulse.py:946-958, 973-992), an effect lifted (pulse.py:892), a thread trimmed (pulse.py:673-675), deeds past `keep_deeds`, history at its cap (pulse.py:315-318), and one rolled-back operation. Run twice and compared per step here; reused by f582, f589, f592.
- **Files:** tools/sim/stream_key_579_test.py, rollback_fields_579_test.py, console_bytes_579_test.py, world_script.py, world_script_579_test.py.
- **Replay:** exact (no game code).
- **Leaves for M1:** the key pin is the line M1 edits on purpose (decision 3).

### f580: the output channel under console (checklist 8). Build now.
- **What:** a `Channel` in ui/console.py with `write(text, end)`; a default that resolves `sys.stdout` at call time, so the window's stdout swap (ui/gui/bridge.py:268) and capturing tools still work; a module-level `print` that writes to the current channel. Module-attribute dispatch, the hygiene gate (ui/console.py:649-670), the recorder's wrap (engine/recording.py:171-188), `turnlog.tap`, the operation hold (scenes/world.py:1088-1109) and `console.ask` are untouched, as are all 907 call sites.
- **Files:** ui/console.py, tools/sim/channel_580_test.py.
- **Test:** console_bytes_579 unchanged; a collecting channel gets every function's text and stdout nothing; a swapped `sys.stdout` is honoured; `console.narrate` is still the gated function; an AST fence finds no builtin print outside the one emit; a line whose ActionPlan fails every try sends no held line and does send the failure line.
- **Replay:** exact by construction.
- **Leaves for M1:** a channel per actor; the input side; lines written before a character exists (main.py:134-150).

### f581: dice as an object behind the module API (pillar 3). Build now.
- **What:** class `Streams` (begin, reset, get, new_id, key, keyed, snapshot, restore) and one DEFAULT; module functions delegate. `fixed()` stays pure. STRICT and the global reseed stay the process's (engine/streams.py:26, 40). Key stays `seed:steps:said` (decision 3). Held references stay valid because the object is the same: scenes/world.py:132, engine/spellcraft.py:25, and the survey's scenes/combat_scene.py:128, 151, services/fight.py:187, npc/life.py:345.
- **Files:** engine/streams.py, tools/sim/stream_object_581_test.py.
- **Test:** stream_key_579 unchanged; a second instance with the same key draws the same and moves nothing in the default; restore across a reseed raises (streams.py:95-96); a HELD ratchet of the references above that only shrinks; a retried line meets the same dice.
- **Replay:** exact.
- **Leaves for M1:** a Streams per actor with the id in the key and a re-record; HELD must be empty first.

### f582: the access layer, doc 05 step 1 (infrastructure). Build at the start of phase 2.
- **Seam:** `store._world` with `load()`, `save(dict)` and the narrow readers, holding today's two lines (storage/campaign.py:404-408). The store's two public methods stay the one whole-state path; a fence pins that the key `world_state` is named only in storage/ (true today: campaign.py:405, 408, 924, 947; migrations.py:236, 270, 294).
- **Narrow readers, read-only, on the seam:** `effects_at` behind `price_factor`, `danger_factor`, `closed_reason`, `closed_until` (engine/pulse.py:83-106, one whole parse each today), plus `threads(status)`, `deeds_since`, `news`. Each is defined as a filter over `load`. They sit on the seam so the old-storage leg of f589's dual run stays whole after f592.
- **Stale-save detector:** with `store.watch_stale` on (simlib and the night tools; off in shipped play, so play is byte-identical), a loaded state carries the hash of the text it came from; a save whose stored text has since changed is noted on the store with its call site and is still made exactly as today. One ratchet test holds the known sites in RECORDED, which only shrinks. No other test fails because of it.
- **Startup checks** in engine/data_check.py for `keep_deeds` (data/rules/events.yaml:39), `history_keep`, `news.keep`, `news.keep_days` (data/rules/pulse.yaml:79, 84-85), and 'gift' among deed kinds (data_check.py:579). Code only; the hash does not move.
- **Files:** storage/campaign.py, engine/worldstate.py, engine/pulse.py, engine/data_check.py, tools/sim/worldstate_582_test.py.
- **Test:** every narrow reader equals its filter on every world-script state; the detector flags a built stale overwrite (load A, load B, save B, save A) and survives a transaction rollback (it compares stored text, not a counter); RECORDED equals what the world script finds; a cap of 0 or text fails startup in a copied rules tree; a plain dict a test builds and saves still works.
- **Replay:** exact.
- **Leaves for M1:** per-player knowledge in rows is carried whole (decision 6).

### f583: one append path per list (infrastructure; the plan's "one append path"). Build with phase 2.
- **What:** `worldstate.add_effect(state, row)` and `add_thread(state, th)`, each a plain append today. Thirteen direct effect appenders move: engine/drift.py:220; engine/events.py:257, 1067, 1291; engine/pulse.py:852, 856, 864; engine/stakes.py:191; engine/world_improv.py:79, 87; scenes/arc_actions.py:608, 615; scenes/road_actions.py:537. Four thread appenders move: engine/events.py:965, engine/pulse.py:431, engine/stakes.py:222, engine/starts.py:139. Deeds already have `deeds.add` (f578), news `add_news` (pulse.py:961), history `add_history` (pulse.py:315). Rebinds that trim stay where they are and are listed: drift.py:196, pulse.py:675, 892, standing.py:118.
- **Files:** engine/worldstate.py and the files above, tools/sim/append_paths_583_test.py.
- **Test:** an AST ratchet over engine, scenes, services: direct appends to the four lists are zero, and the listed rebinds and any aliased form are named in a RECORDED list that only shrinks; world_script_579 states are unchanged.
- **Replay:** exact (the same append on the same dict).
- **Leaves for M2:** the one place a narrow writer goes.

### f584: TurnContext, with the snapshot re-homed (review recommendation 6). Phase 3.
- **What:** engine/context.py `TurnContext` with a declared FIELDS table. Each field is marked LINE (reset by `begin_line`, scenes/world.py:998-1003), ROLLED (in scenes/world.py:982-987) or KEPT: line_ops, line_failed, line_world_failed, line_done, passages, line_untold, unshown_ops, collecting, last_crash (LINE); line_done, buffering, step, ran, interpret_calls (ROLLED); pending, halted, last_failure, last_budget (KEPT).
- WorldScene gets one data descriptor per field that reads the context's own `__dict__` and raises AttributeError when absent, so `getattr(self, 'ran', [])` and the class default `step = None` (scenes/world.py:1596) mean what they did.
- The context is stored as `scene.turnctx`: no underscore and not in ROLLED, or the sweep would deep-copy it each operation and restore a stale copy (engine/session.py:185-191, 215-217). It cannot be called `turn` (the method at scenes/world.py:1456).
- The operation snapshot (`_turn`, engine/session.py:106) moves onto the TurnContext. `begin_turn` and `rollback` keep their signatures (tools/sim/rollback_455_test.py:147 pins the call text) and run the same loop over the dict each ROLLED name lives in.
- View fields (present, partner, convo, recent_narration) and every underscore cache stay on the scene.
- **Files:** engine/context.py, scenes/world.py, engine/session.py, tools/sim/turn_context_584_test.py; the source-text fences the survey lists move in the same commit (rollback_455, tutorial_stages_461, bus_454, brief_486, turn_survives_449, scene_rollback_465).
- **Test:** rollback_fields_579 unchanged (the proof); every field declares LINE, ROLLED or KEPT; a home fence: no descriptor on WorldScene or its mixins is in ROLLED or starts with `_` unless it is in FIELDS, and no context sits under a `_` name; a scene built with no turn open reads each default; assigning a field on the scene writes the context; two scenes over two stores keep their own snapshots when operations alternate.
- **Replay:** exact; each golden holds a failed-every-try call, so rollback over the moved fields is replayed.
- **Leaves for M1:** one TurnContext per actor; the view split.

### f585: ActorContext and the clock view (doc 08 M0; decision 4). Phase 3.
- **What:** `ActorContext(player, dice, out, clock, turn)`; `character_id` reads `player.character.id`, so the six rebinds (scenes/world.py:101, 511, 1232, 1350, 1622; scenes/arc_actions.py:791) cannot leave it stale. `WorldScene.player` becomes a property over `scene.actor.player`; `acting` (scenes/world.py:154-158) reads the actor.
- **Clock:** a view with no state. It reads `store.meta` at call time, because `reload_meta` and `asked_operation` rebind `store.meta` whole (storage/campaign.py:362-366; scenes/world.py:1216, 1233). Its `advance` is the in-play writer (today scenes/world.py:363, 371; engine/starts.py:67). No players row, no clock column. `save_player` still writes the meta in one transaction (storage/campaign.py:444-454).
- **Binding:** `context.bind(actor)` is a context manager entered at five entries: open_world (scenes/world.py:753), run (:817), turn (:1456), handle (:1976), command (:2395; 55 direct calls in 14 test files). It restores the previous actor on exit. With nothing bound, `context.actor()` is the process default: DEFAULT dice, stdout channel. Console's emit and the streams module API resolve through it.
- A ratchet counts `self.player` sites per directory (1,141 today) and only shrinks.
- **Files:** engine/context.py, scenes/world.py, scenes/arc_actions.py, engine/starts.py, engine/streams.py, ui/console.py, tools/sim/actor_585_test.py, tools/sim/regard_480_test.py (SITES at :136).
- **Test:** default dice and channel are the process's; two stub campaigns interleaved on one thread each see their own actor inside an entry and the previous one after; after each rebind `ws.acting` is the new id; after an asked stand-down `ws.player` is the same object; the clock view follows `reload_meta`, an asked restore and a test's direct `store.meta.minutes`; an AST ratchet on writes to `meta.minutes` and `meta.day`; a lesson line replayed twice from one save draws the same (no dropped rng argument, engine/lessons.py:309).
- **Replay:** exact; the saved id stays 'player'.
- **Leaves for M1:** a second actor; per-actor dice, channel and clock (GOALS.md:237 stays open); the per-character kv rows; counting the ratchet down family by family.

### f586: the turn's registers on the context, with one thread owner (doc 08 M0). Phase 3.
- **What:** a `Registers` object holds operation CURRENT, PRESENTED, LEGACY (engine/operation.py:68-73); the ledger's ROWS, LAST, TOTALS; budget CURRENT and LAST (engine/budget.py:189-190); turnlog `_open` and SHOWN (engine/turnlog.py:37, 146-153; SHOWN decides the silent-turn refusal at scenes/world.py:1466, 1579 and is in nobody's reset list today); asked's serving (engine/asked.py:64). In M0 every TurnContext points at the process's one Registers (rule 1).
- Module functions stay the API. The old module attributes are removed, replaced by accessors, with a module `__getattr__` that raises a clear error. All users change in the same commit, including tools the suite never runs (tools/rerun.py:402-413, tools/nightrun.py, tools/acceptance.py, root simbot.py, data/replay/scripts).
- **Thread owner:** `Budget.owner` (engine/budget.py:122, 129-130), `Operation.thread` (engine/operation.py:42, 102, 111) and `asked._LOCAL` become one field, `Registers.owner`. It is set by whichever of `budget.open`, `operation.begin` or `asked.begin` comes first, to the calling thread, and cleared when the last of them closes. It is never set when a context is built: the window builds on one thread and plays on another (ui/gui/__init__.py:36). Off the owner thread there is no turn, as today. The recorder's `asking` flag (engine/recording.py:158, 209) and the gateway's per-call tags (llm/gateway.py:73) are call scope and stay, named in an allow-list.
- `reset()` and `residue()` are driven by one scope table (engine/session.py:53-87).
- **Files:** engine/context.py, engine/session.py, engine/operation.py, engine/ledger.py, engine/budget.py, engine/turnlog.py, engine/asked.py, engine/recording.py, scenes/world.py, tools/rerun.py and the tools above, tools/sim/registers_586_test.py, session_453_test.py (:66), operation_record_462_test.py (:175).
- **Test:** each row dirtied through its module API is named by `residue()` and gone after close; an AST fence over game code, tools and the root finds no load or store of a removed name; an allow-list of `threading.local` and `get_ident` sites; a call on a background thread during a turn is not charged, filed or served; a context built on one thread and played on another owns its line; two contexts given separate Registers keep ledgers and SHOWN apart; a silent turn still gets its line; a failed line takes back its ledger rows (engine/session.py:205-209).
- **Replay:** exact, and strongly gated: `ledger.LAST`, PRESENTED and committed operations are compared per input (tools/rerun.py:402-413).
- **Leaves for M1:** a second actor gets its own Registers; the harness reads through the actor. M2: a thread-to-actor map.

### f587: the actor's caches on the context. Phase 3.
- **What:** canon JOURNAL, IDS, EVENTS, `_SINK`; `names.CAST` (set at scenes/world.py:961-966); `failures._last`; `questions._last`; `enchanting.DISCOUNT` move to an object on the actor, shared with the process default in M0. Same removal rule and fence as f586. Campaign scope stays on the session: `pulse.LAST`, `severity.REACTIONS`, `life._ANCHOR_SLOTS`, `embed._cache`, the bus.
- **Files:** engine/context.py, engine/session.py, engine/canon.py, engine/names.py, engine/failures.py, engine/questions.py, engine/enchanting.py, scenes/world.py, tools/sim/actor_caches_587_test.py.
- **Test:** the residue and fence checks of f586 for these rows, with the fence covering assignment (`canon.IDS = {...}` would otherwise silently re-create a dead attribute); two contexts with separate caches keep `canon.IDS` and `names.CAST` apart.
- **Replay:** exact.
- **Leaves for M1:** separate caches per actor with no further move.

### f588: the operation names who acted (owner, 2026-11-03). Phase 3; safe earlier, but nothing uses it before then.
- **What:** `Operation` gains `actor`, written by `record()` (engine/operation.py:45-47), by the presentation entry (storage/campaign.py:550) and by the recorder's input row (engine/recording.py:163-164). A record without one reads as the save's one character.
- **Files:** engine/operation.py, storage/campaign.py, engine/recording.py, scenes/world.py, tools/sim/operation_actor_588_test.py.
- **Test:** a committed operation's record and entry carry the acting id; an older record loads and is told at the next open; an old recording without the field replays; the state digest is equal with and without it; a failed operation leaves neither.
- **Replay:** exact. The replay compares only id, kind and rows (tools/rerun.py:406), and both kv rows are outside the digest (storage/statehash.py:29). The fields first appear in the goldens at f591.
- **Leaves for M1:** routing an unshown outcome to its own player; per-actor replay.

### f589: the world tables, built and proven, not yet used (doc 05 step 6). Phase 3, built close to f591.
- **What:** `TableWorld` implements the f582 seam over four tables, each `(ord INTEGER PRIMARY KEY, index columns, json TEXT NOT NULL)`: threads(id, status, place), deeds(seq, minute, kind, actor, place), news(minute, origin, thread), effects(kind, place, until, thread). The json is the row exactly as today and the only thing read back. Index columns are derived at write; legacy rows get defaults in columns only; a deed without `by` gets the save's one character id in its actor column (decision 5).
- The kv row keeps every other key (history and about 20 more) and a placeholder at each list's own key position; an absent key has no placeholder; no row means `{}` (callers test `if not state`, engine/events.py:379, engine/deeds.py:30). So `load(save(s))` equals `json.loads(json.dumps(s))`.
- `save` is stateless: inside the caller's transaction it reads the tables, aligns old and new lists (head drop, common prefix, rewritten tail), writes what differs, and always rewrites the kv row, so the void rule still counts a write (scenes/world.py:1040-1041; storage/campaign.py:233). Nothing is cached, so a rollback cannot leave it stale. Fold-to-end, gossip-first eviction and the caps stay Python on the list.
- One DDL string serves the fresh-save path and the migration (storage/campaign.py:266-271).
- `migrations.CURRENT` stays 16. The old two-line storage moves to tools/sim/worldstate_reference.py as the oracle.
- **Fixtures kept here, at the last v16 commit:** the world script's end database and the three goldens' current start.db, under data/replay/saves/ (outside the hash, storage/statehash.py:120). After the re-record the goldens no longer run the v16 step; these do.
- **Files:** storage/worldtables.py, storage/campaign.py, storage/invariants.py, tools/sim/worldstate_reference.py, tools/sim/worldstate_dual_589_test.py, tools/sim/long_campaign_test.py, data/replay/saves/.
- **Test:** the world script played twice from one seed, once over the reference and once over TableWorld; after every step the loaded dict is deep-equal with order, every other table's digest is equal, outcomes and shown lines are equal, and the write counter moved in both or neither. A property test of random list edits. An operation that wrote all four lists then failed every try leaves every table and the kv row byte-equal. Invariants check index columns against json. long_campaign_test: after 1,000 simulated days each table is within its cap and rows written per save stay flat (a count, not wall time; the suite has no clock, engine/budget.py:1-5).
- **Replay:** exact (unreachable in play; precedent engine/operation.py:6).
- **Leaves for M2:** narrow writers and per-row versions, once f582's RECORDED is empty.

### f590: the players table, built and proven, not yet used (doc 08 section 3.1). Phase 3.
- **What:** `players(character_id TEXT PRIMARY KEY, place TEXT, json TEXT NOT NULL)`; json is today's kv player body (storage/campaign.py:444-453); the key stays 'player' for every existing save. No clock column. A port with `load`, `save`, `exists` and `text()`.
- **Files:** storage/campaign.py, tools/sim/players_port_590_test.py.
- **Test:** over a scratch store, save then load through the port equals the kv path for the players of the three goldens' start.db and for one with hires (their memories stay rows); player and meta are written in one transaction (a fault between them leaves neither); a rolled-back operation's reload returns the row as it was.
- **Replay:** exact.
- **Leaves for M1:** more rows; `load_player(id)`; clock, party and online columns once doc 06 is decided.

### f591: the one migration (v17) and the one re-record (decision 1). Phase 3, last, with no other re-record pending.
- **What goes live:** `_v17` after v16; the same DDL in the fresh-save path; `store._world` becomes TableWorld; `load_player`, `save_player`, `player_exists` use the players port.
- **Grafts the replay design missed:**
  - The scene's raw compare of the player row (scenes/world.py:508-510) asks `store.player_text()`; with kv 'player' gone both reads would be None and f466's protection would be lost silently. tools/sim/hire_rows_479_test.py:44, 96 move with it.
  - Migrations v6 and v8 call `store.load_player` / `save_player` (storage/migrations.py:99, 126, 134) and swallow the error, so on a pre-v8 save v8 would silently skip the hires' pronouns. They get frozen readers of the kv row, as v11 already has (migrations.py:176, 189). v14 and v16 read kv world_state raw (:236, :270) and run before v17, so they are unaffected.
  - storage/saves.py:87, 99 read the players table and fall back to kv for a save not yet opened. `export_json` and `_import_legacy` (storage/campaign.py:924, 947) go through the store's own writers.
- `statehash.TABLES` gains the five tables, list tables keyed by position in ord order (storage/statehash.py:20-27); the two table pins move (tools/sim/isolation_456_test.py:124, operation_record_462_test.py:171).
- **Replay, the predicted printout read before anything is kept:**
  1. With the code switched and the OLD recordings untouched, `tools/rerun.py --as-schema 16` replays each under a v16 view of the state (kv world_state composed back, kv player from the players row, the five tables left out). The view is registered beside the migration step, as the standing way to prove a schema-only re-record. Prediction: stub_short 41 of 41, stub_party 15 of 15, stub_fight 27 of 27, with outcomes, operations, presented and shown words equal. rerun only warns on a differing data hash (tools/rerun.py:338-339), so nothing needs bypassing. Any miss stops the feature.
  2. Then `--rebless` each. Predicted to change: meta `data` (850e7a94 today, through CURRENT 16 to 17, storage/statehash.py:124) and `start`; start.db; every input's state digest; f588's actor fields. Predicted not to change: any request, outcome, operation, presented entry or shown word. `report_rebless` prints only ten inputs' tables (tools/rerun.py:96), so the per-table check is read over all 83.
- **Files:** storage/migrations.py, storage/campaign.py, storage/worldtables.py, storage/statehash.py, storage/saves.py, scenes/world.py, tools/rerun.py, data/replay/sessions/stub_short, stub_party, stub_fight, tools/sim/world_tables_591_test.py, isolation_456_test.py, operation_record_462_test.py, hire_rows_479_test.py.
- **Test:** each kept v16 fixture migrates and its v16 view equals the dump taken before; hand-made legacy rows (news without certainty, threads without tier, place or made, a start deed without seq, deeds without `by`) pass and keep their json; a pre-v8 fixture still gets its pronouns; one backup is taken (storage/migrations.py:326); a fresh save's `sqlite_master` equals a migrated one's; a save with no world row loads `{}`; a v17 save is refused by a v16 build with the SaveTooNew message (storage/campaign.py:274-278); the home page lists a v16 and a v17 save; a void operation is still void and one whose only write was the world row still records; an operation writing players and world rows then failing every try leaves all as before; the dual run's table leg now runs on the real store. golden_replay_test, budget_data_459_test (:94) and isolation_456_test (:126) pass on the re-recorded three.
- **Leaves for M1:** rows, not tables. Doc 05 step 7 for per-player knowledge.

### f592: narrow reads read one table (every cost per turn stays flat). After f591.
- **What:** TableWorld's narrow readers become one indexed query each. Write paths keep load, mutate, save: a partial load followed by a whole save would delete what it did not load, so doc 05's "after_deed loads only nearby threads" is not in this bundle.
- **Files:** storage/worldtables.py, engine/worldstate.py, tools/sim/narrow_reads_592_test.py.
- **Test:** each reader equals its filter over the composed dict on every world-script state; a shop listing of N wares at a world filled to its caps composes the whole world zero times and reads effect rows only; a count ratchet of whole-world composes per golden input that only falls; a reader inside an operation that later fails saw its writes and sees the old rows after.
- **Replay:** exact.
- **Leaves for M2:** narrow writers under per-row versions.

## 3. When each can be built (roadmap 5afcd76 puts the bundle in phase 3)

| When | Features | Why |
|---|---|---|
| Now, on their own branch | f578, f579, f580, f581 | No turn code: engine/deeds.py and events.py; tests; ui/console.py; engine/streams.py. f578 is best fixed before phase 2 rewrites thread endings. |
| Start of phase 2 | f582, f583 | The roadmap already places doc 05 step 1 there; "improvised acts become deeds" then writes through one append path. |
| Phase 3 only | f584 to f588 | They rewrite scenes/world.py fields, the session snapshot and the owned bindings ("while no other branch touches the turn code"). |
| Phase 3, last, quiet hash | f589 to f592 | After phase 2's row-shape changes, so the re-record carries nothing but the storage move. Build f589 to f591 close together. |

## 4. Risks

1. **Silent drop-out from rollback** (engine/session.py:183-222). Guard: f579's getattr pin before the move, the same sweep over the field's home dict, f584's home fence.
2. **A missing bind hides in M0.** Everything shares the process default, so code outside a scene entry works today and would reach the wrong player in M1. M1 must turn the default into an error for story output.
3. **The goldens are thin for world state** (6 of 83 inputs; all start empty). The proof rests on the world script's coverage assertions and the dual run. Weakening those assertions hollows it.
4. **Compose not exact** (key order, an absent key turned into `[]`, list order). Guard: placeholders, ord, the property test, the dual run, 83 of 83 under the v16 view.
5. **A diff save turning an operation void.** Guard: the kv row is always written.
6. **More stale overwrites than the one in `finish`**: load and save pairs held across a model call (survey: scenes/road_actions.py:318-539, scenes/explore_actions.py:105-147, engine/threads.py:488). They do not endanger f591, but each blocks a later narrow writer.
7. **f586 and f587 touch many files and tools outside the suite.** A missed site is caught only by the AST fence, which must cover assignment as well as reads.
8. **Two unreachable implementations (f589, f590) can drift** if phase 2 lands between them and f591.
9. **Another branch moving the hash.** `migrations.CURRENT` and every data/ file are in it (storage/statehash.py:118-124). The open prose branch or a second v17 forces f591 to be rebased and its 83 of 83 proof run again.
10. **f578 changes play on purpose:** renown_campaign becomes reachable from the player's own endings; more campaign births and pulse calls. Count them in the first night run.
11. **Whole loads after f591 cost a compose instead of one parse.** Bounded by the caps and guarded by counts, not seconds. The 60 s budget is model arithmetic and is not at risk.
12. **Fences with fixed directory lists** (tools/sim/determinism_439_test.py:109 and the non-recursive globs the survey lists). New code sits only in engine/, storage/ and ui/console.py.

## 5. Questions for the owner

1. **data/runtime/server.yaml** could not be read by the survey, the main session or any design. The plan treats it as untouched. Can you confirm it holds nothing about saves, the turn, dice or output?
2. **Building early.** May f578 to f581 be built now, and f582 and f583 at the start of phase 2, ahead of the phase 3 the roadmap gives this bundle?
3. **The start's deed** (engine/starts.py:149) is appended with no number and no trim. Route it through `deeds.add` (new games with a past get numbered deeds; no recording contains it), or leave it?
4. **The stand-in actor** for deeds with no `by`: the plan writes the save's one character id ('player') in the new column only and leaves the deed's json untouched. Or do you want 'world', or an empty actor?
5. **Other stale saves** the f582 detector finds: fixed each as its own feature before the flip, as decision 2 was, or ruled on one by one? And should shipped play log them, or only the suite and night runs (the plan's default)?
6. **renown_campaign's numbers** (two settled in a region within 42 days, 120-day cooldown): leave for the balance pass, or look at them before it starts firing?
7. **Lost 'settled' deeds in existing saves** are not restored. Confirm no backfill.
8. **A fourth kept recording** covering a matter ended by the player, news folded and capped, an effect applied and lifted? It makes "recordings exact" a real gate for world state, at the cost of one more to re-bless. Decision 1 speaks of three.
9. **One hash move for the phase.** Phase 3 also holds doc 05 steps 3, 4 and 7. Fold their schema into the same v17, or accept a later v18 with its own re-record?
10. **Unreachable storage for two features** (f589, f590), so the switch is small and the hash moves once. Acceptable? The precedent is f462.
11. **Doc 05's "after_deed reads only nearby threads"** is left for multiplayer M2, with f592 giving narrow reads only. Acceptable?
12. **The players table** holds character_id, place and the record in this bundle. Doc 08's clock, party and online columns wait for M1's own re-record. Agreed?
13. **Scope of the world row.** History and about twenty other keys stay in it; only the four named lists move. Is that the intended scope?
14. **A failed migration step** leaves the save as it was with its backup, but the player meets the crash path, because main.py catches only SaveTooNew (main.py:134-138). The rebuild plan asks for a clear refusal and the offer of a new game. Do you want that line in this bundle (yours to word), or is a step that cannot fail on any known shape enough for pre-alpha?
15. **The re-record printout:** do you want to read it yourself before it is kept, or is the 83 of 83 gate plus the commit body enough?

Files read for this plan: C:\Users\tstil\Projects\dnd_ai\docs\design\12_foundations_survey.md, C:\Users\tstil\Projects\dnd_ai\GOALS.md, C:\Users\tstil\Projects\dnd_ai\scenes\world.py, C:\Users\tstil\Projects\dnd_ai\engine\session.py, C:\Users\tstil\Projects\dnd_ai\engine\streams.py, C:\Users\tstil\Projects\dnd_ai\engine\events.py, C:\Users\tstil\Projects\dnd_ai\engine\deeds.py, C:\Users\tstil\Projects\dnd_ai\engine\operation.py, C:\Users\tstil\Projects\dnd_ai\engine\budget.py, C:\Users\tstil\Projects\dnd_ai\storage\campaign.py, C:\Users\tstil\Projects\dnd_ai\storage\migrations.py, C:\Users\tstil\Projects\dnd_ai\storage\statehash.py, C:\Users\tstil\Projects\dnd_ai\tools\rerun.py.

# Removal list: dead code and unneeded files

Meravia audit, second round, 2026-11-18. Repository: `C:/Users/tstil/Projects/dnd_ai`, branch play/faults at 6473815. Nothing was deleted or changed to make this list.

**What is on it.** Only claims a skeptic confirmed, and inside a grouped claim only the names that skeptic found dead. Claims by several finders about the same code are merged into one entry; the finding ids are kept on each entry. Every range below was opened in the code as it stands today: definitions were located by `ast`, references were followed through each file's imports, and the lines of every range were read back. What was dropped, and why, is in the last section.

**How the counting works.** Lines are whole lines of tracked files that would go; bytes are the bytes of exactly those lines (a whole file counts its size on disk). A change inside a line (a parameter, one name of an import, a key of a dict) is written as an edit and counts nothing. The blank lines that set a definition apart, and the test lines named under 'tests', are not counted. An entry marked OWNER'S CALL is not counted in its group's total.

**How to act on it.** Each entry is one change that can be made on its own unless it says otherwise; by the project's rules each is a numbered feature with the full suite passing before a push. A change under `data/` moves the data hash and no golden is re-recorded to make a test pass. None of the entries pulls against the owner's settled rules; where one comes near (sampling, what the model is asked to write) the entry says how it stays inside them.

## Totals

| Group | Entries | Lines | Bytes | Held for the owner, not counted |
|---|---:|---:|---:|---|
| 1. Whole files and modules | 5 | 782 | 44,538 | none |
| 2. Functions, classes and methods | 60 | 708 | 45,075 | 2 entries, 34 lines, 2,316 B |
| 3. Constants, parameters and imports | 36 | 250 | 9,748 | 1 entry, 5 lines, 388 B |
| 4. Code behind a switch that has never been on | 2 | 92 | 6,880 | 2 entries, 503 lines, 30,825 B |
| 5. Tracked files that are not code | 5 | 3,523 | 215,268 | none |
| 6. Things outside git that a tool leaves behind | 6 | not lines | 3,760,590,003 (3.50 GiB) where a size is known | none |
| **Tracked files, groups 1 to 5** | **108** | **5,355** | **321,509** | 5 entries, 542 lines, 33,529 B |

## 1. Whole files and modules

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 1.1 | character/history.py | `character/history.py` (whole file: 47 lines, 1,668 B) | 47 | 1,668 | none | No tracked file imports it: every `from character import` takes fit, creation or kit. Unchanged since the first commit. | dead-code-1, people-13 |
| 1.2 | tools/runstats.py | `tools/runstats.py` (whole file: 220 lines, 13,269 B) | 220 | 13,269 | none | Named by no tracked file but itself (no document, skill, hook, bat file or test). It still runs, so it goes only if the owner does not run it by hand. | dead-code-15 |
| 1.3 | tools/scratch/ (two probes and their README) | `tools/scratch/camp_probe.py` (whole file: 92 lines, 5,200 B); `tools/scratch/prop_probe.py` (whole file: 29 lines, 1,493 B); `tools/scratch/README.md` (whole file: 4 lines, 516 B) | 125 | 7,209 | none | Neither probe runs (camp_probe.py:17 calls arcs.empty(), which does not exist). The README says they are kept for reference only, and nothing names the folder. | dead-code-4, tools3-10, unneeded-files-8 |
| 1.4 | tools/sim/simreport.py | `tools/sim/simreport.py` (whole file: 278 lines, 16,466 B) | 278 | 16,466 | none | An older copy of the root simreport.py that fails at import (ModuleNotFoundError: world). The root simreport.py stays. | dead-switches-19, suite-speed-12, unneeded-files-8, tests-health-14 |
| 1.5 | tools/sim/tune_party.py, tune_camps.py, matrix.py, cc.py | `tools/sim/tune_party.py` (whole file: 17 lines, 1,082 B); `tools/sim/tune_camps.py` (whole file: 33 lines, 1,733 B); `tools/sim/matrix.py` (whole file: 50 lines, 2,724 B); `tools/sim/cc.py` (whole file: 12 lines, 387 B) | 112 | 5,926 | none | tune_party.py execs /tmp/tune4.py, which is not in the repository; tune_camps.py and matrix.py open saves named sim_<class> and fail in load_player; cc.py is named by nothing. None is a test (no _test suffix), so the suite's count does not move. | suite-speed-12, tests-health-14, unneeded-files-8 |

**Group 1 total:** 782 lines, 44,538 B in 5 entries.

## 2. Functions, classes and methods

### 2a. No caller in any tracked file

Each name was searched through every tracked file's imports (aliases, from-imports, composed names). The blank lines that set a definition apart go with it and are not counted.

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 2a.1 | fit.excluded() | `character/fit.py`:68-69 | 2 | 128 | none | engine/lessons.py reads the table fit.EXCLUDED itself; nothing calls the function. | people-14 |
| 2a.2 | CompanionKind, CompanionRole (two enums) | `core/models.py`:56-62, 65-76 | 19 | 453 | none | Neither name appears anywhere else; companions carry plain strings. | shell1-15, dead-code-9 |
| 2a.3 | Battlefield.describe() | `engine/battlefield.py`:89-96 | 8 | 361 | none | No call to describe() on a battlefield through any alias. | engine1-9 |
| 2a.4 | ability_traits.buff_stat_word() | `engine/ability_traits.py`:49-50 | 2 | 129 | none | No caller. The ability field buff_stat itself stays: llm/contracts.py:132 reads it. | engine1-9, dead-code-18 |
| 2a.5 | accessories.fight(), accessories.world() | `engine/accessories.py`:102-103, 106-107 | 4 | 208 | none | No reference through any import alias of engine.accessories. | engine1-9, dead-code-9 |
| 2a.6 | canon.keep_now() | `engine/canon.py`:351-352 | 2 | 129 | none | No caller. | engine2-11, dead-code-19 |
| 2a.7 | combat_perks._tick() | `engine/combat_perks.py`:61-63 | 3 | 113 | none | No caller in its own module, and the name is private. | engine2-11, dead-code-9 |
| 2a.8 | events._scope_regions() | `engine/events.py`:454-459 | 6 | 220 | none | No caller. The scope_places key stays where it is: it is in the state hash. | engine3-12 |
| 2a.9 | data_check.assert_ok() | `engine/data_check.py`:1423-1426 | 4 | 155 | none | No caller: startup and the tools call check() and read the list. | engine3-12 |
| 2a.10 | data_check.ALLOW_TABLES | `engine/data_check.py`:1314 | 1 | 122 | tools/sim/allowlist_509_test.py:99 (the one line that reads the name) | No game code reads it; the test line compares it with the same literal, so the line goes with it. | engine3-12 |
| 2a.11 | martial.is_technique() | `engine/martial.py`:23-25 | 3 | 244 | none | No caller. | engine4-8, dead-code-9 |
| 2a.12 | mentor.state(), mentor.chat_request() | `engine/mentor.py`:29-30, 462-467 | 8 | 531 | none | No caller of either: the game reads player.mentor directly, and the reply is built by the newer request function. | engine5-7, dead-code-19 |
| 2a.13 | orenna.STAGES, orenna.state() | `engine/orenna.py`:19, 22-23 | 3 | 156 | none | No reader and no caller. | engine5-8, dead-code-9 |
| 2a.14 | mounts.owned() | `engine/mounts.py`:50-51 | 2 | 64 | none | No caller. | engine5-8, dead-code-9 |
| 2a.15 | party.gestured() | `engine/party.py`:464-469 | 6 | 272 | none | No caller. | dead-code-19 |
| 2a.16 | pulse.active_effects() | `engine/pulse.py`:41-45 | 5 | 443 | none | No caller: a five-line wrapper; callers use effects_matching directly. | engine5-8, dead-code-19 |
| 2a.17 | pulse_prompts.JUDGE_SYSTEM, judge_request() | `engine/pulse_prompts.py`:160-169, 172-178 | 17 | 1,683 | none | The old whole-event judge. Nothing sends it; tools/live_check.py:168 has a JUDGE_SYSTEM of its own. GOALS.md:176 records the owner's decision that the old judge is retired. | dead-code-6, engine5-8 |
| 2a.18 | quirks.hungover() | `engine/quirks.py`:392-393 | 2 | 134 | none | No caller, not even a test. | dead-code-9, engine6-10 |
| 2a.19 | CampaignWorld.get_place() | `world/campaign.py`:78-79 | 2 | 87 | none | No caller: the definition is the only mention. | dead-code-9 |
| 2a.20 | relevance.on_mind() | `engine/relevance.py`:85-88 | 4 | 265 | none | No caller. Its `import random` (relevance.py:6) then has no user and is counted under 3b. | engine6-10 |
| 2a.21 | retrieval.by_meaning() | `engine/retrieval.py`:73-79 | 7 | 414 | none | No caller: the game calls relevance.pick directly from engine/candidates.py. docs/design/15_phase2_survey.md:173 still lists it as available: correct that line. | dead-code-9, engine6-10 |
| 2a.22 | spellcraft.is_area() | `engine/spellcraft.py`:106-107 | 2 | 74 | none | No caller. | engine7-8 |
| 2a.23 | entities.get() | `engine/entities.py`:172-173 | 2 | 77 | none | No call to entities.get through any alias. | dead-code-9 |
| 2a.24 | world_perks.value() | `engine/world_perks.py`:23-25 | 3 | 101 | none | No call to world_perks.value through any alias. | engine7-8 |
| 2a.25 | voice_profile.sayings() | `engine/voice_profile.py`:146-147 | 2 | 92 | none | No caller. | engine7-8 |
| 2a.26 | backend.close() | `llm/backend.py`:548-551. Edit: llm/backend.py:5 and llm/runtime.py:31 (docstrings that name it) | 4 | 99 | none | No caller: the runtime stops the server by its own path. | llm2-9 |
| 2a.27 | intercepts.describe(), plan_repairs.describe() | `scenes/intercepts.py`:53-54; `scenes/plan_repairs.py`:57-58 | 4 | 305 | none | No call to either module's describe through any alias. | scenes2-13 |
| 2a.28 | WorldScene.npc_context() | `scenes/world.py`:4155-4157. Edit: comments that name it: tools/sim/kept_lines_dash_620_test.py:195, docs/design/18_class_fixes_plan.md:295 | 3 | 197 | none | No caller: a three-line wrapper; the live one is npc_context_parts (scenes/world.py:3754). | world_py-11, dead-code-19 |
| 2a.29 | CampaignStore.reindex_npcs() | `storage/campaign.py`:970-974 | 5 | 316 | none | No caller since the first big commit; storage/migrations.py does not use it. The skeptic's one caution: it is a migration aid and cheap to keep, so ask the owner first. | dead-code-9, shell2-11, trace-save-6 |
| 2a.30 | night_measure.Run.slot() | `tools/night_measure.py`:60-62 | 3 | 187 | none | No caller. | tools2-13 |
| 2a.31 | StartingKit's second weapon test | `llm/contracts.py`:1225-1226 | 2 | 146 | none | Neither live call can reach it: choose_weapon (character/kit.py:144) always lists weapons, so the first test at :1217 has already raised for an unlisted id; give_starting_kit (kit.py:109) asks for a companion, so the elif is skipped. | llm-checks-18 |
| 2a.32 | lora_eval's sentence-length rule | `tools/lora_eval.py`:75-76 | 2 | 156 | tools/sim/lora_test.py:98-99 | It looks for a kit line ('none past twenty words') the game stopped writing at f375, so it never counts a break. | tools2-12 |

### 2b. Called only by tests

The game never calls these. The test lines named exist only to exercise the helper: they go with it, or are pointed at the function the game does use.

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 2b.1 | npc.prompts.conversation_request() | `npc/prompts.py`:236-246 | 11 | 1,182 | lists_back_584_test.py:42, places_test.py:81, pulse_log_test.py:73, townsfolk_test.py:74 (point them at the request the game builds) | The game builds a townsperson's request another way; four tests still read the old form. | dead-code-19, people-14 |
| 2b.2 | runtime.refuse_unless_attached() | `llm/runtime.py`:525-532. Edit: docstring llm/runtime.py:33-35 | 8 | 502 | game_lock_574_test.py:36; server_522_test.py:239, 240, 244 | No caller in the game or the tools. | dead-code-19 |
| 2b.3 | inventory.good_named() | `engine/inventory.py`:62-73 | 12 | 735 | trade_goods_545_test.py:59-61 and half of :64 (they check only the helper: they go with it) | No caller in the game. | engine4-8 |
| 2b.4 | inventory.fits() | `engine/inventory.py`:226-231 | 6 | 418 | left_lying_417_test.py:58-59 (they check only the helper: they go with it) | No caller in the game since f427/f428. | engine4-8 |
| 2b.5 | presence.hearers() | `engine/presence.py`:38-44 | 7 | 373 | prepared_talk_485_test.py:191 (checks only the helper: it goes with it) | No caller in the game. | dead-code-14 |
| 2b.6 | needs.warning(), needs.words() | `engine/needs.py`:91-93, 96-100 | 8 | 345 | needs_test.py:49, :119 (the check on warning goes with it; the one that reads live behaviour through words is pointed at needs.levels) | No caller in the game: even switched on, nothing would show the stage words. | dead-code-14 |
| 2b.7 | loader.campaign_world() | `world/loader.py`:529-535 | 7 | 573 | campaign_world_451_test.py:16, 108-109; turn_survives_449_test.py:33, 110 (build the world as the session does) | The session builds its world itself; only two tests use this shortcut. | dead-code-14 |
| 2b.8 | CampaignWorld.connections_from() | `world/campaign.py`:81-83 | 3 | 138 | campaign_world_451_test.py:52, 53, 78, 104 (they read live behaviour through it: point them at what the game calls) | No caller in the game. | dead-code-14 |
| 2b.9 | quirks.core_lines() | `engine/quirks.py`:203-222 | 20 | 680 | quirk_test.py:47, 49 (they check only the helper: they go with it) | No caller in the game. | dead-code-14, engine6-10 |
| 2b.10 | spells.is_ranked_damage() | `engine/spells.py`:49-51 | 3 | 196 | spells_test.py:266 (reads live behaviour through it: point it at what the game calls) | No caller in the game. | dead-code-14 |
| 2b.11 | combat.hit_chance() | `engine/combat.py`:1008-1009 | 2 | 111 | hit_steps_test.py, stacking_506_test.py and stats_test.py:37 call it (keep the checks, which pin numbers a player saw, and point them at combat.hit_parts(...)[0]) | The fight calls hit_parts; this is a one-line wrapper only tests reach. | dead-code-14 |
| 2b.12 | situation_parts.waiting() | `engine/situation_parts.py`:751-754 | 4 | 295 | births_546_test.py:214 (reads live behaviour through it: point it at adoptable and due) | No caller in the game: scenes/world.py:652 and :670 call adoptable and due. | dead-code-14 |
| 2b.13 | npc.life.unfinished() | `npc/life.py`:197-200 | 4 | 252 | backfill_test.py:53, 64; registration_545_test.py:226 (they read live behaviour through it: point them at what the game calls) | No caller in the game: npc/backfill.py:37-38 repeats its two lines inline. | dead-code-14 |
| 2b.14 | effects.drop() | `engine/effects.py`:95-96 | 2 | 167 | marks_499_test.py:90 (reads live behaviour through it: point it at what the game calls) | No caller in the game. | dead-code-14 |
| 2b.15 | CampaignStore.forget_memory() | `storage/campaign.py`:875-878 | 4 | 285 | memory_rows_test.py:39-41 | Only its test calls it. The forgotten column and the filters on it stay (the schema and old saves carry them). | dead-code-13, shell2-11, trace-save-6 |
| 2b.16 | Targets.exists() | `engine/targets.py`:47-48 | 2 | 83 | targets_593_test.py:109 (write `get(code) is not None` there) | No caller in the game. | engine7-8 |
| 2b.17 | truth.INTERPRETER, AUDIT, PLAYER and the is_player field | `engine/truth.py`:69, 75-76, 274-276 | 6 | 368 | matters_test.py:140, plain_world_test.py:55, stakes_test.py:80, towns_test.py:113 use INTERPRETER (point them at truth.NARRATOR: sees() treats narrator, interpreter and audit alike at :79) | The game builds no viewer of these three kinds, so is_player is never true and its arm of sees() never runs. | engine7-8, dead-code-10 |
| 2b.18 | Seven CombatScene wrappers: order_of, talk, hires_down, binding_ability, try_bind, try_tame, companions_after_fight | `scenes/combat_scene.py`:475-479, 709-714, 744-747, 749-751, 753-758, 760-764, 978-982 | 34 | 2,107 | about 36 call sites in twelve test files, to be pointed at services/fight.py | The game goes through services/fight.py; each wrapper only passes the call on. | scenes1-19 (dead-code-12, the same claim, has no verdict of its own) |

### 2c. Removals that span several files

Each of these must go in one change: the parts hold each other up (an import, a tuple of names, a stub answer, a data row).

#### 2c.1 The retired stat-passives creation step

- **Goes:** `llm/contracts.py`:16-19, 436-450, 1372-1377, 1380-1416; `llm/prompts.py`:3-7, 12-13, 138, 139, 141-172, 226-244, 247-259; `simlib.py`:488-495, 497-528, 614-615, 622-623, 631-632, 639-640, 647-648, 655-656, 663-664, 671-672, 679-680, 687-688, 695-696; `character/creation.py`:19, 128; `core/rules.py`:103-105; `core/models.py`:80-82
- **Lines and bytes:** 205 lines, 13,178 B
- **Edit (not counted):** llm/prompts.py:8 (drop STATS and TRIGGERS from the import); llm/prompts.py:320 (drop PASSIVES_SYSTEM and STAT_PASSIVES_SYSTEM from the tuple: the loop reads globals() by name, so a name left there is a KeyError at import)
- **Tests only for it:** tools/sim/world_facts_test.py:20 (the two names in its list); tools/sim/status_507_test.py:233 (reads llm/prompts.py for `if not t.dormant`, which lives only in _TRIGGER_LINES)
- **Why it is safe:** Nothing sends the task: the contract, both prompts, the request builder, the stub's answer with its four tables and every class's stats row answer a request no code makes. STAT_PICKS and MIN_MECHANIC_PASSIVES have no reader (the comment on STAT_PICKS says trainers use it; no trainer code names it). With them gone the three frozensets in core/rules.py and their re-export in core/models.py have no user.
- **Findings:** dead-code-5, llm1-9, llm2-7, shell1-14, dead-families-3, dead-code-9 (as_lists), people-14 (the two constants)

#### 2c.2 The old one-call abilities flow kept as a fallback

- **Goes:** `character/creation.py`:79-87; `llm/prompts.py`:61-110, 192-198
- **Lines and bytes:** 66 lines, 6,193 B
- **Edit (not counted):** character/creation.py:65-66 (the `except (ValueError, KeyError)` that falls back to it: let the failure be logged and raised as an LLMError instead); llm/prompts.py:320 (drop ACTIVES_SYSTEM from the tuple)
- **Tests only for it:** tools/sim/world_facts_test.py:20 (the name in its list)
- **Why it is safe:** The fallback was reached 0 times in the record; the planned flow is the only one played. A second step is the owner's call and is not counted: the not-planned branch of ActiveSet (llm/contracts.py:191-209, 224-225) and four helpers in engine/ability_traits.py.
- **Findings:** unmeasured-tasks-4

#### 2c.3 The mentor's rank check

- **Goes:** `engine/mentor.py`:63-65, 68-85, 743-746
- **Lines and bytes:** 25 lines, 1,433 B
- **Edit (not counted):** scenes/mentor_actions.py:116-117 (the `ranks` parameter of mentor_speak), :127 (the `ranks` key of the context), :522-523 (the docstring sentence that says the ranks are checked)
- **Tests only for it:** none
- **Why it is safe:** No call passes `ranks`, so the branch in check_speech never runs and check_ranks is never reached; rank_table has no caller. mentor.BUILDS stays.
- **Findings:** dead-code-7, engine5-7

#### 2c.4 save_character and saves/character.json

- **Goes:** `character/creation.py`:26, 330-333; `scenes/goddess.py`:584, 587
- **Lines and bytes:** 7 lines, 428 B
- **Tests only for it:** tools/sim/creation_page_test.py:80-81 (stubs it); tools/sim/page_echo_671_test.py:34 (reads the source for the debug line; its docstring at :2 quotes the line)
- **Why it is safe:** The file is written at the end of creation and read by nothing: the character lives in the campaign's database. scenes/goddess.py:584 is the only call and :587 only prints the path.
- **Findings:** people-14

#### 2c.5 legacy_failure and LEGACY_ERRORS

- **Goes:** `llm/backend.py`:97-98, 101-111
- **Lines and bytes:** 13 lines, 1,105 B
- **Edit (not counted):** tools/rerun.py:287 (the caller: raise the interface's own Failure there); llm/backend.py:43 (KINDS in the import, if nothing else uses it); the sentences at llm/backend.py:32 and tools/rerun.py:255
- **Tests only for it:** none
- **Why it is safe:** They serve a recording shape from before f527, and load() already refuses such a recording, so the row can never arrive.
- **Findings:** dead-code-20

#### 2c.6 simlib.remembered's path for saves from before typed memories

- **Goes:** `simlib.py`:831-834, 837-839, 842-850, 858-861, 868-870
- **Lines and bytes:** 23 lines, 1,647 B
- **Edit (not counted):** simlib.py:862 (select the fixed column list)
- **Tests only for it:** none
- **Why it is safe:** A store is only made by CampaignStore.open_or_create, which adds the typed columns to a new database and migrates an older one before returning, so no store that reaches remembered() lacks them: the skeptic counted 0 calls of _legacy_kind. The three comment lines that explain the interim (831-833) go too.
- **Findings:** shell1-16

#### 2c.7 The typed hiring path

- **Goes:** `scenes/party_actions.py`:291-302, 304-318, 326-329
- **Lines and bytes:** 31 lines, 1,737 B
- **Edit (not counted):** scenes/party_actions.py:325 (picks is the one exact entry), :94 (the 'hire' entry of AT_HALL), :72-73 (party_notice still says 'recruit help') and scenes/guild_actions.py:225; simbot.py:1161 (bot_recruit)
- **Tests only for it:** tools/sim/hall_acts_666_test.py:34 (pins AT_HALL); tools/sim/line_patterns_648_test.py (CENSUS 27 becomes 23)
- **Why it is safe:** The skeptic typed four hiring lines ('recruit help', 'hire <name>' and two more): each cost one party_intent call and reached none of party_list, party_pick or party_hire, because kind hire returns at :113. The pane's button reaches party_hire with exact=, and that stays. Rated medium because party_notice tells the player to type something that does nothing: reword it and the board header, with the words in data.
- **Findings:** scenes3-10

#### 2c.8 The page's `fatal` event

- **Goes:** `ui/gui/web/app.js`:1449-1454, 1530
- **Lines and bytes:** 7 lines, 436 B
- **Edit (not counted):** ui/gui/web/app.js:1352 ("fatal" in ENDS_LOAD); ui/gui/bridge.py:8 (the event list in the docstring)
- **Tests only for it:** tools/sim/load_bar_539_test.py:22
- **Why it is safe:** Nothing in the Python side sends an event named fatal. The other way to close this is to send it where the game fails before the home page; that is a feature, not a removal.
- **Findings:** dead-code-11

#### 2c.9 exits_due and show_exits() without asked=True

- **Goes:** `scenes/world.py`:296, 1038, 2468-2469, 3101, 3105, 3562, 3642; `scenes/explore_actions.py`:103; `scenes/mentor_actions.py`:815, 874; `scenes/orenna_actions.py`:108; `scenes/road_actions.py`:210, 240, 418
- **Lines and bytes:** 15 lines, 454 B
- **Edit (not counted):** scenes/world.py:3103 (the `force` parameter); engine/actor.py:127 (the name exits_due in the declared rows)
- **Tests only for it:** none
- **Why it is safe:** exits_due is never set True, and show_exits() returns at once unless asked=True, so the eleven bare calls do nothing. The one call that works, show_exits(asked=True) at scenes/world.py:2806, stays. Seven test lines stub show_exits with a lambda and are harmless either way.
- **Findings:** world_py-10

#### 2c.10 weight_hint

- **Goes:** `engine/court.py`:128; `engine/events.py`:777, 1373, 1411; `engine/matters.py`:319, 369, 398, 517; `engine/moments.py`:207-208; `engine/stakes.py`:197, 233; `scenes/arc_actions.py`:623, 682, 808, 871; `scenes/camp_actions.py`:537; `scenes/explore_actions.py`:93; `scenes/pastime_actions.py`:45; `scenes/property_actions.py`:136; `scenes/road_actions.py`:228; `scenes/shop_actions.py`:256-257; `scenes/world.py`:811-815, 1002, 3037, 3044
- **Lines and bytes:** 31 lines, 1,593 B
- **Edit (not counted):** engine/actor.py:127 (the name weight_hint in the declared rows)
- **Tests only for it:** tools/sim/frame_test.py:137-145 (three checks on the hint); tools/sim/moments_test.py:92-93; the name is also in a list at prose3_test.py:124 and rollback_declared_720_test.py:107
- **Why it is safe:** Write-only since f375: _narrate_now sets it to None (scenes/world.py:3044) and nothing reads it to decide anything; the one read (engine/moments.py:207) only guards another write. In line with the owner's rule that the narrator has no length limit. Known: GOALS.md:264.
- **Findings:** world_py-9

#### 2c.11 CampaignStore._import_legacy (saves from before the database) (OWNER'S CALL: not counted)

- **Goes:** `storage/campaign.py`:299-300, 976, 978-1006
- **Lines and bytes:** 32 lines, 2,238 B
- **Tests only for it:** tools/sim/storage_test.py:33-36; tools/sim/tables_live_640_test.py:326-336
- **Why it is safe:** The skeptic confirmed the game cannot reach it: the home page lists only folders that hold campaign.db, so the import runs only for the two tests that build an old-layout folder. adopt_legacy and LEGACY in storage/saves.py are a different thing and stay.
- **Owner's call:** docs/design/20_phase3_plan.md:459 carries the import on purpose ('a save from before the database comes in through the tables') and tables_live_640_test.py pins that. The owner's word on old saves is GOALS.md:237 ('don't worry about old saves for now'). Retiring the import is the owner's to say.
- **Findings:** dead-switches-13

#### 2c.12 behaviors.text_for() (OWNER'S CALL: not counted)

- **Goes:** `engine/behaviors.py`:40-41
- **Lines and bytes:** 2 lines, 78 B
- **Tests only for it:** none
- **Why it is safe:** No caller, so the 48 `text:` lines of data/world/families.yaml never reach the narrator.
- **Owner's call:** Whether the 48 lines are wired or deleted is open (docs/design/18_class_fixes_plan.md:365 and :375); tools/sim/families_test.py:25 pins them and tools/calibrate_families.py:56 anchors on them. text_for is the reader they would need, so it waits with them.
- **Findings:** dead-code-8

**Group 2 total:** 708 lines, 45,075 B in 60 entries. Held for the owner and not counted: 2 entries, 34 lines, 2,316 B.

## 3. Constants, parameters and imports

### 3a. Constants nothing reads

The definition is the only mention of the name in tracked code.

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 3a.1 | ability_slots.COMBAT_EFFECTS | `engine/ability_slots.py`:19 | 1 | 62 | none | The definition is the only mention of the name. | dead-code-10, engine1-9 |
| 3a.2 | body.HOWS | `engine/body.py`:20 | 1 | 69 | none | The definition is the only mention of the name. | dead-code-10 |
| 3a.3 | canon.MAX_CANON, canon.STATE_DAYS | `engine/canon.py`:22, 169 | 2 | 54 | none | The definition is the only mention of the name. | dead-code-10, engine2-11 |
| 3a.4 | equipment.OFF_HAND_WEAPON_TAG | `engine/equipment.py`:13 | 1 | 30 | none | The definition is the only mention of the name. | dead-code-10, engine3-12 |
| 3a.5 | starts.TOWN_KEYS | `engine/starts.py`:20 | 1 | 39 | none | The definition is the only mention of the name. | dead-code-10 |
| 3a.6 | exits.LEAVING | `engine/exits.py`:24 | 1 | 166 | none | Only LEAVING_RE is used (engine/exits.py:109, 118). | engine3-12 |
| 3a.7 | runtime.STATES | `llm/runtime.py`:63 | 1 | 69 | none | The definition is the only mention of the name. | dead-code-10 |
| 3a.8 | field_actions.DARK_PENALTY_DEFAULT | `scenes/field_actions.py`:16 | 1 | 27 | none | The definition is the only mention of the name. | dead-code-10, scenes2-13 |
| 3a.9 | passive_hooks.FOOD | `scenes/passive_hooks.py`:23 | 1 | 17 | none | The definition is the only mention of the name. | dead-code-10, scenes3-11 |
| 3a.10 | console.CONTEXT_LABEL | `ui/console.py`:20 | 1 | 67 | none | The definition is the only mention of the name. | dead-code-10, shell2-12 |
| 3a.11 | tools: rerun.GOLDEN, run_suite.SIM, world_report.PLAYER_KINDS, tune_classes.CASTER_HEAD | `tools/rerun.py`:34; `tools/run_suite.py`:33; `tools/world_report.py`:20; `tools/tune_classes.py`:25 | 4 | 247 | none | The definition is the only mention of the name. | tools3-11 |

### 3b. Imports nothing uses

#### 3b.1 Unused `import yaml`: 106 statements in 105 files (Appendix A lists every line)

- **Goes:** one whole line each, in 105 files (Appendix A)
- **Lines and bytes:** 106 lines, 1,301 B
- **Tests only for it:** tools/sim/trade_goods_545_test.py:18 is itself one of the lines; no test exists for the others
- **Why it is safe:** In each file the name yaml is never loaded (ast): every load goes through core/yamlio.py, and no other module reads <module>.yaml. Three of the lines are inside a function (engine/arcs.py:247, engine/memory.py:27, engine/regard.py:27). PyYAML is still loaded by core/yamlio.py, so this is tidiness: it saves no start-up time.
- **Findings:** engine3-14, engine4-9, engine5-9, engine7-9, scenes3-11 and the import lines named inside the other per-area findings

#### 3b.2 Other unused imports the skeptics named

- **Goes:** `engine/candidates.py`:24; `engine/spellcraft.py`:9; `engine/voice_rules.py`:169; `engine/relevance.py`:6; `engine/features.py`:80; `llm/gateway.py`:30; `llm/runtime.py`:49; `scenes/inventory_actions.py`:6; `scenes/party_actions.py`:8; `scenes/work_actions.py`:3; `scenes/orenna_actions.py`:3; `scenes/mentor_actions.py`:227, 568, 651; `scenes/world.py`:19, 70, 81; `ui/console.py`:413; `tools/world_divergence.py`:9
- **Lines and bytes:** 19 lines, 499 B
- **Edit (not counted):** one name out of a longer import: engine/events.py:25 JudgeVerdict; engine/truth.py:19 field; npc/life.py:14 Memory; scenes/combat_scene.py:13 clock and :20 ROLE_PROFILES, whose_blow (keep _Shape); scenes/mentor_actions.py:6 pools; scenes/world.py:75 manner and :76 Memory; ui/console.py:412 pools; tools/tune.py:8 statistics and :11 equipment; tools/tune_classes.py:16 RARITY_MIX; tools/voice_report.py:12 sys; tools/world_divergence.py:18 clock. scenes/mentor_actions.py:570-571 use `_re`: write `re` there when :568 goes
- **Tests only for it:** none
- **Why it is safe:** In each file the bound name is never loaded (ast), or the module already imports it at the top (the three local `import re` and engine/features.py:80). llm/gateway.py:30 carries the comment 'these names stay here', but no file reads gateway.shifted or gateway.RETRY_TEMPERATURE_STEP. engine/relevance.py:6 goes with on_mind (2a). MUST STAY: engine/actor.py:57 `import config` (actor.py:425 needs the module loaded) and tools/eventrun.py:33 `import nightrun` (it sets the working directory).
- **Findings:** engine1-9, engine3-14, engine6-10, engine7-9, llm2-9, scenes1-19, scenes3-11, world_py-11, shell2-12, tools3-11

### 3c. Small dead pieces: attributes written and never read, locals never used, branches that cannot run

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 3c.1 | LlamaClient.loading_seconds | `llm/llama.py`:174, 257 | 2 | 182 | none | Added to and never read. | llm2-9 |
| 3c.2 | gbnf Converter's dotall | `llm/gbnf.py`:439. Edit: llm/gbnf.py:438 (the parameter) | 1 | 29 | none | Stored on the converter and never read; no caller passes it. | llm2-9 |
| 3c.3 | Worker.waited_ms | `llm/worker.py`:65, 160. Edit: llm/worker.py:211 (the background_wait_ms key of stats()) | 2 | 174 | none | Nothing reads the key. Worker.stats() itself stays. | llm2-9 |
| 3c.4 | ui.gui real_out | `ui/gui/__init__.py`:15 | 1 | 26 | none | The saved stdout is never put back or read. | shell2-12 |
| 3c.5 | lessons: used_effects and its no-op test | `engine/lessons.py`:325, 330-331, 335 | 4 | 235 | none | Lines 330-331 assign effect the value it already has; the set is then written and never read. | engine4-8 |
| 3c.6 | items: `b = base_of(item)` twice | `engine/items.py`:307, 321 | 2 | 44 | none | The local is never used after either assignment. | engine4-9 |
| 3c.7 | mapview: `r = ...region` | `engine/mapview.py`:107 | 1 | 39 | none | The local is never used. | engine4-9 |
| 3c.8 | quirks: `v` and `spec` | `engine/quirks.py`:82-83 | 2 | 45 | none | v is read only to bind spec, and spec is never read; the lookup cannot fail and draws nothing from a random stream. | engine6-10 |
| 3c.9 | banter: `R = BN[...]` | `scenes/banter_actions.py`:787 | 1 | 38 | none | The local is never used. | scenes1-19 |
| 3c.10 | arc_actions: an empty elif | `scenes/arc_actions.py`:238-239 | 2 | 54 | none | `elif ...: pass` followed by an `if` on the same test: it changes nothing. | scenes1-19 |
| 3c.11 | dungeon_actions: a branch that cannot run | `scenes/dungeon_actions.py`:33-35 | 3 | 264 | none | Lines 24-27 already `continue` on the same condition and dungeons.due_for_respawn is pure, so the test at :33 is never true here. | scenes1-19 |
| 3c.12 | voice_profile: the 'transfer' arm | `engine/voice_profile.py`:309-310. Edit: engine/voice_profile.py:202 (the word in the docstring) | 2 | 137 | none | culture_feature never answers 'transfer' (it answers nothing, dialect, saying, imagery or word; voice_test.py:87 and playthrough_1030b_test.py:195 pin that). The skeptic's one caution: a save from before f410 that cached the feature at the moment it was rolled could still hold it. | engine7-8 |
| 3c.13 | Blow.deep | `engine/damage.py`:49. Edit: engine/damage.py:494 and :499 (resolve's `deep` parameter and its hand-on); engine/afflictions.py:110 (`deep=deep`). tear()'s own `deep` stays: it sizes the wound | 1 | 22 | none | Set on the blow and read by nothing. | engine3-13 |
| 3c.14 | Edits only (no whole line goes) | (no whole line). Edit: engine/exits.py:143 (`ms[1] if False else next(...)`: keep the next(...)); ui/gui/server.py:136 (the '[::1]' entry: split(':')[0] of a bracketed address is '[', so it cannot match, and the server binds 127.0.0.1 only); scenes/world.py:2879 ('map' in the tuple, shadowed by the test at :2807) | 0 | 0 | none | Each is a part of a line that can never be taken. | engine3-12, shell2-12, world_py-11 |

### 3d. Parameters nothing reads

#### 3d.1 commit_operation's first_of_line

- **Goes:** `storage/campaign.py`:606-607
- **Lines and bytes:** 2 lines, 55 B
- **Edit (not counted):** storage/campaign.py:586 (the parameter); the argument at scenes/world.py:1268
- **Tests only for it:** tools/sim/operation_record_462_test.py:33 (passes the argument)
- **Why it is safe:** save_player already saves the meta row in the same operation, so the extra save decides nothing.
- **Findings:** trace-turn-7

#### 3d.2 npc_memories' min_importance

- **Goes:** no whole line
- **Lines and bytes:** 0 lines, 0 B
- **Edit (not counted):** storage/campaign.py:853 (the parameter) and the `AND importance >= ?` clause with its bound value in the same method
- **Tests only for it:** none
- **Why it is safe:** No caller passes it, and the default of 1 excludes nothing.
- **Findings:** shell2-11, trace-save-6

#### 3d.3 Unread parameters (signature and call-site edits; no whole line goes)

- **Goes:** no whole line
- **Lines and bytes:** 0 lines, 0 B
- **Edit (not counted):** the parameters in the table below
- **Tests only for it:** none
- **Why it is safe:** For each, the function's body never loads the name (ast). Removing one means editing the signature and every call that passes a value in that position: do them one function at a time, with the function's own tests.
- **Findings:** dead-code-17, engine1-9, engine3-13, engine5-8, engine6-10, scenes2-13, people-14

| Function | Defined at | Parameter nothing reads |
|---|---|---|
| `_counts` | `engine/ability_slots.py:69` | interp |
| `_assign_channel` | `engine/ability_slots.py:383` | fams |
| `buff_text` | `engine/ability_traits.py:53` | stat (tier is unread too, but tools/sim passes it: leave tier) |
| `buff_mech` | `engine/ability_traits.py:160` | tier, stat, magical |
| `plan` | `engine/arcs.py:109` | store, taken_places |
| `wanted` | `engine/asked.py:164` | task |
| `duel_ground` | `engine/battlefield_builder.py:102` | place_name |
| `_routs` | `engine/behaviors.py:93` | combat |
| `after_turn` | `engine/behaviors.py:256` | rng |
| `intro` | `engine/bosses.py:63` | rng |
| `_days` | `engine/circumstance.py:14` | kind |
| `select` | `engine/context.py:85` | rng (then engine/mentor.py:394 and scenes/banter_actions.py:507, which only build that rng, go as whole lines: not counted) |
| `names` | `engine/discovery.py:34` | data |
| `nearest_zone` | `engine/events.py:69` | rng |
| `spawn_fighters` | `engine/events.py:150` | player_lvl |
| `mana_share` | `engine/lessons.py:87` | rng (caller at :323) |
| `voice_system` | `engine/mentor.py:693` | player |
| `speech_system` | `engine/mentor.py:750` | player |
| `compose` | `engine/moments.py:129` | rng |
| `step_for` | `engine/motives.py:26` | t |
| `fee` | `engine/party.py:89` | player_level, rank_coins |
| `progress_line` | `engine/quests.py:412` | now |
| `voice_notes` | `engine/quirks.py:486` | others, solo (`solo=True` at scenes/party_actions.py:794 and scenes/quirk_actions.py:290) |
| `details_request` | `engine/quirks.py:675` | core |
| `own` | `engine/regard.py:37` | minute |
| `check` | `engine/situations.py:208` | rng (about 20 call sites; six in tests pass it by keyword) |
| `bind` | `engine/taming.py:69` | enemy_name (four call sites) |
| `start` | `npc/backfill.py:30` | catalog |
| `_knowledge` | `npc/prompts.py:410` | convo |
| `ArcActions.dress_arc` | `scenes/arc_actions.py:160` | q |
| `InventoryActions.to_pack` | `scenes/inventory_actions.py:39` | why (together with the bot's wrapper at simbot.py:148-155) |
| `LawActions.arrest` | `scenes/law_actions.py:501` | forced (passed at scenes/law_actions.py:442, 542, 555, 574) |
| `RoadActions.road_outcome` | `scenes/road_actions.py:698` | prize |
| `obligation` | `simlib.py:885` | minutes, and its unused import of engine.obligations (its two callers, tools/sim/proof_bench_476_test.py:63 and 66, pass no minutes) |

Not on this list, though a finding named them: act._scene_key(actor_id) and act.take_up(text) (struck by the skeptic), moments._fmt's visitor_label (it is read). pulse.catch_up's local `changed` is a local that is set and never used: it can go with any edit there.

#### 3d.4 Temperature arguments the sampling table overrides

- **Goes:** no whole line
- **Lines and bytes:** 0 lines, 0 B
- **Edit (not counted):** scenes/mentor_actions.py:126 mentor_speech temperature=0.8 and :295 mentor_chat 0.8; scenes/banter_actions.py:112 exchange 0.9 and :839 pair_dynamic 0.9; scenes/party_actions.py:801 and scenes/quirk_actions.py:294 hire_chat 0.8 and 0.85
- **Tests only for it:** none
- **Why it is safe:** data/rules/sampling.yaml has a row for each of these tasks and the row wins, so the literal never reaches the server. Deleting the argument changes no sampling: the owner's settled settings stay exactly as they are. Do not add mentor_voice to the table to tidy up (that would move its retry ceiling).
- **Findings:** scenes3-11 (scenes1-16, the same claim for banter, has no verdict of its own)

### 3e. Data keys and rows nothing reads

Every change under data/ moves the data hash (tools/rerun.py:341; the rebless skill, step 5): say so in the commit. No golden is re-recorded for it.

#### 3e.1 Authored text and fields of data/world/mentor.yaml nothing reads

- **Goes:** `data/world/mentor.yaml`:66, 205-207, 208-209, 231-232, 239-243, 262-264, 265-271, 289-290, 309, 310, 311, 346, 360, 370, 371, 372, 394-404, 405
- **Lines and bytes:** 45 lines, 4,070 B
- **Tests only for it:** tools/sim/playthrough3b_test.py:244-245 (its count of 'half an hour northwest of Parth' becomes 1 when joined.go goes)
- **Why it is safe:** Keys: walk_minutes, info_unbadged, info_badged, info_chunk_board, info_not_sure, not_sure, speech_walk, member_close, guild_talk's ranks_lead, board_lead and joining_lead, round_one_hint, miss_narrate, joined.speech[1], joined.taken, joined.go, troll.scenes, figure_kill. No code names any of them, by literal or by a composed key. joined.narrate_open (366-367) is NOT on the list: engine/mentor.py:160-162 reads it by a composed key. Known: docs/design/24c_tier_bc_lines.md:100.
- **Findings:** data-8

#### 3e.2 Other content keys nothing reads

- **Goes:** `data/rules/quirks.yaml`:84, 93, 101; `data/world/banter.yaml`:253; `data/world/orenna.yaml`:96, 106, 116; `data/rules/arcs.yaml`:30; `data/rules/towns.yaml`:84
- **Lines and bytes:** 9 lines, 485 B
- **Tests only for it:** none
- **Why it is safe:** fond_word (three), seed_words, city_slot (three), node_kinds, seasons_from: no code names them.
- **Findings:** data-8

#### 3e.3 Rule keys that promise a rule the engine does not apply: the five to delete

- **Goes:** `data/rules/field.yaml`:260; `data/rules/combat.yaml`:298; `data/rules/events.yaml`:22; `data/rules/arcs.yaml`:77, 94
- **Lines and bytes:** 5 lines, 402 B
- **Tests only for it:** none
- **Why it is safe:** reputation_loss (data/rules/reactions.yaml holds the rule that runs), material_chance, cataclysm_boss_over, escort_slip_hours and bonus_per_clue (both marked reserved). Nothing reads them.
- **Findings:** data-3

#### 3e.4 Rule keys nothing reads where the rule itself is undecided (OWNER'S CALL: not counted)

- **Goes:** `data/rules/field.yaml`:226; `data/rules/arcs.yaml`:101, 115; `data/rules/events.yaml`:50, 99
- **Lines and bytes:** 5 lines, 388 B
- **Edit (not counted):** data/rules/equipment.yaml:85-87 (the stamina_recovery key inside each of the three weight-class lines; evasion and stealth on the same lines are read)
- **Tests only for it:** none
- **Why it is safe:** repeat_goodwill, prisoner_on_win, prices_scarcity, deed_homes_fallback, siege_danger, heavy armour's stamina_recovery: nothing reads them today.
- **Owner's call:** Each names a rule the game does not have. Whether to build the rule or delete the key is a design choice; no design document settles it. Two more keys of this finding are to be wired, not deleted: data/rules/needs.yaml:17 sleep_after_minutes and data/rules/dungeons.yaml:14 rest_in_chamber_only (the code has its own copies at scenes/world.py:4414 and :4398-4400).
- **Findings:** data-3

#### 3e.5 Three ledger kinds with no adder, and their stood lists

- **Goes:** `engine/ledger.py`:42-44; `data/rules/failures.yaml`:114-120, 170-176, 177-183
- **Lines and bytes:** 24 lines, 778 B
- **Tests only for it:** none
- **Why it is safe:** No ledger.add is ever called with worked, gathered or ended (the 'worked' in engine/domain_events.py:616 is a deed event's kind, and the other 'ended' strings are thread and arc states), so their lines can never be shown.
- **Findings:** dead-families-2

#### 3e.6 CampIntent.summary

- **Goes:** `llm/contracts.py`:629
- **Lines and bytes:** 1 line, 22 B
- **Edit (not counted):** scenes/camp_prompts.py:19 (the sentence 'summary is a few words.'); simlib.py:443 (the stub's summary key)
- **Tests only for it:** none
- **Why it is safe:** The engine reads kind, target and method and never the summary, which the model writes on every line typed at a camp. This changes the task's prompt and grammar: replay the goldens before and after, and re-record none to make it pass.
- **Findings:** unmeasured-tasks-10

**Group 3 total:** 250 lines, 9,748 B in 36 entries. Held for the owner and not counted: 1 entry, 5 lines, 388 B.

## 4. Code behind a switch that has never been on

### 4a. Confirmed: the switch has never been on, or has been fixed one way since

#### 4a.1 combat.yaml conditional_rolls (false since the first commit)

- **Goes:** `engine/loot.py`:17-38, 74-77; `data/rules/combat.yaml`:318
- **Lines and bytes:** 27 lines, 2,170 B
- **Edit (not counted):** engine/loot.py:78 onward (the else body moves one level left)
- **Tests only for it:** tools/sim/status_507_test.py:233 reads engine/loot.py for `not TRIGGERS[t].dormant`, which lives only in the dead arm
- **Why it is safe:** With the switch off, WEATHER, FIGHT and the FITS table are read by nothing and every property rolls 'always'. Do not rewrite property_magnitude while there: the goldens would shift. The skeptic left the choice between turning it on and deleting it to the owner; no design document names it, so it is counted here.
- **Findings:** dead-switches-10

#### 4a.2 The model's motive step (motives.yaml engine: true since f360)

- **Goes:** `engine/pulse.py`:286, 291-292, 716, 720-748; `engine/pulse_prompts.py`:58-71; `llm/contracts.py`:1879-1884; `simlib.py`:384-392; `data/rules/budget.yaml`:84; `data/rules/audit_log.yaml`:50; `data/rules/motives.yaml`:8
- **Lines and bytes:** 65 lines, 4,710 B
- **Edit (not counted):** engine/pulse.py:717-719 (the engine's step moves one level left), :287 and :293 (the tests on engine_made), :24 (MotiveStep in the import)
- **Tests only for it:** tools/sim/motives_test.py:62-67 and the clause at :19; tools/sim/prepared_470_test.py:32 (the pulse_motive entry)
- **Why it is safe:** The step has been the engine's own, with no model call, since f360; the model path behind `engine: false` is never taken and pulse_motive is asked 0 times in the record. The budget and audit rows must go in the same change: engine/data_check.py:104-105 and :113-115 refuse a row with no task. pulse.LAST stays (threads use it). Removing a model call is in line with the owner's rule that the engine decides state.
- **Findings:** llm-rest-13, dead-switches-8

### 4b. The owner's call, not dead (not counted)

A design document or GOALS.md says each of these waits on the owner. They are listed so that nobody removes them as dead code.

#### 4b.1 decide_then_speak (data/rules/reply.yaml:8, off as shipped) (OWNER'S CALL: not counted)

- **Where it lives:** `engine/reply.py` (whole file: 386 lines, 22,847 B); `data/rules/reply.yaml` (whole file: 108 lines, 7,250 B)
- **Lines and bytes:** 494 lines, 30,097 B
- **Why it is not dead:** f724 to f728 built it, and four tests turn it on.
- **Owner's call:** docs/design/28_phase4_plan.md:121 and :431: the switch is turned on by the owner after the blind reading, or not.
- **Findings:** dead-switches-17 (refuted)

#### 4b.2 A1's sampling arms and DND_SAMPLING_ARM (OWNER'S CALL: not counted)

- **Where it lives:** `data/rules/sampling.yaml`:27-34; `config.py`:87
- **Lines and bytes:** 9 lines, 728 B
- **Why it is not dead:** tools/sim/a1_arms_587_test.py covers it and engine/data_check.py:234 checks a named arm at startup.
- **Owner's call:** GOALS.md:179: A1 is paused, not closed; the arms are the owner's measuring tool. The owner's rule that sampling settings stay covers them.
- **Findings:** dead-switches-12 (refuted)

**Group 4 total:** 92 lines, 6,880 B in 2 entries. Held for the owner and not counted: 2 entries, 503 lines, 30,825 B.

## 5. Tracked files that are not code

| # | What goes | Where | Lines | Bytes | Tests only for it | Why it is safe | Findings |
|---|---|---|---:|---:|---|---|---|
| 5.1 | runbal.sh, runfull.sh, runfull2.sh, runfull4.sh (repository root) | `runbal.sh` (whole file: 8 lines, 333 B); `runfull.sh` (whole file: 8 lines, 336 B); `runfull2.sh` (whole file: 8 lines, 379 B); `runfull4.sh` (whole file: 9 lines, 389 B) | 33 | 1,437 | none | Each begins `cd /home/claude/r56`, a folder on another machine, and .gitignore:39-40 already says to leave them out (docs/design/meravia_review.md:53 asked for `git rm --cached` on them). First write the recipe they hold into sim_report.md: SIM_TARGET=150 SIM_FAR_LEVEL=95 and `simbot.py <class> <seed> 6000 900000 3300`. | unneeded-files-6, dead-switches-20, dead-code-16, tests-health-14 |
| 5.2 | tools/sim/runall.sh | `tools/sim/runall.sh` (whole file: 8 lines, 305 B) | 8 | 305 | none | It exports NODEATH, which nothing reads; tools/run_suite.py is the runner. | suite-speed-12 |
| 5.3 | sim_report_full.txt (repository root) | `sim_report_full.txt` (whole file: 1,232 lines, 126,991 B) | 1,232 | 126,991 | none | A raw report named only at sim_report.md:7 and excluded by .gitignore. sim_report.md itself (122 lines, 5,212 B) is cited by data/rules/creatures.yaml:13 and docs/design/meravia_review.md:61: move it to docs/measure/, do not delete it. Known: docs/design/meravia_review.md:53. | unneeded-files-6, dead-code-16 |
| 5.4 | docs/patches/perf_easy_wins.patch, docs/patches/bugfixes.patch | `docs/patches/perf_easy_wins.patch` (whole file: 2,179 lines, 83,596 B); `docs/patches/bugfixes.patch` (whole file: 26 lines, 1,366 B) | 2,205 | 84,962 | none | Both are already in the code: neither applies forward or reversed to today's tree. Change docs/design/README.md:22-26, which points at them; docs/design/03 and 04 stay. | dead-code-3, unneeded-files-9 |
| 5.5 | docs/tests/improv_dice_repro_test.py | `docs/tests/improv_dice_repro_test.py` (whole file: 45 lines, 1,573 B) | 45 | 1,573 | none | The same blob (sha1 807ca1b525) as tools/sim/improv_dice_repro_test.py, which the suite runs. It goes together with an edit to docs/design/README.md:22-27 and docs/design/03_bug_repros.md:14, which name the copy. | dead-code-2 |

**Group 5 total:** 3,523 lines, 215,268 B in 5 entries.

## 6. Things outside git that a tool leaves behind

Sizes are as the findings and their skeptics measured them; this audit may not read `logs/` and did not walk the temp folder again. Removing a worktree changes git's records, so these are the owner's to run.

| # | What | Made by | Count | Size | Why it is safe to remove | Findings |
|---|---|---|---|---|---|---|
| 6.1 | %TEMP%/rerun_logs_* (one scratch log folder for each replay, never removed) | `tools/rerun.py:359` | 11,740 folders | 2,236,799,360 B (2.08 GiB) | Scratch logs of finished replays; nothing reads them afterwards. The fix that stops the growth is a finally block in tools/rerun.py that removes the folder it made. | unneeded-files-1, tools3-2 (trace-save-7, the same claim, has no verdict of its own) |
| 6.2 | %TEMP%/meravia_base_<commit> (a git worktree for each commit the stop hook has seen) | `.claude/hooks/quick_suite.sh:9-10` | 46 of the 49 registered worktrees; six of them already emptied | 1,343 MB by file size (1,413 MB by du) | Each is a checkout of a past commit used once to compare a quick suite. Remove with `git worktree remove` and then `git worktree prune`: both change git's records, so the owner runs them, not an audit. | unneeded-files-2 (suite-speed-11, the same claim, has no verdict of its own) |
| 6.3 | .git/worktrees/* (git's record of each of those worktrees) | `.claude/hooks/quick_suite.sh:9-10` | 48 folders | 5.2 MB | They go when the worktrees are removed and pruned. | unneeded-files-2 |
| 6.4 | .claude/worktrees/intelligent-saha-40633a (a second copy of the repository) | a past session's worktree | one folder, at commit 4573c0f on the merged branch pillar3/engine-lines-undash | 105 MB (the first round's du; the skeptic did not measure it again) | The branch is merged. `git worktree remove` without --force (it refuses if anything is uncommitted), then `git branch -d`; add `/.claude/worktrees/` to .gitignore so a plain search no longer walks it. | unneeded-files-19 |
| 6.5 | %TEMP%: small folders that tests make with mkdtemp and never remove | 17 test prefixes in tools/sim | 2,071 folders | size not measured (seen and counted by the unneeded-files-1 skeptic) | Listed for the count only; it is not in the total. | seen under unneeded-files-1; unneeded-files-18, which claims it, has no verdict of its own |
| 6.6 | logs/audit (one file for each session, no cap) | `llm/audit.py:45` | not counted: logs/ may not be read by this audit | about 700 KiB for a 42-line session; total unknown | Old sessions' audit files are read by nothing in the game. The owner's rule that every store gets a cap applies: the fix is a cap on files kept, in llm/audit.py. | dead-switches-3 |

**Group 6 total:** 3,760,590,003 B (3.50 GiB) across the four entries with a measured size; the test temp folders and `logs/audit` are not in it.

## What was dropped, and why

**Refuted by a skeptic**

- trace-threads-9: the dormant start (start_for_game, stop_for_game, _GAME in llm/runtime.py:1157-1206) is a guarded fallback that runs when data/rules/launch.yaml is missing, unreadable or short a line; stop_for_game is called at every exit (main.py:75) and every update (core/updates.py:106).
- dead-switches-17: decide_then_speak is the owner's switch (4b), not dead code.
- dead-switches-12: A1's sampling arms are paused, not closed (GOALS.md:179) (4b).
- unneeded-files-13: docs/research holds the sources of the report (docs/design/17, line 228).
- unneeded-files-3: docs/measure (230 files, 37.3 MB) is the kept record, on purpose: its READMEs say so and GOALS.md:179 cites it as the evidence of the owner's decisions.

**Only plausible, not confirmed**

- dead-code-18: the ability field buff_stat is read at llm/contracts.py:132. Only buff_stat_word() stayed on the list (2a).
- dead-switches-11: hunger and fatigue are off, but rest_heal_per_hour and meal are live with the switch off, and no document says the systems are abandoned.
- dead-switches-9: the dormant start is a fallback kept on purpose and pinned by tests (load_and_slow_526_test.py:404-406, server_522_test.py:411-435); the skeptic calls it the owner's call, not a clean delete.

**Names struck from inside a confirmed group**

- engine/actor.py:57 `import config`: actor.py:425 needs the module loaded.
- body.of_fighter (engine/body.py:76-78): one skeptic listed it, another keeps it as f623's planned infrastructure (docs/design/19, step 7; tools/sim/body_feats_623_test.py:120).
- ledger.totals, mentor.BUILDS, Worker.stats(), worldstate.threads / deeds_since / news, reload_after_rollback, converse_many, list_npcs: the skeptic who checked each group found a reader or a reason to keep it.
- _Sealed.WIDTH and damage_tags: docs/design/20_phase3_plan.md:236 keeps them.
- CampaignStore.export_json (storage/campaign.py:1008-1029) and statehash.words_hash (storage/statehash.py:221-223): unused today, left by the skeptic to the owner's decision.
- data/world/mentor.yaml joined.narrate_open: read by a composed key (engine/mentor.py:160-162).
- The scope_places key, the forgotten column and its filters, adopt_legacy and LEGACY in storage/saves.py: old saves and the state hash carry them.
- sim_report.md (moved, not deleted), the root smoke_test.py and simreport.py, docs/design/03 and 04: all are cited or run.
- tools/botreport.py: only sim_report.md:8 names it; it goes or stays with the decision on that report.
- act._scene_key(actor_id), act.take_up(text), moments._fmt's visitor_label: struck by the skeptic who checked the parameters (visitor_label is read).

**Struck by the families table (tables/dead-families.md)**

- None. The table reaches no name on this list. It does bind two removals: the tuple of names at llm/prompts.py:320 (read through globals()) must lose a name in the same change as the prompt it names, and a row of engine/owned.py that names a removed attribute by its dotted string must go with it.

**No skeptic gave a verdict (so not taken, whatever their merit)**

- dead-switches-14, dead-switches-15, dead-switches-18, engine6-8, unneeded-files-10, unneeded-files-11, unneeded-files-12, unneeded-files-18, unneeded-files-20, tests-health-10, tests-health-13, tools2-11.
- dead-code-12, scenes1-16, suite-speed-11 and trace-save-7 have no verdict of their own but repeat a confirmed claim, and are noted at that entry.

**Confirmed, but not removals**

- unneeded-files-16: the built game ships data/replay (31 files, 2,067,126 B) because build_exe.bat:13 copies all of data/. The fix is a staged copy for the build, not a deletion in the repository.
- unneeded-files-4: the kept recordings' gzipped call logs weigh on git's history. The fix is to store them as plain text through one reader, a change of format, not a deletion.
- unneeded-files-5: the opposite of a removal: eight documents that tracked files cite (docs/play, docs/design/26 and five dated measure reports) are not in git and should be committed.
- logs-fields-2, -3, -4, -10 and their kind: they change what the model is asked to write. Only CampIntent.summary (3e), which no code reads at all, is on this list.
- dead-families-2's other fifteen stood lists: they cannot be shown today, which is a fault to wire, not text to delete.

## Appendix A. Every unused `import yaml` line

- **repository root** (1 file): bestiary_check.py:11
- **core/** (1 file): rules.py:12
- **engine/** (95 files): ability_slots.py:11; ability_traits.py:6; accessories.py:11; ambient.py:15; arcs.py:9, 247; asked.py:19; banter.py:8; battlefield_builder.py:9; behaviors.py:8; bosses.py:14; brief.py:11; budget.py:22; candidates.py:21; canon.py:16; checks.py:9; combat.py:14; combat_perks.py:18; consequences.py:15; court.py:13; crafting.py:6; damage.py:19; deeds.py:9; discovery.py:8; doings.py:13; dungeons.py:11; effects.py:20; elements.py:5; enchanting.py:10; encounters.py:7; entities.py:20; events.py:20; failures.py:15; faith.py:10; features.py:18; field.py:8; guard.py:14; healing.py:12; hygiene.py:14; inventory.py:9; items.py:11; law.py:10; lessons.py:16; loadout.py:9; look.py:12; mapview.py:11; martial.py:8; matters.py:24; memory.py:27; mentor.py:17; moments.py:16; money.py:5; motives.py:13; mounts.py:7; movement.py:15; needs.py:4; obligations.py:14; operation.py:18; orenna.py:13; party.py:10; pools.py:8; presence.py:11; property.py:6; pulse.py:19; questions.py:26; quests.py:12; quirks.py:16; reach.py:13; reactions.py:19; recognition.py:8; regard.py:27; roads.py:8; routines.py:19; ruling.py:23; sets.py:9; severity.py:11; spellcraft.py:12; spells.py:18; stakes.py:17; standing.py:11; starts.py:14; stats.py:5; stay.py:15; summons.py:14; taming.py:8; threads.py:22; town_memory.py:15; towns.py:13; trust.py:11; truth.py:22; voice_profile.py:13; voice_rules.py:6; voices.py:26; weather.py:6; world_improv.py:8; world_perks.py:8
- **llm/** (1 file): audit.py:18
- **npc/** (2 files): names.py:16; traits.py:12
- **scenes/** (4 files): passive_hooks.py:6; pastime_actions.py:13; training_actions.py:5; work_actions.py:7
- **tools/sim/** (1 file): trade_goods_545_test.py:18

## Appendix B. Unused imports the same scan found that no skeptic named one by one (not counted)

The scan (a bound name the file never loads) finds 160 unused import names outside `tools/sim`, the same count a skeptic reached, and 264 more in the tests. The ones below are outside the tests and were not named singly by a skeptic, so they are not in the totals. Check each before removing: an import can be there for what it does on loading, or so that other files can import the name from this one.

- `core/models.py`:79 COMPANION_TARGETS, NONCOMBAT_TARGETS, NONCOMBAT_TRIGGERS, POOL_TARGETS. NOT unused: a re-export. Three of the names go with 2c.1 (lines 80-82); POOL_TARGETS stays, engine/abilities.py:10 imports it from here.
- `engine/actor.py`:57 config. MUST STAY: actor.py:425 needs the module loaded.
- `llm/backend.py`:39 field.
- `scenes/check_actions.py`:3 random.
- `scenes/dungeon_actions.py`:3 random.
- `scenes/guild_actions.py`:186 rules.
- `scenes/party_actions.py`:207 CombatScene.
- `scenes/party_prompts.py`:21 _canon.
- `scenes/trial_actions.py`:11 money.
- `simbot.py`:70 deedlog, money.
- `simlib.py`:9 Path.
- `simlib.py`:719 Ability.
- `simreport.py`:7 sys.
- `tools/eventrun.py`:27 sys.
- `tools/eventrun.py`:28 time.
- `tools/eventrun.py`:33 nightrun. MUST STAY: importing it sets the working directory.
- `tools/live_check.py`:134 BanterActions.
- `tools/nightrun.py`:302 offer_open.
- `tools/scratch/camp_probe.py`:1 random. Moot if the file goes (group 1).
- `tools/scratch/camp_probe.py`:75 io, contextlib. Moot if the file goes (group 1).
- `tools/scratch/prop_probe.py`:26 WorldScene. Moot if the file goes (group 1).
- `tools/scratch/prop_probe.py`:27 CampaignStore. Moot if the file goes (group 1).
- `ui/console.py`:16 config.


# dead-families: handlers reached by a composed name, and three more key sets

Second round. Every family below is a place where the code builds a name from a value and looks it up
(`getattr(self, prefix + value)`, `globals()[name]`, a string-keyed table). For each: the values that can
arrive, the handlers that exist, and what is left over on either side. Checked by importing
`scenes.world.WorldScene` and the tables (no model), scripts under `audit/work/check_dead_families_*.py`.

## 1. Families reached by getattr(self, prefix + value)

| Family | Site | Default at the site | Where the values come from | Values | Handlers | (a) Handlers no value names | (b) Values with no handler | Checked at startup |
|---|---|---|---|---|---|---|---|---|
| `on_<kind>` | scenes/world.py:2434 | none, but `if intent.kind not in actions.BY_KIND` before it | engine/actions.py ACTIONS (the plan's Literal) | 41 | 41 | none | none | yes: actions.problems() (engine/actions.py:229) |
| `on_answer_<kind>` | scenes/world.py:2358 | None: the question is dropped with a note | ask_next(kind, ...) sites; the question is saved | 13 (fork, reforge_keep, reforge_take, discard, give_wanted, law, mentor, orenna_name, orenna_ruin, executioner, seal, enchant, allocate) | 13 | none | none ("clarify" is handled apart, before the site) | no (default covers it) |
| `prepare_<kind>` | scenes/world.py:1504 | None | the plan's kinds (41) | 41 | 1 (prepare_talk) | none; `prepare_step` is the dispatcher itself, and no kind is named "step" | 40 kinds have none, by design | no (default covers it) |
| `camp_<kind>` | scenes/camp_actions.py:327 | none | CampIntent.kind Literal, and keyword_intent's WORDS when the call fails; "none" returns before the site; sneak may be rewritten to ambush | 6 (scout, sneak, ambush, bluff, scare, charge) | 6 | none | none | no |
| `field_<field_use>` | scenes/field_actions.py:68 | None: the ability is refunded | data/rules/field.yaml functions (the FieldUse Literal) | 31 | 30 | none (`field_apply`, `field_precheck` share the prefix; no function has those names) | bind_beast: in-combat only, refused by field_precheck before the site | no (default covers it) |
| goddess `on_<step>` | scenes/goddess.py:113, :126 | none | the Step enum; `who` is handled before the loop and `done` ends it | 7 (name, concept, confirm_class, actives, passives, stats, confirm_stats) | 7 | none | none | no |
| fee `on_<kind>` | scenes/inventory_actions.py:440 | none | each scene part's FEES table (kind, fee function), read at :496 | 1 (join_guild, fee function joining_fee_of; scenes/guild_actions.py:72) | on_join_guild, joining_fee_of both exist | none | none | no |
| `mentor_stage_<stage>` | scenes/mentor_actions.py:411 | none | mentor_ask(stage, ...) literals; the stage is saved with the question | 6 (first, proof, know, sure, lecture, waiting) | 6 | none | none; git history shows no stage ever removed, so no old save can hold another | no |
| `party_<kind>` | scenes/party_actions.py:122 | none | PartyIntent.kind Literal, and keyword_party's KEYWORDS when the call fails; none, list and hire return before the site | 5 (promote, dismiss, hold, with, status) | 5, plus party_list, party_pick, party_hire | party_list, party_pick (first round: scenes3-10); party_hire is called directly with exact= from scenes/guild_actions.py:247 | none | no |
| stub `a_<title>` | simlib.py:59 | `_fill` (an answer built from the schema) | the title of the contract a call asks for | 99 contract titles (two of them made at run time) | 41 | a_StatPassiveSet (first round: dead-code-5, llm1-9, shell1-14); a_MotiveStep only behind the motives switch (llm-rest-13, dead-switches-8) | the other titles are answered by `_fill` | no |
| nightbot `goal_<kind>` | tools/nightbot.py:579 | None: the goal is taken off the list | the goal kinds the bot sets | 13 (retreat, contract, follow, board, go, hunt, report, kill, persuade, clear, find, posting, revisit) | 13 | none (`goal_sentence` shares the prefix and is called by name) | none | no |

Result for (a): nothing new. Every handler no value can name is already a first-round finding.
Result for (b): no value without a handler at a site with no default. Five sites have neither a default nor a
startup check (camp, goddess, fee, mentor stage, party); all resolve today.

## 2. Composed-name sites the first round and tools/line_census.py did not resolve

| Site | What is looked up | From | Safe today |
|---|---|---|---|
| llm/prompts.py:320 | `globals()[_name]` for five prompt names in a tuple | the tuple itself | yes; but it keeps PASSIVES_SYSTEM and STAT_PASSIVES_SYSTEM "used", and a removal that leaves the tuple alone is a KeyError at import (finding dead-families-3) |
| engine/owned.py:45 `_at(key)` | `getattr(importlib.import_module(mod), name)` | the 93 keys of STATE ("module.NAME") | yes: every key resolves; rows that hold only words (for example "llm.runtime._GAME", :154) are never resolved, so a removed name leaves a stale row |
| scenes/world.py:981, :1372 | `getattr(console, name)` | the names of held console calls, in memory only | yes (:981 has a default) |
| scenes/world.py:2374, :2376 | `getattr(self, ic.method)`, `getattr(self, ic.after)` | each part's INTERCEPTS table | yes: scenes/intercepts.py:46-48 checks the names |
| scenes/plan_repairs.py:149 | a repair's method name | the REPAIRS table | yes: checked there |
| scenes/inventory_actions.py:496 | `getattr(self, fn)` | each part's FEES table | yes, no check |
| engine/truth.py:123 | `FACETS[name]` | data/rules/truth.yaml profiles | yes: default `[]`; the 9 names used are the 9 that exist |
| ui/console.py:45, :190; ui/gui/bridge.py:83 | an output by its name | the `@_out` registry | yes |
| tools/rerun.py:141, :513; tools/lora_eval.py:38; tools/think_ab.py:147 | `getattr(contracts, title)` | a recorded call's title, or lora.yaml schemas | :141 and lora_eval guard it; rerun.py:513 has no default (a run-time title such as NPCReplyMany is no attribute of contracts) |
| tools/interp_eval.py:96 | `setattr(ws, f"on_{k}", ...)` | actions.KINDS | yes |
| tools/card_profile.py:167 REQUIRED_TITLES | a task by its contract's title | recordings older than f468 | 23 titles all exist and map to required tasks; 16 required tasks have no title in the table |
| engine/actor.py:331, :422; storage/campaign.py:259; world/campaign.py:113 | `__getattr__` delegation | any attribute | not a family; names resolved on the object behind |

## 3. First-round dead_code findings against these families (59 findings read)

- To strike because a family reaches the name: none.
- Duplicates of one confirmed finding: llm2-7, llm1-9 and shell1-14 are parts of dead-code-5.
- Fixes that must also touch a string-reached name:
  - llm2-7 and llm1-9: the tuple at llm/prompts.py:320 (dead-code-5's fix names it; theirs do not).
  - trace-threads-9 and dead-switches-9 (removing `_GAME`): the row "llm.runtime._GAME" at engine/owned.py:154.
  - dead-switches-8 (the motive step's `LAST`): the row "engine.pulse.LAST" at engine/owned.py:93-95, which reads its fields by name.
- Looked at and left as they are: engine6-10 and dead-code-9 (`on_mind` is a module function, no scene handler);
  engine3-14 (an unused import; the class is alive); llm2-9 and dead-switches-12 (read through `getattr(config, name, default)`).

## 4. Contract classes, task names and sampling rows

| Check | Result |
|---|---|
| Contract classes in llm/contracts.py | 101 BaseModel classes (99 titles, counting the two made at run time by many_reply) |
| Classes no task asks for | StatPassive, StatPassiveSet only (first round: dead-code-5). NPCAnswerPromised and PassiveProposal looked unasked to a first pass and are used (contracts.py:1123, 2314, 2348; character/creation.py, engine/abilities.py, engine/lessons.py) |
| Task names asked at generate() and voice.fresh() sites | 63, all literal first arguments |
| Task table (data/rules/budget.yaml tasks) | 63, equal to the code's; held at startup by engine/data_check.budget_problems |
| Sampling rows (data/rules/sampling.yaml tasks) | 16; every one has a caller; held to the task table at startup |
| Callers of a task with no sampling row | 47 tasks: by design they take the caller's temperature over the base row (the narrator-prose gap is first round's dead-switches-7) |
| Sampling rows that override a temperature the caller passes | exchange and pair_dynamic (scenes1-16), hire_chat (scenes3-11), mentor_chat and mentor_speech (scenes2-13), player_line (tools/nightbot.py:1222: passes 0.9, the row says 1.0; not in the first round) |
| Other per-task lists in data/rules | audit_log.yaml tasks (63), budget.yaml asked_outside (30), hygiene.yaml narrator_tasks (7), lora.yaml tasks/prose_tasks/speech_tasks/schemas, sampling.yaml arm_tasks (6), guard.yaml skip_tasks (15): every name is a task today |
| Lists no startup check holds to the task table | guard.yaml skip_tasks (engine/guard.py:35), lora.yaml tasks, schemas and short_system (tools only) |
| lora.yaml | prose_tasks lists combat_opening; schemas has no row for it (tools/lora_eval.py:36 exits for that task) |

## 5. ui/gui/web/style.css against index.html and app.js

| Check | Result |
|---|---|
| Selectors | 240 classes, 38 ids |
| Ids with no element | none |
| Classes nothing puts on an element | one: `body.no-strip .strip` (style.css:155); `no-strip` is set nowhere in the page, the script or the Python side |
| Classes reached only through a built name | `.k-*` from `"blk k-" + kind` (app.js:158), `.quiet` and the other pulse kinds from `"prow pulse " + r.kind` (app.js:435): all have a value that builds them |
| Classes put on elements with no rule and no lookup | blk, dv, home-credits, jbody (harmless) |
| Events the bridge sends against app.js cases | all matched except `fatal`, which nothing sends (first round: dead-code-11) |
| Panels by name (paintSide) | the 16 names the Python side sends each have a renderer |

## 6. data/rules/told.yaml and failures.yaml against the code

| Check | Result |
|---|---|
| told.yaml kinds | 17 and flight_words; every kind has a caller (told.say, combat's told_player, WorldScene.told); no caller asks for a missing kind; every caller passes the facts its lines name |
| failures.yaml top-level keys | every key is asked for |
| done / missed | the action kinds and `default`, as engine/failures.problems() demands |
| creation_fail / creation_stand_in | equal to the code's lists |
| stood | 23 lists of 6 lines, equal to ledger.KINDS, as problems() demands; but see below |

### The stood lists against the rows that can fill them

A row reaches `failures.stood_lines` only when it carries `facts` (scenes/world.py:1435 and :986). Of the 33
`ledger.add` calls in the game's code (34 by kind: one call adds `gained` or `left`), 7 pass any.

| Ledger kind | Adders | Adders passing facts | Facts passed | Lines of its list that can be shown |
|---|---|---|---|---|
| arrived | 2 (engine/court.py:126, engine/matters.py:366) | 2 | who; what when the name is known | 6 |
| happened | 1 (engine/matters.py:299) | 1 | what (the lines name no fact) | 6 |
| carried | 1 (scenes/inventory_actions.py:341) | 1 | what | 6 |
| left | 3 | 1 (scenes/inventory_actions.py:358) | what | 6, for that one adder |
| paid | 2 (scenes/shop_actions.py:216, :252) | 2 | who, amount, what | 6 |
| changed | 1 | 0 | | 0 |
| closed | 1 | 0 | | 0 |
| departed | 1 | 0 | | 0 |
| end | 1 | 0 | | 0 |
| found | 4 | 0 | | 0 |
| gained | 2 | 0 | | 0 |
| given | 1 | 0 | | 0 |
| hurt | 2 | 0 (the amount is a field of the row, not a fact) | | 0 |
| made | 3 | 0 | | 0 |
| moved | 1 | 0 | | 0 |
| not_done | 1 | 0 | | 0 |
| received | 1 | 0 | | 0 |
| refused | 2 | 0 | | 0 |
| tended | 2 | 0 | | 0 |
| took | 2 | 0 | | 0 |
| ended | 0 | | | 0 |
| gathered | 0 | | | 0 |
| worked | 0 | | | 0 |

Eighteen lists, 108 lines, can never be shown (finding dead-families-2). What the player reads instead is a
`stood_any` line, which says the deed is done. Run under the stub (work/check_dead_families_12_stood_play.py):
an act the engine ruled "no" whose passage is lost shows one line, "You see it through." (finding
dead-families-1); a buy whose passage is lost shows "You give the herbalist 0₲ 1Ş 50₵.", from its row's facts.

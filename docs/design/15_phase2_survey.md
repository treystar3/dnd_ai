# 15. Map: what phase 2 touches

The survey behind docs/design/14_phase2_plan.md, kept so the builder does not have to find it again. Four read-only passes over the
code on 2026-11-11 at main 356c226 (after PR #38). Lines drift: check a line before leaning on it. "Checked" marks what was read
again by hand; the rest is as the survey reported it. What nobody verified is listed at the end.

## 0. Notes for whoever builds

- Numbers: f582 to f588 are used on `prose/section-a` (not on this branch, so the session-start hook prints f581 as the highest).
  This phase starts at **f589**. Doc 13's "f582" and "f583" are f589 and f590 here.
- Order and scope: doc 14 sections 3 and 4. f589 and f590 are designed in full in doc 13 (its f582 and f583 sections); build from
  those, with the two additions in section 5 below.
- Each feature that adds or edits a file under data/ moves the data hash: re-record the three recordings by the `rebless` skill, and
  for a hash-only one prove the replay is otherwise exact first (`tools/rerun.py --golden X` warns on the hash and nothing else).
  After a re-record run golden_replay, budget_data_459, isolation_456, layers_517, load_and_slow_526.
- A new model task needs: a row in data/rules/budget.yaml `tasks` (data_check.py:70-105 checks both directions), its name in
  `asked_outside` to be asked before the transaction, a stub answer `a_<SchemaName>` in tools/sim/simlib.py, and a sampling entry only
  if it overrides the default (`ruling` passes temperature 0.3 itself and has no sampling entry).
- New modules take the acting character's id (`ws.acting`, scenes/world.py:154). Do not copy the `ws.player` reads listed in 3.8.
- f598 (the end-reading) needs a short design note taken to the owner before it is built. f602 (the switch) needs the owner's go
  with the pod's numbers. The pod's hourly price is stated before one is created.
- Tests that pin the old path and must pass untouched until f602: ruling_test, rulings_421_test, ruling_fallback_repro_test,
  improv_test, improv_odds_568_test, nightrun_review_test, plan_limit_test, hazard_ruled_447_test, scenery_test (until f592 changes
  pick-up, where its scenery-with-nothing-behind-it case must still hold).

## 1. Rulings outside combat today

**engine/ruling.py** (checked: `run` 249-262). Public: the_name 59, request 64 (the prompt's user text), means_of 90, ask 105,
verdict 119, change_parts 156, appeared_today 171, make_room 177, appear 206, refuse 237, run 249, odds 265, problems 281.
- `run`: `ask` (252); None gives `ws.ask_back("ruling_failed", ...)` (254, f559) and stops; `verdict` (256); a no is refused (258:
  advance 1, ledger "refused", refusals.note, narrated); a yes goes to `make_room` (260) then `world_improv.resolve(..., ruled=...)`.
- `ask` (111): `generate("ruling", SYSTEM, request(...), Ruling, temperature=0.3, max_tokens=500, validation_context={capabilities,
  checks, roles, becomes})`. SYSTEM is the module constant at 34-56. It catches only LLMError (114) and returns None.
- `means_of` (90-102): the character's capabilities, ability `field_use` and `effect`, people and look element, against
  data/rules/capabilities.yaml (12 entries: flight, pass_through, teleport, water_breathing, shape_change, mind_reading, raise_dead,
  invisibility, speak_with_beasts, speak_with_dead, darkvision, summoning; each `about`, `grants`, `lacking`). `verdict` 124-126
  refuses a `requires` the character lacks.
- `make_room` (177): `thing` (199) calls `ws.add_mark` and a ledger "made", no entity; `feature` and `way` call
  `features.adopt(..., "ruled")`; `person` calls `appear` (206), capped a day by `ws._appeared` (174, 232).
- No kept ruling exists anywhere (no `rulings` on the scene or in the world row; situations.yaml `rulings` is the parts ruling's data).

**engine/world_improv.py.** read_effect 20, is_pose 38, is_rest 45, odds_for 50, apply_changes 60, problems 99, what_of 120,
changed_text 133, resolve 142.
- `resolve`: reads the effect through `asked.compute("improv_effect:...")` (148); a pose with nothing made has no roll and no mark
  (151); a plain yes with no check succeeds (159); else `ruling.odds` then `checks.roll` (163-164); publishes `Improvised` through
  `ws.notice` (169-172); success writes a mark (175), `apply_changes`, `changed_text`; partial a "roughly" mark; failure the table
  (minutes, health_pct, heat).
- `apply_changes` (60-96) writes `state["effects"]` rows `closed` and `danger` with `cause: "improvised"` and news, then saves the
  world row. pulse.py (57, 99, 140) and road_actions.py:99 filter on that `cause`: keep the tag.
- Tables: data/rules/improv.yaml (`effects`, `fails`, `partial`, `pose_words`, `rest_words`, `base_odds`, `min`, `max`).

**Entry points** (checked: `on_other` scenes/world.py:3991-4003). Dispatch `getattr(self, f"on_{intent.kind}")` (world.py:2082);
`on_ability` falls through to `on_other` (3616) when the ability is not the character's. `on_other`: a rest line of 12 words or
fewer goes to `on_wait` (3994); a clue part underfoot to `search_part` (3999-4001); else `ruling.run` (4003). The `other` action is
engine/actions.py:151; also produced by scenes/plan_repairs.py:306, 319, scenes/listening.py:56, engine/intent_audit.py:77.
- **Second caller of `ruling.ask`:** scenes/road_actions.py:484 (`get_past`, hazards, f447); `push_past` 492-511 calls `ruling.odds`
  itself; no `make_room`, `verdict`, `world_improv` or `Improvised`. Pinned by hazard_ruled_447_test. It stays in phase 2.
- Tools: tools/ruling_eval.py:79 and tools/think_ab.py:263 call `ask` and `verdict`.

**Contracts** (llm/contracts.py). Need 512 (kind feature, person, thing, way; name; what; where; role), Stakes 521 (check; hard
easy, fair, hard), Change 526 (part, becomes), Ruling 533 on (sense yes, cost, no; why; needs; requires; stakes; changes; answer;
instead; validator: at most 2 needs and 2 changes, a check named under `requires` moved to stakes, `answer` required for a no,
`becomes` checked against the context). The situation form: RulingChange 1667 (n, part, who, becomes, because, about, needs),
JudgeVerdict 1684 (verdict, reason, ending, changes up to 12), SituationParts 1476 (people, resources, ties, conditions, evidence;
each list sliced to 8 at 1489).

**Asked before the transaction** (engine/asked.py). `compute(key, fn)` 131 keeps a value across an operation's restarts, in call
order (a different key at the same point raises Drift). `call` 94. llm/gateway.py:136-139 routes a task through the serving when
`asked.wanted()`. `ruling` and `event_judge` are not in `asked_outside` (checked: budget.yaml:27-33), so both are made inside the
operation and counted by `operation.note_legacy` (gateway.py:142) as f470 residue. The stub: simlib.py:67 `a_Ruling` returns
`self.ruling` or `{"sense": "cost", "why": "", "needs": [], "requires": []}`.

**The corpus.** data/replay/ruling_cases.yaml (about 50) and ruling_cases_complex.yaml (about 28). tools/ruling_eval.py offline
scores only cases that carry a `model` ruling, through `verdict()`; `--live` runs the real model on the Ruling schema with the rest
stubbed (36-38). Not in the suite (scenes_test.py:43-44 checks the file's shape only).

**The event.** `Improvised` engine/domain_events.py:581-591: a frozen Deed, kind "improvised", fields effect, degree, what, mark,
heat. Published only by world_improv.resolve through `WorldScene.notice` (world.py:160-171, which stamps `by=self.acting`).
data/rules/reactions.yaml:86-87 gives it heat only: no `ledger`, and no `ledger_row()` (the Deed default at 218 returns None), so it
never becomes a deed.

## 2. Situations and the judge today

**Births** (engine/situation_parts.py; checked: heart 402, adoptable 532, due 541, world.py:470-493).
- Asked only for `births.tiers: [rare, campaign]` (data/rules/situations.yaml:287). `pulse.start_thread` sets `parts_due = 0` only
  for those (pulse.py:457-458). births_546_test.py:182 pins "normal is never due".
- `scenes/world.py:470 situation_births`, after the tail: the oldest due birth (`due`) through `asked_operation("parts", ...)`;
  `birth()` (582): `situations.propose` (situations.py:575), `agree()` (501), `register()` (275), then `parts_due` popped.
- A birth whose operation does not commit spends a try in its own operation (`missed` 568; world.py:488-491), whatever the reason,
  a budget drop included. After `tries: 3` (yaml:288) `adoptable` picks it up and `adopt_all` (556) gives the engine's parts.
- `adopt()` (449) builds from persuade and treaty paths, effects it already laid and clues with a living holder; marked
  `engine: True`, `parts_by: "engine"`. `adopt_tiers: [rare, campaign, cataclysm]` (yaml:289).
- Data checks to change in f599: `births.tiers` must be a subset of {rare, campaign} (situations.py:886-887); `adopt_tiers` must
  cover it (892). The comment at situations.yaml:287 ("common and uncommon stay as they are: the owner") is stale.
- `heart()` (402): threats (harmful conditions with who imposes them, people who block, creatures a way must defeat) and stakes
  (people harmed, goods at stake, the place and town), written once (391, 490). Nothing reads it to end anything.
- World row keys: on the thread `parts`, `parts_due`, `parts_by`, `heart`, `changes` (window 40), `paths`, `clues`; on the row
  `effects` (`of_part`), `situation_people` (54), `parts_ended` (1480).
- `rule()` (1143): one `event_judge` call with `JUDGE_PARTS_SYSTEM`, temperature 0.3, max_tokens 900; `ruled()` (667) checks the
  chain; `keep_changes()` (990) writes through the game's own writers. `parts_lines()` (1111) numbers the parts for the model, with
  `Now:` notes for the acting character only. `give_stock` (215): a `stock:` entity per (npc, good, situation).

**The judge** (engine/events.py; checked: after_deed 374-422, judge_ok 457-464).
- `judge_ok`: tier in `judge.tiers` [rare, campaign, cataclysm] (data/rules/events.yaml:32), `stage >= min_stage` (1), deed kind in
  `relevant_deeds` [kill, persuade, dungeon_cleared, quest_done, deliver, defend] (:38), `judge_calls < max_calls` (8),
  a game day since `judge_last` (`per_day` 1), and the deed's place in the thread's regions (463).
- `judge()` (467) bumps the counts first. With parts it goes to `_rule` (508), which ignores the verdict and returns `bool(kept)`:
  it ends nothing (comments at 510, 520 point at the unbuilt f549). Without parts, a JudgeVerdict call may `finish` or delay.
- `after_deed`: a `quest_done` deed carrying the thread's id, on a normal or uncommon thread, ends it by `pulse.end_thread(...,
  "settled by <name>")`, `result="player"`, `matters.remember`, reputation `.get(tier, 3)` (392-401). It skips `finish`, so no
  'settled' deed, no follow-up, no ending kind. Hidden unrevealed threads are revealed first (388). Then paths (402), then
  `judge_ok` (419). `finish()` is 523.
- Callers of `after_deed`: engine/reactions.py:136 (the ledger; legacy, inside the action's operation), situation_parts.py:1358
  (`heard`) and 1403 (`part_done`), tools/event_trial.py:295.
- reactions.py:27 `AFTER_DEED` = kill, persuade, deliver, quest_done, dungeon_cleared, found, defend, gift, bribe.
  reactions.py:125-137 `ledger`: needs `ledger: true` for the kind, `e.ledger_row()`, then `deeds.log`, then `after_deed`.

**Threads** (data/rules/pulse.yaml; checked: 1-32). Pulse every 8 hours, eventful 0.35, kinds motive 4 to thread 4.
`engine_roll`: chance 0.4 a tick within reach (bands here 55, near 45), forced after 24 quiet hours, at most 2 live within reach.

| tier | weight | stages | days | resolved_by_others | made by |
|---|---|---|---|---|---|
| normal | 80 | 1 | 1-2 | 0.5 | the engine (`engine: true`) |
| uncommon | 15 | 2 | 3-6 | 0.35 | the engine |
| rare | 5 | 3 | 7-14 | 0.2 | the model, `fallback: engine` |
| campaign | none | 4 | 30-90 | 0.05 | the model; its own slot, every 60 days (events.yaml:10) |

`start_thread` pulse.py:334 calls `threads.build` (threads.py:288), no call. Model tiers: `pulse_thread` (pulse.py:386), within
`max_new_events_per_action: 2`. Ending by time: `tick_threads` pulse.py:584-606 (`end_thread`, `resolver` 610).
data/rules/threads.yaml: 55 templates carry `paths` (kill, contract, persuade, find) and `contract`; none carries `parts`.

**Tasks and prompts.** budget.yaml: `situation_parts` optional, dropped, 800 (:83), in `asked_outside`; `event_judge` optional,
dropped, 350 (:78), not in it; `situation_agree` 20 (:85). situations.yaml asks 1,400 for parts (:136) and 900 for a ruling; the
budget's estimates are lower than both. Prompts in engine/pulse_prompts.py: PARTS_SYSTEM 215, JUDGE_SYSTEM 160, JUDGE_PARTS_SYSTEM 181.

**The budget** (checked: engine/budget.py:135-154; data/rules/budget.yaml:1-19). One rule: 60 seconds of model time for the longest
turn, margin 5, floor 8, reserve 20 for the passage. An optional call that does not fit raises `Dropped` (or `Deferred` for a
`later: deferred` task). The card: 756.8 prompt and 31.7 answer tokens a second (data/measured/card_profile.yaml, scaled from an
A4000). The background lane (llm/worker.py, `max_wait: 120.0`) is used only by npc/backfill.py and character/creation.py.

**Tests.** births_546 (births, tries, adoption, heart, due, waiting, a fight blocks a birth, normal never due);
situation_ruling_547 (`ruled`, `keep_changes`, `events.judge` with parts 201, 222; `after_deed` 494-554); situations_542;
situation_fixes_545, ways_545; situation_ab_543; events_test; matters_test:125-143 (a hand-in ends the thread "settled by you":
f598 changes this on purpose); settled_deed_578; threads_test, pulse_v2_test. Nothing pins `per_day` or `max_calls` by name.

## 3. Objects, features, entities

1. **Entities.** Table `entities(ref PK, kind, state, place, owner, deadline, json)`, indexed (kind,state), (owner,state),
   (place,state): storage/campaign.py:181-189. Store: `save_entity` 370 (upsert, skips the lifecycle), `delete_entity` 377,
   `load_entity` 382, `find_entities(kind, state(s), owner, place)` 388. No query by name. Model core/models.py:314: `name`, `look`,
   `tags: dict[str,int]` (condition to end minute), `links`, `data`, `history` in the json. Engine (engine/entities.py): `get` 172,
   `begin` 176 (`L[kind]`: a kind missing from lifecycles.yaml is a KeyError), `move` 186 (ValueError when the lifecycle forbids it;
   12 history rows), `final` 201, `_publish` 205 sends `StateChanged`. `problems()` 210 checks a lifecycle's own shape, called from
   data_check.py:586. Lifecycles today: hire, feature, captive, stock, offer, obligation. A new kind needs no migration.
2. **Features** (engine/features.py). `grows_here` 49 (False for road, dungeon, town, city, village), `here` 57, `change` 96 (states
   in `data["now"]` as {state: until}, by features.yaml `becomes`: lit, dark, blocked, barred, opened, cleared, flooded, collapsed,
   fouled, marked), `roll_holds` 131, `register` 159 (ref `feature:<place>:<slug>`; data: kind, what, depth, links, origin, made,
   holds, optional open, clue, tags, entry), `ensure` 186 (not capped), `room` 216 (most 9, 3 an hour; called by `adopt` 248 and
   `grow` 225 only), `find` 281 (word overlap), `spot_of` 300. State changes on features bypass lifecycles (no `StateChanged`).
   `adopt_from_passage` is scenes/part_actions.py:215 (a regex, wild places only), called from world.py:2701.
3. **Marks.** `PlaceState.marks: list[str]` (campaign.py:54); `add_mark` world.py:2386 (dedupes, capped at 12 by a slice in code);
   `marks_keep: 12` pulse.yaml:77. Read back in two places only: the narrator's "LASTING MARKS" (world_prompts.py:185 through
   world.py:271, 288, 2648) and mentor_actions.py:180. `part_of_here` (explore_actions.py:22) matches four-letter words against
   `place.visible` and the last passage, not marks.
4. **Pick up.** `on_pick_up` scenes/inventory_actions.py:273; `inv.pick_up` (engine/inventory.py:297) searches only
   `PlaceState.ground` (dropped Items, `leave_on_ground` 292). Nothing matched: a narrated `SCENERY_PICKUP` (world_prompts.py:100),
   nothing stored. Pinned by scenery_test.py.
5. **Effects and checks.** engine/effects.py is combat only (`ActiveEffect` 46; slots status, buff, curse, ground 101;
   data/rules/active_effects.yaml; `combat.add_status` combat.py:1148). `checks.chance(c, check, active_triggers, npc=None,
   extra=())` returns (percent, why) at checks.py:46: `extra` is a list of (label, amount), a ready way in for a modifier.
   `roll(odds, rng=None, c=None)` returns (degree, die) at 95.
6. **By meaning.** llm/embed.py: `available()`, `vectors()` (LRU 2000, charged to the turn through `budget.embed`), `cos`, `closest`,
   `whole`. engine/retrieval.py:73 `by_meaning(text, rows, label, k, floor)`. Callers fall back to word match when unavailable.
7. **Tests.** features_test, ruling_test (make_room, verdict, means_of), rulings_421_test, improv_test, plan_limit_test, stakes_test,
   nightrun_review_test, town_memory_484_test (marks), identity_test, lifecycle_test, scenery_test, ground_words_571_test.
8. **One-player reads not to copy.** features.py:283, 301-302, 317, 330; ruling.py:66, 92, 132, 136, 174, 189, 213, 242, 269;
   entities.py:60-95. `appear` already uses `ws.acting` (ruling.py:198, 233).

## 4. The recordings

- data/replay/sessions: stub_short (41 inputs), stub_party (15), stub_fight (27). `tools/rerun.py` `replay` (330) compares after each
  input the state digest (401), outcomes, committed operations, presented outcomes and the shown-words hash (416); each call by
  kind, title and `request_hash` (276-280), which includes the schema's sha: a changed contract parts the replay only where a
  recorded call uses it.
- `data_hash` (storage/statehash.py:110): every file under data/ except replay, measured and runtime, plus the model id and
  `migrations.CURRENT`. rerun only warns on it (338); golden_replay_test.py:31-32 fails on the warning; budget_data_459_test.py:94
  and isolation_456_test.py:126 pin it too.
- stub_short (checked): input 37, "I go to the merchant and help with what they need.", plays `action:other` and logs
  "improvised (attempt: help the merchant: d) - strong success", on the stub's default `cost` ruling. It also has a situation born
  (a `threads` diff and `thread:367cedc0` memories at rows 35-36, a queued "Hard bargains at Willowmead"). stub_party and stub_fight
  have neither.

## 5. The world row, deeds, gates

- No engine/worldstate.py yet. Load and save: storage/campaign.py:404-408 (kv key "world_state"; each load a fresh parse). The key is
  named only in storage/ (campaign.py:4, 405, 408, 924, 938, 947; migrations.py:236, 270, 294). 84 loads and 40 saves outside tools
  (8 of the loads in simbot.py, 1 in data/replay/scripts/stub_fight.py).
- Doc 13's lists hold: the 13 effect appenders (drift.py:220; events.py:257, 1067, 1291; pulse.py:852, 856, 864; stakes.py:191;
  world_improv.py:79, 87; arc_actions.py:608, 615; road_actions.py:537), the 4 thread appenders (events.py:965, pulse.py:431,
  stakes.py:222, starts.py:139), the rebinds (drift.py:196, pulse.py:675, 892, standing.py:118), the four readers pulse.py:83-106
  (16 call sites in 8 modules).
- **Not in doc 13:** the news rebinds `state["news"] = cap_news(...)` at pulse.py:984 and 992 (add to f590's RECORDED); direct
  appends to other lists at events.py:207 (camps), 988 (assaults), 997 and 1075 (player_events), out of f590's scope but worth a
  line there; starts.py:149, a deed appended with no `by`, `seq` or trim (f591).
- f589's startup checks do not exist yet: `keep_deeds` (events.yaml:39), `history_keep`, `news.keep`, `news.keep_days`
  (pulse.yaml:79, 84-85). data_check.py:579 is the consequences' deed kinds (kill, offense, quest_done, persuade, deliver,
  dungeon_cleared, found, defend, settled); gift is not in it though gift and bribe are ledger kinds.
- Deeds (engine/deeds.py): KEEP 14, `tick` 17, `add` 25 (f578), `log` 35 (loads, adds, saves; writes nothing on an empty row;
  swallows exceptions), `since` 49, `describe` 53. Writers: reactions.py:134 (`log`), events.py:547 (`add`, the settled deed),
  starts.py:149 (direct). `tick` alone at situation_parts.py:1004, 1350, 1354. Twelve events override `ledger_row`
  (domain_events.py:218): CreatureKilled, Theft, BreakIn, PersonHarmed, Bribe, Gift, Delivered, ContractDone, Persuaded,
  DungeonCleared, ClueFound, GateHeld.
- f579's pins: world_script_579, rollback_fields_579, stream_key_579, console_bytes_579. tools/sim/world_script.py (`play`,
  `run_apart`, `world_text`; seed 11; 13 coverage flags, a player-ended matter at 108-109, the judge's ending at 116,
  `pulse.end_thread` at 159) is the gate for the situation work: extend its coverage, never weaken it.
- The price gate: `tools/latency.py --gate` (`gate()` 432) prices each recorded input at the tasks' `answer_tokens` against
  data/measured/bundle_d_baseline.yaml and checks every input under the limit; `--rekeep MOST --note` (447, f571) is for a cost
  the owner accepted. A grown `answer_tokens` moves both the hash and the gate.
- Slots (f536): llm/llama.py:352-369; `interpret_action` alone on slot 0, the rest on the shared slot, a call bound for a slot the
  worker holds taking the task's own (364-365). The map is in data/runtime/server.yaml (not readable by the survey).
- Switches to copy: `enabled` in data/rules/audit_log.yaml:5 (read at llm/audit.py:34-39 with a config override);
  `DND_THINK_TASKS` (config.py:8, kept in a recording's meta and restored by rerun.py:350-352), as `DND_SAMPLING_ARM` is on the
  prose branch.
- The night's counts: `latency.goal_lines` (tools/latency.py:742-760) from the turn rows' outcomes and refusals.jsonl
  (engine/refusals.py:36, engine/ledger.py; nightrun.py:569).

## 6. Not verified

- The game-day count of births (the plan's "one or two a day" is from the weights; count it on the pod).
- The tier of stub_short's situation, and so whether f599's reach rule makes it ask for parts.
- `engine/relevance.py`'s API, the inventory GOODS structure, `ask_back`'s internals (scenes/audit_actions.py:170).
- The exact corpus counts; whether the reputation table has every tier (events.py falls back to 3).
- Whether the tests named here pass today: nothing was run. Run the suite before f589 for a clean start.
- data/runtime/server.yaml's contents (permission denied to the survey; still the owner's to confirm, GOALS.md).

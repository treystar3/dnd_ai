# 14. Phase 2 plan: pillar 2 outside combat

Status: the plan, with the owner's answers of 2026-11-11 (section 7); nothing built. Written 2026-11-11 on `pillar2/outside-combat` (cut from `foundations/early`, PR #38).
It turns the roadmap's phase 2 (docs 01, 02 steps 2 to 4, 05 steps 1 and 2) into features in build order, after a survey of the code
those docs describe. The owner's four answers of 2026-11-11 are in GOALS.md ("Phase 2, pillar 2 outside combat").

How it was made: four read-only surveys of the code (rulings; situations and the judge; objects, features and entities; the world row,
the budget and the gates), each claim with its file and line, and the claims this plan leans on most read again by hand.
The map itself, with notes for whoever builds, is docs/design/15_phase2_survey.md.

Feature numbers below are provisional: each takes the next free number when it is built. f582 to f588 are used on `prose/section-a`,
so this phase starts at f589. Doc 13's "f582" and "f583" are this plan's f589 and f590; doc 13's later numbers (phase 3) move up after
this phase.

## 1. What the survey found that changes the plan

1. **The end-reading was never built.** Docs 01 and 02 say "use the same end-reading as f549". There is no f549: the commits for f546
   and f547 name it as the next step ("f549 reads the end from the world") and stop. A situation's `heart` (its original threats and
   stakes) is written once at birth (engine/situation_parts.py:402) and nothing reads it. Today a situation with parts ends only by an
   engine-checked way, by time, or by the old judge; a ruling's kept changes end nothing (engine/events.py:508-520). "Threads ending
   from the state of the world" is therefore new design, not reuse, and it is the largest unknown in the phase.
2. **The gate was never widened either (the planned f548).** Which deeds reach a ruling is still the old judge's list
   (data/rules/events.yaml:38), its tier filter and its caps (events.py:457-464). Gifts, bribes and offences are logged as deeds but
   never ruled on; an improvised act is not a deed at all (data/rules/reactions.yaml:86 has no `ledger`).
3. **There is no kept ruling anywhere.** Doc 02 writes `scene.rulings.get(key)`; no such store exists. The reuse rule (the owner,
   11-08, and "the ruling is kept, a no included, so asking again never re-rolls it") is all new, and it has to live in the save, not
   in the scene, to survive a reload and to replay.
4. **A birth is a foreground call, one an input, and a tight turn burns its tries.** `situation_births` runs after the tail
   (scenes/world.py:470), inside the turn's 60-second budget as an optional call. When it does not fit it is dropped, and a drop
   spends one of the birth's three tries (world.py:488-491); past three the engine's own parts stand. On the 3060 (31.7 answer tokens
   a second, data/measured/card_profile.yaml) a parts answer of 800 to 1,400 tokens is 25 to 44 seconds. By the weights in
   data/rules/pulse.yaml, births today are rare (one in some weeks of game time: rare and campaign only); with normal and uncommon
   added they are roughly one or two a game day (an estimate from the weights, to be counted on the pod). Built as it stands, many
   of those births would be dropped on a busy turn and fall to the engine's fallback parts, built only from what it already laid.
5. **Both ruling calls are made inside the transaction.** `ruling` and `event_judge` are not in budget.yaml `asked_outside`
   (data/rules/budget.yaml:27-33); they are the f470 ratchet's legacy residue. The new call should be asked before the transaction
   (read, ask, commit), as every family moved since f485 is.
6. **`ruling.ask` has a second caller.** Road hazards use it directly (scenes/road_actions.py:484, f447), with their own odds and no
   `make_room`. Replacing `ruling.run` leaves that site standing.
7. **Things are strings.** A ruled "loose rock" is a mark on the place (engine/ruling.py:199), shown to the narrator and to nothing
   else. Picking up scenery is narrated and nothing is stored (scenes/inventory_actions.py:273, pinned by scenery_test.py). There is
   no `object` lifecycle (data/rules/lifecycles.yaml), and `Entity.tags` is already a map of condition to end minute
   (core/models.py:314), so doc 05's tag list cannot be that field.
8. **Combat's side of doc 02 step 2 has nothing to stand on outside combat.** engine/effects.py is combat only. Generic states,
   `can_take` and `tag_mod` would be written with no caller until phase 4.
9. **The kept recordings notice all of it.** stub_short holds one improvised line through `ruling.run` (input 37, "I go to the
   merchant and help with what they need.") and one situation born. Every new or changed file under data/rules moves the data hash,
   and golden_replay_test fails on a hash that differs, so each such feature re-records the three recordings for the hash alone.
10. **New code would inherit one-player reads.** engine/ruling.py, features.py and entities.py reach for `ws.player` in about twenty
    places (ruling.py:66, 92, 132, 136, 174, 189, 213, 242, 269; features.py:283, 301, 317, 330). The new modules take the acting
    character's id from the start (checklist 8).

## 2. Shape

- **Three tracks.** A: groundwork with no behaviour change. B: the one ruling outside combat, built unused behind a switch, measured,
  then switched on. C: situations (the gate, the end-reading, parts for every tier).
- **The old path stays until the new one is measured.** `act()` is reachable only with the switch on; the suite and the recordings
  run the old path until the pod session, then the switch flips in one feature with one explained re-record.
- **One ruling call an act, asked before the transaction.** It carries the changes to a situation's parts too, so an improvised act
  never costs a second call.
- **Outside combat only.** Combat's improvisation, action tags, generic combat states and creature parts are phase 4 (doc 02 steps 5
  and 6), on top of phase 3's groundwork.
- **Certain cases first, the model second.** What the engine can decide by id (a named threat killed, a condition met) changes with
  no call; the model is asked only where judgment is needed, and its answer is kept.

## 3. Features in build order

### Track A: groundwork (stub suite only; replay exact)

**f589: the access layer** (doc 13's f582, as designed there). `engine/worldstate.py` and a seam on the store with `load`, `save` and
read-only narrow readers (`effects_at`, `threads(status)`, `deeds_since`, `news`); the stale-save detector for the suite and night
runs; startup checks for `keep_deeds`, `history_keep`, `news.keep`, `news.keep_days`. Survey note: the four readers sit at
engine/pulse.py:83-106 with 16 call sites; 84 loads and 40 saves in all, as doc 12 counted.

**f590: one append path per list** (doc 13's f583). `add_effect` and `add_thread`; the 13 effect appenders and 4 thread appenders
are where doc 13 lists them (checked, none moved). Added to its RECORDED list: the news rebinds at pulse.py:984 and 992.

**f591: the start's deed is numbered like any other** (the owner, 2026-11-10: "as its own feature"). engine/starts.py:149 goes
through `deeds.add`. No recording contains it.

### Track B: the one ruling outside combat

**f592: objects are entities** (doc 05 step 2; pillar 1).
- Data: an `object` lifecycle in lifecycles.yaml (`here, carried, broken, destroyed, hidden, gone`); `data/rules/objects.yaml` with
  the closed tag list (heavy, flammable, sharp, container, light_source, climbable, cover), `objects_per_place`, a carried cap per
  character, and the days an unremarked object lasts. Tags live in the entity's `data["tags"]` as a list, as features keep theirs.
- Code: `engine/objects.py` (`make`, `here(place)`, `find`, `take`, `drop`, `change`), every function given the acting character's id.
  `ruling.make_room`'s `thing` branch makes an object and still adds its mark (the mark stays what people say of the place).
  `on_pick_up` looks among the place's objects before it narrates scenery: a template match becomes an item by the existing path,
  anything else is carried as an object (owner: the character).
- Caps: unowned, unauthored objects past `objects_per_place` go `gone`, oldest unremarked first.
- Tests: a ruled loose rock can be picked up, carried, dropped and found again after a reload; the cap trims; a broken object cannot
  be used; scenery with no object behind it is still narrated (scenery_test holds); two characters carry their own.
- Replay: the hash moves (two data files). stub_short's improvised line makes no `thing`, so nothing else should move; if it does,
  stop and read it.

**f593: targets by id, and the list of changes** (doc 02 sections 2 and 4, the part outside combat).
- `engine/targets.py`: `targets_for(scene, actor_id, ctx)` returns the numbered things an act can use or change, each with its id
  and kind: people present (`p1`), parts of the place (`f1`), objects here and carried (`o1`), the roads out (`r1`), and the parts of
  each situation whose trouble is near (`s1.2`), numbered as `parts_lines()` numbers them today. One printed form for the prompt, one
  lookup back to the record.
- `data/rules/changes.yaml`: the closed list of changes with the kinds each may land on. Phase 2 holds what can be applied outside
  combat: the situation ruling's words as they are (believes, warmer, lifted, safe, ...), `state` and `access` on a part or road
  (features.yaml `becomes`), `broken`, `mended`, `destroyed`, `found`, `hidden_here` on an object, `moved`. The combat rows
  (hindered, blocked, held, opened, harmed, their tier numbers, resistance and repeats) arrive with phase 4.
- data_check: every change's kinds exist; every situation word is still in situations.yaml's lists; no change is listed twice.
- Tests: the same thing is the same target across two builds of the list; a gone or carried-away thing is not listed; a situation
  part is listed only where its trouble is near.
- Replay: the hash moves (one data file); nothing calls it yet.

**f594: the act ruling, asked and kept** (doc 02 sections 3, 5 and 8; the reuse rule).
- Contract `ActRuling` and `ActChange` in llm/contracts.py, as doc 02 section 3, less the combat fields. A new task `act_ruling` in
  budget.yaml (required, sized from the pod session; first estimate 260), named in `asked_outside`. Its prompt lives beside the
  pipeline, built from today's ruling prompt (ruling.py:34-56) and the parts ruling's (pulse_prompts.py:181).
- The kept rulings: a capped store in the save, per character, keyed by the act's normalised words, the ids of the targets it names
  and a hash of their relevant state. A no is kept too. A changed circumstance (a target's state, a part's condition) is a new key.
  Cap and window in data (`data/rules/act.yaml`), oldest out first.
- `validate()`: pure. Capabilities through `means_of` (given the actor), every `uses` target exists, each change checked in order as
  one chain with `situation_parts.ruled()`'s rules for a situation's parts, people within the owner's caps.
- The owner's answer on strength: a strong success raises a change one step only when `uses` names a real target that enables it.
- Tests: the same act under the same circumstances makes no second call, across a save and reload; a changed circumstance does; a
  kept no stays a no; wings with no flight are refused; cover with nothing to hide behind is refused or makes an ordinary object
  within its cap; two characters keep their own rulings; a failed call keeps nothing.
- Replay: the hash moves (budget.yaml, act.yaml); the task is unreachable in the recordings.

**f595: `act()`, behind a switch** (doc 02 sections 4 and 6, outside combat).
- `engine/act.py`: targets, precheck (presence, reach, a gone target, capability), the kept ruling or the call, validate, resolve,
  publish, narrate. `resolve` rolls on the scene's dice with `checks.chance` and `checks.roll`, scales the changes by the degree,
  applies each through the game's own writers (features.change, objects.change, the situation's keep_changes), and on a failure
  applies one of the fail modes that mean something outside combat (time lost, noise, noticed, the object breaks, hurt).
- A new event `Acted` (a Deed, with a ledger row: the improvised act becomes a deed, in data/rules/reactions.yaml).
- The switch: `act.yaml enabled: false`, and `DND_ACT=1` for a measuring run, kept in a recording's meta as the sampling arm is.
  With it on, `on_other` calls `act()`; off, `ruling.run` as today. The rest check and the clue search before it stay as they are.
- Road hazards keep `ruling.ask` (f447 is its own decision). `ruling.py` keeps `ask`, `odds` and `means_of`; nothing is deleted here.
- When the ruling cannot be made, the act waits for it (f596). With the switch off, today's ask-back stands on the old path.
- Tests: with the switch on, a stub play through an act that makes a thing, one that changes a part, one refused, one failed, each
  compared for prose and state agreeing; with it off, ruling_test, rulings_421_test, improv_test and the recordings pass untouched.
- Replay: exact with the switch off.

**f596: an act that waits for its ruling** (the owner, 2026-11-11: built inside this phase; 11-08's "every consequential act
persists as an event, including those awaiting interpretation"). It replaces the ask-back of 11-09 on the new path.
- When the ruling cannot be made (the model down, a timeout, the budget), the act is kept for the character as a pending record in
  the save (capped, in data), the narrator tells the visible attempt and never its outcome, and the attempt's time passes.
- At the next input's edge, before that line is read and outside any transaction, the ruling is asked again. Made, the act resolves
  as any other and a short continuation tells how it went; then the new line plays.
- If what it named is gone or the character has left, it lapses in the story's own terms. After its tries (data) it is told as
  come to nothing and logged as a `ruling_failed` refusal, so the night's counts still see it. Nothing is ever rolled unruled.
- Its price falls on the next turn's budget as a required call; counted at the pod session.
- Tests: a failed call keeps the act and grants nothing; the next input rules on it first and tells it; a reload between the two
  keeps it; a target gone in between lapses it; past its tries it is refused and counted; two characters' pending acts stay apart.
- Replay: exact with the switch off.

### Track C: situations

**f597: the gate** (the planned f548; doc 01 recommendations 2 and 3).
- A deed reaches a situation when it touches it by id: its person is one of the situation's people, its place is where the trouble
  is, its target is one of the heart's threats, or it carries the situation's id. The region test (events.py:463) goes.
- Certain cases need no call and stay first: a way met, a condition met, a named threat killed.
- Otherwise the ruling is asked, at every tier, with no daily cap and no count: `judge.tiers`, `per_day` and `max_calls` leave
  events.yaml. A repeat is stopped by the kept ruling (f594's store, the same key rule). `relevant_deeds` grows by gift, bribe,
  offense, found and acted.
- Cost is held by the budget, never by the story: the call stays optional, and a ruling that does not fit is kept as a pending
  record on the situation and asked at the next input's edge (the owner, 11-08: "a queued event may lose its priority, never its
  unresolved meaning"). It is asked outside the transaction; the old in-transaction call goes from the f470 residue.
- Tests: a gift to a situation's person at a normal tier is ruled on; the same gift again makes no call; ten kills in the region
  that touch nothing make none; a dropped ruling is asked on the next input and loses nothing; the call count over the world script
  is asserted, so a later change that multiplies it fails.
- Replay: events.yaml moves the hash. stub_short's situation is touched by no deed today; if a call appears, stop and read it.

**f598: the end, read from the world** (the planned f549; doc 01 recommendation 4). Its own short design note comes to the owner
before it is built: docs/design/16_end_reading.md. The outline, with the owner's answers of 2026-11-11:
- A pure function over the heart and the world: for each threat, can anyone or anything still impose it (its effect lifted or run
  out, and its controller gone, unable or no longer willing); for each stake, is it safe, lost or still at risk.
- From those, whether the situation is over and how: achieved, partly achieved, lost, transformed, abandoned. The engine decides;
  the model is never asked whether it is over (as f547 left it).
- Read after every kept change, every deed that touched the situation and every tick. `finish()` is the one way out, so every
  ending leaves its 'settled' deed, its follow-up and its memory (f578).
- A contract hand-in stops ending a normal or uncommon situation on its own (events.py:392-401): it is a deed like any other, the
  contract pays by its agreement, and the situation ends when the reading says so.
- What an ending gives: town reputation by ending, in data (most for achieved, some for partly, none or a loss for lost, nothing
  for abandoned); a transformed ending starts its follow-up; a promised reward follows its agreement. Numbers at the balance pass.
- Tests: the threat's holder killed but the condition still imposed by another is not over; everyone at stake lost is over and
  lost; a hand-in whose job removed the threat ends it, one that did not does not; the same world read twice gives the same ending.

**f599: parts for every tier, from the model** (the owner, 2026-11-11).
- `births.tiers` and `adopt_tiers` take normal and uncommon; the checks at situations.py:886-892 change with them; the stale comment
  at situations.yaml:287 goes. New people stay at none for these tiers.
- For an engine-built situation the "prose" its parts must agree with is its template's telling.
- When a birth is due (the owner, 2026-11-11): when the situation is within reach of a character, or that character first hears of
  it or acts on it; nearest first. One far away never asks and ends as it does today. A birth dropped for the budget waits without
  spending a try (a try is for a model failure).
- Tests: births_546's "normal is never due" is replaced by the reach rule's cases; a far situation asks for nothing and ends as
  today; a drop for the budget spends no try; three model failures still fall to the engine's parts.
- Replay: situations.yaml moves the hash, and stub_short's situation, if within reach, now asks for its parts: a real difference,
  read line by line before it is kept.

**f600: an act moves a situation** (doc 02 section 7). `act()`'s kept changes on a situation's parts go through f597's gate as
already ruled (no second call) and then to f598's reading. Tests: barring the granary door moves the looting at every tier; the act
and its ruling are one call in the log.

### The measurement, then the switch

**f601: both paths on the corpus.** `tools/ruling_eval.py --live --path old|new`, the corpora (about 50 and 28 cases in
data/replay/ruling_cases*.yaml) given the targets each case needs, and new cases for objects and for acts on a situation's parts.
It prints false acceptances and false rejections side by side.

**The pod session** (one rented card; the price stated before it is created). In order: the corpus on both paths; two night plays a
path on the same seeds for the made room and said no counts, the refusals log and the turn's time (tools/latency.py); the count and
seconds of births and situation rulings a game day at 3060 speeds; and the f536 slot question (does the understanding's checkpoint
on slot 0 hold from turn to turn, and does a background call on the shared slot delay the turn). Kept under docs/measure.

**f602: a reader for the pod's two open questions.** `tools/night_measure.py` reads a night's run folders for what the other
readers do not answer: the two slots (does the understanding's cached prompt hold from turn to turn, and does a call on the shared
slot make the turn wait) and births and situation rulings a game day, their seconds priced on the minimum card as card_profile scales
(the owner, 2026-11-12: built while the pod's first night played, before the switch; the switch moves to f603).

**f603: the switch flips.** Only on the owner's go, with the session's numbers in front of them (the owner, 2026-11-11: no bar
fixed in advance; "show me the numbers"): false rejections and false acceptances on both paths, the night's counts, the turn's time. `act.yaml enabled: true`; stub_short re-recorded for its one
improvised line, each changed row explained; `world_improv.resolve` and `ruling.run` retired for typed lines (the phrase tables stay
in data; `is_rest` and the hazard's `ask` stay). `tools/latency.py --gate` re-priced if the ruling's answer is larger.

## 4. Order and what can run together

```
f589 -> f590 -> f591                     (A, in order)
f592 -> f593 -> f594 -> f595 -> f596     (B, in order; f592 can start beside A)
f597 -> f598 -> f599                     (C, after f590; f597 uses f594's store)
f600                                     (after f595 and f598)
f601 -> f602 -> the pod session -> f603   (last)
```
A and C touch engine/events.py, pulse.py and situation_parts.py; B touches engine/ruling.py, scenes/world.py `on_other`, inventory
and new modules. The two can be built side by side, but each data change re-records the same three recordings, so they land one at a
time.

## 5. The recordings and the hash

| Feature | Data that moves the hash | Expected in the recordings |
|---|---|---|
| f589, f590, f591, f595 | none | exact |
| f596 | act.yaml (the pending act's cap and tries) | hash only |
| f592 | lifecycles.yaml, objects.yaml | hash only |
| f593 | changes.yaml | hash only |
| f594 | budget.yaml, act.yaml | hash only |
| f597 | events.yaml, reactions.yaml | hash only expected |
| f599 | situations.yaml | hash, and stub_short's situation may ask for parts |
| f603 | act.yaml | hash, and stub_short's improvised line |

Eight re-records, six of them for the hash alone. Each follows the rebless skill: read what first differs, keep only what the
feature explains, list the rows in the commit. Two things outside this branch also re-record the same files: `prose/section-a`
already has (f583, f587, f588) and will again when it is rebased onto this phase (the owner's order), and phase 3's storage move
wants one quiet re-record after both.

The recordings are thin for this work (one improvised line, one situation). The gate for it is the stub suite: the world script
(tools/sim/world_script.py, f579) gains a situation ruled on, ended by the reading, and an act that moves one, with its coverage
asserted.

## 6. Risks

1. **The end-reading is undesigned and decides what "won" means.** Guard: its own design note and the owner's answers before f598;
   pure and tested on built worlds before anything calls it.
2. **Births price the turn.** Guard: the reach rule, no try spent on a drop, and the count measured on the pod before f599 is
   switched to every tier in shipped data if the numbers are worse than estimated.
3. **Calls multiply once the caps go.** Guard: relevance by id, certain cases with no call, the kept ruling, a call count asserted
   over the world script, and the night's count read at the pod session.
4. **Two ruling paths drift while both live.** Guard: the old path's tests stay untouched until f603; the corpus runs both.
5. **The kept ruling's key is wrong in either direction:** too loose and a changed world reuses a stale ruling, too tight and
   nothing is ever reused. Guard: the state hash covers only what the ruling read (the targets it names), with tests for both.
6. **A false object.** The model names a thing the place could not hold. Guard: objects are made only through a ruling's `needs`,
   within the cap, as marks are today; the corpus gains cases.
7. **Eight re-records invite a careless one.** Guard: the rebless rule each time, and hash-only ones proven by an otherwise exact
   replay.
8. **Phase 3 rewrites the same turn code.** New modules sit in engine/ and take the actor's id, so phase 3's context moves under
   them; `on_other` changes by one branch.

## 7. The owner's answers (2026-11-11; GOALS.md holds them)

| Question | Answer |
|---|---|
| 1. When a normal or uncommon situation asks for its parts | When a player can meet it: within reach of a character, or heard of, or acted on. A far one never asks. A drop for the budget spends no try. |
| 2. A contract hand-in | The contract pays by its agreement; the situation ends only when the world says so. |
| 3. What each ending gives | Reputation by ending, in data; a transformed ending starts its follow-up; numbers at the balance pass. |
| 4. An act whose ruling could not be made | The pending act is built inside this phase (f596), not after the switch. |
| 5. The order branches land | PR #38 now, and phase 2 on it. `prose/section-a` stays apart and is rebased onto phase 2 when it lands, its recordings re-recorded then. A3's exemplars stay for narration and speech; the fight pool comes out until phase 4 reshapes fight prose. |
| 6. Combat's rows | Wait for phase 4. |
| 7. Road hazards | Keep their own ruling call through this phase. |
| 8. The bar for the switch | None fixed in advance: the numbers are brought to the owner. |
| (f597, asked in its review) A situation without parts | Ruled on not at all: the old judge is retired; it ends by its ways and its time. |
| (f597) Where a waiting ruling is asked | After a later line, where births are asked, never before the player's line. |

What the answers changed in this plan: f596 is new, so the pod session compares a path that asks back with one that waits (the
corpus measures rulings made, so it is unaffected; the nights will differ where a ruling fails, and those are counted apart).
`prose/section-a` carries f582 to f588 and will be re-recorded once more when it lands on top of this phase.

## 8. Not in this phase

Arcs as campaign situations (the owner: after phase 2). Combat onto the one ruling, the fast path by meaning, and the merged
understanding and ruling call (phase 4). Parts of settled places, the resolver by meaning, narration read back in the background and
`seen_by` (doc 05 steps 3, 4, 5 and 7). The world lists into tables (phase 3). Births on a background lane, which doc 08 wants for
multiplayer, waits for phase 3's turn context.

# 1. Review of the modules I had skimmed

Commit 06b393c. Read in full or near full: `situations.py`, `situation_parts.py`, `threads.py`, `arcs.py`, `quests.py`, `matters.py`,
`stakes.py`, `consequences.py`, `deeds.py`, `domain_events.py`, `events.py` (the resolution path), and `pulse.py` (outline and the
thread lifecycle). For `combat.py` (3,137 lines) I read the outline, the control contest, the riders and the improvisation hookup in
`services/fight.py`. I did not read every line of the enemy AI.

## Corrections to what I told you earlier

**"Seven overlapping systems to merge into situations" was wrong.** There is one backbone, the **thread**: a record in
`world_state["threads"]`. The modules are layers on that one record, not rival systems:

| Module | Its job on a thread |
|---|---|
| `pulse.py` | Starts, ages and ends threads, and applies their effects (closures, danger, prices, news) |
| `threads.py` | Builds normal and uncommon threads from templates with no model call, and re-tells them once the player arrives |
| `matters.py` | How a thread is met (a door: the board, someone's word, a scene, a summons) and its clues |
| `situation_parts.py` / `situations.py` | The parts of a situation: people, stakes, wants, conditions, evidence. Checks them, writes them into the world, and rules on acts against them |
| `events.py` | Big threads: spawns, camps, seals, resolution paths, the judge, cataclysms, rewards |
| `consequences.py` | Deeds that start a thread |
| `stakes.py` | Who posted a board job and why. It can open a matter |

The two tracks that really are separate are **guild contracts** (`quests.py`, plain dicts) and **arcs** (`arcs.py`, fixed chains of
contract steps). So the "merge" is much smaller than I said. It isn't seven systems into one; it's closing gaps in one backbone, plus
deciding what to do about contracts and arcs.

**The effect-primitive idea from my improvisation design already exists.** It's in the situation ruling. `llm/contracts.py
RulingChange` is a closed vocabulary of changes (`believes`, `doubts`, `afraid`, `surrenders`, `lifted`, `broken`, `found`, `destroyed`,
...). Each change has a cause (`because`: words, coin, goods, force, evidence) and a list of the earlier changes it depends on (`needs`).
`situation_parts.ruled()` checks them as a chain, and `keep_changes()` writes them through the game's own writers. That is the right
pattern. The improvisation design (doc 2) now extends it instead of inventing a second one.

**The combat rules are deeper than I implied.** There are zones and rows, engagement, telegraphed blows, interposing, orders to allies,
riders on abilities, an element wheel, morale and surrender, and a graded control contest with diminishing returns. The 80% of fights
rated trivial comes from which encounters are picked and the level ceiling. The rules themselves aren't thin.

**The narration read-back exists for wild places.** `scenes/part_actions.py adopt_from_passage()` turns parts the narrator names into
real entities, using a regex and the feature kinds' vocabulary, within a budget. What's missing is coverage: towns and buildings, and
objects as well as places.

## What I found

### A. Most situations can't be resolved openly
- `data/rules/pulse.yaml`: normal threads make up 80% and uncommon 15%. `situations.yaml` only gives parts to **rare and campaign**
  threads at birth (`tiers: [rare, campaign]`, with adoption for rare, campaign and cataclysm).
- `events.judge_ok()` only calls the judge (and so the situation ruling) for `tiers: [rare, campaign, cataclysm]`, at most **once a
  game day** and **8 times in all** per thread (`events.yaml judge`).
- `events.after_deed()` ends a normal or uncommon thread as soon as a linked contract is handed in (`quest_done`), "settled by" the
  player, with a reputation reward.

So for about 95% of situations, the only ways to resolve them are the fixed paths and handing in a contract. That's the
completion-based ending the owner rejected on 2026-11-08 ("never pretending they completed it successfully"; "rewards follow actual
accomplishments"). The daily cap and the cap of 8 turn a technical limit into something that affects the story ("technical limits must
never become fictional restrictions"). The owner's own instruction to reuse an earlier ruling when circumstances haven't changed is
the right substitute for those caps.

### B. Improvised acts never reach a situation
`events.judge.relevant_deeds` is `[kill, persuade, dungeon_cleared, quest_done, deliver, defend]`. An improvised action outside combat
publishes an `Improvised` event, but no deed. So "I sabotage the bandits' boat" or "I bar the granary door against the looters" can
never move a situation, even a rare one with parts.

### C. Three separate rulings with three different output formats
1. `engine/ruling.py`: improvisation outside combat (`Ruling`: needs, changes to parts of a place, stakes).
2. `situation_parts.rule()`: acts against a situation (`JudgeVerdict.changes: RulingChange`).
3. `events.judge()` for big events without parts (resolved, partial, no).

Combat improvisation has no ruling at all. Each ruling has its own prompt, format and checks, so a single act against a situation that
happens in a place, during a fight, gets judged by whichever path happens to catch it.

### D. Two confirmed bugs in improvisation (doc 3)
- The combat improvisation roll ignores the fight's dice.
- When the ruling call fails, an impossible action can succeed.

### E. Combat improvisation skips the control contest
Abilities that control a target go through `combat.contest()`: a graded resistance, with diminishing returns and bosses counting as
already controlled once. The improvised `disable` and `force_move` effects call `add_status` directly. So improvised control is weaker
per use but **can't be resisted by wisdom and never gets diminishing returns**, and that includes against bosses. Repeating "I throw my
cloak over its head" is a reliable lock that abilities can't match. It's the inverse of "an ability is a promise".

### F. Arcs are fixed skeletons
`arcs.py` says "the model dresses the skeleton once; nothing it says can add a step." A chain is a fixed list of steps: a person first,
the finale last. That fits poorly with "Campaigns and pulse quests like this should be open ended to how a player tackles them." Arcs
could become campaign-tier situations whose steps are parts and paths, not a required sequence.

### G. Still holds from before
- All threads, news, effects, deeds and history live in one `world_state` JSON row, read and written whole (`deeds` keeps 300,
  `history` is capped). It's capped, so it doesn't grow without limit, but every `after_deed` call loads and saves the whole blob, and
  the code is untyped dicts.
- `domain_events.py` is a clean, synchronous bus with typed events, and should be the spine for the changes below.

## Revised structural recommendations (replacing my earlier "merge into situations")
1. **Give every tier parts.** Normal and uncommon templates in `threads.yaml` should give their thread parts with no model call (the
   owner already approved template parts for the common tiers on 11-07). Then every situation can be resolved through its parts.
2. **Remove the judge's tier filter and its caps, and use cached rulings instead.** Keep the key the owner specified (the same act
   under unchanged circumstances reuses the earlier ruling), and keep the background-slot budget for time.
3. **Make improvised acts and situation-relevant acts deeds**, so they reach a situation (`Improvised` gets a `ledger_row`, and
   `relevant_deeds` grows).
4. **End normal and uncommon threads from the state of the world, not from a hand-in.** Use the same end-reading as f549.
5. **One ruling with one output format** for improvisation, situations and combat (doc 2).
6. **Arcs become campaign-tier situations** (needs the owner's decision).
7. **Move threads and deeds out of the JSON row** (doc 5).

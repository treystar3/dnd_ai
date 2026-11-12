# 16. f598: a situation's end, read from the world

Status: a design note for the owner, nothing built. It is the planned f549, named in docs 01 and 02 and never written, and f598 in
docs/design/14. It decides what "won" means, so the plan asks for the owner's answers before it is built (section 6).

## 1. What the owner has already decided

- Open resolution, 2026-11-08: "A player should be able to end a quest badly without the game pretending they completed it
  successfully." Situations are resolved by the established state of the world, never by obstacle counts, mandatory combat, living
  bosses or prescribed methods.
- The objective comes from the situation's original facts: what threatens it, what is at stake, and who or what controls the
  relevant conditions. It is never re-read from the changing state.
- A threat is resolved when no one and nothing (a person, a faction, a mechanism or an environmental condition) can still impose the
  harmful condition. It is not resolved just because a person flees, dies or is won over.
- A situation ends when its objective is achieved, irreversibly lost, or otherwise settled. The engine names the ending: success,
  partial success, failure, transformation or abandonment. The model is never asked whether it is over.
- Rewards follow accomplishments and agreements, not completion alone. Only meaningful setbacks speed up the clock. A completed
  situation may give birth to a new one.
- 2026-11-11:
  - A contract hand-in pays by its agreement and no longer ends a situation on its own.
  - Reputation follows the ending, set in data, and a transformed ending starts its follow-up. The numbers wait for the balance pass.
  - A situation without parts is not ruled on; it ends by its ways and its time.

## 2. What the game already holds

- **`heart`** (engine/situation_parts.py:402). Written once, when the parts are written, and never again: the original facts.
  - Threats:
    - each harmful condition (closed, danger, prices), with where it lies, who or what imposes it (`by`, `by_kind`: person, group,
      creature, mechanism, nature) and the effect it laid;
    - each person who blocks an end to it;
    - each creature its ways must defeat (a named target, or a spawn).
  - Stakes:
    - each person it harms;
    - each good it puts at stake (scarce, stranded, wanted);
    - its place and town.
- **The parts as they stand.**
  - Each part's `now`: lifted, safe, moved, given up, lost, broken, mended, tested, found, destroyed, fled, surrendered, joined.
  - Each person's willingness toward each character (`willing[by]`: open, wary, hostile, refusing, terrified, committed).
- **The world.**
  - The effects each condition laid (`of_part`, `lifted`, `until`).
  - The situation's spawns (defeated or not).
  - Whether each person is alive (`npc.gone`).
- **The ways out today:**
  - a way met calls `finish` (engine/events.py);
  - time calls `end_thread` (engine/pulse.py tick_threads), settled by others by the tier's chance, else ignored with its fallout;
  - (until f597) the old judge's verdict.

  Nothing reads `heart` yet.

## 3. The reading

A pure function, `situation_parts.reading(store, world, state, th, t)`. It reads and never writes, and returns each threat and stake
with its standing, plus whether the situation is over and how.

### Each threat

| Threat | Resolved when |
|---|---|
| A condition | It is no longer in force, **and** nobody who could impose it again is able and set on doing so. "No longer in force" means its effect is lifted or has run out, or its part is `lifted`. "Able and set on it" means its controller (`by_kind` person) is alive, free (not fled or surrendered) and not won over (`willing` toward the acting character is not open, and they have not joined). A creature controller's spawn is defeated. A condition imposed by a group, a mechanism or nature is resolved once it is no longer in force. |
| A person who blocks | They no longer stand in the way: open, joined, surrendered or fled, or gone. Whatever conditions they impose are separate threats and are read on their own, so the blocker's death resolves the blocking, never the chain across the road. |
| A creature | Its spawn is defeated, or a kill of the named target was done where the trouble is. |

### Each stake

| Stake | Secured | Lost |
|---|---|---|
| A person harmed | `safe` | gone (dead), or in the hands of a threat the reading finds unresolved when the situation ends |
| A good | `moved` or `given_up` (delivered, handed over) | `lost` or `destroyed` |
| The place | every threat resolved | the time ran out with a threat unresolved |

A stake neither secured nor lost is **at risk**.

### When it is over, and how

| Ending | When |
|---|---|
| **Achieved** | Every threat resolved, and no stake lost. |
| **Partly achieved** | Every threat resolved, but some stake lost; or, at the time limit, some threat resolved and some stake secured. |
| **Lost** | Every stake lost, irreversibly (no one left to harm, every good gone), whatever the threats stand at; or, at the time limit, nothing secured. |
| **Transformed** | Every threat resolved, but one of its controllers is still alive, free and set against the character who acted (hostile, refusing or committed). The trouble ends; its source does not. Its follow-up is started (threads.follow_up "settled"), as the owner decided. |
| **Abandoned** | The time limit reached, and no character ever touched it (no change of theirs on its record, no deed of theirs that reached it). Today's path stands: settled by others by the tier's chance, else the fallout lands. |

`Lost` and `achieved` can be read at any moment. The rest are read only when every threat is resolved, or at the time limit.

### When it is read

- After every ruling's kept changes (f597's gate, an act through f595, a way met).
- After every tick of the pulse.

It is never read on a timer of its own, and never asks the model.

### What an ending does: `finish()`, the one way out

- Every ending goes through `finish()`, which gains the ending kind:
  - it lifts what the situation laid;
  - it records the ending;
  - it writes each contributor's `settled` deed (achieved, partly achieved, transformed; never lost or abandoned);
  - it adds reputation by ending (data: `memory.yaml reputation_by_ending`, a number by tier and ending);
  - it remembers the ending (matters.remember with the ending's own words);
  - it starts the follow-up (transformed always; achieved and partly by the chain's chance, as today);
  - it pays the grand reward for a campaign or cataclysm (achieved or partly only).
- **Contributors** are the characters whose kept changes on the situation's record resolved a threat or secured a stake (th["changes"]
  by `by`). Each gets their own deed and their share of reputation. With one character, that is the player.
- **Contract hand-in** (events.py:392-401): it stops ending the situation on its own. The contract pays by its agreement. The hand-in
  is a deed like any other, ruled on through the gate, and the reading decides.
- **A way met** for a situation with parts: it stops calling `finish` directly. It makes its certain change (met_way today), and the
  reading decides. A situation without parts keeps today's way to `finish`.

## 4. What it costs

Nothing on the model: the reading is arithmetic over the save, run after changes and on the pulse. The parts are capped by the owner's
decision ("no caps for anything but new people"), so a reading walks a handful of parts. It is never a stored list of its own.

## 5. Tests (tools/sim/end_reading_598_test.py)

- The blocker of a closed road killed while the chain stays in force: not over. The chain lifted by hand: over, achieved.
- The harmed person dead before the threat is resolved: partly achieved (threats resolved, a stake lost), or lost if they were the
  only stake.
- Every threat resolved while the controller is alive and committed against the character: transformed, with a follow-up queued.
- At the time limit with nothing touched: today's path (by others, or the fallout). Touched but unresolved: partly or lost by the
  stakes.
- A contract handed in whose job removed the threat: ended by the reading. One whose job did not: still active, and the contract paid.
- A way met: ended by the reading, not by the way.
- The same world read twice gives the same reading. Reading never writes.
- Two characters' changes: each contributor gets their own deed.
- The world script gains a situation ended by the reading (its coverage asserted).

## 6. Questions for the owner

1. **A threat resolved:**
   - The note's reading is "no longer in force, and nobody able and set on imposing it again". Is that the rule?
   - Should a controller won over count as unable, as the note has it? Or must they also be gone, or must the condition itself be
     made impossible (the chain cut, not just unchained)?
2. **Achieved against partly achieved:**
   - Does any stake lost make it "partly", as the note has it?
   - Or only the stake the situation was mostly about, for example the harmed person when there is one?
3. **Transformed:**
   - The note reads it as "the trouble ends, but its source is still free and set against the character, so a follow-up starts".
   - Is that the transformation meant? Should death, diplomacy and deception also be told as transformations when they end it?
4. **Ways:** Should a way met on a situation with parts feed the reading (recommended: one way to end, the world's), or still end it
   directly as today?
5. **The time limit:**
   - A touched situation is read at its last time (partly or lost by the stakes); an untouched one keeps today's roll for others or
     the fallout. Is that right?
   - "Only meaningful setbacks accelerate the clock" is not built here. Is that later, or is it part of this?
6. **Credit:** Should every character whose change counted be a contributor, with their own deed and reputation? Or only the one whose
   act resolved the last threat?

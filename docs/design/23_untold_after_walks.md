# f711: what the world does after a long walk is told, or waits until it can be

Pillars 1 (the world is real: prose and state agree) and 5. Found in the third blind play
(docs/play/2026-11-16_blind_play_journal.md, 20th day): `We walk on up the King's Pass to Ironvein.` walked 288 minutes and told the
arrival; then a matter fired, "Norvald Balarakk comes looking for the player" (The market at Ironvein), its passage was refused for
the turn's budget, and the player read **"The thing is settled. No passage came, and none is needed for it to be so."** Nothing was
settled. Looking about the gate next turn found no one seeking me. The same afternoon, after a road fight, the rest of the walk to
Parth ran in the same turn and both the fight's end and the arrival were lost ("It happened, and it holds. The story of it will have
to wait for another breath", which nothing ever makes good).

## What happens today (facts, traced)

- A turn has 60 s of model time (budget.yaml; GOALS f459: "the budget is not raised"). A long walk's own calls (road happenings,
  the arrival passage) can spend all of it. A required call past the floor is refused (BudgetSpent); an optional one is dropped.
- The arrival's matter check (matters.on_arrival, scenes/world.py turn: after the line's passage) runs whatever is left of the budget.
  A summons sets `summons = "met"`, puts the sender among those present for 120 minutes (ws.visit: in memory only, not saved), and
  asks for a passage. The state commits with the arrival; only the passage rolls back. Nothing retries: "met" is never pending again.
- A passage that rolls back prints a stand-in (engine/failures.py stood_standin): the ledger's facts when there are rows for it,
  else one of six `stood_any` lines (failures.yaml), all written for **the player's own deed** ("What you did stands"). A world
  happening has no ledger rows, so it gets a deed line, and some of those promise a telling that never comes.
- The deferred queue (f469, run_deferred) replays only banter, persona and arc work, never a matter's moment.

## The change

1. **A matter's moment waits for a turn that can tell it.** Before on_arrival fires a summons or a moment, it asks the budget whether
   a passage can still be paid for (the narrate estimate above the floor). If not, nothing of it happens this turn: it stays pending,
   is queued as deferred work of a new kind, `matter_moment` (f469's queue), and is fired at the start of the next turn while the
   acting character still stands in that town, as if they had just arrived. Walked away first, it waits for the next arrival there,
   as a pending moment does today. No state commits without its telling.
2. **Whatever the world does that the player must know is a fact, told plainly if its passage is lost.** A summons or moment writes
   a ledger row (a new kind, `arrived`: who has come and why, by label) beside its passage, so a lost passage prints that fact
   ("Norvald Balarakk, a land agent, is here and has been asking for you by name.") through the stood_lines that exist, never a
   deed line. This is the safety net behind 1 for any other cause of a lost passage (a timeout, the model down).
3. **A stand-in never says what it cannot know, and reads as an author wrote it.** The owner (2026-11-16): the first lines read as
   "very ai and inhuman like"; tune them "to be in the voice of a human author". So no line talks about the telling, the words or
   the story; each says what happened in the scene's own terms, briefly, as a novelist would. `stood_any` (the player's own deed,
   no facts to fill) is rewritten whole, and a new list, `world_stood`, is for a world happening with no facts. Lines for the owner
   to read first:
   - stood_any: "You do it, and it's done." / "That's done." / "You see it through." / "It's done, and it stays done." /
     "You finish what you set out to do." / "No trouble. It's done."
   - world_stood: "Something's changed around you. You might want to look." / "Heads are turning nearby. Something is going on." /
     "There's a stir close by. Worth a look around." 
   - the arrived fact (a summons whose passage was lost): "{who}, {what}, is here and has been asking for you by name." /
     "{who}, {what}, has come looking for you, and has found you." / "Someone has been asking after you: {who}, {what}. They're here now."
     ({who} the name, {what} their trade with its article; "they" because the line cannot know the person.)
   - the walk held after a road fight: "The road on to {place} is open whenever you're ready." / "{place} is still ahead, and the
     way is clear." / "Nothing else stands between you and {place}. Walk on when you like."
4. **After a won road fight, the walk resumes only if the turn can still tell the arrival.** If the budget cannot pay for a passage,
   the player stands at the stop with the fight's end told (its own passage keeps its place) and a plain line (the walk_held lines
   in point 3). The walk goes on when they say so. Nothing is skipped and nothing is told twice.

Numbers and words in data: budget.yaml `moment_needs` (the passage estimate a moment needs left, defaulting to narrate's own),
failures.yaml `world_stood` and the replaced lines, ledger.py's new `arrived` kind with its stood lines; data_check rows.

## What it costs

- No model call is added: a moment that waits fires later with the same one passage. A resumed walk waits one input when the turn
  is spent.
- Goldens: a recording whose arrival fired a matter on a spent budget would move (the moment one turn later); each change read
  before a rebless.

## Tests (tools/sim/untold_moment_711_test.py, written first)

- A summons on arrival with the budget spent: nothing commits (summons stays pending, nobody visits), it is queued; the next turn in
  that town fires it with its passage and the sender present.
- Walked on to another town before then: it waits for the next arrival there.
- A summons whose passage fails for another reason (a stub timeout): the plain line names who came and why, never a deed line.
- A lost passage of a world happening with no facts prints a world_stood line; a deed's lost passage still prints its own.
- No stand-in line promises a later telling or claims something settled (a check over failures.yaml).
- A won road fight on a spent budget: the player stands at the stop, told the way on is clear, and walks on when they say so; with
  budget left, it resumes as today.
- A second case besides the summons: a "moment" door (a scene that happens on arrival) on a spent budget waits the same way.

## Modules touched

engine/matters.py (the budget check and the deferred moment), scenes/world.py (run_deferred's new kind, the resume gate in the
tail), engine/ledger.py (the arrived kind), engine/failures.py and data/rules/failures.yaml (world_stood, the replaced lines),
data/rules/budget.yaml, engine/data_check.py, the new test. Over two modules: this plan waits for approval.

## Questions for the owner

1. **A matter's moment that cannot be told waits for the next turn there (recommended), or fires anyway with a plain line?** Waiting
   keeps the moment whole (a person coming to you is told as it happens); firing with a plain line is cheaper but tells a scene
   in one flat sentence.
2. **The lines in point 3, retuned to an author's voice: take them (recommended), or adjust?** They are new player-facing lines, so
   you read them first. The other stand-in lists in failures.yaml (victory_stood, the gained/lost lines: "the telling of the end
   slipped away", "the moment went untold") share the old voice; retuning them too is offered as part of this feature.
3. **After a won road fight with the turn spent, stand at the stop until told to walk on (recommended), or keep walking and accept
   an untold arrival?** Standing costs one input; walking on loses the arrival's telling, as it did on the way to Parth.
4. **Should someone a summons sends be kept in the save (out of scope here, recommended as a later fix)?** Today they are in memory
   for 120 minutes, so a restart in that window loses them.

# 21. Plan: the faults two live plays found

Status: **approved by the owner on 2026-11-15 for groups A to D and F** (section 11 has the answers); group E is designed
alongside and built after. Written 2026-11-15 on `foundations/phase3-switch` at 3f7847a, after phase 3
(docs/design/20_phase3_plan.md). Built on `play/faults`, cut from that commit.

The source is `docs/play/2026-11-15_play_findings.md` (two plays on the live model, 33 and 524 lines, about 70 faults, each with its
cause in the code) and the blind player's journal beside it. This plan does not repeat the causes; it cites them by the findings'
numbers (1.1 to 8.10). The line numbers of the main causes were read again on this tree and hold.

Feature numbers are provisional: each takes the next free number when it is built (f643 on).

## 1. What this plan is held to

- **GOALS.md, "Infrastructure over patches".** No fault here is fixed as one sentence or one scene. Each feature names the class it
  covers and is tested on a case other than the one that found it (checklist 4).
- **Pillar 1:** prose and game state agree. **Pillar 2:** a line the game fails to act on is a bug; an impossible act is refused,
  never granted and then forgotten. **"The engine decides; the model names, describes and speaks. What the model writes is checked
  before the player sees it."** Most of the findings are one of these three broken.
- **The owner's decisions that bound it** (GOALS.md decisions table):
  - Q31: the cap of deeds in a line is 15. The code still caps at 3 (finding 1.10). Decided, not yet built.
  - Q14: bad weather only under open sky. The engine honours it; the narrator's time label does not (2.14).
  - Q27: foes anywhere can yield. The yield's own sequence is what is wrong (2.6 to 2.8), not that they yield.
  - Q9, Q10: every blow stays in the prose; damage markers rely on engine alignment for now (2.16).
  - Q11, Q13: encounters and XP scaled to the party, and the XP curve, are **left for the balance pass**. So most of the
    findings' section 5 is not built here (section 8 below says which parts are and asks about the rest).
  - Maren's tutorial may be the same every run. It may not be a trap (5.6), which is a different thing.
- **The roadmap.** Phase 4 is next on docs/design/ROADMAP.md: combat onto the one ruling (doc 02 steps 5 and 6) and prose section B
  (doc 09: the engine writes a beat, plain-text prose, decide then speak; about 90 narration call sites move once). Section 9
  says what is built before phase 4 and what is built so that phase 4 does not redo it.

## 2. The classes, and the eight groups of work

The findings name eight mechanisms. They fall into eight groups of work. Size is S (one module and its test), M (two or three
modules), L (a design of its own first).

| Group | The class | Findings | Needs the live model | Size |
|---|---|---|---|---|
| A | The engine does what it said, and says only what it did | 1.7, 1.10, 2.1, 3.1, 3.3, 6.1, 7 (until an hour) | no | 5 x S |
| B | A typed line is read for what it asks, not for a word in it | 1.1 to 1.6, 1.8, 1.9, 2.7, 4.1, 4.2, 4.5, 4.7 to 4.10, 6.2, 6.3 | a live check at the end | M, M, M, S |
| C | The engine tells the player what it did | 2.8, 3.4, 3.6, 4.4, 4.5, 4.6, 4.11, 5.7, 6.4 | no | M |
| D | One sequence for a thing that happens (engine faults, no model in the fix) | 2.3, 2.6, 2.9, 2.11, 2.12, 2.13, 2.14, 2.15 (part), 2.17 (part), 4.4 (part), 5.8, 5.9 | no | 8 x S |
| E | A passage is checked against what the turn did | 2.2, 2.4, 2.5, 2.10, 2.15, 2.16, 2.17, 7 (a distance a speaker tells), run 1's prose slips | yes, a pod | L |
| F | The page and the panes | 7 (the echo's time), 8.1 to 8.9 | no | M |
| G | Danger, levels and XP | 5.1 to 5.6, 5.10, 5.11 | no | the owner's call, section 8 |
| H | Causes not yet found | 1.6 (the lost move), 3.2, 3.5, 4.3, 4.4 (the bear), 5.11 (armour), 7 (the theft's clock), 8.10, run 1's four | the two plays' logs | S each, once found |

Every finding is in one row. Where a finding has an engine part and a prose part (2.15, 2.17, 4.4), each part is in its group.

## 3. Group A: the engine does what it said

Five small features. None touches a prompt. Each is the first to build because each is a promise the game breaks in the first hour.

**A1. A fight rebuilt from its row has one fighter for each person (1.7).** `Combat.mentor_ally` holds a whole fighter who is also
in `fighters`; after a round trip through the saved row they are two, so the player's order reaches one and the mentor's strike
reads the other. That one split is the tutorial's deaf mentor, the troll's blow that leaves her bar full, and the draught that
heals nothing.
- The class: any field of `Combat` that holds, by value, a fighter who is also in the fight.
- The fix lives in how a fight is written to and read from its row (services/fight.py): such a field is kept as who it is, and
  read back as the fighter in `fighters`.
- Test first: a fence over every field of `Combat` typed as a fighter (a new one fails the test until it is declared as in the
  fight or not yet in it, as `reserves` are); the mentor's fight with an operation stood down in the middle, which the stub never
  does today; and the same on a second such field made for the test.
- **As built (f643, tools/sim/fight_one_fighter_643_test.py, written first).** The rule is the fight's own, not the row's: `Combat`
  declares which of its fields name one of the fight (`ONE_OF_THE_FIGHT`) and which hold those not yet in it (`NOT_YET_IN_IT`),
  and whenever a fight is made from its data (the row, a save) a field of the first kind is the very fighter in `fighters`.
  This is not where the plan put it (the writing and reading of the row): the row's shape is unchanged, and every way a fight
  is read is covered, not the one. A row saved with the two apart (a troll fight under way in an older save) comes back as the
  one in the fight, the one the bars showed.

**A2. What a line says it did is read from what was committed (3.1, 3.3).** "The rest of the line did not take; say it again" is
built from the steps that finished, and a walk and a hand-in are committed as operations of their own before the talk. So a paid
contract is reported as not having happened.
- The class: every stand-in that reports what stood (`part_stood`, `turn_not_taken`, `stood_any`, `round_stood`).
- The fix: each reads the line's committed operations and their ledger rows, the record phase 3 already keeps for every
  operation. The list of finished steps is no longer what is shown.
- A line whose deed was taken back because the reply to it could not be written (3.3) says that it was the reply that failed and
  that nothing was spent. The wording is the owner's, as many lines (pillar 3).
- Test first: a hand-in whose clerk's reply fails; a gift whose reply fails; a three-deed line that fails at its second and at
  its third. No case in tools/sim checks this wording against what was committed today.
- **As built (f644, tools/sim/line_stood_644_test.py, written first).** An operation says what it did as it runs
  (engine/operation.py `did`, kept for the line and not saved): a step its summary, a hand-in what was handed in and paid (said
  by `turn_in` itself, so it is named in whichever operation paid it: before a talk, or inside a gift), and an operation of the
  player's that moved its character and said nothing else, the walk and where to. A step the game said no to is not named, even
  when part of it was done before the refusal (what it paid is still named, by the hand-in's own word). The
  line's outcome and the words of `part_stood` are read from the operations that committed (`line_stood`, `line_outcome`,
  scenes/world.py); the list of finished steps is gone. A model's failure knows whether the words were someone's to speak
  (llm/gateway.py; the contract says so itself, `REPLY`, llm/contracts.py), and the operation keeps it. `turn_not_taken`, `stood_any` and `round_stood` were read against the record and
  are true as they stand: the first is said only when nothing committed, the other two only after the deed's own operation has.
- **What a refused step counts as.** It is told by its refusal, which the player reads, and it is a turn (the count of turns and
  steps moves; the character and the clock do not). When the next step then fails, the line is told as not taken: nothing the
  player asked for was done. The test holds exactly that, by what moved in the save.
- **What `did` is not.** A step's `did` is the reading's summary of the deed, not its outcome: a search that found nothing is
  still "a search of the benches". Saying what came of a deed is group E's (the facts of a turn), not this.
- **Waiting on the owner: the wording.** New lines a player reads are read by the owner before they are data (f512, f525). Until
  then the data holds none, a reply that did not come is told in today's `turn_not_taken` line, a walk is named by its place
  alone, the data's hash does not move and no recording is made again. The drafts:
  - `reply_not_come` (six, never the one shown last):
    1. "No reply came to that, so it was not done. Nothing was spent and nothing changed hands; say it again."
    2. "The words that should have met that never came, and without them it did not happen. What you carried, you still carry;
       try it once more."
    3. "That waited on a reply, and none came. Nothing was given, nothing taken, nothing paid; say it again."
    4. "It did not take: no words came back for it. Your purse and your pack are as they were; say it again."
    5. "No word came back, so the moment was let go whole. Nothing of yours was spent; try it again."
    6. "The reply to that was lost before it was spoken, and the deed with it. All you had is still yours; say it once more."
  - `walked`: "the walk to {where}" (as in "This much is real: the walk to the temple of Parth. ...").
  - On the owner's yes: the two go into data/rules/failures.yaml (the start-up check already holds them), and stub_party is made
    again for the one line that changes (input 13, a talk whose reply fails).

**A3. An item used on someone goes to them (2.1).** `on_use` never reads the target; the draught heals the player while the story
has the companion drink.
- The class: every consumable used "on" someone. One path with giving (`give_to_hire` already heals the hire).
- A target the item cannot be used on is refused in a line, never used on the player instead.
- Test first: a draught on a hurt hire, on a townsperson, on a foe, on someone not here; a bandage the same way.
- **As built (f645, tools/sim/used_on_645_test.py, written first).** Outside a fight, using a thing asks whom it is for
  (scenes/inventory_actions.py `used_on`), and the engine acts for someone else only when two things agree: the reading's target
  for that step, and the line's own words naming that same one here (scenes/world.py `those_named`). Then (`use_on`): a companion
  who is hurt takes what restores health, by the one path with giving (`give_to_hire`, whose words now say "uses", a bandage not
  being drunk); what it cannot do is refused in a line and the thing kept (not hurt, not with the player, a thing that would do
  nothing for them); someone of the town who is here is handed it, as giving does.
- **When they do not agree, the engine does not guess.** A line that names someone here whom the reading does not confirm is
  asked about in a line and the thing is kept: it is never used on the player in their place (the fault found), and never handed
  to someone who was only named ("I use a bandage on my cut while Elerina watches"). The same when the reading names someone
  here and the line names nobody ("I pour it down her throat", "my companion", "the fighter": a companion is matched by name,
  not by trade). A line that names nobody is the player's when the reading names nobody here. A line that says in the first person that the player takes it ("I drink", "I'll eat", "on myself";
  engine/actions.py `takes_oneself`) is the player's, unless another thing is used in the same line, when the words could be
  that one's; and when the reading and a name agree on someone and the words say that too, the line says both and is asked
  about ("I tend Odly's wound myself with a bandage"). Someone known who is elsewhere is told as not here when the reading names
  them, and asked about when it does not, unless the line walks to them or speaks to them in another step (`rest_of_plan`: the
  step now knows the plan it is part of, engine/actor.py `plan_now`).
- **The lines a refusal says (new, each one line, as every refusal in that file is):** "Odly is not hurt." / "Odly is not with
  you." / "Mana tonic would do nothing for Odly." / "Hude is not here." / "Is the healing draught for you or for someone else? Say
  that you take it yourself, or give it to the one you mean."
- **What this costs until the reading names whom a thing is used on.** The interpreter is told what `target` is for talk, attack
  and buy, and not for use. Where it leaves the target empty, the very line found in play ("I use a healing draught on Raerei")
  is now asked about instead of healing the player: right, and one line more than it should take. "I give Raerei a healing
  draught" does it in one, as it always did. One line in the field's description ("for use, whom it is used on, when not
  themself") makes the first line work; it is a prompt line, so it is group B's and the owner's yes (question below), and it
  is measured on the real model before it is kept.
- **Left, and why.** A pronoun alone ("pour it between her lips") names nobody: where the reading names her it is asked about,
  and where the reading is silent it is the player's own (the fault as found, for that wording, until the prompt line; and
  after it, such a line is still asked about, the line itself naming nobody). Asked about, where a person would not need to
  ask: "I use a healing draught" when the reading aims it at someone here (whether it does so by habit is not known: the real
  model's readings of a use are not measured, the logs of the two plays being closed to this session); "I use my draught, then ask the clerk about work" (the clerk is named
  and "use" is not a word of taking it oneself; "I drink my draught, then ask the clerk" is not asked); a way of taking it the
  list does not hold ("I take a swig of my draught and tell Odly I am fine"); a name that is there for another reason ("the
  draught Bram gave me"); "I drink a draught and nod to Odly" when the reading aims the draught at Odly. The question's way
  out, "give it to the one you mean", reads a companion's name from the line; for someone of the town it goes by the reading's
  target, as giving always has. In a fight a thing given to a companion by name was already read
  (scenes/combat_scene.py `ally_for_item`); a thing used on a foe is not refused there, the fight's reading filling `target` with
  a foe for every kind of step, so the plan's "on a foe" case is not built and not tested. `give_to_hire` takes the thing by its
  name again: of two of one name and different origin, it may take the other.

**A4. A count and an hour asked for are kept or refused (6.1, 7).** Buying reads no count; "until eight" becomes one of eight
named periods.
- The class (the findings' mechanism 8): a handler that ignores part of the intent it was handed.
- Buying takes the count, refuses in a line when the purse or the shelf falls short, and says what was bought and for how much.
- A wait to an hour waits to that hour. The contract keeps the named periods and gains an hour of the clock.
- Test first: a fence that every field of each intent the interpreter fills is read by the handler that takes it, or declared
  unused; then the two cases, and a count of one, a count the shelf cannot meet, and an hour already past.

**A5. The cap of deeds in a line is 15, in data (1.10).** The owner's decision of review Q31, not yet built. The cap moves from the
contract to data/rules; a line over it is told how many were taken, as now.
- Checked with it: the turn's budget. Fifteen deeds are fifteen operations, and the minute on the minimum card is a decision
  too (GOALS.md, f459). The price of a long line is measured on the recordings before the cap is raised, and the plan stops for
  the owner if a line of fifteen cannot fit.

## 4. Group B: a typed line is read for what it asks

The findings' mechanism 2. A pattern searched over the whole typed line decides an act, so an ability's own name ("Guard Breaker",
"Twin Hammer Strike"), a companion named as an object ("behind Kennard's shield") or a common word ("point out the wires") fires
an order, a retreat from a dungeon or a prayer. There are about a dozen such sites.

**B0. The fence, built first.** A test that counts, file by file, every pattern that is searched over the whole typed line and
changes what a deed is. A count only falls (the form of acting_character_630's census). Beside it, the corpus the repairs are
pinned by (`data/replay/interp_cases.yaml`, read by interp_eval_test) gains its other half: for each repair, lines that must not
fire it, taken from the blind journal and from lines written for the test. Today the corpus holds only the case that made each
repair, so a repair that catches too much passes. These are the tests of the engine fixes below, not a stand-in for them.

**B1. An order is to someone addressed (1.1 to 1.5, part of 1.6).**
- An order is recognised from who is spoken to (a name the line addresses, in speech or at the head of a clause), never from a
  name anywhere in the line.
- The names of the player's own abilities and gear are taken out of the line before any word list is read, in a fight and out
  of one. This one mechanism serves B2 as well.
- A guard order says whom to guard, and the order's record and its printed line carry it.
- Out of a fight, one member can be told to hold back, not only the whole party.
- The player's own act in a line that also orders is kept, whoever it names.
- Test first: the five lines of the journal, each with a twin the journal did not hold (another ability name with an order word
  in it, another companion as an object, an order to guard a third), and orders_test's patterns still passing.

**B2. A repair rewrites a deed by that deed's own words (4.1, 4.2, 4.5, 4.7 to 4.10, 2.7).**
- Leaving a dungeon, praying, staying within a place, talking to a hire, naming a ware, the verbs a purchase covers, and
  finishing a foe who yielded are each decided by the deed the interpreter wrote (its summary, its destination, its target),
  not by a word found in the line.
- A foe who has yielded and is then attacked, in any words or by any ability, is attacked. He is not let go (2.7).
- An answer to the game's own question is read against that question (4.10: "Both at once").
- Test first: B0's corpus, both halves, for each repair.

**B3. Every part of a fight line is acted on, or the player is told which was not (1.8, 1.9).**
- A free act and an act in one line (drink, then strike) are both done. The fight's reading returns one intent today.
- A target the player named is the target. When it cannot be (dead, gone), the line says who was struck instead and why.
- This is the fight's side of pillar 2: "a line the game fails to act on is a bug. It is logged, counted and fixed."
- Phase 4 moves the fight's improvised acts onto the one ruling (doc 02 step 5). B3 changes the reading of ordinary fight
  lines, which step 5 keeps, and is written so that an improvised part of a line is handed on as its own part.

**B4. Coin and goods change hands only when the line asked for it (6.2, 6.3).**
- A question about what is sold is not a haggle that ends in a purchase.
- Coin handed to a clerk for a thing with a price (the guild's fee) pays for that thing, or is refused. It is never taken as a
  gift and the fee asked again.
- The class: a payment or a purchase made by a reading the line did not ask for.

After B, one short live play on the user's card reads the journal's own lines again. That is a check, not the test.

## 5. Group C: the engine tells the player what it did

The findings' mechanism 7. The engine changes what the player asked for and tells only the narrator, who may leave it out: a foe
out of reach becomes a walk (4.4), a search fails after three hours (4.5), a refused pick-up drops the rest of the line (4.6), a
flight is one hidden roll (4.11), yielded foes vanish (2.8), an ability's cost rises (5.7), a rest without a room is not a full
rest (6.4), a matter of the world ends that the player never heard of (3.6).

**One mechanism:** an outcome the engine decides against or beside what was asked is a typed note of the turn, with its reason,
written in data as several lines for each kind (pillar 3) and shown in the game's own italic voice. The narrator is still told.
The note does not depend on the passage saying it.
- A fence: every place the engine turns one act into another, or refuses a part of a line, raises a note. Found by the kinds of
  refusal and substitution the code already has (engine/actions.py, the fight's access check, the explore and pick-up handlers),
  not by the eight cases above.
- 4.6 also needs an engine change: coins that lie there can be picked up, and a refused pick-up does not stop a walk that does
  not need it.
- 3.6: a matter ending is told only to a player who had met it or heard of it, and the line agrees with its title.
- 4.11: the flight line says how likely it was, in words (the danger label's kind of word, not a percentage). The numbers stay.

## 6. Group D: one sequence for a thing that happens

Engine faults where two parts of the engine tell one event two ways. No model is in any of these fixes. Eight small features.

| Feature | Class | Findings |
|---|---|---|
| D1 | A foe who yields: who yields is settled before the round's passage is written, among the living; a foe who leaves after yielding is said to leave | 2.6, 2.8 |
| D2 | A person's leaving is written to the journal with whether they died, by every writer; mourning reads that and nothing looser | 2.13 |
| D3 | Under the ground: a dungeon's fights take the underground ground, and the time label gives the weather only under open sky (Q14) | 2.14 |
| D4 | An act of the party that happens at a hall needs the hall and its clerk, as hiring does | 2.3 |
| D5 | A thing handed over that settles a matter is handed over before the person speaks about it | 2.9 |
| D6 | What the narrator is told of a foe's stance stands on a state the engine holds, or is not told (a warning with no way to back off; a foe who speaks and "cannot be reasoned with") | 2.11 |
| D7 | A contract's tally counts what the contract is about wherever it was done: a foe taken alive, a kill in the place's own dungeon; two contracts do not count the same leaves | 5.9 |
| D8 | Data that must only rise is checked at start-up: a hire's health never falls with a level; and the smaller items: a nickname comes with its reason (2.12), a found cache is told as taken (2.15), a fixed line that names the hour reads the clock (2.17), a slow fighter already engaged does not spend the round advancing (4.4) | 5.8, 2.12, 2.15, 2.17, 4.4 |

Each is tested on its own class: D2 on every writer of a leaving, D4 on every party act, D7 on every kind of contract.

## 7. Group E: a passage is checked against what the turn did

The findings' mechanism 1, and the largest piece. A passage is bare text. Nothing compares it with who is present, who is alive,
what was found, who received what, or what the clock says. The one check that exists (`voice_rules.contradicts_nothing`) is three
word lists, run only on a turn where nothing happened.

**This needs a design of its own before any code** (doc 22), because it touches every narration site, the minute on the minimum
card, and phase 4's prose work. What the design has to settle:

- **The facts of a turn, as one typed thing.** Who is here, who has fallen, who acted, what changed hands and to whom, what was
  found and how much, the hour, sky or no sky, and how far the places near are by the map (what a speaker says of a distance). Built from the turn's ledger and the scene's roster, which exist. This is the same
  thing doc 09's beat is built from (B1: facts, and what to withhold), so it is built once, here, in the form phase 4 takes up.
- **Checks with no model first.** A fallen companion named as acting (2.2). A person placed where the roster has no one (2.5).
  Coin or goods told that the ledger did not move (2.10, 2.15). An hour or weather the clock and the sky do not hold (2.14, 2.17).
  The foe the opening names (2.16). These cost no time. A model as a checker is the last resort and is measured before it is kept.
- **What happens on a mismatch.** One retry that names the mismatch, as `contradicts_nothing` does, then the stand-in. Each retry is
  a narration call, so the design prices it against the minute (tools/latency.py) and counts how often it fires on a pod.
- **People the story names.** Narrated places are made real (f394). Narrated people are neither made real nor refused. The owner's
  decision Q26 says an improvised person can become real when the narrative calls for it. The design proposes one rule for when.
- **The engine's part of the same faults.** Town talk is not handed to the narrator at a place with no town (2.4). The fight's
  narrator is told who has fallen (2.2).
- **Measured, not asserted.** The night's Consistency counts (prose that contradicts the engine) before and after, on a pod, as
  prose section A was.

If the owner wants it, this design can be run as a survey and a design with the `meravia-bundle` workflow, as the foundations
bundle was. That spends many agents and is the owner's to ask for.

## 8. Group G: danger, levels and XP, and what is the owner's to rule

By the owner's decisions most of this waits for the balance pass (Q11, Q13). Three parts are not balance numbers:

- **5.9** (tallies) and **5.8** (a hire's health falling with a level) are engine and data faults. They are in group D.
- **5.1, what the danger label means.** It measures one thing: whether the player survives a simulated fight. A fight that
  kills every companion reads "trivial". That is a label that does not say what it shows (pillar 6: "what the player sees in a
  stat, a cost or a choice makes sense"). **The owner's answer (section 11): the label is for testing, not for the player.**
  So it is taken off what the player sees (G1) and its meaning is left for the balance pass.
- **5.6, the first fight.** A character who misses often cannot lose, cannot leave and cannot be helped. It is the first ten
  minutes of every new player. Needs the owner's choice (question 2).

Left for the balance pass, with the findings' measurements kept for it: the level 35 ghost on a starter road (5.2), XP for a
higher foe (5.3), a pack creature's XP (5.4), the floors' letters (5.5), crafted values and the sell rate (5.10), harvest and
armour (5.11, its armour half is in group H until its cause is found).

## 9. Order, and how it sits with phase 4

1. **Group A** (five small features). The tutorial, the false "did not take", the draught, counts, the cap.
2. **Group B** (the fence first). The largest share of "the game did something I did not ask".
3. **Group C**, then **group D**. C's notes are what D's and B's refusals speak through.
4. **Group F**, the page, at any point: it shares no code with the rest.
5. **Group E's design** is written while A to D are built, and built after them, with a pod session to measure it.
6. **Phase 4** follows. E's typed facts are what its beats are built from. B3 leaves the fight's reading in the shape doc 02
   step 5 expects. Nothing in A, C, D or F is touched by phase 4's rewrites.
7. **Group H** as its causes are found. **Group G's rest** at the balance pass.

Every feature: a test in tools/sim written first and seen to fail, the suite passing at every commit, the goals review before each
commit. Recordings: A1, A2 and B change what the three recordings hold only where a recording meets the fault. Each re-record is
read line by line under the rebless rules, and none is expected for A3 to A5, C's notes aside (a note is a new line a recording
may show).

Group F in short, each a class: the page echoes no machinery (one list of what is never shown, held by a test over every input
the page can send: `create:` lines, "Character saved", the bracketed card); a card's parts are written once (the level three
times, 8.6); a pane's mode follows the view shown, typed or clicked (8.4); notices do not move what is under the pointer (8.5,
pillar 7); abilities offered at creation differ by what they do, not only by name (8.2); the weapon asked for is the weapon
given, or the goddess says which part was changed (8.3); the Continue card shows when the game was last played (8.7); an event
told once (8.8); and the small wrong words (8.9), each fixed where its line is built.

## 10. Questions for the owner

1. **Order.** Build groups A to D and F now, before phase 4, with E designed alongside? Recommended: yes. They are the faults a
   new player meets in the first hour, and none is redone by phase 4.
2. **The first fight (5.6).** When a new character is stuck at 1 health in the tutorial's first fight, what should happen?
   Recommended: Maren steps in and ends it after a set number of rounds at 1 health, and says so. The other choices: flight is
   allowed in that fight; or the wolves are fewer or weaker (a balance change).
3. **The danger label (5.1).** Make it count the party now, or leave it for the balance pass with the rest? Recommended: now.
4. **The level 35 ghost (5.2).** Your decision Q11 leaves encounters scaled to the party for the balance pass. Does a foe 28
   levels over the party on a road between starting towns wait for it too? Recommended: it waits, and the findings' numbers go
   to the balance pass. Named here because it killed the run's first long journey.
5. **The logs.** About a dozen causes are not found (group H), and every "inferred" cause would be settled by the turn log of its line. This
   session is refused the game's `logs/` folder, and it will stay that way unless you say otherwise. Either allow the logs of
   those two plays to be read, or run "Send a report" and say where the zip is.
6. **Group E's design.** Written by this session alone, or run as a survey and a design with the bundle workflow? Recommended:
   alone first; the workflow only if the first draft leaves open questions.

## 11. The owner's answers (2026-11-15)

1. **Order:** "Yes build A through D and F." Before phase 4.
2. **The first fight:** "Leave the first fight as it is for now, they can't die but they can't lose they should always be able to
   win." Nothing is built for 5.6. What it must hold is named: the fight can always be won.
3. **The danger label:** "something I think should only be left for internal testing and not a player viewable thing." This
   replaces the recommendation. The label is taken off everything a player sees and stays for testing (the debug view, the
   night tools, danger_500_test). It is built as a feature of its own after group A (G1). What a player is told of a fight's
   odds from then on is what the story shows.
4. **The level 35 ghost, and the rest of group G:** "Leave the balance for later."
5. **The logs:** open. The folder is refused by this project's own settings (`.claude/settings.json`, `Read(./logs/**)` in its
   deny list), which the owner changes, not the session. Group H waits on it.
6. **Group E's design:** not answered; written by the session alone first, as recommended.

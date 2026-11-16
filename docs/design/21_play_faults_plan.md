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
- **As built (f646): the fence and the count. The hour is not built.** The table of kinds (engine/actions.py) now says, for
  each kind, which fields of the reading the interpreter is told to fill (`fills`; a targeted kind is also told the target) and
  which of those its handler does not read (`unread`). tools/sim/intent_fields_646_test.py reads every handler's source, with
  the methods it hands the reading to, and holds that what is told and not read is exactly what is declared; it holds the table
  to the interpreter's instructions both ways (the words set aside as not an instruction, "use that person's place id", are
  listed in the test); and start-up refuses a field the reading does not have. The fields every kind has (summary, checks,
  mark, force) are the turn's and are outside it.
- **What the fence found besides buying**, declared in the table and not built here, eight in all: a count is not read by
  pick_up (all that lies there is taken), craft and commission (one is made), show and equip (nothing to count); the person
  named is not read by board, train and commission (each finds its own clerk, teacher or crafter). The player is not told when
  one of these is not kept. That telling is group C's note (an outcome beside what was asked); the list only shrinks.
- **Buying.** A listed ware takes the reading's own count (`count_asked`), and never a number read out of a name: "a meal for
  the two of us" is one meal, and a "Blade of Seven Stars" is one blade. That many are paid for at the quoted price each,
  carried (or, the pack full, set down here and told so), and a meal or a drink is eaten or drunk that many times. The line of
  the purchase names the number and the whole sum ("Paid ... for three jars of wine"). What a seller holds of a good is sold
  first; when their own trade lists the good too, the rest comes from that list at its own price, and only a seller whose trade
  does not sell it can run short. What is held goes by the good's bare name, so it is counted as the trades sell it ("two
  sacks of salt"), or in measures when no trade does ("two measures of yarrow").
- **The new lines a player reads, for the owner to read:** "That is sold one at a time. Ask for one." (a piece of gear, a
  mount, a house); "A room is let one at a time, for the one night. Ask for a room." (said before the quote, so a room that
  would be free is not announced and then refused); "<Seller> has only two bandages to sell." and "<Seller> has only the one
  to sell."; "Three jars of wine come to <sum>, and you have <sum>."; "No more than 99 of a thing are sold at once." (a
  count over the most is refused, never cut to it and charged); and, to the narrator, "They have three jars of wine, but
  no room to carry them: they are set down here." (or "all of them: the rest is set down here."). A count of one is as it
  was, and the three recordings replay unchanged.
- **Left, and why.** The hour: the plan's way is a new field of the contract, which is a line of the interpreter's
  instructions, a re-record of all three recordings, and a reading by the real model that is not measured without a pod. It
  waits for the owner's answer and goes with group B's own line of the instructions, in one re-record. A count is taken at
  the reading's word, as selling and giving take it: whether the real model ever writes a price or another figure into it is
  not measured (the logs are closed to this session). A house's upgrades and its rebuilding take no count. Haggling ends in
  this same purchase and hands it the reading, but the instructions tell a haggle only the ware and the seller, so "I haggle
  him down on three jars" buys three only if the reading wrote the count unasked; the fence holds what is told and not read,
  not what is read and never told. That is a line of the instructions, and B4 reworks the haggle. Meals and drinks have no
  limit of their own below the count's 99: ninety-nine are paid for and eaten. A room for a companion, and a room for two
  nights, are not things the engine has; the room's line says what it lets. The most sold at once is 99, the number giving
  already holds in code; it is named once here and not moved to data, which would move the data hash under all three
  recordings for a number nothing tunes. A bargain struck once (the barter, a won haggle) takes its share off every one of
  the count, as it does off a whole stack sold; the owner has not ruled on it. A haggle won for a thing sold singly and asked
  for in a number prints its win and then the refusal. A purse short for one is told by the narrator, as it was; short for
  several, in a line.

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
- **As built (f648).** tools/line_census.py reads the code from every door a typed line comes in by (the world's turn, each
  intercept, each repair, each kind's handler, each answer to the world's own question, the fight's turn) and follows the line
  into every method and function it is handed to: by name, by a method reached through getattr with a prefix (the party's and
  the camp's own dispatch), through what a function imports inside itself; over the line, a plain or reworded form of it, a
  longer string it is set in, and its clauses. A method reached by getattr is followed when it takes as many arguments as the
  call gives, whether called there or kept and called later. It stops at the prose the narrator is told. It counts each pattern, word or test
  searched over it: 250 places in 48 files. tools/sim/line_patterns_648_test.py holds that count file by file. It only falls,
  and the table is lowered when one goes; a fix that adds a guard over the line (a question, a negation, who is addressed) may
  raise a file's count only beside a line that names the feature and why. The count is of every search over the line, not only
  those that decide a deed: a question mark, a command's mark and a word made singular are in it. It does not see the line
  handed on by keyword or stored on the scene, compared with ==, put on the left of `in`, or handed to the model; and, being per
  file, one search swapped for another in the same file.
- **The corpus's other half.** A case may name the intercepts and repairs that must not take it or change its plan
  (`not_by`). Every intercept and repair that reads the line's words now has a case where it acts and a case it gets right that
  it must not touch, but three the bench cannot stage (an arc's camp, Maren's first stepping in, a foe who yielded: that one is
  B2's, in a fight of its own) and one held off today only by a case it gets wrong (to_the_named, B1's). 19 cases already there
  were such near misses and now say so; 26 are new. A case the game gets wrong today is kept and marked owed, with the fix that
  owes it and what it does today (`owed: {fix, now}`): owed while it goes wrong that way, wrong if it goes wrong another way, and
  wrong once it comes out right until the mark comes off. An owed case counts as wrong in the table by kind and in what the
  intercepts took. Eight are owed: the journal's three (4.1 "point out the wires", 4.2 "I kneel and jam the plates", read with and
  without the kneeling in the deed's own words, and 4.7 a companion named while the party rests) and four the near misses found:
  "I tell Hollis I lost a game of dice" is a gamble; "I nod and tell the guard the road north is clear" leaves town by that road;
  "Here, take this healing draught, Bram" is taken by the hire intercept and nothing is given; "I ask my companion what he makes
  of the guard's story" is said to the guard (B1's: who is addressed). The rest are B2's, whose list below is widened to hold them.

**B1. An order is to someone addressed (1.1 to 1.5, part of 1.6).**
- An order is recognised from who is spoken to (a name the line addresses, in speech or at the head of a clause), never from a
  name anywhere in the line.
- The names of the player's own abilities and gear are taken out of the line before any word list is read, in a fight and out
  of one. This one mechanism serves B2 as well.
- A guard order says whom to guard, and the order's record and its printed line carry it.
- Out of a fight, one member can be told to hold back, not only the whole party.
- The player's own act in a line that also orders is kept, whoever it names.
- Out of a fight, a talk goes to the one the line speaks to by the same reading of who is addressed: a talk aimed at a companion
  is not turned to someone else only because the line names them (to_the_named: "I ask my companion what he makes of the
  guard's story", owed in B0's corpus).
- Test first: the five lines of the journal, each with a twin the journal did not hold (another ability name with an order word
  in it, another companion as an object, an order to guard a third), and orders_test's patterns still passing.
- **As built (f649): orders in a fight.** engine/addressing.py reads who a line speaks to, in one place: a name at the head of a
  sentence or of the words said ("Kennard, guard me", "Kennard guard me", "Kennard attacks the wolf"), several at once ("Kennard and
  Raerei, hold back", "Kennard and Raerei take wolf 1": a list ends at its comma, so "Raerei, Kennard is down, heal him!" is said to
  Raerei), one the player has, gets or lets do a thing ("I have Kennard guard me", "I let Kennard take wolf 1"), a name said alone
  before the order ("Kennard! Fall back!"), a sentence that asks something after one said to someone ("Kennard, I'm hurt. Cover
  me!"), a name called at the end or in the middle ("Cover me, Kennard!", "Cover Raerei, Kennard, while I take wolf 1"), one the
  player tells, orders, asks or shouts to ("I tell Almund to take wolf 1", "I shout for Kennard to fall back"), one signed to with
  the words after a colon, a "to" or a comma ("I nod at Kennard: take wolf 1", "I turn to Raerei, heal me!"; "I look at Kennard,
  then take wolf 1" is the player's own), words in quotes given to someone by the sentence after, whatever the player then does
  ('"Hold back," I tell Kennard, and I charge wolf 1.'), or the whole party ("Everyone, hold back"). A name followed by how they
  are ("Raerei is down") is spoken of, not to; a sentence that begins with a foe's name is not read as a companion's at its head
  ("Wolf 1 is on me, Kennard, guard me!" is said to Kennard, by the name called in its middle). A name said alone followed by what
  the player does ('"Kennard!" I yell, and charge wolf 1.') tells the companion nothing. What the player says they do themself in those words, from "and I", "while
  I" or "I'll" up to where the words to them start again ("Kennard, while I strike wolf 0, take wolf 1"), is cut off and kept as
  the player's own; "I'm done for" and "I need you to" stay said. The fight reads each order's kind only from what is said to them, after
  the player's own ability names and worn gear are taken out ("follow my Guard Breaker with a strike" is an attack); a question is
  still no order. A guard or a heal is for whom the words right after its own word name: "me", a companion, or the one a "him" or
  "her" points to, back in the line or on in it ("Raerei, heal him, Kennard is bleeding!"); a him or her is never the player, and
  with no one named it is no order. "Kennard, guard me while Raerei heals" guards the player; a guard order with no one named
  guards the player. The order
  keeps it (engine/combat.py give_order), the line printed says it ("You tell Kennard to guard Raerei."), and a blow aimed at that
  one is what the guard steps in front of (combat.guards_of; a guard whose charge is no one on the player's side guards the player).
  An order refused (a fighter with no healing told to heal) lets the next order in the line be given; any order after the one
  given, to anyone, is said to wait ("One order a turn: Raerei will have to wait for the next."); when the turn's order was given
  already, that is said once and no order in the line is given. own_part keeps every
  clause said to no one that says what the player does, whoever it names, and the player's own part of what is said to someone.
  tools/sim/addressed_orders_649_test.py holds the journal's 1.1 to 1.5 and 1.9, a twin of each, and the forms above; orders_test,
  the two playthrough tests of orders and mentor_test pass unchanged, and so do the three recordings. The census, which now also
  follows a line given back in a record of ours, reads the fight 21 to 18 and the new module's 12 as a named raise: the reading of
  who is addressed replaces the searches for a name anywhere, and the orders read only what is said to someone. The better reader
  also sees old code it missed before (exits 15, features 3, the world 36, listening 5, part_actions 5, questions 1, severity 3):
  those are the table's new baseline, 275 places in 50 files, not new searches.
- **Left, and why.** An ability whose whole name is an order word ("Cover") is read as the ability inside an order. "Almund, get
  back out of its reach!" is no order: no word of the order lists says it, and widening the lists is not this fix. The order lists
  themselves (the kinds and the ways a name is called) are closed lists of words; what is not in them is read by the interpreter as
  before. A guard order with no one named guards the player, the one fight's single player; with a second player it will need the
  speaker. Misread before f649 and still (owed to a later pass of this reading): an order and another to a second companion in one
  sentence ("Kennard, guard Almund, Raerei, heal me!" gives only the first, unsaid); a need said of a companion before an order
  ("Kennard needs it too, heal him after"); "Kennard! Hold!" ("hold" alone is no order word); "Cover me, Kennard, I'm going for
  wolf 1" keeps no part for the player.
- **As built (f650): a talk out of a fight.** The repair that turns a talk aimed at a companion to someone else here
  (to_the_named, scenes/listening.py) reads who the line speaks to with engine/addressing.py, as the fight reads an order: a
  person by their trade with its article ("the guard"), by the bare trade only when called ("Guard, ..."; "Guard the gate, I
  tell Bram" is not to the guard), or by name once the acting character knows it; at the head of the line, called, or the one
  the player asks or tells, now with what they are asked of ("I ask the guard who he serves", "I tell the guard that my
  companion needs rest"). A talk aimed at anyone the line speaks to stays theirs, so a line that speaks to two keeps each with
  its own ("I ask the guard who he serves, then I ask Bram what he thinks"); one aimed elsewhere goes to the first spoken to, and
  of two of one trade, to the one already talking. When the line speaks to no one, the old rule stands (a name or trade it
  holds, unless it names the companion), so nothing it reached is lost ("I talk to the guard about the road"). The case B0 owed
  to B1 comes out right and its mark is off; six new cases and a test of the repair itself hold the class
  (tools/sim/addressed_talk_650_test.py). In a fight, words asked or told of a companion ask them nothing to do; what follows
  them in that sentence is the player's own when it is an act of theirs (an "I", or one of their abilities named: "I ask Raerei
  if she is hurt, then Brutal Strike wolf 1"); a name called with a comma is spoken to whatever follows ("Kennard, has your
  shield held? Take wolf 1!"); a sentence after one asked of a companion is carried to them when it asks ("I tell Kennard of
  the trap. Guard me!"). The census counts one more place in engine/addressing.py, the trade only when called.
- **Misread before and still (owed):** "my companion" with two companions; a name not yet known ("I ask Garran ..." before his
  name is learned); "one of the guards", "the guards", "Guards, ..."; two of a trade with neither talking (the talk stays); "I ask
  about the guard" goes to the guard by the old rule; "Guard the door tonight, my friend" goes to the guard; "Guard, Bram here
  needs a bed" is taken by the hire intercept before any repair (B2's); in a fight, "I ask Raerei if she is hurt, then attack
  wolf 1" drops the attack, the player's act having neither an "I" nor an ability's name.
- **As built (f651): an order to the party is to the members it names.** Holding back: the companions the line speaks to by name,
  clause by clause, or else those the reading's target names by name or role, hold back where they are (the member's `held_at`);
  the others stay with the player, and the line printed names who. A line said to everyone, or naming no one, holds the whole
  party as before; "Kennard, hold back. Everyone else, with me" holds Kennard. One held alone is shown so in the Party pane (the
  owner's Q19), arrives later at a camp and is not counted in its noise (the estimate as the fight), falls in again, said so, when
  the player walks away, and comes when a typed line calls them. Dismissing: those named go, by name or role, and the rest stay;
  "I dismiss Bram from the party" no longer sends everyone; a name not in the party sends no one and says so (it sent everyone).
- **Left.** Inside a dungeon every chamber is one place, so holding one back there holds them for the whole delve, until the
  player climbs out; whether "stay behind me" means holding back is the reading's choice; and the move in 1.6's line after the
  party order is still not done (the party intercept takes the whole line). A companion held alone still banters and is tended
  after a fight, being in the same place.

**B2. A repair rewrites a deed by that deed's own words (4.1, 4.2, 4.5, 4.7 to 4.10, 2.7).**
- Leaving a dungeon, praying, staying within a place, talking to a hire, naming a ware, the verbs a purchase covers, and
  finishing a foe who yielded are each decided by the deed the interpreter wrote (its summary, its destination, its target),
  not by a word found in the line. So are two B0 found: a way out of town by road (the exit intercept takes "I tell the guard
  the road north is clear"), and a talk read as a hand of cards, a haggle, a lesson or a job (talk_to_deed), which reads what
  the talk asks for, never a deed it tells of ("I lost a game of dice last night"). And a move onward within a delve, to
  the next chamber, is the delve, as that kind's own words say (with "point out the wires", B0's corpus expects it).
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
   **As built (f647): the label is off the screen, not yet off everything a player reads.** It is no longer handed to the
   fight's pane, printed at the head of a fight, or said in the note of a camp scouted well ("Charging in looks: DEADLY.").
   The debug view prints the word beside the rate. The estimate itself is untouched. Kept, and for the owner to rule on: (a) two abilities are promised a reading of the fight by their own text
   in data, and still get it, in figures and never by the label's word: Keen Judge and the Oracle's effect ("you see your exact
   odds": "You judge your odds at 62%"), and a sworn enemy ("you see its strength, speed and your odds at once": "A sworn foe,
   read at a glance: 62% odds, slow - it cannot follow a quick step"; its "strength" is now the level and health every fight
   shows); the figure is the same estimate the label is cut from, so it has the label's fault (5.1: it counts the player's
   survival, not the party's). (b) The narrator is still told the
   odds in words at a fight's opening ("THE ODDS: the player should win this") and after a scouting ("Charging in would be
   deadly"), so the story can still say it, and the fight of 5.1 would still open as "no real threat"; taking that away
   changes what every opening is written from, and is a re-record.
   (c) After a scouting that reads dangerous or deadly, the advice to hire help is still given ("That is a garrison, not a
   gang."), which is the label in other words. tools/sim/danger_hidden_647_test.py holds all of it, and a fence on who asks
   for the estimate and who reads its label among the code that shows a player something.
4. **The level 35 ghost, and the rest of group G:** "Leave the balance for later."
5. **The logs:** open. The folder is refused by this project's own settings (`.claude/settings.json`, `Read(./logs/**)` in its
   deny list), which the owner changes, not the session. Group H waits on it.
6. **Group E's design:** not answered; written by the session alone first, as recommended.

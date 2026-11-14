# Feats of the body: the model says how big, the engine says whether a body can

Written 2026-11-13. Steps 1 to 4 of section 12 are built as f623 (the owner, 2026-11-13: "Approve, build it"); section 13 says where
the build left this plan. The rest is not built. It is part D of docs/design/18_class_fixes_plan.md, which waited on a
probe of whether the model gives honest sizes. The probe ran the same day; its numbers are in section 2. The owner answered six
questions the same day (section 10); one answer widened the design to falling harm for any being (section 6). Nothing is open;
the pod session of section 8 comes next.

## 1. What is wrong today

The act's ruling (engine/act.py) asks the model whether an attempt makes sense and how hard it is: easy, fair or hard. The engine
then rolls. Nothing in that path knows how big the feat is.

- **"I jump up onto the roof of the guild hall"** is ruled a cost at fair on dexterity in every pass of every measure so far. A
  character of dexterity 15 clears a two-storey building half the time.
- **"I lift the portcullis with my bare hands"** is a cost at hard on strength. The roll is 50 + (strength - 15) x 1.5 - 20, kept
  between 10 and 90: a character of strength 10 raises it 22 times in 100, one of strength 15 does 30 times in 100.
- **"I jump down from the top of the watch tower"** is a cost at fair. If it fails, the worst the act's path can do is a knock of
  6 in 100 of health.
- **"beyond"**, the level f613 gave the model for an attempt past anyone, was not chosen once in 198 rulings on the pod, nor in
  the 218 of the run after f619 (two passes of 99 and the probe's 20).
- **The model's difficulty says little.** In those two passes it chose fair 88 times, hard 9 and easy 8.

The engine holds no sizes. The guild hall is not a part of the place, so there is nothing to measure the jump against, and a
harder roll is still a roll.

## 2. What the probe found

Twenty feats (jumps, lifts, throws, a held breath), each asked for one number in a unit under two framings, then ruled as the game
would rule it. Gemma 4 12B, one pass.

- **The sizes are sensible.** 34 of 40 answers fell inside ranges set before the run. Every miss was within about a factor of two
  and on the low side (the guild hall roof 12 feet, a loaded grain cart 450 pounds, a river 40 to 45 feet across).
- **They are steady.** The same number came back under both framings for 10 of the 20; the rest moved by a small step (a
  millstone 850 or 1,200 pounds, a breath 15 or 45 seconds).
- **The rulings ignore them.** A 12 foot jump up: fair. A 1,200 pound portcullis: hard. A 35 foot drop to the street: fair. Only
  the grappling hook was refused, and not for its size.

So the model knows how big the thing is and does not use it. That is the split the game is built on: the model describes the
world, the engine decides.

**What the probe did not measure:** the size asked for inside the ruling itself. It was asked alone. Section 8 measures that
before anything is trusted.

## 3. The class

Every attempt whose success is bounded by what the character's own body can do: how high or far it jumps, what it lifts, carries
or throws, how long it holds a breath. And every fall: what dropping a given height does to the body that drops, whoever it is.

Not in the class, and unchanged: an attempt bounded by skill (picking a lock, a climb with good holds), by a power (flight; f618
decides those), or by what the words claim (f616).

## 4. The mechanism

*Since f624 the feat is not a field of the ruling: section 14 says why. Point 1 below is as f623 built it; the rest stands.*

1. **The ruling says what the body must do.** The act's ruling gains one field, `feat`: a kind from a list the engine hands it,
   and a size in that kind's unit. "Jump up onto the guild hall roof" is `{kind: jump_up, size: 12}`. Most attempts are no feat
   of the body, and say so.
2. **The engine holds what a body can do.** A new table, data/rules/body.yaml, gives each kind its unit, the attribute that
   bounds it, and the most a body of that attribute can do (section 5). It is read for the acting character, by id.
3. **The engine decides, in three bands,** by the share of that limit the feat asks for:
   - **Within easy reach** (half the limit or less): the ruling stands as the model made it.
   - **Within reach, with effort:** the ruling becomes at least a cost. Past half, at least fair; past four fifths, at least
     hard. The model's own difficulty stands when it is harder, and its own check stands; a plain yes is rolled on the kind's
     attribute.
   - **Past the limit:** a no, never rolled. It is told in the world's words from the table ("You get your hands under it and
     heave, and it does not shift."). Up to a quarter past, it is told as nearly ("It comes up a hand's breadth and no more.").
   - **A drop is the one kind that is not refused past its limit.** It is done, and paid for (section 6; the owner, section 10).
4. **A power still wins.** When the ruling names a capability the character has (flight for the roof), the body's table is not
   asked: the power does it. When the capability is lacked and something stands in for it (f618: a held breath for breathing
   water), both speak and the harder holds.
5. **Both ruling paths read the same table,** the act's and the road's, as f618 did for powers.

The field is always asked for and may be "none", the way f618 made a no say what power it wants, if any. Left optional it would go
the way of "beyond", which the model never chose.

### What the model is told

One entry in the ruling's instructions, and the list of kinds in the request beside CAPABILITIES:

    feat:     when the attempt is done by the body's own strength or reach, its kind from FEATS and how big it is, as the world
              plainly is: one number in that kind's unit. Only what their own body must do: with a lever, a winch or help, their
              share. "none" for everything else.

This is a field of the ruling with a list from data, as `requires` is. It is not a rule added to a narrator's prompt.

### What it costs on the card

About 120 tokens of request (eight kinds, one line each), 60 of instruction, and 10 to 15 of answer in every ruling: an
estimate, to be measured against the turn's budget (data/rules/budget.yaml) when it is built. The act's ruling is one call of the
turn.

## 5. The table, first numbers

Each kind's limit is given at three attributes and runs straight between them and on past the last, with no ceiling (the owner,
section 10). Attributes start at 10, a character may start with one at 30, and they grow by five points a level with no cap.

| Kind | What is measured | Bounded by | At 10 | At 15 | At 30 | At 60 |
|---|---|---|---|---|---|---|
| `jump_up` | feet, up onto or over a thing | strength or dexterity, the better | 4 | 6 | 9 | 15 |
| `jump_across` | feet across a gap, with a run | strength or dexterity, the better | 8 | 13 | 26 | 52 |
| `drop` | feet dropped and landed unhurt | dexterity | 8 | 12 | 25 | 51 |
| `lift` | pounds raised off the ground | strength | 150 | 250 | 1,000 | 2,500 |
| `carry` | pounds moved with | strength | 80 | 130 | 450 | 1,090 |
| `throw` | pounds hurled | strength | 30 | 50 | 200 | 500 |
| `throw_far` | feet a thing in the hand is thrown | strength | 60 | 100 | 300 | 700 |
| `breath` | seconds without air | constitution | 50 | 80 | 300 | 740 |

Read as: 10 is an ordinary person, 15 a fit one, 30 the best a person can be. Past 30 a hero is more than a person, as in a
fight. These are first numbers, set against the sizes the model gives and not against a tape measure, since the model's sizes
run low. They are tuned on the measure (section 8).

### What it does to the probe's twenty feats

The model's size (the larger of its two answers), what it ruled, and what the engine would make of it for three bodies.

| The attempt | Feat | Size | Ruled today | At 10 | At 15 | At 30 |
|---|---|---|---|---|---|---|
| Jump up onto the roof of the guild hall | jump_up | 12 ft | cost, fair | no | no | no |
| Jump over the market stall | jump_up | 4 ft | yes | at least hard | at least fair | as ruled |
| Leap across the alley, rooftop to rooftop | jump_across | 12 ft | cost, fair | no | at least hard | as ruled |
| Jump the town ditch | jump_across | 6 ft | yes | at least fair | as ruled | as ruled |
| Vault the low garden wall | jump_up | 4 ft | cost, fair | at least hard | at least fair | as ruled |
| Leap from the quay onto the barge | jump_across | 8 ft | cost, fair | at least hard | at least fair | as ruled |
| Jump down from the watch tower | drop | 35 ft | cost, fair | warned, then done: it takes all | done: 64 in 100 | done: 13 in 100 |
| Lift the anvil off its block | lift | 180 lb | cost, fair | no, nearly | at least fair | as ruled |
| Lift the loaded grain cart off the man | lift | 450 lb | cost, fair | no | no | as ruled |
| Pick up the sack of flour | lift | 50 lb | yes | as ruled | as ruled | as ruled |
| Lift the portcullis with bare hands | lift | 1,200 lb | cost, hard | no | no | no, nearly |
| Carry the sleeping child up the stairs | carry | 25 lb | cost, fair | as ruled | as ruled | as ruled |
| Heave the fallen millstone upright | lift | 1,200 lb | cost, fair | no | no | no, nearly |
| Throw the grappling hook to the battlement | throw_far | 45 ft | no | (a no stands) | (a no stands) | (a no stands) |
| Throw a stone across the river | throw_far | 45 ft | cost, fair | at least fair | as ruled | as ruled |
| Hurl the full ale barrel at the door | throw | 160 lb | cost, fair | no | no | at least fair |
| Swim under the sunken gate | breath | 45 s | cost, fair | at least hard | at least fair | as ruled |
| Hold a breath until the smoke clears | breath | 45 s | yes | at least hard | at least fair | as ruled |
| Dive to the harbour's bottom | none | | cost, fair | as ruled | as ruled | as ruled |
| Climb the cliff above the cove | none | | cost, fair | as ruled | as ruled | as ruled |

The roof and the portcullis stop being rolls. A fit character still vaults a stall and jumps a ditch. A strong one lifts the cart
off the man without a roll made harder; a weak one cannot, and is told so. The watch tower is jumped, and the fall is paid for.

## 6. Falling: one table for any being

The owner, 2026-11-13: a drop past what a body can land is "done and paid for. This should set groundwork for fall damage being
calculated to any being in the world. If the player shoves someone else off a cliff that should be reflected".

### What the engine has today

- **No height anywhere.** A fight's ground has an `elevated` tag and hazards worded as "a long drop on either side" and "a fall
  beside it" (data/rules/battlefields.yaml); a place has ledges and overlooks tagged `high`. None is a number, and nothing reads
  them for harm.
- **Harm outside a fight never takes the last of a character's health.** Four writers hurt the character (a failed act, a hazard
  of a place, a trap, a moment), each floored at 1. The game's one death (engine/death.py: half the coin, three days, waking at
  the last rest) is reached only from a fight.
- **A being's body is held four ways.** A character has attributes and health. A hire has a level, a profile and a share of
  health (`hp_frac`). A creature has a size and a profile, and gets health only when a fight builds its fighter. A townsperson
  has no attributes, no level, no health: only `gone`.
- **A shove.** In a fight, `force_move` pushes a target out of a zone (it slips away, exposed, sometimes prone), with no harm
  and no height. Outside a fight, attacking a person answers "Attacking people isn't supported yet"; an act on a person can
  change only what they believe, feel and will do. The fight's `harmed` and `moved` on a person are phase 4's.

### The mechanism

**One function, one table.** `fall(body, feet)` in the engine gives the share of a being's whole health a fall takes, from 0 to
all of it. It reads only a small view of the body, which every kind of being can give:

| The being | What lands it (dexterity) | Its size | Where the share goes |
|---|---|---|---|
| A character | their own, with gear | Medium | their health (engine/pools.py) |
| A hire | from their level and profile | Medium | their `hp_frac` |
| A companion | from its template | its own | its health |
| Anyone in a fight (a creature, a hire, the character) | the fighter's | the fighter's | the fighter's hp, as a blow's would |
| A townsperson | an ordinary person's (10, from the table) | Medium | no health to take: see below |

**The share.** The `drop` row of section 5 is the height a body lands unhurt. Past it, the fall takes a share of health that
rises straight from nothing at that height to everything at four times it. A bigger body falls harder: its unhurt height is
scaled by size.

| | Tiny | Small | Medium | Large | Huge | Gargantuan |
|---|---|---|---|---|---|---|
| Unhurt height, times | 3 | 1.5 | 1 | 0.8 | 0.6 | 0.5 |

An ordinary person (unhurt to 8 feet): 16 feet takes a third, 24 feet two thirds, 32 feet all. A hero of dexterity 60 lands 51
feet unhurt and dies at 204. A share of health, not a number of points, so it means the same at level 1 and level 40.

**When all of it is taken,** each being ends by the way it already ends, never a new one: a fighter falls as it would to a blow
(and the owner's rule of 2026-11-12 holds: a human who falls in a fight is down until it ends); a hire by the hire's own fall and
mourning; a townsperson is dead through the world's one writer of that (engine/pulse.py remove_npc). The character dies the
game's one death (engine/death.py), warned first (section 11).

**A townsperson short of death** has no health to lose. What happened is kept the ways the engine can keep it today: a memory, a
mood, their regard for whoever did it. A wound that lasts is the fight's `harmed`, with phase 4.

### Who calls it, and when each is built

1. **A character's own drop (with this feature).** The ruling names `{kind: drop, size: 35}`. Within the unhurt height it is
   judged in the bands of section 4. Past it the character jumps; the ruling's own check, at hard, decides the landing: landed
   well, half the share; landed badly, all of it. The narrator is told what it took in words from the table (jarred, hurt, badly
   hurt), never to soften it. A drop that would take everything even landed well is warned of first (section 11).
2. **A shove off a height in a fight (the feature after).** Here shoving exists today. A `force_move` that wins outright, out of
   ground that has a drop, sends the target over it: the same function, on the target's fighter. The height is the ground's own,
   a number in data/rules/battlefields.yaml on the grounds that have one (a bridge of stone, an icy ledge, a ledge over the
   dark; a default for `elevated`). It works for a creature, a hire, a companion, and the character when an enemy does the
   shoving. No size comes from the model.
3. **A shove of a townsperson outside a fight (with phase 4; the owner, section 10).** Not buildable honestly today: a person
   cannot be attacked outside a fight, has no body to resist with, and a killing has no answer from the law. When an act can
   move a person, a move off a height calls the same function with the size the ruling gives.

## 7. What stays as it is

- **A no stays a no.** The engine does not turn the model's refusal into a yes because the size is small: the refusal may rest on
  something else (no hook in hand).
- **The check and what a failure costs** are the model's, as today.
- **A fight's own rules** for the ground and for improvised acts; the fall is added to its forced move, nothing is replaced.
- **The reuse rule:** a kept ruling keeps its feat and size, so the same act at the same place is the same size. The engine's
  band is worked out each time, so a character who has grown stronger is judged as they are now.

## 8. The measure, before it is trusted

The corpus gains a kind, `feat` (the kinds of f616): a case says which feat a sensible table would name and the range its size
should fall in, and what the engine should answer for the bench's character. From the probe's twenty lines and twenty more, half
of them not feats of the body at all, and some with a lever, a winch or help.

One pod session (about an hour, under a dollar, the price stated before it starts) answers, in order:

1. **Is the field filled when it should be,** and "none" when it should not? Over the feat cases and the 99 existing cases.
2. **Are the sizes given inside the ruling as honest as those asked alone?** Against the probe.
3. **Does the engine's answer come out right** for a weak, a fit and a strong character? This part is the engine's arithmetic
   and is also tested offline.
4. **Did anything else move?** The three corpora before and after, since every ruling's request and grammar change.

If 1 or 2 fails, the fallback is a second small call that asks the size alone, as the probe did, only when the first ruling names
a feat. It costs a call on those turns and is not the plan.

Falling is the engine's arithmetic alone and needs no pod: it is tested on every kind of body (a character, a hire, a companion,
a creature of each size, a townsperson) at heights below, between and past the table's marks.

## 9. What it does not cover, said plainly

- **Fishing by rewording.** A different wording is a new ruling and may get a different size ("the guild hall's low roof"). That
  is true of every ruling today. The fix is for a size, once said, to be kept on the thing itself. The owner: the step after.
- **Help and tools.** The model is asked for the body's own share. Whether a 12B model sizes a lever or four pairs of hands
  rightly is unknown; the measure carries such lines. The engine adding a party's strength together is not in this design.
- **A margin of about two.** The model's sizes run low by up to a factor of two, so a feat just past a body's limit may be
  allowed, and a fall may take less than it should. The feats that fail today are past the limit by three to ten times.
- **Depth, distance swum, hours marched, weight borne for a day.** Not in the first eight kinds. A kind is a row of data.
- **A size the model gets badly wrong** (a portcullis of 60 pounds) is believed. Bounds on a kind's sensible sizes could catch
  the wildest; nothing in the probe was that wrong.
- **What a fall lands on** (water, hay, stone) and what is worn. One table for now.
- **A wound that lasts,** for anyone: a broken leg that slows a character for days. The share of health is all a fall takes.

## 10. The owner's answers (2026-11-13)

1. **Do feats grow with the character without a ceiling?** "No ceiling". The limits run straight on past 30.
2. **A drop past the limit: refused at the edge, or done and paid for?** "done and paid for. This should set groundwork for fall
   damage being calculated to any being in the world. If the player shoves someone else off a cliff that should be reflected".
   Section 6 is the design that answer asked for.
3. **Is "beyond" removed** once the measure shows the field works? "Remove it then".
4. **Is keeping a size on the thing itself part of this, or the step after?** "The step after".
5. **Can a fall kill the character outside a fight?** "Yes, warned first". Section 11 is how.
6. **When is the shove of a townsperson outside a fight built?** "With phase 4". Until then a shove off a height is reflected in
   a fight, where shoving exists (section 6, caller 2).

## 11. A fall that would kill the character

Today nothing outside a fight can kill a character: every harm there is floored at 1. A fall is the first that can, by the
owner's answer, and only after a warning.

- **When it is warned.** The engine works out the share before anything is rolled. If the fall would take everything the
  character has left even landed well, the jump is not made: the turn is told as them at the edge, seeing that it would kill.
  No roll, no harm, no time lost. This is the engine's line from data/rules/body.yaml, not a ruling of the model's.
- **What is kept.** One mark for the character: warned of a deadly drop, at this place. One per character, dropped when they
  leave the place, so it cannot grow. It is kept by place and not by wording, so a reworded jump is the same jump.
- **When it is done.** A drop at that place that would again take everything, tried while the mark stands, is made. The
  character dies the game's one death (engine/death.py: half the coin, three days, waking at the last rest), which today is
  reached only from a fight and takes the acting character by id here.
- **A fall that might kill.** One that takes everything only when landed badly is not warned as certain death: the narrator is
  told the height is deadly before the check, and a bad landing leaves the character at 1, as every other harm outside a fight
  does. Only a fall that kills however it is landed kills, and only after the warning.
- **Someone else's fall is not warned.** A creature shoved off a bridge in a fight falls at once.

## 12. Order and size, if approved

| Step | What | Where |
|---|---|---|
| 1 | The table, its reader, the fall, and the startup check | data/rules/body.yaml, a small engine/body.py, engine/data_check.py |
| 2 | The field in both rulings, the list in the request, the grammar | llm/contracts.py, engine/act.py, scenes/road_actions.py |
| 3 | The engine's decision, the character's own drop, the warning and the death, and how each is told | engine/act.py, engine/ruling.py, engine/death.py |
| 4 | The corpus's feat cases and the measure's reading of them | tools/ruling_eval.py, data/replay/ruling_cases_act.yaml |
| 5 | The pod session, then the numbers tuned | data only |
| 6 | "beyond" removed (the owner: once the measure shows the field works) | llm/contracts.py, engine/act.py, data/rules/act.yaml |
| 7 | A shove off a height in a fight | data/rules/battlefields.yaml, engine/combat_improv.py, engine/body.py |

The feat cases are a file of their own, data/replay/ruling_cases_feat.yaml, so the three older corpora are the same before and after.

Steps 1 to 4 are one feature (more than two modules: this note is its plan), with a test written first on feats the probe did not
hold and on falls for every kind of body. Step 7 is a feature of its own. Every recording that holds an act's ruling will be
re-blessed with steps 2 and 3, since the request and the grammar change for all of them.

## 13. As built (f623), and where it left the plan

Built: steps 1 to 4. The table and its reader (data/rules/body.yaml, engine/body.py), the `feat` field in both rulings and both
grammars, the engine's decision on both paths, the character's own drop, the warning and the death, forty feat cases and the
measure's reading of them. Tested by tools/sim/body_feats_623_test.py on feats the probe did not hold.

Where the build differs from the sections above:

- **Which power does which feat is in the table.** Section 4 said a capability the character has wins. Built narrower: each kind
  names the capabilities that do it in the body's place (`powers`: flight for the jumps and the drop, breathing water for a held
  breath). Seeing in the dark does not lift a portcullis.
- **A fall that takes everything takes it however it is landed.** Section 6 said landed well, half the share. Read alone that
  let a character at full health walk away from any height on a good roll. Built: at four times the unhurt height the roll
  decides nothing; below it, a good landing takes half the share, a rough one three quarters, a bad one all of it.
- **The warning is of that drop, not of the place alone.** Section 11 kept the warning by place. A character warned of the bell
  tower, then wounded, would have died of a low roof with no word. Built: the warning holds the height. A deadly drop at that
  place of at least half that height is the same drop, however worded; a much shorter one is warned of in its turn. A drop made
  and survived spends the warning. What is left: two deadly drops of like height in one place are one drop to the engine.
- **The fatal fall is told in the engine's own words,** one of several lines (body.yaml `died`), then the Threshold as after any
  death. A narrator's passage is written after its operation stands, by which time the character has woken elsewhere, three
  days on.
- **How a landing went is told from the table:** well, roughly or badly, with the part of the share each takes (`landing`).
- **The death's flow moved, engine/death.py did not change.** What follows a death (the goddess, the days, waking at the last
  rest) lived in the fight's scene. It is now the world scene's (scenes/world.py `threshold`), which the fight calls, and a death
  outside a fight goes through the same lines (`dies`).
- **On the road a drop that would hurt is gone around,** as a feat past the limit is. Pressing on past a hazard is not the
  character's own jump; the road's ruling has no warning and no death. One function settles the road's ruling now
  (engine/ruling.py `settled`), for a lacked power and for the body.
- **Below the table's first mark** a limit falls away in proportion to the attribute. The plan did not say; a creature may have
  less than 10.
- **The refusals are keyed `past` and `nearly`.** YAML reads a key `no` as false.
- **The feat cases are their own file,** not part of ruling_cases_act.yaml. Their `expect` is the table's arithmetic held still,
  not a ruling of the owner's, and the file says so: when the owner rules a feat fair or not, the table changes and the case
  with it. Live, the model's feat is counted apart from the verdict. A case may say a drop is `deadly`.

Measured when built: the list of feats adds 513 characters to each ruling's request and its instruction 300, about 130 and 75
tokens; the answer about 12. The three recordings were re-blessed: one request differs in one of them (the act's ruling, with its
list of feats), and the kept ruling carries its feat from that input on.

Not built, said plainly:

- **Where the share goes for anyone but the character.** Every kind of body gives its view and falls by the one table, and the
  test holds that for a creature of each size, a hire, a companion and the character in a fight. Nothing yet takes health from
  any of them for a fall: that is step 7 (a shove off a height in a fight), and the townsperson's with phase 4.
- **A Phoenix item** turns a killing blow aside in a fight. It does not turn a fall aside.
- **The size inside the ruling is still unmeasured** on the real model. That is step 5, the pod session. (Measured since: section
  14. The field did not stand, and f624 took it out of both rulings.)
- **"beyond"** is still in the ruling (step 6, after the measure).

## 14. The measure (the pod session of 2026-11-13), and what it says

One pod, the RTX PRO 6000 MIG 24GB card, 36 minutes, about $0.42. The code at b641acc. The forty feat cases and the three older
corpora (99 cases), each twice. The run before it (f619, at 5b71e02, the same card and the same two passes) is the "before".
Between the two commits the act's ruling differs by this feature alone: its instruction (300 characters), its list of feats, and
the field in its grammar.

**The engine's arithmetic did what the table says on every case.** Every wrong verdict below comes from the kind or the size the
model named, or from what the field did to the rest of the ruling.

Against section 8, in its order:

1. **Is the field filled when it should be, and "none" when it should not? Filled, yes. "None", no.**
   - On the thirty feat cases the kind was right on 24 and 25 (the two passes). The misses: a jump over a stall named as a jump
     across, a stone thrown far named by the stone's weight, a climb named as lifting 180 pounds, a dive named as a drop, a
     breath held under the millpond named as nothing.
   - On the ten cases of the feat file that are no feat, "none" on 9 of 10.
   - **On the 99 older cases a feat was named on 44, both passes,** where a handful are feats at all. Most are of two shapes:
     the character's own weight (lift or carry 150 to 180 pounds for a climb, a wade, a walk, a wrestle, a door broken down), and
     a token size of 1 to 10 for handling a small thing. The token sizes are under half of any limit and change nothing. The
     body's own weight does: it raises the difficulty unseen for the bench's bodies, and for a weak one it is a refusal (a lift
     of 180 pounds is past strength 10, whose limit is 150). Two were refused outright in the run: climbing onto the rocks above
     the cave mouth (named a jump up of 10 feet, both passes) and diving with water breathing (named a jump up of 10 feet, one
     pass).
2. **Are the sizes inside a ruling as honest as those asked alone? For most, yes. For the heaviest, no.** Of the probe's
   eighteen sizes, fourteen came back within a factor of 1.6 and two under another kind. The two heaviest came back at under half: the portcullis 500 pounds (asked
   alone, 1200) and the millstone 400 (1200). A ruling that has said "cost" names a size the cost can be paid for. The
   portcullis, tried at strength 30, was let through in both passes.
3. **Does the engine's answer come out right?** 34 and 35 of 40. The wrong ones: the portcullis and the water cask (size low),
   the anvil at the limit exactly (150 pounds, a hard roll, where the case wants a no), the broken span (12 feet of a limit of
   13), the boulder moved with a lever (the boulder's weight named, not the body's share, so refused), and the millpond (the
   model said no for want of water breathing and named no feat; holding a breath stood in for the power, f618, and the body was
   never asked).
4. **Did anything else move? Yes, and this is the finding.**
   - The sense or the verdict differs from the run before on 16 and 14 of the 99 (the two passes). Right, by file, before and
     now: the 50 simple cases 49, now 50 and 48; the 28 of several steps 27, now 26 and 26; the 21 of things and situations 21,
     now 19 of 19 and 20 of 20, with two rulings and one lost (below).
   - What it fixed: the jump to the guild hall's roof is refused, both passes.
   - What it broke: digging a tunnel into the guild's vault went from no to a cost (both passes). Six lines went from a cost to
     a plain yes (searching rocks, following tracks, finding a stream, asking the wolf, asking the dead sailor, chalking arrows).
   - **The ruling writes less of itself.** Of the rulings that stand, 5 of 70 gave no `why` before and 31 of 68 now; 1 gave no
     `requires` before and 28 now. A ruling that does not say what power it needs is not held to f618: breathing water was
     required before and is not now.
   - **Every ruling with two or more changes numbered them all 1.** Eight rulings a pass were refused by the contract and asked
     again (none before); two were lost in one pass and one in the other.
   - The two passes of the run before differed on 1 of 99. These differ on 5.

**So the field does not stand as built.** Questions 1 and 4 fail, 2 fails at the heavy end. The fallback of section 8 was a second
small call asking the size alone "only when the first ruling names a feat". That keeps the field in the ruling, and the field in
the ruling is what moved it. What the measure points to instead: the ruling goes back to what it was at f619, word for word, and
the feat is asked in a call of its own, as the probe asked it. The engine's side (the table, the bands, falling, the warned
death) is unchanged by that. It needs the owner's word and its own measure, since the probe has only been run on twenty lines and
two of them no feat.

The results are kept outside the repo with the session's files (pod6/out), beside the run before (pod5/out).

### What was done about it (f624)

Three ways forward were set out and ranked by a reader who did not know which the author leaned to: the feat read in a call of its
own, each attempt; sizes kept on the thing (the owner's "step after", section 10 answer 4); and the one call kept and hardened.
The reader put them in that order, and found the order of work that beats any one of them. The owner, 2026-11-13: "Yes, step one".

1. **The field is out of both rulings (f624).** Each asks what it asked before f623: the same instruction, request and grammar,
   and the recording's request for the act's ruling is again the one recorded before f623. What an attempt asks of the body is a
   reading of its own (engine/body.py `reading`), the one place either ruling path gets it, and no call makes it yet: an attempt
   stands as ruled. The table, the bands, falling and the warned death are as built and answer whoever hands them a reading; in
   play nothing does, so today no feat is refused by the table and no fall is paid for.
2. **The engine numbers a ruling's changes (f625).** A number the engine can count is not asked of the model. In both rulings
   that list changes (the act's and a situation's) a change's number is its place in the list, the first 1; `needs` names earlier
   changes by their place; neither grammar has a number to write. Before the field (pod5) the model numbered in order on 10 of 10
   rulings with two or more changes and used `needs` in none of 198; with the field every such ruling was numbered all 1. Whether
   the model points `needs` at the right place with no number written beside each change is for step 3 to show.
3. **One session on the real model:** the restored ruling against the run before f623; the reading asked alone on all 139 lines,
   as a kind with a size and as a kind with a thing and no size, each with and without a kind for the body moving itself. The
   probe told the model what to measure, so whether it can tell a feat from none, asked alone, has never been measured.
   The tool for it is tools/reading_eval.py (f626): four arms (`size`, `size+self`, `thing`, `thing+self`). It scores each
   reading against its case, says what the table answers with it, lists every feat named on a line whose case says nothing, and
   counts the cases read as another kind when asked again. It wires nothing into play. What differs from f623's ruling besides
   the call, so that the two are not compared as like with like: the opening sentence is new (the kind's clause and the size's
   are f623's words); the model is handed the place's name and the line, where the ruling was handed the whole scene, so this is
   a reading at its barest and one wired into play needs its own measure; the kind for the body itself is named as a class with
   no example; the words a `thing` arm gives are kept and judged by no one, so that arm is evidence on the kind only.
4. **By that result:** the reading wired as a call of its own, kept as a ruling is kept (a feat refused must be the same feat
   asked again), then sizes kept on the thing. If the model names feats where there are none when asked alone too, the game does
   without the reading.

## 15. The second measure (the pod session of 2026-11-14), and what it says

One session on the same card as before (41 minutes at $0.69 an hour), on the code at f626. The three older corpora (99 cases) were
ruled on twice with the field out and the engine numbering changes, and every line of all four corpora (139) was read alone,
twice, in each of the four arms of tools/reading_eval.py: 1,112 readings.

### The ruling, with the field out and the engine numbering its changes

| | before the field (f619) | with it (f623) | now (f626) |
|---|---|---|---|
| right, of 99 (each pass) | 97 and 97 | 95 and 94 of those ruled | 96 and 95 |
| asked again, each pass | 0 | 8 | 0 |
| left with no ruling | 0 | 2 and 1 | 0 |
| standing rulings that give no `why` | 5 and 6 of 70 | 31 of 68 | 5 and 5 of 70 |
| read otherwise on the second pass | 1 of 99 | 5 of 99 | 1 of 99 |

The ruling writes itself as it did before the field. Two cases are worse than before it. "I dig a tunnel under the guild hall
tonight and come up inside the vault" was a no and is a cost on both passes, with a success that stops short of the vault ("a
crude tunnel is partially excavated, but the floor of the vault remains intact"); the measure counts it a false acceptance.
"I declare myself king of Parth" was a bounded yes and on one pass is a yes with no bound. Neither is traced to one change: the
instruction was also reworded between the two runs (f620 to f622).

The engine's numbering was hardly tried. Three rulings a pass listed two or more changes, each numbered by the engine and none
sent back; `needs` was written in none of 198 rulings, so whether the model points it at the right place is still unmeasured.

### The reading, asked alone

| arm | kind right, of 40 labelled | a feat named, of the 99 that say nothing | read as another kind the second time |
|---|---|---|---|
| `size` | 36 and 37 (the size too on 32 and 33) | 17 and 18 | 2 of 139 |
| `size+self` | 36 and 36 (32 and 32) | 16 and 16 | 3 of 139 |
| `thing` | 35 and 36 | 11 and 12 | 2 of 139 |
| `thing+self` | 36 and 36 | 13 and 11 | 2 of 139 |

A reading takes 0.41 to 0.44 seconds on the rented card, and none of the 1,112 was lost.

- **It names far fewer feats where there are none: 17 or 18 of 99, against 44 inside the ruling.** Read one by one, four of
  those are feats (the whole inn, the top of the guild hall, the two lines that breathe water). The rest are not: a climb read
  as lifting the body's own weight (150 to 180 pounds) or as a jump of the height climbed, a wrestle as a lift of 180, a barrel
  smashed as a lift of 40, a cloak thrown as a throw of 5.
- **What that would cost in play depends on the body.** For the strong character the corpora use, the table would refuse one
  fair act on one pass (the climb onto the rocks, read as a jump of 12 feet) and make two harder. For an ordinary body
  (strength 10: a lift limit of 150 pounds, a jump of 4 feet) about five of the 99 would be refused or made hard: the climbs,
  the wrestle, the cellar door.
- **The kind is right on 36 or 37 of 40**, against 24 and 25 of the 30 feats inside the ruling. The misses are neighbours (a jump
  over a stall read as a jump across; a grappling hook thrown read as a heavy throw) and one feat missed outright (staying under
  the millpond: none).
- **The sizes are still the weak part.** With the size arm the table's yes or no is the case's on 34 of 40 (34 and 35 inside the
  ruling). Of the six misses two are sizes too small (the portcullis at 400 pounds on both passes, where the model said 1,200
  when told what to measure; the water cask at 50) and one is the millpond. The other three are sizes the case itself calls fair
  that fall on the other side of that body's limit from the case's own reading (the anvil at 150 pounds, a stone thrown 150
  feet, the bridge's span at 12 feet): where an act sits near a body's limit, the answer turns on a size no one could call wrong.
- **Not asking for a size names fewer feats** (11 to 13 of 99, against 16 to 18), and costs nothing on the kind.
- **The kind for the body itself does not cut the feats named with a size** (16 against 17 and 18). With a thing it takes the
  climbs: `thing+self` reads the ledge, the tree, the cliff, the rocks, the rope and the wrestle as the body's own, and what it
  still names beyond the four feats is nine lines, of which two would touch a fair act (a barrel smashed, read as a lift; climbing
  onto a fountain, read as a jump). It also reads talk and waiting as the body's own (29 lines), which the table takes as none.

### What it says for step 4

Asked alone, the model can mostly tell a feat from none, and the ruling is whole again. It cannot be trusted with the size in
the same breath: sizes shrink for the heaviest things as they did inside the ruling. The earlier probe, which named the thing and
the unit, got those sizes right. That points at the order the owner already called "the step after": the kind and the thing read
in one call (`thing+self`), and the size asked of that thing alone, only when a feat is named, and kept on the thing.

Not measured: the reading with the scene given; the size asked of a named thing on these 40 cases (the earlier probe asked 20
lines); either on a 3060. The results are kept outside the repo with the session's files (pod7/out).

## 16. Step 4: the plan (approved 2026-11-14; f627 built, the gate not met: section 17)

What section 15 found decides the shape: the model classifies best when no size is asked, and sizes best when it is told the
thing and the unit. So the reading is two small calls, each asked only when it is needed, and neither is part of the ruling.

### What is asked, and when

1. **The ruling**, as today. A no ends it there: nothing is read for an act that does not stand.
2. **The feat** (new call): for a ruling that stands, whether the attempt is a feat of the body, which kind, and the thing it is
   done to. It is the `thing+self` arm exactly as measured: the same instruction, the place's name and the player's line, the
   same grammar. Most acts end here with none, or with the body's own kind, which the table reads as none.
3. **The size** (new call, only when a kind of the table was named, about one in eight of the 99 plain lines): the size of that
   thing, in that kind's unit, with what the kind measures stated (body.yaml `about` and `unit`). Its instruction is the earlier
   probe's, which gave honest sizes for the heaviest things; where a tool or other hands help, it is asked for the body's share.
4. **The table**, as built in f623: free, at least a cost, a no in the table's words, or a fall that is made and paid for.

On the rented card the two new calls took about 0.4 seconds each, against 3.2 to 3.6 for the ruling.

### Three features, in this order

| | What | Where | How it is checked |
|---|---|---|---|
| f627 | The two calls, built in the engine and not yet called in play; the measure runs them as play would | engine/body.py (what each is asked, its grammar, the asking), llm/contracts.py (two small contracts), tools/reading_eval.py (an arm `sized`, and each case's answer for an ordinary body as well as its own) | A test on the stub; then one pod session, quoted first |
| f628 | Wired: `body.reading` makes the two calls on both ruling paths, and the reading is kept beside the kept ruling | engine/body.py, engine/act.py (the kept row), data/rules/budget.yaml (two tasks, asked outside the transaction), tools/ruling_eval.py (feat cases are read live again) | A test first; stub_short re-blessed (its one act gains a call); the full suite |
| f629 | A size is kept on the thing: once said for a thing at a place, it holds for every character and every wording that names it the same | engine/body.py, storage (one capped store), data/rules/body.yaml (the cap) | A test first, on the road's path too, which keeps no ruling |

f627 is measured before f628 is built. f623 was wired first and measured after, and had to come out.

### The gate between f627 and f628

The session reads all 139 lines twice with the `sized` arm. f628 is built only if, on both passes:

- the table's yes or no is the case's on at least 36 of the 40 labelled cases (it was 34 and 35 inside the ruling, and 34 with
  the size asked in the same call);
- of the 99 lines that say nothing of feats, no more than 2 fair acts would be refused for an ordinary body (strength,
  dexterity and constitution 10), read one by one;
- the portcullis is refused.

If it does not pass, nothing is wired and the result is written here, as section 15 was.

### What is kept, and how it grows

- **With the kept ruling** (f628): the row a character's ruling is kept in also holds what was read for it: none, or the kind, the
  thing and the size. The same act by the same character at the same place is the same feat, asked again or not. It is beside
  the ruling, never inside it. A row kept before f628 holds no reading and is read once when next used.
- **On the thing** (f629): one store by place, each row a kind, the thing as named, and its size; a size is reused when the kind
  and the thing's words are the same. Its cap is data (a first number: 24 a place, the oldest going first).
- Both readings are optional calls in the budget: when the model gives none, or the turn's time is spent, the attempt stands as
  ruled. Nothing waits on them.

### What the player sees

Nothing new is written for this step. What f623 built becomes live again: the table's own lines for a feat past the body, a
drop that is made and paid for, and the warning before a drop that would kill (the owner, 2026-11-13: "Yes, warned first").

### Said plainly

- **It will still read some acts as feats that are not.** As measured, nine of 99 plain lines beyond the four real feats, two
  of which touch a fair act (smashing a barrel read as lifting it; climbing onto a fountain read as a jump). The gate counts
  these for an ordinary body.
- **A feat near a body's limit turns on a size no one could call wrong** (section 15: the anvil, the thrown stone, the bridge's
  span). The table's bands are the engine's; the size is the model's, kept once said.
- **The reading sees the place's name and the line, not the scene.** That is what was measured. Giving it the scene is its own
  change with its own measure.
- **The thing is matched by its words** (f629): the same wall named in other words is sized again. Tying a size to a thing the
  place already holds (a part, an object) comes after, with the scene.
- **Neither a 3060 nor the whole turn's time is measured** by these sessions; the night runs are where that shows.
- **After this:** "beyond" removed (the owner: "Remove it then"), once f628 has been measured in play; the shove off a height
  in a fight; the townsperson's shove with phase 4.

## 17. The third measure: the two calls as play would make them (f627), and the gate

One session on the rented card (2026-11-14), on the committed tree of f627 (`ba11262`): the `sized` arm of
tools/reading_eval.py, all 139 lines, two passes. 278 attempts, 354 calls (278 for the feat, 76 for a size), none lost.

**The gate is not met, on either pass, on any of its three conditions. Nothing is wired: `body.reading` still answers none, and
f628 and f629 are not built.**

| | Pass 1 | Pass 2 | The gate |
|---|---|---|---|
| The engine's yes or no is the case's, of the 40 labelled | 35 | 35 | at least 36 |
| Fair acts refused an ordinary body, of the 99 plain lines | 4 | 3 | at most 2 |
| The portcullis | not refused (800 lb) | not refused (800 lb) | refused |

Beside the gate:

| | Pass 1 | Pass 2 |
|---|---|---|
| Kind right, of 40 | 35 | 36 |
| Kind and size inside the case's range, of 40 | 34 | 34 |
| A feat named, of the 99 plain lines | 12 | 11 |
| Fair acts refused for the case's own body (the corpus's strong warrior), of 99 | 0 | 0 |
| Labelled cases that expect a no, refused by the table, of 9 | 5 | 6 |
| The body's own kind named, of 139 | 28 | 28 |
| A size asked (the second call made), of 139 | 38 | 38 |

The feat took 0.55 seconds at the median and the size 0.50, so about a second where both are asked. Between the passes 3 of 139
lines changed kind, and 7 of the 38 sized the same kind differently (a breath of 45 seconds and then 15; a millstone borne by
four at 400 pounds and then 1,200).

### Against the measure before

| | The size asked in the same call (section 15) | Two calls (here) |
|---|---|---|
| The engine's yes or no the case's, of 40 | 34 | 35 and 35 |
| Fair acts refused an ordinary body, of 99 | about five, worked by hand | 4 and 3 |
| The portcullis, in pounds | 400 | 800 and 800 (1,200 when the probe was told the kind and the thing by hand) |

Better on each count, and short on each.

### Where the engine's answer was not the case's

Four cases, the same on both passes, each with a size **inside the range the case itself calls right**:

| The line | Read | The body's limit | The case expects |
|---|---|---|---|
| I lift the anvil off its block. | lift 150 (range 100 to 400) | 150, a body of 10 | no |
| I lift the portcullis with my bare hands. | lift 800 (range 600 to 5,000) | 1,000, a body of 30 | no |
| I haul the full water cask up the cellar steps on my back. | carry 120 (range 100 to 500) | 130, a body of 15 | no |
| I throw a stone across the river. | throw_far 120 and 150 feet (range 30 to 300) | 60, a body of 10 | a cost |

And one more a pass, a reading that was wrong:

- Pass 1: staying under the millpond read as the body's own kind, so no breath was sized. Pass 2 read it as a breath of 120
  seconds, and it was refused.
- Pass 2: the millstone borne by four sized whole (1,200 pounds) and refused; pass 1 gave a share (400) and it stood. This is
  the only labelled line where the share is asked for and a feat is named: the winch and the lever were both read as no feat.

### The fair acts refused an ordinary body

| The line | Read | An ordinary body's limit |
|---|---|---|
| I break down the cellar door where they keep (a person) and pull them out. | lift 185, then 240 (the person) | 150 |
| I climb onto the fountain and give a speech... | jump_up 6 feet | 4 |
| I breathe underwater and swim to the sea floor. | breath 120 seconds | 50 |
| I bar the granary door and drive the looters off with my sword. (pass 1 only) | lift 450 (the door) | 150 |

Three of the four are the kind misread (a pull, a climb and a door barred, read as a lift, a jump and a lift). The fourth is a
line the corpus rules a cost.

### What it says

1. **The first call holds.** The kind is right on 35 and 36 of 40, and a feat is named on 12 and 11 of the 99 plain lines, as
   in section 15. What is left of its misreads still costs an ordinary body three or four fair acts in 99.
2. **The size is right to a range, and the table decides at a line.** Worked on the corpus itself, with no model: given each
   case's own single reading the engine's answer is the case's on 40 of 40; given the low end of every range it is 35, and
   given the high end 35. Ten of the 40 labelled cases have a range that crosses the limit of the case's body, so a size the
   corpus calls right can give either answer. The model's 35 is what a reader gets whose sizes are right to the range and no
   better. The four misses above are of that kind.
3. **So the gate's 36 asked for sizes more exact than the corpus's own labels on those ten cases.** That was not seen when the
   gate was proposed. It is not a reason to move the gate after the measure: it is what the measure found.
4. **A better wording of the size is unlikely to be the fix.** The size moved from 400 to 800 for the portcullis between the two
   forms, and it moves between passes of the same form. A number from the model is a fair guess of the size of a thing; the
   table as built turns a yes into a no on which side of one number that guess falls.

### Waiting for the owner

Step 4 stops here unless the owner says otherwise. In play nothing changes: an attempt stands as ruled, the table is not asked,
no fall is paid for. What could come next, none of it planned or built:

- **Leave it.** The ruling alone decides what a body can do, as it has since f624. The table, the falls and the two calls stay
  in the code, called by nothing.
- **A table that does not turn on a guess.** Near a body's limit the answer becomes a check with a cost, and only a size far
  past the limit is a no. This changes what f623 decides, so it needs its own plan, and its own measure on lines other than
  these (the rows of this session have now been read too closely to test it).
- **Sizes the world already holds.** Where the thing is an object or a part the place keeps, its size is the engine's, kept
  with it, and the model is asked only for what the world does not hold. This is f629's idea turned around, and it sits with
  the scene being handed to the reading, which is also unmeasured.

Not covered, said plainly: the reading was handed the place's name and the line, never the scene; nothing was measured on a
3060; the size's instruction was measured in this one wording only; the 99 plain lines were scored by the corpus's own ruling
(a fair act is one it does not rule a no), read one by one in the tables above.

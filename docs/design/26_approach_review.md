# 26. Review: how the play faults are produced, and whether the approach should change

Written 2026-11-17 at the owner's request, before another round of fixes: "let's do a review of the code base so far and how these
errors are produced. Let's think if maybe a different approach entirely would be more effective or if what we have is best", and
"see if there are any infrastructure changes you would make to this project".

Nothing in the code was changed for this review.

## How it was done, and how far to trust it

Six read-only readers each traced one area (reading a line, model time, narration and speech, the scene layer, storage and data, tests
and tooling). The claims this review leans on were then read again in the code, or were seen in play. Each carries a mark:

- **[checked]** read in the code a second time by the session.
- **[seen]** seen in live play this week (docs/play).
- **[reader]** found by a reader with file and line, not read a second time.

The `logs/` folder is refused to this session, so nothing here comes from the record of what the model answered.

## The answer in brief

1. **The architecture is right and should stay.** "The engine decides; the model names, describes and speaks" is the only design that
   fits a 12B model on a 3060 and the pillars. Every alternative considered (section 4) breaks an owner's decision or a pillar.
2. **The method is wrong at three seams, and those seams produce most of the faults.**
   - A typed line has several readers that can disagree (word patterns before the model, the model, word patterns after it).
   - The narrator and the speakers get a wide brief and thin checks, where the principle asks for a narrow brief.
   - Too much model work sits on the path the player waits on, and the card is idle while the player reads and types.
3. **The play-and-fix loop has stopped paying for one class.** About 30 of the roughly 70 features since the live plays began (f643 to
   f716) are "a line that says X was read as Y". Each was built as a class, but the classes are narrow, and natural language has no end
   of them. More rounds will keep finding more.
4. **Most of the structural answer is already designed and agreed, and has been waiting.** Phase 4 of the roadmap (doc 09 section B: the
   engine writes a beat, decide then speak, smaller prompts) was put behind the fault rounds on 15 November. This review recommends
   going to it now, and adding the one piece no doc covers: a redesign of how a line is read (section 5.1).
5. **Nothing here should be taken on faith.** No live number exists for how often the model reads a line right. The first step of any
   path is to take that number, and keep a change only if it moves.

## 1. The numbers

| What | Figure | Mark |
|---|---|---|
| Code | engine 43k lines, scenes 21k, llm 7k; tests 73k lines in 505 files | checked |
| scenes/world.py | 4,450 lines, 221 methods of its own, 32 mixins | reader |
| Features since the live plays (f643 to f716) | about 70, about 30 of them a misread line | checked |
| Readers of the typed line | 13 intercepts before the model, 28 repair rules after it, 291 places in 51 files that search the line by pattern | reader, checked |
| Kinds of model call | 62 in data/rules/budget.yaml: 36 the player must wait on, 21 optional, 5 for tools | checked |
| The card (3060, scaled from an A4000) | 757 prompt tokens a second read, 31.7 tokens a second written | reader |
| A turn | median 23.9 s, 95th percentile 60.9 s, the limit 60 s | reader |
| A townsperson's prompt | median 29,155 characters (about 10 s to read uncached); the owner's target is 14,000 | reader |
| Interpretation corpus | 252 cases; the suite replays each case's stored reading through the repairs; no live pass rate is recorded | reader, checked |
| Passages | written whole inside JSON, not streamed (`"stream": False`, llm/llama.py:125) | checked |

## 2. How each class of fault is produced

### 2.1 A line read wrongly (the largest class)

The path of a typed line (scenes/world.py turn, take_line, understand):

1. **Thirteen intercepts** read the raw line by word patterns. The first to match takes the whole line; the model never sees it.
2. **The interpreter** (one model call). Its grammar fixes the kind of each step, but `destination`, `target`, `ware`, `ability` and
   `item` are free strings (llm/contracts.py:457-466) **[checked]**. The model can write any id, offered or not.
3. **Twenty-eight repair rules** rewrite the plan. plan_repairs.py says what they are: the model's "habits", each fixed by "one small
   rule".
4. **The audit**, when a risk flag fires: two more model calls, then a re-proposal. It both adds and drops steps (f698, f699, f707 are
   all fixes to the audit itself).
5. **The handlers** read the typed line again by pattern: 291 places in 51 files.
6. **A fight has its own interpreter**, one action only.

So one sentence is read by word patterns, then by the model, then by word patterns again, and each fix adds a rule to settle one more
disagreement between them. That is the mechanism behind the class. The faults of the last play fit it:

- "After breakfast we set out along the River Road for the Willowmead wetlands." became speech to a companion: the model gave one talk,
  and no repair covers a line that does not open on a walking verb **[reader]**.
- "We follow the causeway deeper into the wetlands" became a walk to the Mirewater Fens, 18 hours away: the candidate list offered the
  far fens by likeness of meaning, and nothing stops the model choosing it **[reader]**.
- "We leave the toad be and follow the slime trail" in a fight lost its second half: the fight's reader has room for one action
  **[reader]**.
- This session's own f716 added two more patterns that read the line for camp words. It was built in the house style, and the house
  style is the cause.

The suite's interpretation test cannot see any of this: it feeds each case's stored reading through the repairs, so it tests the
repairs and not the model **[reader]**.

### 2.2 A turn that runs out of time

- The first turn after loading has spent its budget in both plays **[seen]**. There is no warm-up of the chat model **[checked]**.
- The budget is arithmetic over prompt size and expected answer; a required call goes ahead until less than 8 s is left, then the line
  gets a stand-in or stands in part **[reader]**.
- A family of features exists to make running out honest (f463 to f471, f597, f684, f711, f715). They work. They do not make the turn
  shorter.
- The card is idle while the player reads and types. Only one kind of work uses that time (building a place's missing residents);
  deferred work waits for the tail of a later turn **[reader]**.
- The player sees nothing until a whole passage is written and checked, about 8 s of writing for a short one **[checked]**.

### 2.3 The story says what the game does not hold

- The narrator's rule is a sentence in its prompt: "never add people, creatures, items of value, exits or events that are not in the
  GAME STATE" (scenes/world_prompts.py:106) **[checked]**.
- The checks after it catch a capitalised name nobody gave, a creature of the bestiary that is not there (f701), machinery, stale
  wording and invented speech. Nothing compares what a passage claims with the world. An unnamed person ("a watchman"), a prop ("your
  grain cart", Pae's shield) or a clue (drag marks and a slime trail) passes every check **[reader]**.
- Only one thing carries an invention forward: a named part of a place can be adopted as a place (part_actions.py:215). People, things
  and clues are not, so the next passage cannot agree with them and following them leads nowhere **[reader]**, **[seen]**.
- The 90 briefs at the call sites are English sentences written by hand, and each passage starts from the last three passages as text.

### 2.4 People who say what they do not know, or do not sound like people

- **The news leak.** A townsperson's prompt holds "NEWS THAT HAS REACHED HERE" in full. The reveal gate only decides what the engine
  records as learned; it cannot stop the words **[reader]**. One call is asked to decide what to share, move trust, offer work and
  sound like a person, with twelve fields beside the speech (doc 09).
- **The stiff companions.** `accent()` tells the model "in every line and the same each time", and the habit it then quotes says "now
  and then leaves out a small word" (engine/voice_profile.py:238, quirks.yaml:76) **[checked]**. The instruction contradicts itself,
  and "in every line" wins. That first half is the owner's decision f410 ("An accent is in every line a speaker says, not rolled for
  some"), made after the opposite fault: a smith whose accent vanished from one reply to the next.

### 2.5 The game's own lines out of order or at odds

- "Nothing comes of that here" printed beside the part line; the camp note printed before the walk to the camp **[seen]**.
- Notes print the moment code calls them, and passages are queued. Nothing holds the turn's page as one ordered list.
- The typed-line path and the pane path each wrap a line by hand (world.py:1068-1113 and 1745 on); the pane path has no "part" outcome
  **[reader]**.

## 3. What is sound and should be left alone

- The engine decides every number and state change.
- Operations, the write fence, and model calls before transactions.
- Seeded streams, the recordings and their replay, the state fingerprint.
- The truth view (engine/truth.py facets): one way to ask what is true, by who is asking.
- Data in YAML with startup checks; migrations as ordered steps.
- The stub model and one process per test; the feature number and its reason at the head of every test.
- The budget's honesty features, and the mixin split by domain (large, but legible; replacing it is high risk for little gain).

## 4. A different approach entirely? What was considered

| Approach | Verdict | Why |
|---|---|---|
| The model as the dungeon master, calling the engine as tools | No | Many calls a turn on a 12B model: slower and less reliable, and it gives up "the engine decides" |
| A larger or hosted model | No | The owner's decisions: local only, a 3060 as the minimum, hosted services out |
| A parser with menus | No | Pillar 2: "the player can try anything" |
| Check harder afterwards (a second model call judging each passage against the world) | No | Costs time the turn does not have, and a 12B judge is itself unreliable |
| Keep the architecture, change the method at the three seams | **Yes** | Section 5 |
| Train the reader (a LoRA on the interpretation corpus) | Later | It has right and wrong answers, so it is a better first target than prose; it waits until the reader's contract stops changing |

## 5. What I would change

### 5.1 One reader for a line (new; no doc covers it)

The engine should decide what can be done here, and the model should be the only thing that reads the sentence.

1. **Ids come from the engine's list.** The grammar for each call is built from the candidates offered: `destination`, `target`, `ware`,
   `ability` and `item` may only be an offered id or empty. A place the player named that is not on the list goes in its own field and
   must be words of the typed line. The model can no longer choose the Mirewater Fens unless the player typed it.
2. **Each step says which words of the line it stands for.** Code then checks coverage: a step that stands for no words is the model's
   invention and is dropped; a clause no step covers is said to the player. This replaces the audit's model calls with a check that
   cannot disagree with itself, and saves two to four calls on flagged lines.
3. **What a handler needs is a field the reader fills,** never a second reading of the text: a count, an hour, a camp, a room, who is
   spoken to. The census of 291 pattern sites becomes the list to work down.
4. **An intercept becomes an offer.** Whether a yielded foe, a mentor or a camp is in play stays the engine's test of state; the special
   act is then offered to the reader as a candidate, not matched by words before the model.
5. **Fights use the same reader,** with a fight's candidates and more than one step.

How to build it: behind a switch in data, as act() was (f603), and measured against the old path on the 252 cases with the live model
before the switch is flipped. I cannot promise it reads better. The repairs record real habits of this model, and a 12B model may quote
its words badly. That is why the measure comes first.

### 5.2 Narrow briefs (already designed: doc 09 section B, roadmap phase 4)

- **Decide, then speak (B4), with the smaller prompt (B5).** The engine, or a small call, chooses what a person shares; the speaking
  call is given only that. The news leak ends, because unshared news is not in the prompt, and the largest prompt on the card shrinks
  toward the 14,000 target.
- **The engine writes a beat (B1).** The 90 hand-written briefs become data: the facts, one angle, what to withhold, and I would add a
  short list of true incidental details the passage may use (who is in sight by trade, what stands in the place).
- **Invented people: adopt or send back.** The check that stops a creature the game does not have (f701) can be widened to a person of a
  trade nobody present holds. Where the place could have one (a town has a watchman), make the person real, as named parts are
  adopted today; where it could not, send the passage back once. This is the dungeon master's rule: what is said becomes true, or is
  not said.
- **Invented clues will not be fully closed** on this model. Beats narrow them; the rest is a known remainder.

### 5.3 Time

1. **Warm the chat model at load,** while the opening passage is read. Small.
2. **Use the idle card.** Run deferred and optional work (situation rulings, the pulse's threads, births, exchanges) while the player
   reads and types, through the worker that already cancels background calls when a line arrives. The waited path becomes the reading,
   the outcome and the passage only. Medium; the recorder must say which input an idle call belongs to.
3. **Drop the audit's calls** (5.1).
4. **Release a passage as it is written,** a sentence at a time, each sentence through the cheap checks first. The player starts
   reading after seconds, not after the whole passage. This needs prose out of JSON (B3) and a decision from the owner, because a
   passage sent back whole can no longer be withdrawn (section 7).

### 5.4 Infrastructure, in the order I would do it

| # | Change | Replaces | Size | Risk |
|---|---|---|---|---|
| 1 | **Live measures as a gate before a person plays:** the reader's pass rate on the corpus, inventions per passage, stiff speech, seconds per turn shape, all on the real model | Finding these only by playing | Medium | Model variance; use thresholds |
| 2 | **Rollback of scene state by declaration.** A failed operation restores Python state from a hand-kept list of attribute names; one left off the list survives the rollback (world.py:1165, 1180) | The list and the copy of every `_` attribute | Medium | Recordings may move |
| 3 | **One turn driver and one page.** Typed lines, pane commands and the opening share one wrapper; every note and passage of a turn joins one ordered list | The duplicated wrapper; notes printing out of order or at odds | Small to medium | Recordings depend on order |
| 4 | **Split the data hash into rules and wording.** Any change of wording in data re-blesses all three recordings today (twice this week) | Needless re-blessing | Small | Low |
| 5 | **The suite loop.** Choose affected tests by imports, not by word match; skip the stray repo copy under .claude/worktrees; run the heavy subprocess tests in a serial lane; one lock so two runs never collide (a collision on 16 November reported 55 false failures) | Flakes that block a push; false failures | Small | Low |
| 6 | **Declare a model task once** (schema, budget, sampling, audit and checks are five places today) and, kind by kind, **an action kind once** (forage is spread over about nine files) | The spread | Medium, by steps | Low |
| 7 | **A schema layer for data** in place of the hand-written checks in data_check.py (about 600 lines); `yamlio.row` already does this in eight files | Repeated checks | Medium, file by file | Low |
| 8 | **One registry of stores and their caps,** with one test over all of them | About 15 scattered constants; "nothing grows without bound" is unchecked for threads, effects and entities | Small | Low |
| 9 | **A narrow contract for what the scene offers engine modules** (act.py reaches into the scene 167 times, events.py 145), and `self.player` moved to the acting character as each file is touched (about 1,000 reads left) | Engine modules that can only be tested with a whole scene; the multiplayer goal | Medium, by steps | Low |
| 10 | **Retire the phase 3 scaffolding tests,** and write new tests through typed lines where they can be | Tests that break on a rename that changes no behaviour | As files are touched | Low |

## 6. The three faults found on 17 November, under this review

- **"Nothing comes of that here" beside the part line:** a small engine fault. Fix it now.
- **Travel read as speech:** a reading fault. Record it in the corpus as a case; do not write a twenty-ninth repair for it. It is fixed
  by 5.1 or it shows that 5.1 does not work.
- **The innkeeper's news:** fixed by decide, then speak (5.2), not by another rule in his prompt.

## 7. Decisions for the owner

1. **Stop the fault rounds for misread lines, and take the baseline first?** Run the 252 cases against the live model on this machine
   (about 20 minutes) and record the pass rate. Recommended: yes.
2. **Build the one reader (5.1) behind a switch, kept only if the number improves?** Recommended: yes.
3. **Go to phase 4's speech work now** (decide then speak, the smaller prompt), ahead of more fault rounds? Recommended: yes.
4. **The accent decision (f410).** Keep the voice in every line (word choice, rhythm, the sayings the engine offers), but let the engine
   decide, reply by reply, whether a slip of grammar shows, and tell the model so in plain words either way. Recommended: yes. This
   changes f410, which asked for the accent in every line.
5. **Release a passage sentence by sentence?** "What the model writes is checked before the player sees it" would hold for each
   sentence, not for the passage as a whole. No recommendation until prose is out of JSON and the wait has been measured.
6. **Which infrastructure items (5.4) to take, and when.** Recommended: 1, 4 and 5 now (they speed up everything after them), 2 and 3
   before phase 4 touches the turn again, the rest as files are touched.

## 8. A suggested order

1. The baseline, the small engine fault, the suite loop and the hash split.
2. The live gate (5.4 item 1), so each later step is measured before anyone plays.
3. Decide then speak with the smaller prompt, and the accent change if the owner agrees.
4. The one reader, behind its switch.
5. Warm-up and the idle card.
6. Beats, with adoption of invented people.
7. Then play again, and see what is left.

# Model settings, the request, and other models: an overnight trial

18 November 2026. You asked whether there are model settings to tweak or other models to try, then for trial runs with Nemo and
Qwen, then gave eight hours for any lead.

**Nothing in the game was changed.** No code, no data, no commit. Every run replayed saved speaking requests straight at
llama-server from scripts kept outside the game. `data/rules` is clean. Everything here is a measurement for you to judge.

If you want to read replies blind before you read my conclusions, stop here and open the sheets named under "Where everything is".

## The answer in short

1. **Sampling settings are not the lever.** Warmer, XTC, DRY, a min_p floor, no repeat penalty: none of them made the replies less
   alike or better to read. Your decision to keep them as they are holds up.
2. **What the request says about the moment is the lever.** A short block of true facts placed just before the typed line ("nobody
   was hurt in that fight", "they speak to you as if you were a smith; you are a baker") cut the replies that contradict the game
   from 29% to 17% on the first eight requests and from 43% to 11% on a second eight, and roughly halved the replies readers
   called machine-written (58% to 24%, then 58% to 35%). This is on the game's own Gemma, with no other change.
3. **No other model is needed to get that gain.** Of five other models, four are worse than Gemma for this game. Qwen 3.5 9B is the
   one worth a second look: with the same block it reads level with Gemma, sounds less like a machine, is about twice as fast and
   a smaller file, but it makes more things up. It would need its own full measure before any swap.
4. **Two engine-side fixes fell out of the trial**, each small, each a feature for you to approve or not:
   - About 1 reply in 100 from townsfolk never ends: it runs on to the 2,048 token limit inside the last field of the reply,
     `journal_note`. On the 3060 that one reply is over a minute. With that field left out of the reply when no note is due, it
     did not happen once in 416 replies, and those replies took half the time.
   - Replies to the same question open the same way about half the time whatever the sampler seed. A grammar that refuses the
     speaker's lately used openings breaks that: six replies running open six different ways against two or three, as long as
     it refuses at the start of a word and holds only the last few openings (section 5).
5. **A correction to what I told you yesterday.** I said townsfolk speak at temperature 0.8 against Google's default of 1.0 for
   Gemma 4. That was wrong. I read the caller's figure and missed that every warm task has 0.15 added to its temperature and 0.1
   to its repeat penalty (`DND_TEMP_ADD`, `DND_REPEAT_ADD`, f393). Townsfolk really run at temperature 0.95 with a repeat penalty
   of 1.22 over the last 192 tokens, and companions at 1.15 and 1.22. Temperature was never a gap.

## What was run

- **Eight saved requests** from the measuring set, exactly as the game sent them with the switch off: the baker asked for a
  waterskin, the baker taken for a smith, the butcher taken for the clerk, the herbalist shown a plant, the innkeeper asked the
  news, Jesna asked who is hurt worst, Khash asked what he makes of the place, Khash told about a lost fight.
- **A second eight**, other typed lines, added late to check the main finding on cases that did not find it: the innkeeper Hys
  offered a hand, both companions asked about their past, the baker asked who made a knife, Khash asked whether to rest or move
  on, the baker asked to sharpen a blade, Jesna told the player takes first watch, Ingmer asked what is strange on the roads.
- Each request replayed at 12 sampler seeds (20 or 40 for a few rows), the same seeds in every row, so a row is 96 replies.
  About 6,600 replies in all.
- **Six models**, all on the game's own llama-server build, Q4_K_M files: the game's Gemma 4 12B, Mistral Nemo 12B, Mag Mell 12B
  (a Nemo roleplay merge), Qwen 3.5 9B, Gemma 4 12B StyleTune and G4 Plainsong 12B (two fine-tunes of Gemma 4).
- **Three blind readings**, three readers each, 24 sheets a round. Every sheet printed who is answering with their personality,
  traits and way of talking (your rule from the last blind pairs), the facts of the moment, the typed line, and the replies
  shuffled and lettered. The readers were instances of a large hosted model, not people. Your reading is the one that counts.
- Counts by rule (openings, length, names never given, dashes, replies that never end) and rough checks per request (does Jesna
  say nobody was hurt, does the butcher answer which job is closest).

## 1. Sampling: no

Gemma, today's request, 20 seeds, 160 replies a row.

| Sampling | Different openings of 20 | Open the commonest way | A dash in the speech |
|---|---|---|---|
| Today's | 7.6 | 49% | 8 |
| Warmer by 0.25 | 9.0 | 41% | 10 |
| XTC, DRY and a min_p floor | 7.1 | 48% | 18 |

"Opening" is the first three words. On one request, 14 of 20 seeds open "I don't sell"; on another 16 of 20 open "The clerk is".

This answers the caution I added to yesterday's analysis. Every earlier run was played at one campaign seed, so the same typed
line met the same sampler seed, and I could not say how much of the sameness was the seed. Now I can: it is the model's habit.
Twenty different seeds give the same first words half the time.

- **Warmer** gave slightly more openings and nothing else. In the blind reading it was the worst row: 0 of 72 among the best,
  46% among the worst, 62% called machine-written, against 4%, 44% and 58% for today's.
- **XTC with DRY over a min_p floor** (the arm the 11 November trial pointed to and never ran) changed nothing and doubled the
  dashes.
- **No repeat penalty** made replies longer (38 words against 24) and 12 of 96 never ended.

## 2. The request: a reading of the moment

For each request I wrote two or three true lines and put them just before the typed line, under the heading "THIS MOMENT, AS THE
GAME READS IT (all of it true; answer to this, not only to the words)". Examples:

- Jesna: "Nobody in the party was hurt in that fight: not you, not Khash Yagrakh, not the one who hired you." and "The question
  was put to the whole party. You are the one answering, to his face."
- The butcher: "They speak to you as if you were the guild clerk. You are the butcher." and "The clerk, Aldley Rushton, is not
  here. The board is on the wall beside you both, and you can read it as well as anyone."

**These lines are mine, written by hand, and you have not read them.** They stand in for what an engine could hand over. Most of
each block is something the engine already holds with no model call: what the speaker sells, whether anyone was hurt, what was
asked a moment ago, who else is in the room, whom the question was put to, the true facts of a companion's past. The rest needs
the typed line read first (who the player has taken them for, what the question is really about), which is the work plans 29 and
31 describe. So this is a measure of how much that direction is worth, not a feature.

What the replies did, Gemma, 12 seeds each:

| Request | Check | Today's | With the moment |
|---|---|---|---|
| Jesna, who is hurt worst | says nobody was hurt | 0 | 4 |
| | makes up an ailment | 5 | 1 |
| Butcher taken for the clerk | answers which job is closest | 4 | 10 |
| | says only that the clerk is away | 6 | 1 |
| Herbalist shown a plant | names or reads the plant | 1 | 6 |
| Hys offered a hand (second set) | names someone in the room who wants one | 0 | 10 |
| Khash, rest or move on (second set) | says which he would rather | 2 | 11 |
| | turns it back with only a question | 11 | 1 |
| Jesna asked about her past (second set) | something true of her past | 0 | 12 |
| Khash asked about his past (second set) | something true of his past | 2 | 6 |
| Ingmer, strange on the roads (second set) | states something uncanny | 6 | 2 |

Two of those rows are worth a second look. Jesna's true past (the wharves of the Great River, the boy who braided willow) and
the names of the farmers in Hys's room were **already in today's request**, and Gemma used them 0 times in 12. Said again in two
lines just before the typed line, it used them 12 and 10 times in 12. The requests run about 4,000 tokens (2,000 to 4,900), and
the block adds about 110. So part of the gain is not new information at all: it is the same facts put where the model looks.

The blind reading, first eight requests (72 showings a row; 48 for the hosted model):

| Request, on Gemma unless said | Among the best two | Among the worst two | Reads as a machine | Contradicts the facts |
|---|---|---|---|---|
| A large hosted model, today's request | 100% | 0% | 0% | 0% |
| A large hosted model, the changed request | 100% | 0% | 0% | 0% |
| Own lines, the moment, three short rules | 17% | 11% | 47% | 4% |
| The moment | 17% | 17% | 24% | 17% |
| Own lines and the moment | 8% | 14% | 31% | 8% |
| Own lines as earlier turns, and the moment | 8% | 22% | 42% | 6% |
| No JSON, spoken words only | 12% | 46% | 60% | 25% |
| Today's request | 4% | 44% | 58% | 29% |
| Today's request, warmer | 0% | 46% | 62% | 29% |

The second eight (one best and one worst a sheet, four replies a sheet):

| Model and request | Best | Worst | Reads as a machine | Contradicts the facts |
|---|---|---|---|---|
| Gemma, today's request | 15% | 32% | 58% | 43% |
| Gemma, the moment | 32% | 17% | 35% | 11% |
| Qwen, its own request | 12% | 29% | 42% | 39% |
| Qwen, the moment | 40% | 22% | 33% | 29% |

What the other request changes did on Gemma:

- **Example lines written for the person** (three lines each, mine, in place of the three shared "how people sound here" lines):
  little on their own. As a described list they changed nothing countable. Given as earlier turns of the conversation they
  shifted the voice a little ("Still looking for an anvil in my flour sacks?") and Khash picked up his "sir" and "madam".
- **Taking out the one rule "match the length of what was said to you"**: nothing. Mean length 26 words against 24. That rule
  is not what holds the replies short.
- **Three plain sentences in place of the twelve DIALOGUE STYLE rules**: longer replies (34 words against 24), more invention,
  five times the dashes. With the moment block it had the fewest contradictions (4%) but nearly half its replies were called
  machine-written.
- **No JSON, spoken words only**: twice as long, no better read, a quarter contradicting the facts. The JSON is not what makes
  the speech stiff.
- **The large hosted model on today's unchanged request** took a best-two place on every sheet. So the request is good enough for
  a big model as it stands, and model size is a larger share of the gap than I ranked it yesterday. Two cautions: the readers
  are from the same family as that model, so they may favour its manner; and it still gave Jesna "a bramble scratch" until the
  moment block told it nobody was hurt. It cannot ship in any case: a hosted model stays out.

**What did not move: the first words.** With the moment block Jesna says "I'm fine. Not a scratch on me." where she said "I'm
fine. Just a bit of dust in my throat." The truth changed; the opening did not. Section 5 is about that.

## 3. Other models

*Followed up the same day:* Gemma and Qwen in blind pairs at new seeds, with a copy for the owner to read:
`2026-11-18_gemma_qwen_side_by_side.md`.

Twelve seeds, 96 replies a row. "Own settings" are the sampling each model's makers recommend; the game's repeat penalty of 1.22
over 192 tokens garbles every model but Gemma, so the fair rows use a light one (1.1 over 64).

| Model | Open the commonest way | Words | Names never given | Dashes | Never ended | Seconds a reply here |
|---|---|---|---|---|---|---|
| Gemma 4 12B (the game's), today's | 50% | 24 | 0 | 2 | 2 | 2.8 |
| Qwen 3.5 9B, own, light penalty | 24% | 28 | 1 | 0 | 1 | 1.6 |
| Qwen 3.5 9B, own, no penalty | 28% | 37 | 0 | 0 | 21 | 6.2 |
| Gemma 4 StyleTune, light penalty | 32% | 32 | 0 | 22 | 0 | 2.3 |
| Mistral Nemo 12B, own | 58% | 23 | 4 | 0 | 0 | 1.2 |
| Mag Mell 12B, own | 28% | 37 | 3 | 4 | 2 | 2.8 |
| G4 Plainsong 12B, light penalty | 14% | 26 | 3 | 11 | 0 | 2.1 |

The blind reading across models, first eight requests (72 showings a row):

| Model and request | Among the best two | Among the worst two | Reads as a machine | Contradicts the facts |
|---|---|---|---|---|
| Qwen, the moment | 46% | 0% | 3% | 18% |
| Gemma, the moment | 44% | 1% | 10% | 12% |
| StyleTune, the moment | 35% | 1% | 17% | 14% |
| StyleTune, today's request | 31% | 17% | 31% | 38% |
| Qwen, today's request | 18% | 11% | 19% | 56% |
| Gemma, today's request | 14% | 3% | 29% | 25% |
| Nemo, own settings | 8% | 11% | 53% | 32% |
| Mag Mell, own settings | 0% | 25% | 79% | 44% |
| Plainsong, the moment | 4% | 50% | 71% | 32% |
| Plainsong, today's request | 0% | 81% | 82% | 85% |

- **Qwen 3.5 9B.** The only one worth a second look. With the moment block it is level with Gemma and reads less like a machine
  (3% against 10% here, 33% against 35% on the second set). Its lines have turns Gemma does not find: "I am Gisette Bradton, and
  I cut meat, not paper." "Though your feet are muddy, so maybe the ground is the one who took a hit." It is a 6.2 GB file and
  ran at 82 tokens a second here with no draft model, a reply in 1.6 seconds against Gemma's 2.8. Against it: it makes more
  things up. Left on today's request, 56% of its replies contradicted the facts ("the well's been dry since dawn", "Khash's arm
  is wrapped in a rag", "just like Redstone did after the winter raid", a butcher selling "meat for sixteen copper a ration").
  With the block it still contradicts more than Gemma (18% against 12%, then 29% against 11%). It broke speakers' rules more
  (calling the stranger "friend", "love", "old man"), put narration inside speech now and then ("I'm fine, he said."), and on
  "I take the first watch" it had Jesna take the watch herself 4 times in 12 (Gemma: 0). Without any repeat penalty 21 of 96
  replies never ended.
- **Gemma 4 12B StyleTune.** Close to Gemma, a little livelier, no better once both have the moment block. It writes dashes in
  about a quarter of its replies, which your rule forbids. No reason to switch.
- **Mistral Nemo 12B.** Natural rhythm, but short of ideas: at its own settings 58% of replies to a request open the same way
  and many are word for word the same. It invents names and prices ("Old Gerrick", "2 copper"). Out.
- **Mag Mell 12B.** Invents freely (a 12 copper waterskin, a new smith by the old mill) and loses track of who is speaking. 79%
  called machine-written. Out for a game where the engine owns the facts.
- **G4 Plainsong 12B.** Garbled even at fair settings ("This isn't a forge, out-of-cell question; it is a bakery."). Out.

**The interpreter.** Everything but speech (the interpreter, the audit, the narrator, every contract) was tuned on Gemma, so a
swap is far more than a speaking test. The only check I ran is the nine audit-gate cases in `data/replay/cases.yaml`, through
`tools/replay.py --live`: Gemma got 4, 5 and 5 of 9 in three passes, Qwen 8, 7 and 6. That is nine hard cases, so it says only
that Qwen is not plainly worse at reading intent. It is not the interpreter measure (163 to 166 of 170).

## 4. Thinking first: not on this card

Gemma with thinking on and no JSON gave the most varied openings of anything tried (20% open the commonest way). But the median
reply took 1,715 tokens and 24 seconds here, the slow tenth over 69 seconds, and 8 of 96 came back empty. At the 3060's measured
31.7 tokens a second the median alone is about 54 seconds, the whole budget for a turn. The text was also looser, not better
("There aren't no-no forge around this square."). With the JSON grammar on, the model does not think at all (it goes straight to
the reply), so that earlier row said nothing either way.

## 5. The same first words, and a grammar that refuses them

Sampling does not move the openings (section 1) and neither does the moment block (section 2). So I tried the engine doing it:
the grammar that already shapes the reply also refuses the openings this speaker used lately. No prompt rule, nothing for the
model to obey or ignore. For "lately" I used the two-word openings Gemma gave most often to the same request, which is the
hardest case: what it most wants to say.

The first version refused the exact two words and broke. Refused "I don't", the model had already written "I don'" and could
not finish the word: "I don'm sell those here", "There isn'e no forge". Where the refusal happened to fall at the start of a
word it worked well: refused "The clerk", the butcher said "Aldley is not here" and "The lad who works that desk"; refused "I'm
fine", Jesna said "I'm alright for now." and "I'm still standing."

The second version refuses where the second word begins (for "I don't", any line opening "I d..."; for "The clerk", any line
opening "The c..."), so the model is turned away before it starts the word. No broken words. Two ways of measuring it:

*Every seed refused the same openings* (12 seeds, the first eight requests): the share opening the commonest way fell from 50%
to 29% on today's request. With the moment block it fell only from 51% to 44%, and on the second eight it did not fall at all
(42% to 51%). The model steps sideways into its next habit: refused "I don't sell", 6 of 12 open "I haven't got any"; refused
"There isn't", 6 of 12 open "There aren't no forges". That is the wrong test of it, though, because in play a speaker's refused
list follows what they actually said.

*In sequence, as play would meet it*: the same person given the same request six times running, each reply's opening refused to
all the later ones. 16 requests, 4 runs each, with the moment block.

| | Different openings in six replies | Broken replies, lines 1 to 4 | Broken replies, lines 5 and 6 |
|---|---|---|---|
| Nothing refused | 2.1 of 6 (first eight), 3.0 of 6 (second eight) | | |
| Lately used openings refused | 6 of 6 | 5 of 256 | 7 of 128 |

A run reads like this (Jesna, six times asked who is hurt worst): "I'm fine. Not..." / "I'm untouched. Just..." / "None of us..."
/ "I'm steady enough." / "I'm doing just..." / "I'm all good." And the butcher: "The clerk is..." / "The man who..." / "The boy
who..." / "The lad who..." / "The Clerk is..." / "The scribe is...".

So it does what sampling could not, and for the first three or four lines it costs nothing I can count. Its limits showed too:

- By the fifth and sixth line, when every refused opening shares its first word, the model runs out of natural second words
  and strains: "I'm wide clear.", "There's wasn't any forge here", "I'mn't selling any here", one reply with a Vietnamese word
  in it. A real version would hold only the last two or three openings, and refuse the first word itself once it has been used
  twice running.
- It dodged by case once per run on one request ("The Clerk is" after "The clerk" was refused). A real version would refuse
  without regard to case.
- This only varies the first words. It does not make a dull reply interesting.

I have not had this read blind. The replies are in `set1/results/results_gemma_seq.jsonl` and `set2/results/` beside it.

## 6. Replies that never end

About 1 in 100 of Gemma's replies at today's settings runs on to the 2,048 token limit: 3 of 320 on the unchanged request, and
12 of the trial's first 1,250 replies at the game's own sampling across all the request variants. Here that is 14 to 42 seconds.
On the 3060 it is about 65 seconds for that one call, over the budget for the whole turn, and what comes back is not a whole
reply.

Every one of them ran away in the same place: the last field, `journal_note`, in townsfolk's replies (companions' replies have
no such field and never ran away). The model writes "empty" or "none" into a field it was told to leave empty, then does not
close it:

    "journal_note": "empty\n\n\n\n\n\n\n\n\n ...
    "journal_note": "none = nothing requested by JOURNAL NOTE DUE ...

- Forbidding escaped newlines inside strings did not help (9 of 320 against 3 of 320): it found other things to write.
- **Leaving `journal_note` out of the reply's schema did.** 0 of 320 at today's settings, and 0 of 96 with no repeat penalty,
  where 12 of 96 ran away before. The speech itself was unchanged (27 words against 28, the same share of common openings).
  Townsfolk's replies also got shorter: 134 tokens against about 238. Across all eight requests a reply took 1.3 seconds here
  against 2.5, and the slowest took 3 seconds against 25.

The engine already knows when a note is due (it adds JOURNAL NOTE DUE to the request), and the decide-then-speak contract
already asks for the field only then (f726, `llm/contracts.py`). The plain `NPCReply`, the one that ships with the switch off,
still carries it on every reply. Doing the same there is a small feature. I have not built it.

## 7. Smaller things found on the way

- **The plant never reaches the herbalist.** The typed line was "I pick some of whatever's growing by the road and ask if anyone
  knows what it is." His request holds only `THEY SAY: "Does anyone know what this is?"`. So Gemma talks about "marks" in the mud
  from his memories, 11 times in 12. With one line saying they hold out a plant, he reads the plant.
- **Broken engine text in companions' requests**: "She keepses a notched wooden spoon that she carveds", "She spents her
  childhood", "She grews up". A verb is being given an s twice somewhere.
- **A made-up ailment stays.** Once Jesna has said "Just need a minute for my hands to stop shaking", that line rides in later
  requests under SAID LATELY BY YOU and in the conversation so far, with nothing to say it was never true. Khash's "My ribs are
  singing a bit too much" does the same.
- **Companions' requests carry no personality or traits**, only HOW YOU SPEAK and a one-line WHO YOU ARE. For the blind sheets I
  could print only those. That may be by design; I note it because your rule was to print the personality.
- **The speech is about a third of a reply.** The rest is the other fields and white space, about 150 tokens a reply in all.
  When the reply was shown as compact JSON in example turns, Gemma wrote compact JSON back: 79 tokens against 128, a reply in
  1.0 second against 1.7, and none of 192 ran away.
- **Gemma writes dashes in speech** now and then ("Greywood—sheep"): 2 in 96 replies on the first eight requests, 10 in 96 on
  the second eight, and 20 in 96 there with the moment block. The three-short-rules request made it 10 to 14 on the first eight.
- **Qwen needs a repeat penalty**: with none, 21 of 96 never ended. With 1.1 over 64 tokens, 1 of 96.

## 8. What I would do, in order

None of this is started. Each is yours to say yes or no to.

1. **Leave `journal_note` out of the plain reply unless a note is due.** Small, engine-only, removes the over-a-minute replies,
   and makes townsfolk about twice as quick. It would be the next feature (f731) with a test first.
2. **Take the moment block as evidence for plans 29 and 31**, which are waiting on you. If you want a first slice that needs no
   model call, it is the facts the engine already holds, said in two lines before the typed line: was anyone hurt, what was
   asked a moment ago, what this person does and does not sell, whom the question was put to, the true facts of their past. The
   lines themselves would be player-facing in effect, so you would read the wording first.
3. **Refused openings**, if section 5 holds up in your reading: a design first (how many openings to hold, case, when to refuse
   the first word), since it touches the grammar, the speaker's memory of what they said and the request.
4. **Keep Gemma.** Give Qwen 3.5 9B a proper second look only if you want one: it would need the interpreter measure, the prose
   baseline and the live gate run on it, and its inventions dealt with.
5. **Leave alone:** sampling arms, thinking, replies without JSON, Nemo, Mag Mell, Plainsong, StyleTune.

## 9. What this trial cannot tell you

- Sixteen requests, six speakers. The checks are regular expressions, rough counts and not judgments.
- The blind readers are a hosted model, three instances. They agreed closely with each other, which is not the same as agreeing
  with you. Your own earlier blind reading disagreed with model readers on some pairs.
- The moment lines and the example lines are hand-written by me with the request in front of me. An engine's would be plainer.
- Each reply here is one call. In the game a reply is checked and may be retried, so the share that reaches the player is not
  these raw counts.
- Timings are this machine's (a 4070 Ti SUPER). The 3060 figures are scaled from the measured card profile.
- No model swap was tested through the game. The nine-case interpreter check is a hint and nothing more.

## Where everything is

Kept in the repo, untracked, for you to commit or delete:

- This file.
- `docs/measure/2026-11-18_model_settings_trial_samples.md`: replies to every request at the same three seeds, unpicked, for the
  rows that matter.
- `docs/measure/model_settings_trial/`: the scripts, the sixteen requests, every reply (`set1/results`, `set2/results`), the
  count tables (`tables12.md`, `tables20.md`), the interpreter runs, and the blind sheets with their keys and the readers'
  answers:
  - `set1/read/gemma/sheets_1.md`: Gemma's request variants and the hosted model. Key: `key.json` beside it.
  - `set1/read/round2/sheets_1.md`: the models against each other.
  - `set2/read/set2/sheets_1.md`: the second eight requests.

Outside the repo: the five downloaded model files, 36 GB, in the session's scratch folder (path in my closing message). They are
not needed again unless you want Qwen looked at further.

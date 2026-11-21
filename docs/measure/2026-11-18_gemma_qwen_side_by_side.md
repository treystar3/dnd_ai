# Gemma 4 12B and Qwen 3.5 9B, side by side (18 Nov 2026)

A measurement for the owner to judge. Nothing in the game was changed and no model was swapped in the game.

**If you mean to read the pairs blind, read them first:** `2026-11-18_gemma_qwen_pairs.md`. This file gives counts only and quotes
no reply. Which writer is which, and every reader's reason, is in `2026-11-18_gemma_qwen_pairs_key.md`.

## The answer in short

1. **On the request the game sends today, the readers chose Gemma**: 21 pairs of 36 by majority, 66 readings of 108. Qwen's
   replies were marked as contradicting the moment or making things up almost twice as often (47% against 25%) and as out of
   character ten times as often (31% against 3%).
2. **With last night's short reading of the moment added, they chose Qwen**: 13 pairs of 16, 36 readings of 48. Both models then
   contradicted the moment equally seldom (17% each), and Gemma's replies read as a machine's far more often (46% against 10%).
3. **Qwen is faster and never ran away.** A townsperson's reply took 1.5 seconds against 2.3 at the median here, and none of
   Qwen's 272 replies ran to the token limit; 8 of Gemma's 160 townsfolk replies did. Gemma wrote a dash in 24 replies of 272,
   Qwen in 3.
4. So the two results point the same way as last night's: **Qwen is the better writer when it is handed the facts close to the
   line, and the worse one when it has to find them in today's long request.** A swap alone, with the request as it is, would
   trade Gemma's flat and tangled lines for made-up people and places, the costlier fault in a game where the engine holds what is true.

## What was run

- **The requests.** Eighteen saved speaking requests, exactly as the game sent them (decide then speak off): the sixteen of last
  night's trial and the two saved moments it had not used (the innkeeper asked what is in the stew; the herbalist asked where a
  traveller can get a meal). The saved set holds about eighteen different moments in all, so there was no wholly new set to draw.
  Eleven are townsfolk, seven are companions.
- **The seeds.** 7201 to 7208, none used before. Every reply here is new; none was read last night.
- **Gemma**: the game's own server and the game's own sampling (townsfolk at temperature 0.95, companions at 1.15, repeat penalty
  1.22 over 192 tokens).
- **Qwen 3.5 9B** (Q4_K_M, 6.2 GB): the game's llama-server build, the same grammar, thinking off, its makers' sampling
  (temperature 0.7, top_p 0.8, top_k 20) with a repeat penalty of 1.1 over 64 tokens. Last night showed the game's own repeat
  penalty garbles it and no penalty lets about one reply in five never end.
- **Part 1**: the request untouched. 18 requests at seeds 7201 and 7202: 36 pairs.
- **Part 2**: the same request with last night's hand-written reading of the moment (two or three true lines) put before the
  typed line. 16 requests at seed 7203: 16 pairs. The two new requests have no such lines, and I wrote none for this test.
- **The pairs.** One reply from each model to the same request at the same seed, lettered A and B by a coin for each pair. Above
  them: who answers (personality, traits, how they talk; for a companion also the manner the game holds), the moment's facts, and
  the line typed.
- **The readers.** Three fresh instances of a hosted model, each given the 52 pairs in its own order and told nothing about the
  writers. Four answers a pair: which is better, which reads as a machine, which contradicts the moment or makes things up, which
  does not fit who answers. The owner's copy holds the same pairs under the same numbers, part 1 first, a moment's two pairs under
  one heading.
- **The counts below the readings** come from all eight seeds: 272 replies a model.

## The blind reading

| | Part 1: today's request | Part 2: with the moment added |
|---|---|---|
| Pairs | 36 | 16 |
| Chosen by most readers: Gemma | **21** | 3 |
| Chosen by most readers: Qwen | 15 | **13** |
| Readings for Gemma / for Qwen | 66 / 42 | 12 / 36 |
| Reader 1 (Gemma / Qwen) | 23 / 13 | 3 / 13 |
| Reader 2 | 21 / 15 | 4 / 12 |
| Reader 3 | 22 / 14 | 5 / 11 |
| Pairs where all three agreed | 31 | 13 |
| Reads as a machine: Gemma | 34% | 46% |
| Reads as a machine: Qwen | 37% | 10% |
| Contradicts the moment or makes things up: Gemma | 25% | 17% |
| Contradicts the moment or makes things up: Qwen | 47% | 17% |
| Does not fit who answers: Gemma | 3% | 6% |
| Does not fit who answers: Qwen | 31% | 25% |

No reader answered "same" for any pair.

**By request, part 1** (two pairs each, chosen by most readers):

- Gemma both times (7 requests): the innkeeper offered help; the mage asked about his past; the baker asked who made the knife;
  the archer asked about her past; the mage asked what he makes of the place; the innkeeper asked about the roads; the herbalist
  asked where to eat.
- Qwen both times (4): the butcher asked which job is closest; the mage asked whether to rest or move on; the innkeeper asked
  what is going on in town; the baker asked how long she has had the forge.
- One each (7): the waterskin, the plant, the edge on the blade, the stew, who is hurt worst, the first watch, the lost fight.

**By request, part 2** (one pair each): Qwen in 13; Gemma in 3 (the innkeeper offered help, the mage asked whether to rest or
move on, the baker asked for an edge on the blade).

## The counts, all eight seeds

| | Gemma, today's | Gemma, with the moment | Qwen, today's | Qwen, with the moment |
|---|---|---|---|---|
| Replies | 144 | 128 | 144 | 128 |
| Words spoken (median) | 22 | 22 | 27 | 26 |
| Tokens written (median) | 126 | 120 | 88 | 88 |
| Seconds a reply (median) | 1.7 | 1.6 | 1.2 | 1.1 |
| Townsfolk: seconds (median / mean) | 2.3 / 3.9 | 2.2 / 3.4 | 1.5 / 1.7 | 1.5 / 1.7 |
| Companions: seconds (median) | 0.9 | 1.0 | 0.7 | 0.7 |
| Slowest reply, seconds | 36 | 14 | 14 | 18 |
| Ran to the 2,048 token limit | 4 | 4 | 0 | 0 |
| Replies with a dash | 15 | 9 | 1 | 2 |
| Open the commonest way (first three words) | 40% | 37% | 31% | 30% |
| Different openings in 8 | 5.0 | 5.4 | 6.2 | 6.0 |
| Empty or failed | 0 | 0 | 0 | 0 |

- All eight of Gemma's runaways were townsfolk replies (8 of 160, one in twenty; last night's larger count was about one in a
  hundred), 12 to 36 seconds each here. One of them is in the pairs: its speech was whole, so it is shown, and the key marks it.
- Qwen's two slow replies (14 and 18 seconds, 1,040 and 1,359 tokens) did end; they are long fields, not runaways.
- Both models write to the game's JSON grammar; Qwen fills the later fields more briefly, which is most of its lead in time.
- Times are on this machine's card. Qwen has not been timed on the 3060 class; it is a smaller file, so it should not be slower.

## What this does and does not tell you

- **The readers are one hosted model three times.** They agreed on 44 pairs of 52, which is more than three people would. Read
  it as one careful reader, not three. Your own reading of the same pairs is the check; the key will score it.
- **Part 1's margin is small.** 21 against 15 pairs is within what a coin gives about four times in ten. What is not small is
  the difference in kind: Qwen's losses are mostly invention and loss of character, Gemma's mostly flat or tangled lines.
- **Part 2 is one seed a request**, 16 pairs. Last night's larger reading with the moment added (three seeds, the first eight
  requests) put the two level, with Qwen less machine-like. Together: with the moment, Qwen is at least level and likely ahead.
- **The moment lines are mine and you have not read them.** They exist for sixteen saved moments only. In the game the engine
  would have to write them (plans 29 and 31).
- **The moments are last night's.** Sixteen of the eighteen requests were used in the trial, at other seeds. Qwen's sampling
  was picked on them.
- **"The moment" on the sheets is the game's truth as I read it off each request.** In a few places it says more than the
  request plainly tells the writer (the game holds no plant; Hys is a woman), and the sheet says so where it matters.
- **Speech only.** Nothing here tests Qwen as the interpreter or the narrator, at the game's own sampling, or through a played
  turn. *Run since:* `2026-11-18_gemma_qwen_played.md`. Last night's nine interpreter cases (Qwen 8, 7, 6 of nine; Gemma 4, 5, 5) are still only a hint.
- **Gemma's runaways are the `journal_note` field** (last night's section 6), a fault of the request's shape and not of the
  model's writing; with that field left out Gemma did not run away in 416 replies.

## Where everything is

- The pairs to read: `docs/measure/2026-11-18_gemma_qwen_pairs.md`
- The key, with each reader's choice and reason: `docs/measure/2026-11-18_gemma_qwen_pairs_key.md`
- Scripts, requests, every reply, the readers' sheets and answers: `docs/measure/model_settings_trial/side_by_side/`
- Last night's trial: `docs/measure/2026-11-18_model_settings_trial.md`

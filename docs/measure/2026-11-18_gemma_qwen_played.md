# Gemma 4 12B and Qwen 3.5 9B through a played script (18 Nov 2026)

A measurement for the owner to judge. Nothing in the game was changed: no file under `data/`, no code, no golden, and
`data/measured` was not written. Qwen was reached through the game's own switch for a hand-started server.

**If you mean to read the played pairs blind, read them first:** `2026-11-18_gemma_qwen_played_pairs.md`. This file says which
run did what on lines 27 to 30 and 36 onward. The key is `2026-11-18_gemma_qwen_played_pairs_key.md`.

## The answer in short

1. **Qwen can run the whole game.** 42 typed lines through the real turn, twice (a warrior, a ranger): no failed call, no
   stand-in shown, no crash, no line over 60 seconds. Every reply the game's checks sent back was put right on a later try.
2. **It reads the player's line worse where it counts.** In both of its runs the same two misreadings cost the player
   something: a purchase was refused because the plan named the ware in the wrong field, and "I keep walking until we reach
   Willowmead", typed in Willowmead, was read as a walk to the wetlands, where a fight began. The last six lines of town talk
   were typed into that fight and never answered. Gemma made neither mistake.
3. **Its narrator is the weaker one.** Blind readers chose what Gemma's run showed in 23 of the 35 comparable lines and Qwen's
   in 10 (2 were word for word the same). Qwen's text was marked as a machine's in 50% of readings against 21%, and as padded in
   31% against 13%.
4. **Its townsfolk were preferred when they spoke.** Most of Qwen's ten wins are spoken replies in town. That matches the
   request-by-request test earlier today.
5. **The game sent back more of what Qwen wrote**: 10 replies against 3 in the warrior run. Spoken replies accepted on the first
   try: 85% against 94%.
6. **So Qwen is not a drop-in replacement.** With prompts written around Gemma it loses on reading the line and on narration,
   which are most of a turn. Its strength is speech, and the two models would not fit together on a 12 GB card.

## What was run

- **The script**: `data/replay/gate_script.yaml`, 43 typed lines (42 played: the turn limit), through `tools/live_gate.py
  --no-reading`, seed 719, two companions. The same tool and script as the decide then speak measure.
- **Gemma**: the game as it starts itself, its own server and sampling.
- **Qwen 3.5 9B**: the game's `DND_BACKEND=llama` switch pointed at the game's llama-server build loaded with the Qwen file (two
  slots of 16,384 tokens), with the game's own embedder kept running beside it so both runs filtered and compared text the same
  way. Sampling through the game's two environment switches only: `DND_TEMP_ADD=-0.1` and `DND_REPEAT_ADD=-0.02`, which give
  townsfolk temperature 0.7, companions 0.9 and a repeat penalty of 1.10 over 192 tokens. The readers of the player's line keep
  their cold settings. A pre-check of 72 replies at this sampling showed no garbled words and no runaway. It is not Qwen's
  makers' top_p and top_k; those cannot be set without editing `data/rules/sampling.yaml`.
- **Runs**: a warrior on each model, then a ranger on each. Gemma's ranger run did not start (see "What went wrong").
- **The blind reading**: lines 1 to 35 of the two warrior runs, where both runs stood in the same place. For each line, all that
  each run showed the player, lettered by a coin; three fresh readers of a hosted model; four answers a pair.

## The course, line by line (warrior)

Both runs went the same way for 26 lines: the fields, the Greywood, a fight won, a camp, Parth, the inn, the guild house, the
market. Then:

| Line | Typed | Gemma | Qwen |
|---|---|---|---|
| 2 | I climb the nearest rise... | A rise is found and kept as a place | The find was sent back twice for lacking a name and description; nothing was found |
| 8 | I keep my guard up and hit it again. (the fight is over) | Plan: attack a companion. The game refused: "There's nothing here to fight." | Plan: a swing at the air, narrated |
| 14 | I take the first watch. | Read as something said to the archer; she answers | Read as waiting; nobody answers |
| 27 | I buy some rations, then ask the merchant who made that knife. | Bought, then asked | **The purchase was refused** (the ration was put in the plan's `item` field, not `ware`); the game showed the price list |
| 28 | I walk to the smithy. | Refused with a notice: this run's Parth has no smith | Walks to a smith who exists in this run's Parth |
| 29, 30 | I ask the smith... | The baker answers that she is no smith | The smith answers |
| 36 | I keep walking until we reach Willowmead. (already there) | Stays in Willowmead | **Walks to the Willowmead wetlands; a fight begins** |
| 37 to 42 | six lines of town talk and an inn | Answered: a meal bought, a room taken | **All six typed into the fight**; none answered |

The ranger run on Qwen repeated lines 2, 27 and 36 to 42 exactly. The sampler is seeded, so that is the same fault seen twice,
not two independent sightings.

The towns differ a little between the runs because the model also writes the people of each place: Qwen's Parth has a smith,
Gemma's does not.

## What the game sent back (warrior)

| | Gemma | Qwen |
|---|---|---|
| Model calls | 154 | 152 |
| Replies sent back by a check | 3 | 10 |
| Calls that failed for good | 0 | 0 |
| Stand-ins shown | 0 | 0 |
| Spoken replies accepted on the first try | 94% | 85% |
| Passages sent back for a creature not there | 0 of 38 | 0 of 40 |
| Names the game does not hold, in passages shown | 0 | 0 |
| Dashes in what the player saw | 0 | 0 |

- Gemma's three: two narrations that used a game label as a word, one companion speaking of an inn building the village lacks.
- Qwen's ten: a find with no name or description (twice); a made-up name in a character's past; a plan with no action; a
  speaker opening on a filler word against their manner; the same speaker repeating a late line (twice); a word in Chinese
  characters in a job posting; a spoken reply that copied its instructions' wording; a talk's frame ending on a stock gesture.

## The blind reading of what the player saw (warrior, lines 1 to 35)

| | Gemma | Qwen |
|---|---|---|
| Chosen by most readers (35 pairs; 2 were identical) | **23** | 10 |
| Readings (105; 6 "same") | 69 | 30 |
| Reader 1 / 2 / 3 | 23 / 21 / 25 | 10 / 12 / 8 |
| Reads as a machine | 21% | 50% |
| Padded, or decorates instead of telling | 13% | 31% |
| Does not do or answer what was typed | 8% | 14% |
| Words shown a line (median) | 89 | 110 |

All three readers agreed on 29 of the 35 pairs.

- **Qwen was chosen** on lines 3, 13, 19, 22, 24, 29 and 30 by all three readers and on 18, 20 and 32 by two: three moves
  from place to place (3, 22, 32) and seven lines of people speaking (the innkeeper three times, a companion, the guild's
  clerk, the smith twice).
- **Gemma was chosen** on the rest: looking about, searching, the fight, the camp, the night, the arrivals in Parth and at the
  inn, the market, the stream, the plant.
- The readers' reasons are in the key. In short: Qwen's narration was marked for decoration, for things that are not there (a
  companion for the enemy, a fallen friend), for garbled sums in the fight, and for stopping to describe the player's own gear;
  Gemma's for stock phrases and for running long in the fight. Qwen's speakers were chosen for having a voice and giving
  particulars.

## Time

| Warrior run | Gemma | Qwen |
|---|---|---|
| Seconds a line, median | 6.0 | 5.3 |
| 95th percentile | 15.2 | 15.1 |
| Longest line | 16.5 | 21.1 |
| The whole script | 268 s | 288 s |

Read these as "about the same" and no more. The card was shared with another program for part of the session (see below), Qwen
ran without the game's own server flags or its draft model, and one run a side settles nothing about time.

## What went wrong, and what this cannot tell you

- **The second pair of runs was spoiled by a shared card.** Midway the card was at 99% use with a few GB held by a game
  running on this machine. Gemma's ranger run timed out three times at 120 seconds while creating the character and never
  started; Qwen's ranger run finished but took 14 minutes against 5 (median 14.6 seconds a line). I did not run Gemma's again
  while the card was in use. The ranger run is used above only for its course and what was sent back, never for time.
- **One clean run a model.** The course comparison rests on the warrior runs. The seeded sampler makes a repeat nearly the same
  run, so more classes, not more repeats, would be the way to widen it.
- **The prompts, the plan's fields and the script were all shaped on Gemma.** The script's line 36 only makes sense on the course
  Gemma takes. Some of Qwen's faults might yield to prompt work; none of that was tried.
- **Qwen's sampling was the nearest the switches allow**, not its makers'.
- **The readers are one hosted model three times**, and they judged prose without the game's state in front of them, so
  "contradicts the game" was not asked here.
- **Not measured**: the reading corpus (163 to 166 of 170 on Gemma), long play, saves, the 3060.

## Where everything is

- The played pairs to read: `docs/measure/2026-11-18_gemma_qwen_played_pairs.md`
- Their key and the readers' reasons: `docs/measure/2026-11-18_gemma_qwen_played_pairs_key.md`
- Both transcripts, each line's plan and the gate's own report for every run:
  `docs/measure/model_settings_trial/side_by_side/played/`
- Scripts: `docs/measure/model_settings_trial/side_by_side/scripts/` (`play.sh`, `serve2.py`, `compare.py`, `reads.py`,
  `tpairs.py`, `tscore.py`)
- The request-by-request test from earlier today: `docs/measure/2026-11-18_gemma_qwen_side_by_side.md`

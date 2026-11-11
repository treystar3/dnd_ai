# Prose baseline (docs/design/09, section A)

Two measurements of the game as it stood at `d9948d1` (prose/section-a: main plus the measuring tools, no prose change), run back
to back on one rented RTX 5090 on 2026-11-10 with `tools/prose_baseline.sh`. Model `gemma4-12b-bb722270` on the game's own
llama-server; every server loaded all 49 layers on the card (`run.json`: class minimum, no warnings).

Each measurement is: `live_check --runs 3`, `interp_eval --live`, and two scripted plays of 60 turns with a hired party of 3 (a
hunter, seed 101; a talker, seed 102; since f577 the script plays four hunters and the talker, in `play_<persona>_<seed>` folders).
`base1/` and `base2/` hold each one's reports, transcripts, `prose.md` (the table and sample
passages), `prose.json` (the numbers) and the call logs (gzip; `tools/prose_measure.py` reads them as they are).

## The two baselines side by side (base1 / base2)

Lower is better. Nothing changed between them: the difference is the noise a change has to beat.

| Task | Passages | Repeated phrases /1k | Repeated sentences /1k | Shared openings | Worn words | Stock phrases /1k |
|---|---|---|---|---|---|---|
| narrate | 53 / 47 | 1.78 / 1.73 | 0 / 0 | 4% / 13% | 14 / 10 | 0 / 0.19 |
| combat_opening | 8 / 12 | 0.97 / 11.42 | 0 / 0.57 | 0% / 33% | 3 / 2 | 0 / 0 |
| combat_narrate | 16 / 24 | 5.56 / 19.81 | 0 / 0.27 | 19% / 50% | 2 / 3 | 0 / 0 |
| combat_aftermath | 10 / 17 | 15.64 / 24.08 | 0 / 0 | 0% / 24% | 4 / 7 | 0 / 0 |
| exchange | 68 / 74 | 10.58 / 8.94 | 3.07 / 0.93 | 44% / 34% | 3 / 4 | 0 / 0 |
| dialogue_frame | 105 / 105 | 16.05 / 14.61 | 0.19 / 0 | 22% / 31% | 12 / 14 | 0 / 0 |
| npc_conversation | 50 / 39 | 0 / 0 | 0.60 / 0 | 8% / 13% | 0 / 1 | 0.60 / 0 |
| hire_chat | 69 / 80 | 2.89 / 1.43 | 0 / 0 | 16% / 6% | 1 / 2 | 0 / 0 |

Other measures:
- `interp_eval --live`: 164 of 170 right, then 162 of 170.
- `live_check`'s judge, over 102 judged lines each time: vivid 23 / 22, flat or generic 75 / 76, stock phrases 14 / 1.

## What the baseline says about the measuring

1. **The fight measures are too noisy at this size.** With 8 to 24 passages a task, repeated phrases in fight narration went from
   5.6 to 19.8 per 1,000 words with no change at all. The same seed does not give the same play on the live model, so the two
   plays had different fights.
2. **Narration, frames and exchanges are steadier** (53 and 47 narrations: 1.78 against 1.73 repeated phrases), though shared
   openings still moved from 4% to 13%.
3. **The measures grow with the amount of text.** Pooling both baselines gives 5.3 repeated phrases per 1,000 words of narration,
   not 1.75: more passages means more chances to repeat. A change must be compared with a measurement of the same shape, never with
   a pool.
4. **The judge's stock-phrase count is not usable alone** (14 against 1 on the same game).
5. **Much of the fight repetition is the engine's events told again** ("Alwick thrusts his staff forward"), which a prompt change
   cannot remove.

So a change "holds" when its numbers sit inside the band the two baselines span, and "improves" only when it lands clearly outside
it. For the fight tasks that band is wide; longer plays, or a measure taken over fixed-size samples, would narrow it.

## Steadying the measure (f577)

`tools/prose_measure.py` now also measures each task over 200 draws of a fixed size (40 narrations, 60 exchanges, 90 frames, 30
townsfolk replies, 60 hire replies, 20 fights drawn whole) and gives the mean with a band (the 10th to 90th draw). `prose.md` and
`prose.json` in both folders were re-measured from the kept logs; the numbers above are unchanged.

What it shows on these two runs:
1. **The size effect is gone.** Narration's repeated phrases read 1.38 and 1.51 (whole: 1.78 and 1.73, and 5.3 pooled); dialogue frames
   14.5 and 13.0; exchanges 10.1 and 7.9, their bands overlapping.
2. **A band drawn inside one run is narrower than two runs differ.** Compared with base1 alone, unchanged base2 came out "better" or
   "worse" on many cells. So a verdict needs two or more baselines and judges by the span between them; with one, the tool gives none.
3. **Fights differ between runs by more than their number** (a one-off reading of the kept logs, not printed by the tool). Drawing the same number of fights from each (6 of them: 4.0 against 13.3
   repeated phrases per 1,000 words in fight rounds), base2 still repeats about three times as much, and almost all of it is across
   fights (70 repeated runs across fights, 4 within one), much of it the same fighter's moves told again ("Alwick thrusts his staff
   forward", "bronze longsword in a wide arc"). base1's hunter play had 7 fights, base2's 12, and both are short of 20.
4. So `tools/prose_baseline.sh` now plays four hunters (seeds 101, 103, 105, 107) and the talker, to get 20 or more fights a
   measurement from different parties. These two baselines are of the old shape: before measuring A2, take two new baselines with the
   new script (five plays of about 8 minutes each, so a measurement takes about 25 minutes longer on a 5090), and check that their
   fight bands overlap. If they still do not, fights need more plays again, or the fight measures are
   reported but not used to keep or drop a change.

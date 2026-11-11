# A1 measured (f587: DRY and XTC sent whole, four sampling arms)

Five measurements of `prose/section-a` at `a597d7f` (A3's exemplars, the lists restored, per-request seeds), one per arm, on one
rented RTX 5090 on 2026-11-11 (about $4.10 for the pod, including a first run every request of which the server refused: f588).
Each ran `tools/prose_baseline.sh` exactly as new1 and new2 did. The arm was laid over the six prose and speech tasks only
(`DND_SAMPLING_ARM`, kept in each play's `run.json`):

| Arm | Settings (over each task's own) |
|---|---|
| control | none: today's sampling |
| dry | dry_multiplier 0.8, dry_base 1.75, dry_allowed_length 2, dry_penalty_last_n 512 |
| xtc | xtc_probability 0.5, xtc_threshold 0.1 |
| both | dry and xtc together |
| min_p | min_p 0.05 |

Every arm played the same seeds and was sent the same request seeds, until its own words took the play somewhere else. The talker's
first narration went out with seed 1286810230 in all five. The interpreter runs at the same settings in every arm, so its spread
shows the run-to-run noise: 163 to 166 of 170.

An arm's prose is judged against all three runs without an arm (control, new1, new2): better only below all three bands, worse only
above all three (`prose_measure.py ... --against control new1 new2`). A3 itself (the control) is judged against new1 and new2.

## Verdict: no arm wins outright. "both" writes the least repetitive prose, at a price in first tries

| Arm | Prose (against the three runs without an arm) | Judge: vivid / stock / flat | Narration taken first try | Junk refusals | Model s per call |
|---|---|---|---|---|---|
| control | | 29 / 7 / 73 | 91% | 5.0% | 1.55 |
| dry | nothing better; combat worn uses **worse** (11.7) | 17 / 13 / 83 | 90% | 6.6% | 1.63 |
| xtc | frames' repeated phrases **better** (5.0 against 9.4 to 10.5); narration's halved (1.0) | 19 / 5 / 82 | **81%** | 8.8% | 1.62 |
| both | frames' repeated phrases **better** (3.2), fights' **better** (opening 1.7, blows 3.6), hires' shared openings **better** (6%); narration's halved (1.0); exchange 2.5 against 6.9 | 26 / 6 / 77 | **79%** | **11.0%** | **1.84** |
| min_p | frames' repeated phrases **worse** (12.8); exchange's up (10.4) | 22 / 8 / 79 | 99% | **1.3%** | 1.46 |

Baselines for the last three columns: new1 90% / 5.2% / 2.39 s, new2 93% / 3.8% / 2.33 s (on another pod, so its seconds do not
compare). The judge gave new1 20 / 12 / 83 and new2 19 / 7 / 83.

- **Junk refusals** are answers sent back for something no reader should see: a word in another alphabet, a broken character,
  a written `\n`, words joined with underscores, a template brace, a bracketed note. XTC takes the likeliest words out, and with them
  goes some of what keeps the model on plain English. The checks catch nearly all of it, and each catch costs a second model call
  before anything is shown. Two words got past them and reached the player, both Vietnamese in Latin letters: "bites deep vào her
  flank" (both, a fight) and "stays on một spot" (dry, a stallholder). The check looks for another alphabet, and these use ours.
  A Chinese word (control) and a model's own note, "final check passed ✅" (both), were accepted by a townsperson's talk but never
  reached a transcript.
- **Name errors** did not rise in any arm: 0 to 5 refusals a task, the same kinds as the control (a hire naming someone never
  given; min_p's five frames opening on the wrong person are the most). Silent mends 0 to 3 a task.
- **Repeated sentences in a townsperson's talk** read "worse" for xtc, both and min_p: every run without an arm had none, so one
  repeated sentence is enough. It is noted, not counted.

## What it says

DRY alone does nothing measurable for this model's repetition and the judge liked it least. It looks back 512 tokens, the end of
the request and the passage being written; the repeats the measure counts are between passages, mostly further back than that. min_p 0.05 is the tidiest sampler:
the fewest refusals, the fastest, nearly every narration taken first time. But it cuts the tail the variety comes from, and frames
and exchanges repeat more. XTC is what moves the repetition, and DRY beside it helps. "both" is the only arm that is better on four
measures, worse on none, and kept the judge's view of A3's prose.

Its price is the measure the owner asked to be counted: one narration in five is sent back at its first try (one in ten without an
arm). Nearly all of those are junk, not prose. Together with slightly longer calls, the model's time per call is up 19% on the 5090,
and more on a 3060. By the owner's rule (hold or improve on every measure) "both" does not hold. It is not made the default, and the
sampling row in GOALS.md is unchanged.

The way forward the numbers point to: XTC and DRY together with min_p's floor under them. In llama-server's sampler order min_p runs
before XTC, so it takes out the junk tail before XTC takes off the top. That is one more arm, measured the same way.

## A3 (the control) against new1 and new2

The exemplars hold on most measures and the judge liked them: vivid 29 against 20 / 19, flat or generic 73 against 83 / 83. Two
measures moved the wrong way:

- **combat_narrate worn uses** 8.3 per 1,000 words against 3.8 / 2.6 (whole runs: 11.4 against 6.7 / 4.2). All five runs with the
  exemplars sit between 7.2 and 11.7, so it is real. The words are "instantly", "harmlessly", "simultaneously", "heavy", "motionless":
  none is in the fight exemplars, which are short and plain. The fight lines may be teaching the shape (one blow, then a quick
  aftermath) and the model fills it with adverbs.
- **dialogue_frame shared openings** 29% against 21% / 16% ("you stand near", "you lean against"). In the arms it runs from 12% to 25%,
  so it may be noise. XTC and "both" bring it under the baselines.

(combat_opening's shared openings, 6% against 0% / 0%, is one fight in twelve: noise at this size.)

## Sample passages (the talker's play, seed 102, the same request seeds)

The first narration, control:
> Dust kicks up as birds erupt into flight from the grain stalks nearby, their wings creating a frantic flutter in the warm air.
> Straight ahead, rows of golden wheat stretch toward Parth, several rooftops visible just beyond the sweep of land. Gorz Skorgarth
> walks beside you along the dirt track that cuts through the field.

The first narration, "both":
> Golden sunlight hits the rows of grain stretching toward the north. Birds burst upward from the stalks in an erratic cloud as
> shadows flicker over their feathers. To one side, a low stone wall anchors the boundary of the path.

A frame at the granary, control:
> You step into the shade of the granary as Gorz Skorgarth slows his pace beside you. Yamaku Omari adjusts her pack strap, her thumb
> tracing a frayed edge of leather. They both turn toward the cluttered contract board where papers flutter like trapped moths.

A frame at the granary, "both":
> Gorz shifts his weight, the heavy plate of his pauldrons groaning softly as he turns his torso fully toward you.

What DRY let through once in an exchange (accepted; the junk checks look for other alphabets and joined words, not this):
> This place has too many sharp edgesyand fine labels to be useful near a properly-sized cauldron.

## Files

Each arm's folder has the shape of `prose_a2`: the live check's calls and report, `interp_eval.txt`, the five plays (calls,
`run.json` with the arm and the name mends, summary, transcript), and `prose.md` / `prose.json` from the pod.

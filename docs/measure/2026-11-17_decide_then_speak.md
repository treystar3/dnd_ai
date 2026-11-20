# Decide then speak, measured (plan 28, step A6), 2026-11-17

The gate's script (data/replay/gate_script.yaml, 42 typed lines, a draft the owner has not yet read) played on the local model
(gemma4-12b, RTX 4070 Ti SUPER) with `decide_then_speak` off and on. The switch was turned on in the file only for the length of
an "on" run and put back after each (checked: data/rules is clean). The reading corpus was left out (it does not depend on the
switch). Nothing here is a floor: the gate's floors are the owner's to set.

The three bars (the owner's, 17 November): no leaks in the gate's talk lines; a talk turn's 95th percentile no more than 20%
slower; the owner prefers the new replies in at least 60% of twenty blind pairs.

## What was run

| Run | Character | Switch | Used for |
|---|---|---|---|
| 1 | warrior, seed 719 | off, then on | sizes, leaks, pairs (its "off" times are not trusted, see Time) |
| 2 | warrior, seed 719 | off, then on | sizes, leaks, pairs, time (nothing else running) |
| 3 | paladin, seed 719 | off, then on | sizes, leaks, pairs (tests were running beside it: no times taken) |
| 4 | warrior, seed 719 | on, then off | time (nothing else running) |
| 5 | warrior, seed 719 | on, then off | time (nothing else running) |
| 6 to 9 | ranger, monk, priest, mage, seed 719 | off, then on | pairs only (the owner asked for a second set; the machine ran slow: no times taken) |
| not used | warrior, seeds 720 and 721 | off, on | the script left its course (below) |

**The script only holds its course at seed 719.** At 720 and 721 nothing was found at the tracks, a fight broke out on waking,
and the town lines were typed in the Greywood in the middle of it; almost only companions answered. A fixed list of lines is at
the mercy of what the world rolls. A script that waits for a fight to end before its next line would hold on any seed (a
follow-up, not built).

**A run played again is nearly the same run.** The sampler is seeded, so run 2 repeated run 1 word for word on most lines (33 of
42 lines with the switch off, 38 of 42 with it on). That is why a third run with another class was needed to reach twenty
different pairs.

**The script asks a smith for work in a town with no smithy.** Since the lines were put in a new order (f729), the two smith
lines are played in Parth's trading square and a flour seller answers them. The replies are still fair pairs (the same line, the
same person), and both arms answer truthfully that Parth has no smith, but the lines want moving or rewording when the owner
reads the script.

## Bar 1. Leaks: held, by reading

| Run | Switch | Marked lines answered | of them with news or a happening around | Counted as leaks | Leaks, read |
|---|---|---|---|---|---|
| 1 | off | 6 | 6 | 0 | 0 |
| 1 | on | 6 | 6 | 1 | 0 |
| 2 | off | 4 | 4 | 0 | 0 |
| 2 | on | 6 | 6 | 1 | 0 |
| 3 | off | 6 | 6 | 0 | 0 |
| 3 | on | 4 | 4 | 0 | 0 |

Every marked line that counted had news or a happening around it, so the count could have failed (f729). The one reply counted
with the switch on is the same reply both times, and read, it is no leak: it says nothing of the news. The counter matched it
to the news of the sickness in the flocks of Parth by the words "through" and "Parth". (The reply is one of the blind pairs, so
it is quoted with the key and not here.) **The counter's fault:** it counts a town's own name and
common words as the piece's words. Leaving out the run's own names and words every reply uses would end this false count (a
small change to tools/live_gate.py, not made here).

Of all spoken turns, those that carried a piece of news or a happening at all, asked for or not: 1 of 19, 1 of 15 and 1 of 21
with the switch off; 2 of 18, 2 of 18 and 0 of 16 with it on.

**This bar did not separate the two.** Neither way of speaking leaked on these lines. The leaks that began this work were seen
in play, on longer talks than a script of single questions gives.

## Bar 2. Time

Seconds for a turn the gate calls talk (14 lines a run), and for the same lines answered aloud in both arms of a run:

| Run | Off: median, 95th | On: median, 95th | The 95th, on against off | Same lines, on against off |
|---|---|---|---|---|
| 1 (off not trusted) | 9.4, 16.3 | 5.9, 8.7 | 47% faster | 35% faster |
| 2 | 4.9, 8.4 | 7.4, 10.4 | 24% slower | 13% slower |
| 4 | 4.9, 8.3 | 5.9, 8.4 | 1% slower | 7% faster |
| 5 | 6.8, 11.5 | 5.9, 8.8 | 23% faster | 11% faster |
| Runs 2, 4 and 5 together (42 talk lines an arm) | 5.1, 8.4 | 6.8, 9.5 | **13% slower** | |

**The bar holds on the clean runs taken together (13% slower at the 95th percentile, against a bar of 20%), but one run is no
measure of it.** Runs that say the same words differ by a quarter in their times (the switch-on arm said nearly the same
words in runs 1, 2, 4 and 5 and its 95th percentile ran from 8.4 to 10.4 s), which is as wide as the bar. What is steady: the usual
talk turn is about a second and a half slower with the switch on (median 5.1 s to 6.8 s), because two calls are made where one
was; the slowest talk turns are not slower. Over every turn with a spoken reply (walks and
events with a word in them too) the two are level: median 7.1 s against 7.2 s, 95th percentile 16.7 s against 14.2 s.

Run 1's switch-off times are left out. Tests were running beside its first minute, and it stayed about twice as slow as the
same words in run 2 to its end, for a reason not found. With it in, the switch-on arm looks 35% faster at the 95th percentile,
which the clean runs do not bear out. The first figures given for this bar (15.1 s against 8.3 s) were that run's.

All of this is on an RTX 4070 Ti SUPER. On the minimum card (RTX 3060) every call is slower and the second call's fixed cost
weighs more; that is not measured here.

## Bar 3. The blind reading: the owner's

Twenty pairs are in docs/measure/2026-11-17_blind_pairs.md, the key in docs/measure/2026-11-17_blind_pairs_key.md (not to be
opened first). Fourteen are a townsperson's, six a companion's; ten have the new reply first; no reply appears twice. Each pair
is the same typed line answered by the same person in the two arms of one run. Eight pairs are from run 1, three from run 2
(the lines where it did not repeat run 1), nine from run 3.

**A second set, asked for by the owner: forty more pairs (21 to 60)** in docs/measure/2026-11-17_blind_pairs_2.md, the key in
docs/measure/2026-11-17_blind_pairs_2_key.md (not to be opened first). Nineteen are a townsperson's, twenty-one a companion's;
twenty have the new reply first; no reply appears twice and none is in the first twenty. Thirty-two are from runs 6 to 9 (all
four held the script's course), eight are pairs of runs 1 to 5 that the first set did not use. The same seven speakers answer
throughout (the script meets the same people at seed 719), and the same typed line comes up as many as five times, each time
with other replies.

**Eight of the sixty pairs do not test the switch** (found 17 November, after both sets were sent): 13, 19, 27, 29, 31, 38, 39
and 59. In seven the replies are companions talking among themselves, written by a call the switch does not touch (it acts on
a townsperson's reply and on a companion answering the player, nowhere else); in pair 13 one reply is the game's own question
when it could not act on the line. The pairs were gathered from any spoken line without looking at which call wrote it. Fifty-two
remain: 18 of the first twenty, 34 of the second forty.

**Each reply set against the game's records**, by letter: docs/measure/2026-11-17_blind_pairs_accuracy.md (the owner asked which
reply of a pair is accurate). The same by arm is in the second key.

**The reading (18 November; docs/measure/2026-11-18_blind_reading_owner.md).** The owner read one list of 38 pairs
(docs/measure/2026-11-17_blind_pairs_clean.md: the 52 less the 14 in which a reply was marked against the game's records) and
answered where a pair had a clear answer.

- **Bar 3 is not met.** Of 18 preferences given, the new speech was preferred in 6 (33%) and the speech as it is in 12 (67%);
  the bar was 60% for the new. One pair was called even and 19 were left blank.
- **The new reply was marked as reading like a machine's twice as often**: 10 times against 5.
- **What lost:** the moves that give less than was asked. "A word or two, or only a look" lost 3 of 4 and was marked a
  machine's 5 times; "answer the part you care about", "keep back what they asked for" and "turn to what weighs on you" won
  none of the 4 pairs judged. "Ask something of them first" split 4 to 4: it won where the reply still gave the answer and
  then asked, and lost where the question took the answer's place.
- **Among townsfolk** the speech as it is was preferred 8 to 2; among companions it was level, 4 to 4.

The bar was the owner's preference in 60% or more of the twenty; over the fifty-two that test the switch that would have been
thirty-two. The reading is done; the bar is not met and the switch is off.

**Who was speaking (added 18 November, at the owner's asking).** The speaker's traits and habits are now printed with each of
the 38 pairs, and the reading's write-up has a section setting the choices beside them. The move's die takes no trait into
account; a move that fitted the speaker did not win for it (the owner: 3 new, 6 as it is); and two more things drawn by the
engine differ between the replies of a pair, a companion's habits (8 of 20 pairs) and a townsperson's stance (4 of 32). In pair
12 the move had been read from the other companion's call in the same turn; the tables are corrected (it was "answer the part
you care about").

**Three blind readers beside it (18 November; docs/measure/2026-11-18_blind_readers.md).** The owner asked for three model
readers to score the pairs as well. Each read its own reshuffled sheet of the 52 pairs. None reaches 60% for the new speech:
50%, 51% and 38% over the 52, and 53%, 58% and 39% on the owner's 38. They agree with the owner that the moves which keep back
or leave out what was asked lose ("keep back" won none of 24 readings) and that a question in the answer's place reads as a
machine's. They differ on the six clerk lines, where they chose the reply that answers over the reply that says the clerk is
away (16 of 18 readings), though the game's records bear out the second; without those pairs the three together stand at 39%
for the new speech. They are a second opinion and no part of the bar: they chose as the owner did in 11 or 12 of 18.

## What a reply reads

| | Switch off | Switch on |
|---|---|---|
| A townsperson's speaking request, median characters | 17,313 / 18,152 / 17,735 | 13,352 / 13,352 / 14,033 |
| ... 95th percentile | 19,498 / 19,498 / 19,367 | 15,040 / 15,040 / 15,797 |
| The reading before it (npc_decide), median | none | 4,018 / 4,018 / 4,536 |
| ... 95th percentile | none | 5,176 / 5,176 / 5,190 |
| Read in all for one reply, roughly (the two medians added) | 17,313 / 18,152 / 17,735 | 17,370 / 17,370 / 18,569 |
| A companion's request, median | 9,054 / 8,670 / 8,779 | 8,688 / 8,688 / 8,935 |
| ... 95th percentile | 10,997 / 10,026 / 10,828 | 11,082 / 11,101 / 10,183 |

(Runs 1 / 2 / 3.) The speaking request is about a quarter smaller, and the reading before it takes the saving back: a reply
reads about as much in all as it does today. The plan's estimate that the total would be smaller did not hold. The speaking
request is still over the 14,000 the plan aimed for at its 95th percentile (15,040 to 15,797); the candidate cuts are listed in
the plan (the people they know, a seller's wares, the guild's rules).

## Accepted on the first try

| | Switch off | Switch on |
|---|---|---|
| Townsperson | 0.909 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 |
| The reading | none | 1.0 / 1.0 / 1.0 |
| Companion | 1.0 / 1.0 / 1.0 | 0.857 / 1.0 / 1.0 |

No reading was sent back in 31 calls: the model chose ids the engine accepted every time, which was the plan's named risk
("a 12B model choosing ids"). Stand-ins shown: one, in run 3 with the switch off. No line took over 60 seconds and the model
failed no line in any run. Stiff replies sent back: none of 53 checked with the switch off, 1 of 52 with it on.

## The maker's own reading of the pairs

Kept with the key (docs/measure/2026-11-17_blind_pairs_key.md), so that it is not read before the blind reading.

## For the owner

1. Bar 3 is read and not met (above). What becomes of decide then speak is the owner's: leave it off as built, or rework the
   moves that give less than was asked and measure again.
2. Bar 2 holds on the clean runs together and is close enough to the noise that it is the owner's call; it is not measured on
   the minimum card.
3. The script's lines (42, in their new order) are still to be read, and the gate's floors to be set, among them
   `leak_lines_with_news`.

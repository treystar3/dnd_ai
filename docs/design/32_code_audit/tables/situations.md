# The situations system tested by property (second round, finder "situations")

All runs are under simlib's stub: no model was called. Scripts are in
`C:/Users/tstil/AppData/Local/Temp/claude/dad68772ed0cbd02/d2ae1f65-36c6-4be3-9744-2919d03b2cce/scratchpad/audit/work/`
(`sit_base.py`, `sit_prop_check.py`, `sit_prop_ruled.py`, `sit_prop_act.py`, `sit_cases.py`, `sit_cases2.py`, `sit_cases3.py`,
`sit_time.py`). Each opens a campaign named `audit_situations_<label>` and removes it in a finally block.

## 1. Random runs

| Run | Generated | Kept / dropped | Properties asserted | Failed |
|---|---|---|---|---|
| `situations.check` | 2,495 proposals past the contract: every stake, want, condition, state, tie, by_kind and certainty; `who` and holders pointing at ids, names, trades, places, roads, the player, a person who is gone, empty and odd strings; repeated entries; lists of 0 to 9 | n/a | never raises; never writes (`store._writes` and a hash of every table row unchanged); its input not mutated; the same twice; every accepted part rests on a living person, a real place or road, and a person among the accepted | none |
| `situation_parts.register` | 300 of the accepted sets, at three tiers, with and without ways | n/a | never raises; the accepted list not mutated; every part names a real npc, clue, place; the heart's part numbers in range; every `of_part` effect points at a condition or resource; every harmful condition has an effect of its own; parts, heart, paths and clues the same after close and reopen | none |
| `situation_parts.ruled` + `keep_changes` | 30,000 chains on three situations of 22 parts (6 people, 3 goods, 3 ties, 7 conditions of every by_kind, 3 pieces of evidence), rebuilt every 400: all 27 words, part / who / about from -2 to 30, needs forward, backward, cyclic and repeated, repeated n, every `because`, every act kind and degree | 9,319 kept, 127,743 dropped; every word kept at least once | never raises; never writes; thread, act and chain not mutated; at most `rulings.most`; no kept change needs a dropped one; the kept set checked alone is kept whole; nothing of the world by words alone; no gain from a failed act; a world change just kept is "already so" when asked again; the record within its window; parts and clues the same after reopen | none |
| `act.validate` / `_chain` / `apply` | 12,000 rulings past `ActRuling.check`, two situations near sharing two people, six people present, two objects: every change word, target of every kind, `who` and `about` of every code, needs, every check and difficulty | 3,749 kept, 20,392 dropped | validate never raises and never writes; apply never raises and its operation stands; no kept change needs a dropped one; the kept set checked alone is kept whole; on a roll of talk nothing of the world by the act's own hand; a doer outside the situation is never counted as the act; parts the same after reopen | **2 properties**: a doer outside the situation counted as the act itself (213 kept changes); a world change on a roll of talk through `because: earlier` (3) |

Why changes were dropped in the 30,000-chain run (the engine's own reasons):

| Dropped | Reason |
|---|---|
| 56,807 | it rests on a change that was not kept |
| 18,756 | it names no part of the situation that change can be made to |
| 12,730 | words alone change what people believe, feel and will do, never the world itself |
| 7,211 | the person was not there to hear it or see it done |
| 5,311 | whoever it says did it could not: not a living person of the situation, or not the one it must be |
| 5,297 | no piece of evidence has been found to show |
| 5,009 | nothing was given |
| 4,388 | the one who acted was not where it is |
| 3,948 | no coin was handed over, or less than was asked |
| 3,133 | whoever it says did it has no say over that |
| 2,776 | whoever it says did it does not hold that |
| 1,261 | an act that failed brings no gain |
| 940 | it is already so |
| 176 | they stand against the one who acted / nothing has changed that would move one who refuses / only evidence or force moves one who is committed |

## 2. Cases built from what the runs and the code pointed at

| Case | What was done | What happened | Finding |
|---|---|---|---|
| 12 | Heart: one creature threat, one person harmed. The way "Slay the wolves" met by a kill deed through `events.after_deed`, three times, differing only in the record before | record empty: way done, situation still active, `read_ends` leaves it. Record `[(fixer, believes)]`: **ended, result lost, ending_kind lost**. Record `[(harmed, believes)]`: resolved, player, achieved | situations-1 |
| 6 | Blocker won over (open, a gift), then N kept `believes` on a part outside the heart, then the kill way met and `read_end` | N = 5: contributors `[player]`, resolved, achieved. N = 41: record 40, contributors `[]`, **ended, lost** | situations-2 |
| 15 | The act path (`ws.on_other`): one line wins the blocker; a second line said 41 times | 3 ruling calls in all; trust of the one addressed 50, 60, 70, 80, 90, 100; record at 40; the `open` gone from the record, contributors `[]`, the blocker's part still open | situations-2, situations-8 |
| 1, 13 | "The flood (held by nature) is lifted", the doer named four ways | no doer: kept (the act's own). `s1.1`: dropped, "has no say over that". `p1` (the same person, a part of two situations): **kept as the act's own**. `p7` (no part of it): **kept as the act's own**, record `by: player`, contributors `[player]`. The judge's path with a doer outside the parts: dropped | situations-3 |
| 5 | A person who blocks situation A and is harmed in B; ruling `p1 open (words)` | kept as `s2.2 open`: B's part. A's record empty | situations-4 |
| 2 | Rolled on performance: `[harmed grateful (words); flood lifted; harmed safe]` | the last two with `because` skill or force: dropped, "words alone...". With `because: earlier, needs [1]`: **all kept**; after apply the closure is lifted | situations-5 |
| 4 | Rolled on strength: `[o1 broken (force); s1.7 lifted (earlier, needs [1])]`, and the same across two situations | change 1 kept, change 2 dropped "it rests on a change that was not kept". With `because: skill` and the same needs: kept | situations-6 |
| 3 | Only the guard present: `[guard terrified; guard warns the boss; boss afraid (needs [1])]` | 1 and 3 kept, 2 dropped (one change a person). 1 and 3 checked alone: 3 dropped, "not there to hear it". After apply the absent boss: mood frightened, source `parts:c3` | situations-7 |
| 11 | The same line six times, ruling `p7 warmer` | trust 50, 60, 70, 80, 90, 100, 100; one ruling call; 30 game minutes | situations-8 |
| 7, 10 | A situation ended by `lose`, by `finish`, by the pulse's `end_thread`, 30 situations, each person asked for their request first | In the save: stock 0, open requests 0, worries 0, moods 0, live effects 0. On the scene's copies after `lose`: 32 worries, 32 moods; saving such a copy writes the worry back. After `finish`: none | situations-9 |
| 8 | A 3-day danger adopted as a part (`adopt`) | day 2: in force. Day 3 + 1 min: not in force, threats resolved. Day 4 + 5 min, after `apply_one` prunes the row: **in force again** | situations-10 |
| 9 | A ruling keeps `lost`, then `given_up`, on a scarce good its holder has | `lost`: part lost, stake lost, price rise on, stock rows unchanged, still among the holder's wares. `given_up`: price lifted, stock unchanged | situations-11 |

## 3. Timing (CPU, stub)

| Measured | Result |
|---|---|
| `events.read_ends` (run every line) with six live situations of 4 people, 1 good, 1 condition each, nothing to end | median 3.5 ms; 54 person loads a call |
| one `store.load_npc` | 0.05 ms |
| `targets.targets_for` with the six near | 7.1 ms; 36 person loads; 55 lines |

Nothing here is worth changing for speed.

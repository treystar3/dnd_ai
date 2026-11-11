# A2 measured (f582: what to avoid checked after writing, never shown before it)

One measurement of `prose/section-a` at `1de8d98` (f582 on top of the baselines' game), on a rented RTX 5090 on 2026-11-11 (about
$1.45), with `tools/prose_baseline.sh` exactly as for new1 and new2: `live_check --runs 3`, `interp_eval --live`, four hunter plays
and the talker. Judged task by task against the span of the two baselines (`prose.md`, the table "against").

## Verdict: A2 does not hold

| Task | What moved, against new1 / new2 |
|---|---|
| narrate | worn-word uses **worse** (17.6 per 1,000 words against 12.5 / 11.9); stock phrases in what was shown 0.54 per 1,000 against 0.14 / 0.08; **rewrites 49 of 180** against 16 of 157 and 21 of 192 |
| dialogue_frame | repeated phrases **worse** (13.5 against 9.9 / 10.5); worn uses **worse** (27.5 against 20.1 / 25.2) |
| npc_conversation | repeated phrases **worse** (6.0 against 0.6 / 0.0; one townsperson's board talk repeated: "afraid our current board doesn't", "'high tier' work available right"); repeated sentences worse |
| combat_narrate | worn uses **worse** (9.3 against 6.7 / 4.2); repeated phrases hold |
| combat_opening | shared openings marked worse at 2% against 0% / 0%: noise at this size |
| exchange, hire_chat, combat_aftermath | hold |

Other measures: `interp_eval --live` 163 of 170 (163 / 165 before). The live check's judge: vivid 28 (20 / 19), flat or generic 72
(83 / 83), stock phrases 10 (12 / 7): the one measure that moved the other way, and the judge is the least steady of them.

## What it says

The lists were doing work. With the worn words and stock phrases no longer shown beforehand, narration leaned on them more, and
the checker had to send back nearly three times as many drafts (each a second model call before the player reads anything): the
cost the plan named. Shown passages still carried more stock phrases, since a rewrite is asked for once. The design doc's reasoning
(a list puts what it forbids in front of the model) does not hold for this model and these lists.

By the owner's rule (keep a change only if its measures hold or improve), A2 is not kept. The two checks it added (a hire's reply,
and a townsperson answering several at once, held to the worn words) are kept: they back the lists, they do not replace them.

## Sample passages (the talker's play, the same seed)

Before (new1), narration:
> The heavy door creaks shut behind you as you step out into the cooling evening air. The cobblestones of the trading square remain
> damp from the day's activity, reflecting the dimming orange light above. One man with a broom sweeps a pile of straw near a vacant
> stall at the edge of the market area. He pushes the debris into a heap without looking your way.

After (A2), narration:
> The Tilted Plough sits low against the dusty street, its name painted in crooked strokes upon a wooden sign overhead. Dust motes
> dance in the warm afternoon light outside the entrance. Inside, the atmosphere shifts; it is heavier here, smelling of toasted
> grain and old wood.

Before (new1), a frame:
> The scarred veteran pulls a thick cord through an eyelet to tighten a pack strap. His hands stop mid motion as he looks up,
> squinting one eye against the low light of the granary.

After (A2), a frame:
> She straightens from her crouch, pressing the damp cloth into the crook of one arm. The rag she holds drips onto the clean board.

# Roadmap: the order across the design docs

Agreed with the owner on 2026-11-10. The design docs each order their own steps; none orders the others. This is that order, built
from their stated dependencies. Single-player depth comes before multiplayer (the owner's call).

**Not covered here:** "the rebuild plan" that GOALS.md's decisions cite (Bundles B to F, Stages 3, 4 and 8) lives outside this repo.
Anything still open there has to be folded in by the owner.

## What shapes the order

- Doc 08 says to build its groundwork (M0) together with the turn overhaul (TurnContext) and doc 05: all three rewrite the same code.
- Split-party time (docs 06, 07) needs doc 05's tables and doc 08's two-character harness (M1).
- Doc 02's object checks (`uses`, `targets_for()`) read doc 05's object tags and resolver.
- Training (doc 09 C) waits until the prompts stop changing.
- Work that needs the live model is batched into pod sessions.

## The phases

| Phase | Work | Needs the live model |
|---|---|---|
| 1 | Doc 09 section A (A2, A4, A3, A1), measured on a pod against a baseline. Beside it, on the stub suite: doc 11 step 1 (the "Send a report" zip), doc 10 step 1 (the human-line corpora) | A only |
| 2 | Pillar 2 outside combat: doc 01's situation fixes (parts for every tier, no judge caps, threads ending from world state), doc 02 steps 2 to 4 (one ruling pipeline; improvised acts become deeds), doc 05 steps 1 and 2 (the thread access layer, objects as entities). One pod session compares old and new rulings and settles the f536 slot question | doc 02 step 3 |
| 3 | Groundwork with no behaviour change, the goldens replaying exactly throughout: doc 08 M0 (one actor context), the turn overhaul, doc 05 steps 3, 4, 6 and 7. Done while no other branch touches the turn code | no |
| 4 | The rewrites that sit on the groundwork: doc 02 steps 5 and 6 (combat onto the one ruling), doc 09 section B (smaller prompts, decide then speak, beats; about 90 narration call sites move once) | yes |
| 5 | Multiplayer: doc 08 M1 to M5 with docs 06 and 07. Then doc 09 section C (training) once the prompts are stable | from M3 |

Doc 10 steps 2 to 6 (the screen-only player agent, the judge, the chambers) fit wherever the owner answers its question; earlier is
better, because it measures everything else. Doc 11 steps 2 and 3 follow doc 10's corpora.

## Why this order

- **Phase 2 before 3:** pillar 2 work improves the game played today and replaces f559's interim ask-back; its new code takes a
  character id from the start, so little is built twice.
- **Phase 3 before 4:** the combat and prose rewrites both cut through the turn code; before the groundwork they would be done twice.
- **Multiplayer last:** the longest dependency chain, four of its six milestones marked large.

## Waiting on the owner

- Doc 10: may a hosted model act as test player and judge, for testing only? (GOALS keeps hosted models out of the game.)
- Doc 02: arcs as campaign-tier situations; an improvised strong success matching an ability's.
- GOALS.md open questions: a class's main attributes; picking up a copied save folder.
- Provisional numbers for the balance pass: combat `base_odds` 60 (f568), `scant_odds` -20 (f570).

# 3. Two confirmed bugs, with reproductions and fixes

Both tests are in `tests/`, in the repo's own style (plain scripts for `tools/sim`, running against simlib's stub). Both **fail on
06b393c** and **pass with `bugfixes.patch`**. To run: copy them into `tools/sim/`, then
`python3 tools/run_suite.py --only repro`.

## Bug 1: a combat improvisation rolls on the wrong dice
- **Where:** `engine/combat_improv.py resolve()`, line 61: `checks.roll(odds_for(p, effect))`.
- **What happens:** `services/fight.py:379` passes the fight's dice (`self.dice`) in as `rng`, but the roll ignores it. The result is
  drawn from the global `checks` stream (`engine/streams.py`). The damage that follows in the same function does use `rng`.
- **Why it matters:** the Bundle E decisions keep a fight's dice its own, so outcomes are consistent across a reload and the odds
  simulation leaves no trace. Here, an improvised move's success depends on how many non-fight checks happened earlier in the same
  input.
- **Test:** `tests/improv_dice_repro_test.py` spies on `checks.roll` and checks it receives the fight's dice.
- **Fix:** one argument, `checks.roll(odds_for(p, effect), rng)`. The fight fixture and fight-service tests (16) still pass. Golden
  fights that contain an improvisation may change their rolls, so re-bless `stub_fight` if it moves.

## Bug 2: an impossible act succeeds when the ruling call fails
- **Where:** `engine/ruling.py run()`. When `ask()` returns `None` (an LLMError: a timeout, a budget deferral, a validation failure on
  every retry), it calls `world_improv.resolve(ws, words, text)` with no ruling. That skips the capability check and any chance of a
  "no".
- **What happens:** "I grow wings and fly away over the rooftops" gets sorted into the improvisation list and rolled. On a success, the
  narrator is told: *"THE GAME HAS DECIDED: what the player attempts (grow wings and fly away over the rooftops) WORKS."* (Reproduced
  exactly by the test.)
- **Why it matters:** GOALS.md pillar 2 says "Impossible actions are refused, and never granted and then forgotten."
- **Test:** `tests/ruling_fallback_repro_test.py`. The ruling call fails, the die is forced to a success, and the test checks the
  narrator is not told it worked.
- **Fix:** with no ruling, ask back in character (`ask_back`, the game's existing clarify path, which logs a refusal) instead of
  rolling. The existing improvisation and ruling tests (13) still pass.
  - **Trade-off:** when the model is down, the player is asked to rephrase instead of getting a roll. That's an honest result, and the
    clarify path already has a plain fallback line.
  - **Better long term:** the `act()` pipeline in doc 2 can defer the act and retry it, instead of asking.

## Related finding, not yet a test: improvised control skips the control contest
`combat_improv` `disable` and `force_move` call `add_status` directly, while abilities go through `combat.contest()`, which applies
wisdom resistance, diminishing returns and the boss prior. So repeated improvised control is never resisted and never wears off. The
fix belongs in doc 2's step 5, but a quick interim fix is to call `contest()` before `add_status` in `combat_improv.resolve()`.

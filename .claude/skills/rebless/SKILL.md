---
name: rebless
description: Use when a golden recording (data/replay/sessions) no longer replays after a change, or golden_replay_test fails.
---
# Re-blessing a golden recording

A golden is re-recorded only when every changed line is explained by the feature. Never to make a test green.

1. `python tools/rerun.py --golden <name>` and read which input first differs and how (state, outcome or words).
2. Decide: is the difference what the feature intends? If not, it is a regression: fix the code, not the recording.
3. If intended: `python tools/rerun.py --golden <name> --rebless`, read the printed changes row by row
   (storage/statehash.changes), and list them in the commit body with the reason for each.
4. Re-run golden_replay_test, budget_data_459_test, isolation_456_test, layers_517_test, load_and_slow_526_test.
5. If the data hash moved (a data/ file changed), say so in the commit: the goldens are now on the new data.
6. The fight fixtures (tools/sim/fixtures/fights) carry the data hash in their headers too. With `MERAVIA_SAVES` and `MERAVIA_LOGS`
   each set to a scratch folder, run `python tools/sim/fight_fixtures.py` to compare. If no case moved, `python tools/sim/fight_fixtures.py --record`
   refreshes the headers; check that each decompressed body is unchanged. If a case moved, read it as for a golden: re-record only
   what the feature explains, and name each moved case and its reason in the commit.

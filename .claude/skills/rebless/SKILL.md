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

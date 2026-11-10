---
name: feature
description: Use when building or changing anything in Meravia (a numbered fNNN feature). Walks the owner's process from GOALS.md: pillar, plan, test first, build, checklist, suite, commit.
---
# Building one feature (fNNN)

1. **Number it.** The next number after the highest fNNN in `git log` (the session start prints it).
2. **Pillar.** Name the GOALS.md pillar(s) it serves, in one line. If it pulls against a goal or an owner's decision, stop and ask.
3. **Read before writing.** Read the modules you will touch and their tests in `tools/sim` (search the test names for the module).
   Prefer infrastructure over a narrator rule (GOALS.md "How it is built").
4. **Plan.** For anything over ~50 lines or touching more than two modules: write the plan (files, data, tests) and wait for approval.
5. **Test first.** Add `tools/sim/<name>_<NNN>_test.py` in the house style (plain script, simlib stub, `check(...)`, exit 1 on failure).
   Run it and see it fail for the right reason.
6. **Build.** Numbers and content in `data/` (YAML) and checked in `engine/data_check.py`. New code takes a character id, never
   `self.player` (checklist 8). Every store gets a cap. Comments: one short `(fNNN)` line of why, not a history.
7. **Checklist.** Go through GOALS.md "Checking a change" items 1-8 and write one line each in the commit body.
8. **Suite.** `python tools/run_suite.py -j 4`. If a golden recording moved, use the `rebless` skill; never re-record to make a test pass.
9. **Commit.** Subject `fNNN: <what> (pillar N)`. Body: the checklist lines and what was measured.

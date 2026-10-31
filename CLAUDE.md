# Working on Meravia

Read GOALS.md before building anything. It is the owner's statement of what this game should be, and every change is held to it:

- Say which pillar a change serves, in its commit message.
- Run the checklist at the end of GOALS.md before calling a change done.
- If a request seems to pull against a goal there, raise it with the owner before building.
- When the owner decides something about what the game should be, add it to GOALS.md under "Owner's decisions" (newest first), in
  their words where there are any. When an open question there is answered, move it into the decisions.

Conventions:

- Each change is a numbered feature, (fNNN), named in its comments and its commit subject.
- Tests are plain scripts in tools/sim (*_test.py) that run against simlib's model stub. A change gets a test, and the whole suite
  (python3 tools/run_suite.py -j 4) passes before it is pushed.
- Numbers and content live in data/ (YAML) and are checked at startup by engine/data_check.py.

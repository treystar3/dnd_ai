# Working on Meravia

Meravia is a sandbox RPG narrated by a local model (llama-server, Gemma 4 12B, RTX 3060 minimum). The engine decides every number and
state change; the model names, describes and speaks, and what it writes is checked (llm/contracts.py) before the player sees it.

**Read GOALS.md before building**: the pillars, "How it is built" and "Checking a change". Read only the owner's decisions that
touch the systems you change (search the table). If a request pulls against a goal, ask before building.

## How to work
- Use the `feature` skill for any change. Each change is a numbered feature (fNNN) with a test in tools/sim.
- Plan first for anything touching more than two modules; wait for approval. Design docs live in docs/design/.
- Use the `suite-runner` agent for the suite and `goals-reviewer` before committing. `code-explorer` for unfamiliar systems.
- Commit subject: `fNNN: <what> (pillar N)`. The full suite passes before any push (a hook enforces it).

## Facts that save time
- Python 3.12+ (nested f-strings). Tests: plain scripts in tools/sim against simlib's stub; `python tools/run_suite.py -j 4`,
  `--only a,b`, `--changed DIR`. Goldens: data/replay/sessions, replayed by tools/rerun.py; see the `rebless` skill.
- Numbers and content live in data/ (YAML), checked at startup by engine/data_check.py. data/measured is written by tools only.
- The turn: scenes/world.py turn() -> operations (engine/operation.py); model calls before transactions (f470), never inside.
- New code takes a character id (`self.acting`), not `self.player`: multiplayer is a goal (GOALS.md checklist 8).
- Never put the dash character in story text; no length limits on narrator or speakers (owner's rules).

## Don't
- Don't re-record a golden to make a test pass. Don't edit data/measured by hand. Don't add rules to narrator prompts where engine
  infrastructure would do (GOALS.md "Infrastructure over patches").
- Comments: one short `(fNNN)` line of why. The history belongs in the commit, not the code.

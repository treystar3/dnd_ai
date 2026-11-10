# Meravia (treystar3/dnd_ai): review against GOALS.md

Reviewed at commit 06b393c (2026-11-08). Read-only: the repo was cloned to /tmp and nothing was pushed.

## The goals in brief
Meravia is a sandbox RPG narrated by a local LLM (llama-server on the player's GPU). The model acts as a dungeon master. It names, describes and speaks, and the engine owns every number and every change to the game state. The pillars:
1. **A real world, not a stage set.** Anything the narration names can be entered or used. The player's actions leave marks, and the world keeps changing when the player isn't there.
2. **The game is a DM.** It accommodates whatever makes sense in the fiction. When it refuses, it refuses in the world's own voice, never with a parser error.
3. **No two runs alike.** Prose is never stamped out the same way twice.
4. **People who feel like people.** Voices stay consistent, eccentric characters are passive rather than obnoxious, and the party plays like a table at a real game.
5. **Good prose.** No dashes, no length limits, no machinery leaking onto the page.
6. **Deep, fair systems,** with balance tuned later.
7. **Easy to read and play.**

Infrastructure rules: fix the system rather than patching the instance, keep data in YAML, nothing grows without bound, every change is tested, and multiplayer is a goal, so state is keyed by character id.

## Recommendations, highest impact first

### 1. Build "places within places" for towns and buildings (Pillar 1, Pillar 2) - High priority, large effort
- **Where:** `engine/features.py:48 grows_here()` never lets a town, city, village or building grow parts. In that case `scenes/world.py:~3040` falls through to `scenes/explore_actions.py:30 within_place()`. That function logs a `facade`, then tells the narrator to "add no one and nothing of value", and nothing is saved. Otherwise the player gets `no_such_place()`. The docstring at `scenes/world.py:2909` admits the gap: "Rooms, doors and the party as places to go come with the work on places within places."
- **Change:** Extend the feature/part system (`engine/features.py`, `scenes/part_actions.py`, `data/rules/features.yaml`) to cover settled interiors: back rooms, cellars, upstairs rooms, yards and alleys. Gate them by plausibility tables in data, such as which kinds of building have which parts. When `part_of_here()` matches, call `part_move(adopt=True)` to create and save a real part, and use `within_place` only as the fallback.
- **Why:** This is the owner's own complaint in GOALS.md: "stages in a play ... everything behind them is a facade". The engine already counts each facade it hits. This change closes them rather than just counting them.

### 2. Turn the explore roll's "nothing new" result into a real outcome (Pillar 1, Pillar 2) - High priority, medium effort
- **Where:** `scenes/explore_actions.py on_explore()`. Exploring is a flat random roll against `explore_chance`. If the roll fails, or `discovery.room()` is full, a spot the player saw named in the narration still gets "They find nothing new... Describe the search and its fruitlessness". That is a stage-set result for something the narration itself put there.
- **Change:** When `part_of_here(seek)` is true, never let the roll erase the spot. Always give it a saved part. Use the roll only for what the part *holds*, such as a clue, a cache or nothing of value. For spots that weren't named, a failed roll should leave a lead (`data["leads"]`) or a cost, not a blank result.
- **Why:** "Anything the narration names ... can be gone into ... or the game says plainly why not."

### 3. Move the hard-coded refusals into the world's voice (Pillar 2, Pillar 3) - High priority, medium effort
- **Where:** There are 88 `self.refuse("...")` literals across `scenes/`. Examples: "Not from here. Get to a proper place first." (explore_actions.py), "Which one? Say its number or name.", "How much? Say an amount.", "There's nothing here to skin or butcher."
- **Change:** Give each refusal a *reason code* plus facts, and route it through one refusal service. That service either picks from data-held variants or hands the reason to the narrator to phrase. Keep the engine's decision and change only the wording.
- **Why:** GOALS says refusals come "in the world's own voice, never with a parser error". It also says lines the player sees often must not be "stamped out the same way each time". This is the infrastructure fix the owner asks for, not more rules for the narrator.

### 4. Fix the Python version mismatch (Pillar 7, "Every change is tested") - High priority, small effort
- **Where:** `play.bat:8` tells testers "Python 3.10 or newer". But `tools/eventrun.py:483` and other modules use nested same-quote f-strings, which only work on Python 3.12+ (PEP 701). On 3.11, 5 suite tests fail with `SyntaxError: f-string: unmatched '('`: clerk, eventrun, nightbot, nights_529, one_constructor_450 and regard_480.
- **Change:** Either require 3.12 in `play.bat` and the tester README, or rewrite the handful of f-strings. Add a version check at startup.

### 5. Make the golden data hash line-ending-proof and re-bless it (infrastructure, "Every change is tested") - High priority, small effort
- **Where:** `storage/statehash.py:110 data_hash()` hashes the raw bytes of each file. The repo has no `.gitattributes`. On a clean Linux clone the hash is `1b5d103a82d3` but the goldens expect `2c85101a6937`. Six tests fail because of this: budget_data_459, isolation_456, golden_replay, layers_517, load_and_slow_526 and nights_529. golden_replay also shows real differences in the fight text.
- **Change:** Add a `.gitattributes` with `* text=auto eol=lf` and `*.yaml/*.json eol=lf`, or normalise CRLF to LF before hashing. Then re-bless and check whether the remaining fight-text differences are real regressions.
- **Caveat:** I couldn't tell whether this comes from Windows line endings or from goldens that weren't re-blessed after a data change. Either way, the suite does not pass on a fresh clone.

### 6. Break up the WorldScene god object, starting with the multiplayer seams (infrastructure, Checklist #8) - Medium priority, large effort, do it in steps
- **Where:** `scenes/world.py` has 4,005 lines. `WorldScene` inherits from 32 action mixins, and its `__init__` sets about 40 mutable fields that track the turn. There is one `self.player`, and `self.player` appears about 1,078 times across `scenes/` and `engine/`.
- **Change:** Pull the turn-pipeline state (`line_ops`, `passages`, `unshown_ops`, budget and so on) out into a `TurnContext` object. Have new code take an *acting character* (an `acting` already exists in places) instead of reaching for `self.player`. Move each mixin toward a service with explicit dependencies, the way `services/fight.py` and `services/party.py` already do.
- **Why:** The owner said "changes and additions made later to systems should be easy" and that multiplayer must not need to "be built twice".

### 7. Move place-type lists and magic numbers into data (infrastructure: "Data is the source of truth") - Medium priority, small effort
- **Where:** Examples include the place-type tuple at `scenes/world.py:~3054` ("hut", "camp", "grove", ...), `NOT_A_SPOT` in `explore_actions.py`, the cache coin roll `randint(5, 20)` in `part_actions.py:172`, and `temperature=0.9, max_tokens=700` in `invent_discovery`.
- **Change:** Move them into `data/rules/explore.yaml` and `features.yaml`, and validate them in `engine/data_check.py`.

### 8. Repo hygiene - Low priority, trivial effort
- `.gitignore` excludes `/sim_report*`, `/runbal.sh` and `/runfull*.sh`, but those files are still tracked. Remove them with `git rm --cached`.
- `scenes/world.py`'s module docstring still says "Anything else is narrated as an attempt with no consequences". That is outdated now that rulings exist, and it misleads contributors.

## What I could and couldn't inspect
- **Checked:** GOALS.md and CLAUDE.md in full; the repository layout (659 Python files, about 141k lines); the explore, part and movement paths in detail; refusal patterns; the data hash; and the full simulation suite run locally. The suite passed 339 of 351 tests on Python 3.11 with the model stubbed out. Failures are listed above.
- **Not checked:**
  - Live play with the real model. I had no GPU or llama-server, so I didn't assess prose quality, voices, repetition or latency.
  - The web UI in `ui/gui/web` (not exercised).
  - Combat balance beyond the committed `sim_report.md`.
  - Most of the roughly 130 engine modules, which I skimmed by name only, including the new Stage 4 situations code.
  - pywebview didn't install in my sandbox; the tests didn't need it.

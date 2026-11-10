# 10. Testing the game the way people play it

The problem: the suite, the evaluations and the night bot test that the *engine* is right. They don't test what a *person* experiences.
The night bot (`tools/nightbot.py`) is a big step up from the old random bot: it has goals, personas and model-written lines. But it
still differs from a human in ways that matter for these goals.

## How the bot differs from a person (from its own code)
| The bot | A person |
|---|---|
| Chooses from what the engine supports, through a goal stack (contracts, a situation's `paths`, unvisited places) | Tries what the *prose* suggests, including things the engine can't do. That's exactly how facades and swallowed actions are found |
| Reads state through engine structures (a thread's paths, the roads' `nearby_wilds`, contract fields) | Has only the screen, misreads it, forgets it, takes notes |
| Writes lines from a goal, so they're always on-task and parseable | Writes several actions in one line, uses sarcasm, typos, asks questions out of character ("wait, what does trust do?"), plays a role for its own sake, says "lol", rephrases after a failure |
| Played by the **same model as the game** (Gemma writes the player's line that Gemma then reads) | Uses words the model wasn't tuned on. Gemma reading Gemma hides misreadings |
| Never gets bored, confused or frustrated, and never quits | Stops when bored or lost, and that point is the most valuable thing a test can find |
| Doesn't use the window (panes, buttons, hover details) | Clicks the shop, reads the character pane, opens the map |

## A layered plan

### Layer 1: the engine (keep as is)
The suite, the golden replays, `data_check`, balance simulations. They prove the rules; nothing to change.

### Layer 2: corpora of real human lines (cheap, high value)
- **Grow `interp_corpus` and the ruling cases from humans, not bots.** Every tester session's `logs/turns.jsonl` goes through
  `tools/interp_eval.py --promote` and `tools/interp_corpus.py`.
- **Tag each line by what makes it human:** several intents in one line, a pronoun with no clear reference ("give it to him"),
  sarcasm, an out-of-character question, a typo, a role-play flourish, a correction ("no, I meant the other one").
- **Track accuracy per tag.** "159 of 170" on average hides that most errors probably sit in a few tags.

### Layer 3: an agent that sees only the screen (the main new tool)
`tools/playeragent.py`: a player agent that sees **only what a person sees.**
- **Input:** the GUI's event stream (`ui/gui/bridge.py` events: text, panels, combat, status), which is exactly what the window shows.
  Pane actions go through the same endpoints the window's buttons use. So it tests the UI as well.
- **State it keeps:** its own notes (a capped scratchpad), the last screens, and a persona. **Never** the save, threads or paths.
- **Each turn's output:**
  ```json
  {"line": "...", "expecting": "what I think will happen", "feeling": "curious|bored|confused|annoyed|delighted",
   "notes": "what I want to remember", "report": "optional: something felt wrong, in my words"}
  ```
- **Persona traits that make it human,** in data (`data/test/players.yaml`):
  ```yaml
  roleplayer:  {verbosity: high, in_character: 0.9, multi_intent: 0.3, typos: 0.02, ooc_questions: 0.05, patience_turns: 40, curiosity: 0.8}
  speedrunner: {verbosity: low,  in_character: 0.2, multi_intent: 0.5, typos: 0.05, ooc_questions: 0.1, patience_turns: 8,  goal_focus: 0.9}
  explorer:    {verbosity: mid,  pokes_scenery: 0.6, follows_prose_nouns: 0.7, patience_turns: 25}
  newcomer:    {verbosity: mid,  ooc_questions: 0.3, misreads: 0.15, uses_panes: 0.6, patience_turns: 15}
  chaos:       {impossible_tries: 0.2, lies: 0.4, steals: 0.3, patience_turns: 30}
  ```
  `patience_turns` is how long it tolerates no progress or confusion before it quits. **Where it quits gets reported.**
- **The player's model is a different, stronger model** (for example Claude through the API), used **only to test, never in the game.**
  That breaks the "Gemma reads Gemma" loop and gives more human-like variety. The owner's rule against hosted models covers the game,
  not test tooling, but confirm with the owner and record it as a decision.
- **Cost and GPU:** the game runs on its usual server (local or a pod, `tools/HOSTED.md`); the agent is an API call per turn. Nothing
  is added to the game's card.
- **Calibrate it against humans:**
  - Compare the agent's lines with real testers' lines: length, verbs, the share of each tag (Layer 2), and the rate of rephrasing
    after a failure.
  - Tune the personas until the distributions are close. Keep a **human-likeness report** per night so drift is visible.

### Layer 4: probe agents for specific features (targeted, short)
Same tool, with a mission instead of a persona. Each runs from a **test chamber**: a seeded start placed right at the feature (extend
`data/rules/starts.yaml` with test starts: "at a situation's second stage", "in a town with a closed road", "with two companions of
opposite temperaments").

| Probe | Mission | What it measures |
|---|---|---|
| Facade hunter | Try to go into, take or use **every noun the narration names** | Facades and dead ends per 100 named things (pillar 1) |
| Improviser | Plausible but unusual actions, in and out of combat (the dragon's wing) | Rulings: wrong acceptances and wrong rejections, judged against a referee (below) |
| Boundary tester | Impossible acts and impossible framing ("I'm actually a god") | Impossible actions granted (should be 0; doc 3, bug 2) |
| Continuity checker | Comes back days later and asks people about earlier events, names, promises | Identity drift, forgotten deeds, contradictions (pillar 4) |
| Social engineer | Lies, bribes, threatens, plays people against each other in a situation | Open resolution, the lie rules, regard |
| Party watcher | Long travel with companions, morally loaded deeds | Companion reactions, banter frequency and repetition |
| Splitter (multiplayer, later) | Two agents split up, act, reunite | The doc 06 rules |

### Layer 5: judges
- **A turn-by-turn referee:** a judge model reads each turn's player line, the passage and the turn record (`engine/turnlog.py` rows:
  what the engine actually did) and labels it: *responded to what was said / swallowed / facade / contradiction / repetition / no
  dashes broken / invented a fact*. Use the same stronger model as the agent, not Gemma.
- **The agent's own report field,** gathered per night: "I tried X, expected Y, got Z". This is the bot version of a think-aloud
  usability test.
- **Blind readings stay** (`tools/blind_review.md`) for prose quality.
- **Spot-check the judges:** humans hand-label 50 turns a month; keep an agreement figure, as the ruling corpus does.

### Layer 6: real people (the ground truth)
- **The tester build** (`installer/README_testers.md`) with **opt-in session logs:** turns, refusals and facades are already logged;
  add session start and stop points.
- **Signals that work without asking anyone:**
  - **The rephrase rate:** the same intent typed again within 2 turns, which signals a swallowed action.
  - **Confusion lines:** "what?", "huh", "I said", "no I meant".
  - **Where sessions end:** the last 5 turns before quitting.
  - **How long turns take,** to compare against perceived waiting.
- **A three-question form after each session:** what was the best moment, what was the worst, and was there a point where you didn't
  know what to do.
- **Every bug a human finds becomes a test chamber and a replay case**, so it can't come back unnoticed.

## The night, put together
1. Start the game server (local or a pod).
2. Run 3–5 screen-only agents with different personas for 1–2 hours each, plus 2–3 probes on test chambers.
3. The referee labels every turn; `tools/world_report.py` and `tools/latency.py` run as now.
4. A **night report**:
   - facades, swallowed actions and contradictions per 100 turns;
   - impossible actions granted;
   - quit points with the agent's reasons;
   - the human-likeness score;
   - top complaints quoted from the agents' report fields;
   - a comparison with last night.

## Building it, in order
1. **The human-line corpora with tags (Layer 2):** cheap, and immediately shows where interpretation fails.
2. **`playeragent.py` with one persona, screen-only, a different model, and the report field.**
3. **The referee judge and the night report.**
4. **Test chambers plus the facade hunter and the improviser.**
5. **More personas, calibrated against tester logs.**
6. **The tester program's opt-in logs and the post-session form.**

Each step is a numbered feature with its own tests in tools/sim, using a stub for the agent: a canned player model so the harness itself
is tested offline.

## Questions for the owner
1. Can a hosted model be used **as the test player and judge only**?
2. Are testers' session logs opt-in, and what's kept?
3. Which personas matter most for the audience you're making the game for?

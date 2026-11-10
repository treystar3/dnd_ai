# Meravia (treystar3/dnd_ai @ 06b393c): advisor deliverables

The repo was not modified. Everything was tested in a local clone.

## Reviews and designs (put these in docs/design/)
| File | What it is |
|---|---|
| `meravia_review.md` | First review (doc 01 corrects parts of it) |
| `01_module_review.md` | The situation, quest, arc, event and combat modules read properly; corrections; findings |
| `02_improvisation_design.md` | One improvisation ruling for every context (data, contract, pipeline, migration, tests) |
| `03_bug_repros.md` | Two confirmed bugs, with repro tests and fixes |
| `04_performance_patch.md` | The C YAML loader and the skipped map layout; tested, about 2x faster load and replay |
| `05_world_objects_design.md` | Parts of settled places, objects as entities, narration read-back, threads out of the JSON row |
| `06_split_party_time_design.md` | Time when players split up (a clock per character; touch, perceive and window rules) |
| `07_mud_mmo_time_research.md` | How MUDs, MMOs and play-by-post games handled it; changes to doc 06 |
| `08_multiplayer_implementation_plan.md` | Host and clients, actor contexts, concurrent turns, scenes, routing, milestones M0 to M5 |
| `09_prose_and_dialogue.md` | Better narration and dialogue: prompt diet, beats, decide then speak, signature lines, LoRA |
| `10_human_like_testing.md` | A screen-only player agent, probes, a judge, tester signals |
| `11_send_logs_feature.md` | An in-game "Send a report" button, with an upload service sketch |

## Code (put these in docs/patches/ and docs/tests/)
| File | What it is |
|---|---|
| `perf_easy_wins.patch` | Performance patch (`git apply`), applies to 06b393c |
| `bugfixes.patch` | The two one-line bug fixes (`patch -p1`) |
| `tests/*.py` | Repro tests; copy into tools/sim. They fail before the fix and pass after |

## Claude Code setup (copy the contents of claude_code_kit/ into the repo root)
`CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/`, `.claude/skills/` (feature, rebless) and `.claude/agents/` (suite-runner,
goals-reviewer, code-explorer). On Windows, replace `python3` with `python` (see the chat instructions).

Use Python 3.12 or newer; on 3.11, five existing tests fail on f-string syntax.

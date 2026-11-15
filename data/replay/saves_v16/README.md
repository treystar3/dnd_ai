# Saves kept at version 16 (f637)

Four saves as the game wrote them while the world's state was one JSON row, kept for the migration to the world's tables
(docs/design/20_phase3_plan.md, f640) to be tested on. They are not played and not re-recorded: a save here is what a
player's save of that version holds, and the point is that it stays so.

| File | What it is |
|---|---|
| `stub_short.db`, `stub_party.db`, `stub_fight.db` | The start of each golden recording, a byte for byte copy of `data/replay/sessions/<name>/start.db` as it stood at f636. |
| `world_script.db` | The end of the seeded world script (`tools/sim/world_script.py`, its own seed), played over the row: all four lists in use. |

Made once, at the last commit whose saves are version 16: the goldens' starts copied, and the world script played in a
process of its own (`world_script.run_apart`) with its `campaign.db` copied after the save closed.

tools/sim/worldtables_637_test.py holds that each is version 16, that a golden's is its recording's own for as long as
that recording's start is version 16, and that each loads the same world from the tables as from the row. If a recording
is made again at a later version, the save here is not copied from it again: it is the older one that is wanted.

The folder is not `data/replay/saves/` (docs/design/13 named that) because `.gitignore` leaves out every `saves/`.

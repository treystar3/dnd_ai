"""(f640) A save as version 16 kept it: the world's state in one row, the player's record in another (docs/design/20_phase3_plan.md).

The game keeps both in tables now. The tests that hold the tables to the rows (worldtables_637_test, players_638_test, the caps,
the world script) still need the row's side of the comparison, and the migration's test needs a save not yet migrated. This is how
they get one, and it is only for tests: the game never puts a save back.
- opened(name, kept) opens a save with no step past 16 run: a copy of one kept in data/replay/saves_v16, or a new one.
- world_to_row(store) and player_to_row(store) put a live store's world or player back in its row and take the tables away.
- lowered(store, version) makes a live store a save of an older version: both back in their rows, the version set.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from storage import migrations, playerstable, worldrow, worldtables
from storage.campaign import DB_NAME, CampaignStore

KEPT = Path("data/replay/saves_v16")
VERSION = 16


def world_to_row(store) -> worldrow.RowWorld:
    """The store's world is the one row again, holding what the tables held; the four tables are gone."""
    state = store._world._state() if isinstance(store._world, worldtables.TableWorld) else None
    with store.transaction():
        for table in worldtables.LISTS:
            store._db.execute(f'DROP TABLE IF EXISTS "{table}"')
        if state is not None:
            store._put(worldrow.RowWorld.KEY, json.dumps(state))
    store._world = worldrow.RowWorld(store)
    return store._world


def player_to_row(store) -> playerstable.RowPlayers:
    """The store's player is the one row again, the first character's record as the table held it; the table is gone."""
    text = store._players.text() if isinstance(store._players, playerstable.TablePlayers) else None
    with store.transaction():
        store._db.execute(f'DROP TABLE IF EXISTS "{playerstable.TABLE}"')
        if text is not None:
            store._put(playerstable.KEY, text)
    store._players = playerstable.RowPlayers(store)
    return store._players


def lowered(store, version: int = VERSION) -> None:
    """A live store as a save of that older version kept it: its world and its player in their rows, its version lowered."""
    world_to_row(store)
    player_to_row(store)
    store.set_version(version)


def opened(name: str, kept: str = "") -> CampaignStore:
    """A save at version 16, its world and its player in their rows: a copy of a kept one, opened with no later step run, or a
    new one put back."""
    folder = Path("saves") / name
    shutil.rmtree(folder, ignore_errors=True)
    if not kept:
        store = CampaignStore.open_or_create(name)
        lowered(store)
        return store
    folder.mkdir(parents=True)
    shutil.copyfile(KEPT / kept, folder / DB_NAME)
    steps, current = migrations.MIGRATIONS, migrations.CURRENT
    migrations.MIGRATIONS, migrations.CURRENT = [m for m in steps if m[0] <= VERSION], VERSION
    try:
        return CampaignStore.open_or_create(name)
    finally:
        migrations.MIGRATIONS, migrations.CURRENT = steps, current

"""(f589) The game's way to the world's state (docs/design/05 step 1): the narrow readers on the store's seam (storage/worldrow.py).

A caller that wants only part of the world asks for that part here, never for the whole row: when the world's lists are kept apart
(docs/design/13, the tables), these answer from them and no caller changes. The whole state is still `store.load_world_state()` and
`store.save_world_state(state)` for the code that writes it.
"""
from __future__ import annotations


def effects_at(store, kind: str, place: str, now: int, good: str = "") -> list[dict]:
    """The effects of this kind live at this place now (a price rise on one good counts only when that good is asked about)."""
    return store._world.effects_at(kind, place, now, good)


def threads(store, status: str | None = None) -> list[dict]:
    """The world's matters in the order held; with a status ("active", "resolved", ...), only those."""
    return store._world.threads(status)


def deeds_since(store, minute: int, kinds=None) -> list[dict]:
    """The deeds done at or after a minute; with kinds, only those."""
    return store._world.deeds_since(minute, kinds)


def news(store) -> list[dict]:
    """The news as held, oldest first."""
    return store._world.news()


# ---------- (f590) one append path per list: a writer adds through these, never to the list itself ----------

def add_effect(state: dict, row: dict) -> dict:
    """Lay an effect on the world (a price rise, a danger, a closure) in the state in hand; the caller saves it."""
    state.setdefault("effects", []).append(row)
    return row


def add_thread(state: dict, th: dict) -> dict:
    """Start a matter in the state in hand; the caller saves it."""
    state.setdefault("threads", []).append(th)
    return th

"""Residents made while the player reads. The model call for the rest of a place's people runs on one background thread;
everything that touches saved state (planning, applying the answer) stays on the main thread.

Jobs belong to the save they were planned for (f345). A job is keyed by the save's folder and the place, and only that save can
collect it: switching saves, or starting a new game, while a place's people are still being written must never hand them to
another game standing in a place of the same name. drop() forgets a closed save's jobs; their answers, when they come, go nowhere."""

import threading

_jobs: dict[tuple[str, str], dict] = {}
_lock = threading.Lock()


def _save(store) -> str:
    return str(getattr(store, "root", "") or "")


def pending(place_id: str | None = None, store=None) -> bool:
    """A job is still waiting: for this place, and for this save when one is named."""
    with _lock:
        return any((place_id is None or pid == place_id) and (store is None or key == _save(store)) for key, pid in _jobs)


def start(store, world, catalog, place_id: str) -> bool:
    """Begin making the people a place still lacks. Does nothing when a job of this save is already running or nobody is missing.
    A job left over from another save is forgotten first."""
    from npc import life
    drop(keep=store)
    if pending(store=store):
        return False
    state, _, _, slots = life._plan(store, world, place_id)
    if not (state.populated and slots):
        return False
    job = {"slots": slots, "result": None, "error": None}
    place = world.places[place_id]
    town = life.town_lines(store, world, place_id)          # read here, on the main thread; the call below only carries it

    def run():
        try:
            job["result"] = life._ask(place, world, slots, town)
        except Exception as err:
            job["error"] = err
        finally:
            job["done"].set()

    job["done"] = threading.Event()
    with _lock:
        _jobs[(_save(store), place_id)] = job
    threading.Thread(target=run, daemon=True).start()
    return True


def collect(store, world, catalog, wait_for: str | None = None, wait_all: bool = False) -> list[str]:
    """Apply every finished job of this save (and wait for the one on wait_for, or, with wait_all, for every one: (f439) a session that
    must replay exactly takes its background people in at an input's edge, never whenever a thread finishes). Returns the places that
    gained people."""
    from npc import life
    gained = []
    mine = _save(store)
    with _lock:
        keys = [k for k in _jobs if k[0] == mine]
    for key in keys:
        pid = key[1]
        job = _jobs.get(key)
        if job is None:
            continue
        if pid == wait_for or wait_all:
            job["done"].wait()
        if not job["done"].is_set():
            continue
        with _lock:
            _jobs.pop(key, None)
        if job["error"] or job["result"] is None:
            continue                       # the people are simply still missing; the next visit asks again
        try:
            life._apply(store, world, catalog, pid, job["slots"], job["result"])
            gained.append(pid)
        except Exception:
            pass
    return gained


def settle(store, world, catalog, place_id: str) -> None:
    """Before anything plans for a place, let its running job finish and be applied, so people are never made twice."""
    if pending(place_id, store):
        collect(store, world, catalog, wait_for=place_id)


def drop(store=None, keep=None) -> int:
    """Forget jobs: those of `store` when one is named, else every job not of `keep` (or all of them). Returns how many went.
    Called when a save closes, so a game opened next never collects them."""
    with _lock:
        gone = [k for k in _jobs if (store is not None and k[0] == _save(store))
                or (store is None and (keep is None or k[0] != _save(keep)))]
        for k in gone:
            _jobs.pop(k, None)
    return len(gone)

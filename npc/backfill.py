"""Residents made while the player reads. The model call for the rest of a place's people runs on one background thread;
everything that touches saved state (planning, applying the answer) stays on the main thread."""

import threading

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def pending(place_id: str | None = None) -> bool:
    with _lock:
        return bool(_jobs) if place_id is None else place_id in _jobs


def start(store, world, catalog, place_id: str) -> bool:
    """Begin making the people a place still lacks. Does nothing when a job is already running or nobody is missing."""
    from npc import life
    if pending():
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
        _jobs[place_id] = job
    threading.Thread(target=run, daemon=True).start()
    return True


def collect(store, world, catalog, wait_for: str | None = None) -> list[str]:
    """Apply every finished job (and wait for the one on wait_for). Returns the places that gained people."""
    from npc import life
    gained = []
    with _lock:
        ids = list(_jobs)
    for pid in ids:
        job = _jobs[pid]
        if pid == wait_for:
            job["done"].wait()
        if not job["done"].is_set():
            continue
        with _lock:
            _jobs.pop(pid, None)
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
    if pending(place_id):
        collect(store, world, catalog, wait_for=place_id)

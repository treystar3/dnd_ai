"""(f589) The world's state behind one seam (docs/design/05 step 1; docs/design/13, its f582).

The world's state is one JSON row today, read and written whole. Everything reaches it through this seam: `load()` and `save()` for the
whole state (the store's `load_world_state` and `save_world_state`, unchanged), and narrow readers for what most callers want from it
(the effects at a place, the matters by status, the deeds since a minute, the news). Each narrow reader is defined here as a filter over
the whole state, so storage that keeps the lists apart later answers them without changing a caller.

The stale-save detector (`WATCH_STALE`, on for the suite and the night tools, off in shipped play, so play is byte for byte as before):
a loaded state remembers the text it came from; a save whose stored text has changed since that load (a copy held across another
write, then saved over it) is noted on the seam with the function that saved it, and is still made exactly as today.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

WATCH_STALE = False                 # (f589) the suite and the night tools turn it on; shipped play never pays for it
_HERE = Path(__file__).resolve().parent
_SKIP = (str(_HERE), str(_HERE.parent / "engine" / "worldstate.py"))


def _digest(text: str | None) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


class Loaded(dict):
    """(f589) A loaded world state that remembers the text it came from (only while the detector watches)."""
    came_from: str = ""


# ---------- the filters every storage answers the same way ----------

def effects_matching(state: dict, now: int, kind: str, place: str, good: str = "") -> list[dict]:
    """The effects of this kind live at this place. (f545) A price rise on one good (its `good`) counts only when that good is asked
    about: a scarce salt is no dearer bread."""
    return [e for e in (state or {}).get("effects", []) if e["kind"] == kind and e["place"] == place and e["until"] > now
            and (not e.get("good") or e["good"] == good)]


def threads_matching(state: dict, status: str | None = None) -> list[dict]:
    """The world's matters, in the order held; with a status, only those."""
    return [x for x in (state or {}).get("threads", []) if status is None or x.get("status") == status]


def deeds_matching(state: dict, minute: int, kinds=None) -> list[dict]:
    """The deeds done at or after a minute; with kinds, only those."""
    return [d for d in (state or {}).get("deeds", []) if d["minute"] >= minute and (not kinds or d["kind"] in kinds)]


def news_matching(state: dict) -> list[dict]:
    """The news as held, oldest first."""
    return list((state or {}).get("news", []))


class RowWorld:
    """(f589) The world's state in one row of the store's kv table, as it has always been kept."""

    KEY = "world_state"

    def __init__(self, store):
        self._store = store
        self.stale: list[dict] = []           # (f589) the saves the detector caught, each with the function that made it

    # ---- the whole state
    def load(self) -> dict:
        text = self._store._kv_text(self.KEY)
        state = json.loads(text) if text else None
        if not WATCH_STALE:
            return state or {}
        out = Loaded(state or {})
        out.came_from = _digest(text)
        return out

    def save(self, state: dict) -> None:
        text = json.dumps(state)
        if WATCH_STALE and isinstance(state, Loaded):
            now = _digest(self._store._kv_text(self.KEY))
            if state.came_from and now != state.came_from:
                self.stale.append({"site": _site(), "turn": int(getattr(getattr(self._store, "meta", None), "turn", 0) or 0)})
        self._store._put(self.KEY, text)
        if isinstance(state, Loaded):
            state.came_from = _digest(text)   # saved: the stored text is now this copy's own

    # ---- the narrow readers: read-only, each a filter over the whole state
    def effects_at(self, kind: str, place: str, now: int, good: str = "") -> list[dict]:
        return effects_matching(self.load(), now, kind, place, good)

    def threads(self, status: str | None = None) -> list[dict]:
        return threads_matching(self.load(), status)

    def deeds_since(self, minute: int, kinds=None) -> list[dict]:
        return deeds_matching(self.load(), minute, kinds)

    def news(self) -> list[dict]:
        return news_matching(self.load())


def _site() -> str:
    """The function outside storage that made the save, as module:function (lines drift; the ratchet holds names)."""
    f = sys._getframe(2)
    while f is not None and f.f_code.co_filename.startswith(_SKIP):
        f = f.f_back
    if f is None:
        return "?"
    path = Path(f.f_code.co_filename).resolve()
    try:
        mod = path.relative_to(_HERE.parent).with_suffix("").as_posix().replace("/", ".")
    except ValueError:
        mod = path.stem
    return f"{mod}:{f.f_code.co_name}"

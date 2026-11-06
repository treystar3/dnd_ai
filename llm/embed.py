"""How alike two lines are in meaning, from a small embedding model (config.EMBED_MODEL) on the game's own server (f524: the embedder's
own llama-server, decided at the load). Used where the game would otherwise guess with word lists: has this person said this already,
is the player asking the same thing again, which subject is a question about.

When there is no embedder this session, or it fails, available() is False and every caller uses its simple fallback, so play never
waits on it.

(f518) Whether there is an embedder is the source's to say (llm/backend.py facts, R4): a stand-in has one when it was given an embed
function, a replay when its recording had one, the runtime when its embedder loaded; a source that does not say has none. Nothing
outside llm/ writes the state below: reset() puts it back."""
from __future__ import annotations

import math
import re
import threading
from collections import OrderedDict

import config

_cache: OrderedDict = OrderedDict()
_state = {"failed": False}
_lock = threading.Lock()
CACHE_SIZE = 2000


def available() -> bool:
    """Is the embedding model here and answering? The source says (f518); a failure turns it off for the session."""
    if not getattr(config, "EMBED_ENABLED", True) or _state["failed"]:
        return False
    return bool(_facts().get("embedder", False))


def _facts() -> dict:
    """The source's facts. (f524) A runtime still deciding whether it has an embedder refuses them: here that is "not yet", never a
    failure of the embedder's, so nothing is turned off for it."""
    from llm import backend
    from llm.errors import NotFinal
    try:
        return backend.facts()
    except NotFinal:                                    # (f524's review) only the refusal, never another RuntimeError
        return {}


def reset() -> None:
    """(f518) The embedder's state as a fresh process has it: not failed (the session's vectors are left alone). A test or a replay
    starts from here instead of writing the state."""
    _state["failed"] = False


def failed() -> bool:
    """(f518) Did a call fail this session, turning embeddings off?"""
    return bool(_state["failed"])


def vectors(texts: list[str]) -> list[list[float]] | None:
    """One vector per text, from the cache where it can. None if the model is not there or fails."""
    if not available():
        return None
    texts = [" ".join(str(t).split()) for t in texts]
    who = _facts().get("embed_model")
    if who is not None:
        if _state.get("model", who) != who:             # (f524) another embedder: its vectors are not these
            with _lock:
                _cache.clear()
        _state["model"] = who
    want = [t for t in dict.fromkeys(texts) if t not in _cache]
    if want:
        from core.interrupts import Interrupt
        from llm.errors import Failure
        try:
            from llm import backend
            got = backend.embed(["clustering: " + t for t in want]).vectors      # (f515) the game's own interface; today's request
        except Interrupt:
            raise                                     # (f516) cancelled, or stopped on purpose: no failure of the embedder's
        except Failure as f:
            if f.kind != "too_big":
                _state["failed"] = True               # (f516) a request too big is this call's own fallback; the embedder stays on
            return None
        except Exception:
            _state["failed"] = True
            return None
        from engine import budget
        budget.embed(len(want))                       # (f468) the texts this call read, on the turn's budget (part of the required path)
        with _lock:
            for t, v in zip(want, got):
                n = math.sqrt(sum(x * x for x in v)) or 1.0
                _cache[t] = [x / n for x in v]
    with _lock:                                       # what this request needs is read first, then marked as just used; only then
        out = [_cache[t] for t in texts]              # is the cache trimmed, so a long game can never drop a vector mid-request
        for t in dict.fromkeys(texts):
            _cache.move_to_end(t)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return out


def cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", " ".join((text or "").split())) if len(p.strip().split()) >= 3]
    return parts or ([text.strip()] if text and text.strip() else [])


def closest(text: str, others: list[str]) -> tuple[float, str] | None:
    """The highest similarity between any sentence of text and any sentence of the others, and that other sentence. None if unavailable."""
    mine = sentences(text)
    theirs = [s for o in others for s in sentences(o)]
    if not mine or not theirs:
        return (0.0, "") if available() else None
    v = vectors(mine + theirs)
    if v is None:
        return None
    a, b = v[:len(mine)], v[len(mine):]
    best, which = 0.0, ""
    for x in a:
        for j, y in enumerate(b):
            c = cos(x, y)
            if c > best:
                best, which = c, theirs[j]
    return best, which


def whole(text: str, others: list[str]) -> list[float] | None:
    """Similarity of the whole text to each of the others (no splitting into sentences). None if unavailable."""
    if not others:
        return []
    v = vectors([text] + list(others))
    if v is None:
        return None
    return [cos(v[0], o) for o in v[1:]]

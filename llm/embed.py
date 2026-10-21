"""How alike two lines are in meaning, from a small embedding model run by Ollama (config.EMBED_MODEL). Used where the game would otherwise
guess with word lists: has this person said this already, is the player asking the same thing again, which subject is a question about.

The model is pulled in the background the first time the game runs without it. Until it is there, or if it fails, available() is False and
every caller uses its simple fallback, so play never waits on it."""
from __future__ import annotations

import math
import re
import threading
from collections import OrderedDict

import config

_cache: OrderedDict = OrderedDict()
_state = {"ok": None, "pulling": False, "failed": False}
_lock = threading.Lock()
CACHE_SIZE = 2000


def _client():
    from llm import gateway
    return gateway._client


def available() -> bool:
    """Is the embedding model here and answering? Checked once, then remembered; a failure turns it off for the session."""
    if not getattr(config, "EMBED_ENABLED", True) or _state["failed"]:
        return False
    if _state["ok"] is None:
        c = _client()
        if not hasattr(c, "embed"):
            _state["ok"] = False
            return False
        try:
            from llm import setup_check
            _state["ok"] = setup_check.model_present(config.EMBED_MODEL)
        except Exception:
            _state["ok"] = False
    return bool(_state["ok"])


def pull_in_background() -> None:
    """If the model is missing, fetch it quietly; the game carries on with its simple checks until it arrives."""
    if not getattr(config, "EMBED_ENABLED", True) or _state["pulling"]:
        return
    try:
        from llm import setup_check
        if setup_check.model_present(config.EMBED_MODEL):
            _state["ok"] = True
            return
    except Exception:
        return
    _state["pulling"] = True

    def run():
        try:
            from llm import setup_check
            setup_check.pull_model(lambda frac, text: None, name=config.EMBED_MODEL)
            _state["ok"] = None                       # check again next time it is asked for
        except Exception:
            _state["ok"] = False
        finally:
            _state["pulling"] = False
    threading.Thread(target=run, daemon=True).start()


def vectors(texts: list[str]) -> list[list[float]] | None:
    """One vector per text, from the cache where it can. None if the model is not there or fails."""
    if not available():
        return None
    texts = [" ".join(str(t).split()) for t in texts]
    want = [t for t in dict.fromkeys(texts) if t not in _cache]
    if want:
        try:
            r = _client().embed(model=config.EMBED_MODEL, input=["clustering: " + t for t in want], keep_alive=config.KEEP_ALIVE)
            got = r["embeddings"] if isinstance(r, dict) else r.embeddings
        except Exception:
            _state["failed"] = True
            return None
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

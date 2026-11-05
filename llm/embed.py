"""How alike two lines are in meaning, from a small embedding model run by Ollama (config.EMBED_MODEL). Used where the game would otherwise
guess with word lists: has this person said this already, is the player asking the same thing again, which subject is a question about.

The model is pulled in the background the first time the game runs without it. Until it is there, or if it fails, available() is False and
every caller uses its simple fallback, so play never waits on it.

(f518) Whether there is an embedder is the source's to say (llm/backend.py facts, R4): a stand-in has one when it was given an embed
function, a replay when its recording had one, Ollama when its server has the model (probe(): never under the suite's switch, and fixed
for a strict session); a source that does not say has none. Nothing outside llm/ writes the state below: reset() puts it back."""
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


def available() -> bool:
    """Is the embedding model here and answering? The source says (f518); a failure turns it off for the session."""
    if not getattr(config, "EMBED_ENABLED", True) or _state["failed"]:
        return False
    from llm import backend
    return bool(backend.facts().get("embedder", False))


def probe() -> bool:
    """(f518) Does the Ollama server have the embedding model (OllamaShape's facts)? Checked once, then remembered. Never asked under the
    suite's switch (no server there). (f439) A session that must replay exactly decides it once, never mid-session."""
    import os
    if os.environ.get("MERAVIA_NO_SERVER"):
        return False
    from engine import streams
    if streams.STRICT and "fixed" in _state:
        return _state["fixed"]
    if _state["ok"] is None:
        try:
            from llm import setup_check
            _state["ok"] = setup_check.model_present(config.EMBED_MODEL)
        except Exception:
            _state["ok"] = False
    if streams.STRICT:
        _state["fixed"] = bool(_state["ok"])
    return bool(_state["ok"])


def reset() -> None:
    """(f518) The embedder's state as a fresh process has it: not yet probed, not failed, no strict answer kept (the pull under way and
    the session's vectors are left alone). A test or a replay starts from here instead of writing the state."""
    _state.update(ok=None, failed=False)
    _state.pop("fixed", None)


def failed() -> bool:
    """(f518) Did a call fail this session, turning embeddings off?"""
    return bool(_state["failed"])


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


def warm(session=None):
    """(f469) One small embed on a daemon thread, so the embedder's first load is paid at the home page and not inside the first turn's
    checks; the session owns the thread when there is one (engine/session.py own: a close waits for it). Nothing when the model is not
    there or embedding is off. Returns the thread, or None."""
    if not available():
        return None

    from llm import backend
    src = backend.source()                            # (f518) the source answering now, below the layers as before (no row, no count)

    def run():
        try:
            src.embed(["clustering: ready"])
        except Exception:
            pass
    t = threading.Thread(target=run, daemon=True, name="embed-warmup")
    t.start()
    if session is not None:
        session.own(t)
    return t


def vectors(texts: list[str]) -> list[list[float]] | None:
    """One vector per text, from the cache where it can. None if the model is not there or fails."""
    if not available():
        return None
    texts = [" ".join(str(t).split()) for t in texts]
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

"""(f761) What the checks and prompts remember of the telling, kept in one row of the save (kv "telling").

The worn-word watches (engine/worn.py, f349), the lines said in town for the house-voice guard (engine/voices.py, f350), how the last
passages after a fight began and what they opened on (scenes/combat_scene.py, f412), the exemplar draws (scenes/world.py exemplars,
f583), the hires framed in this town (scenes/party_actions.py, f347) and the partings heard lately (engine/partings.py, f347) live on
the scene, each capped where it is noted. Which names the row keeps is the opening's table's to say (engine/actor.py OPENING: kept in
the save, row "telling"), so another name of the kind is kept by one line there and a noted() where it is noted (the test's census
finds every function that stores a name the row keeps and holds it to that), with a reader here when JSON cannot hold it as it is
or what it holds is checked on the way back.

A noting site marks the row due (noted). An operation's commit writes it when it is due (scenes/world.py operation), so it rolls
back with the operation; the game's loop writes it before each prompt and as the menu ends it, for what was noted outside any
operation (the opening's passage). It is put back as the scene is made. It is the campaign's, not one character's: the habit is the model's. It is not state
(storage/statehash.py NOT_STATE_ROWS): what was told is not what is."""
from __future__ import annotations

from collections import deque

ROW = "telling"


def names() -> list[str]:
    """The scene's names the row keeps: the opening's table's rows kept in the save under this row."""
    from engine import actor
    return [n for n, r in actor.OPENING.items() if r.fate == actor.IN_SAVE and r.why.split(":", 1)[0] == ROW]


def _watches_in(v: dict) -> dict:
    from engine import worn
    return {str(k): worn.Watch.load(rows) for k, rows in v.items()}


def _said_in(v: list) -> deque:
    from engine import voices
    return deque(((str(t), str(who), set(map(str, grams))) for t, who, grams in v), maxlen=voices.window())


def _plain_in(v):
    if not isinstance(v, (list, dict)):
        raise TypeError(f"a list or a dict, not {type(v).__name__}")
    return v


def _lines_in(v: list) -> list:
    if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
        raise TypeError("a list of lines")
    return v


def _draws_in(v: dict) -> dict:
    if not (isinstance(v, dict) and all(isinstance(x, int) if k.startswith("n:") else isinstance(x, list) and all(isinstance(s, str) for s in x)
                                        for k, x in v.items())):
        raise TypeError("each pool's count and last draw")
    return v


_SAME = lambda v: v
# name -> (what the row holds of it, what the scene holds of the row's, raising on a damaged entry); a name not here is a list or a
# dict of plain values
CODECS = {
    "_worn": (lambda v: {k: w.rows() for k, w in v.items()}, _watches_in),
    "_said_in_town": (lambda v: [[t, who, sorted(grams)] for t, who, grams in v], _said_in),
    "_framed_hires": (sorted, lambda v: set(map(str, v))),
    "_after_starts": (_SAME, _lines_in), "_after_opened": (_SAME, _lines_in), "_partings_heard": (_SAME, _lines_in),
    "_exemplars": (_SAME, _draws_in),
}
PLAIN = (_SAME, _plain_in)


def noted(ws) -> None:
    """Something the row keeps was added to: it is written at the next commit."""
    ws.__dict__["_telling_due"] = ws.__dict__.get("_telling_due", 0) + 1


def dump(ws) -> dict:
    """The row as the scene holds it."""
    return {name: CODECS.get(name, PLAIN)[0](ws.__dict__[name]) for name in names() if name in ws.__dict__}


def save(ws) -> None:
    """The row written when something was noted since it was last written; none while nothing is remembered."""
    if not ws.__dict__.pop("_telling_due", 0):
        return
    rec = dump(ws)
    if rec:
        ws.store.save_telling(rec)
    else:
        ws.store.clear_telling()


def restore(ws) -> None:
    """The row put back on a scene made over the save. A damaged entry leaves that memory to start empty, and the rest is kept."""
    rec = ws.store.load_telling() or {}
    for name in names():
        if name not in rec:
            continue
        try:
            ws.__dict__[name] = CODECS.get(name, PLAIN)[1](rec[name])
        except (TypeError, ValueError, AttributeError):
            ws.__dict__.pop(name, None)

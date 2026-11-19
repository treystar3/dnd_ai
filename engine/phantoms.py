"""(f701) A passage may not show a creature of this place that the game does not have.

The narrator is told to add no creatures; nothing held it to that, and passages showed the awakened tree a search had found only signs
of, and wisps the game never had. A narrator's passage is read for the creatures the place can hold (its roster, given by the scene
through use()); one its request does not name (in view, the event, the fight's foes, the people here) is sent back once by the gateway
with the reason, and a second, or one on the last try, is taken, so the telling is never lost to it (llm/gateway.py). What a request
names is read from all of it but the passages it shows again (RECENT NARRATION, ALREADY SHOWN), which may hold an earlier phantom.

Names are read whole: "awakened tree", "will-o'-wisps"; never a common word alone ("trees", "wisps of mist"). A one-word name counts
as a creature only when written as one: plural, or after a word of hygiene.yaml phantom.before ("the bat", "two wolves"); never before
"of" or a word of what is left of one ("a wolf pelt"), as a likeness, owned, or done by someone; and a name that is a common word first
(phantom.common: "shadow", "ghost") is never chased alone."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from core import yamlio

ROOT = Path(__file__).resolve().parent.parent
_source: Callable[[], list[str]] | None = None
_names: dict[str, str] | None = None
SHOWN_AGAIN = ("RECENT NARRATION", "ALREADY SHOWN")          # the headings of what was told before


def use(source: Callable[[], list[str]] | None) -> None:
    """The scene says how to read the creatures its place can hold (bestiary ids)."""
    global _source
    _source = source


def _hy() -> dict:
    from engine import hygiene
    return hygiene.H.get("phantom") or {}


def _bestiary() -> dict[str, str]:
    global _names
    if _names is None:
        rows = yamlio.safe_load((ROOT / "data" / "world" / "bestiary.yaml").read_text(encoding="utf-8")) or []
        rows = rows.get("creatures", rows) if isinstance(rows, dict) else rows
        _names = {r["id"]: re.sub(r"\([^)]*\)", "", r.get("name", r["id"])).strip() for r in rows if isinstance(r, dict) and "id" in r}
    return _names


def _words(text: str) -> list[tuple[str, str]]:
    from engine.inventory import _stem
    return [(w, _stem(w)) for w in re.findall(r"[a-z]+", (text or "").lower())]


def named(text: str, creatures: list[str], strict: bool = True) -> list[str]:
    """The creatures (by name) a text shows, of those given; strict=False: any mention at all ("signs of wolf")."""
    hy = _hy()
    words = _words(text)
    raw = [w for w, _ in words]
    stems = [s for _, s in words]
    before, window = set(hy.get("before") or ()), int(hy.get("window", 3))
    after_not, before_not, common = set(hy.get("after_not") or ()), set(hy.get("before_not") or ()), set(hy.get("common") or ())
    out = []
    for cid in creatures:
        name = _bestiary().get(cid, cid.replace("_", " "))
        want = [s for _, s in _words(name)]
        if not want or (strict and len(want) == 1 and want[0] in common):
            continue
        n = len(want)
        for i in range(len(stems) - n + 1):
            if stems[i:i + n] != want:
                continue
            if strict:
                nxt, prev = (raw[i + n] if i + n < len(raw) else ""), (raw[i - 1] if i else "")
                if nxt in after_not or prev in before_not:
                    continue                                          # a likeness, an owner, what is left of one, a doer
                if n == 1 and raw[i] == stems[i] and not (set(raw[max(0, i - window):i]) & before):
                    continue                                          # one word, singular, with no word that makes it a creature
            out.append(name)
            break
    return out


def requested(request: str) -> str:
    """A request without the passages it shows again."""
    out, skipping = [], False
    for line in (request or "").split("\n"):
        if line.startswith(SHOWN_AGAIN):
            skipping = True
            continue
        if skipping and line.startswith("  "):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def found(task: str, text: str, request: str) -> str:
    """The creature a narrator's passage shows that the request does not name, or ''."""
    from engine import hygiene
    if task not in hygiene.NARRATOR or _source is None:
        return ""
    try:
        roster = list(_source() or ())
    except Exception:
        return ""
    if not roster:
        return ""
    allowed = {n.lower() for n in named(requested(request), roster, strict=False)}
    extra = [n for n in named(text, roster) if n.lower() not in allowed]
    return extra[0] if extra else ""


def reason(name: str) -> str:
    return f"{_hy().get('reason', 'that creature is not here')} (not '{name}')"

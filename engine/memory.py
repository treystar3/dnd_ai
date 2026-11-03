"""(f478) What a person remembers, typed. Every memory is one of KINDS (data/rules/memory.yaml says what each is), says whom it is about
(subject: a character's id, "player" today; "" for no one), who it came from (source: "self" for what they saw or lived, a person's id,
"town", "guild"), what it is about (about: the same thing again counts up on its row instead of filling the rows) and when. keep() is the
one way a memory is made; the store writes it and keeps every kind within its cap (storage/campaign.py _keep_row and _trim) in the same
transaction, so nothing a person remembers grows without bound on a long campaign.

A deed's line keeps a slot for the one who did it ({them}); it is read as "the stranger" (render) until a person's view of each
character names them (Bundle D f486)."""
from __future__ import annotations

from pathlib import Path

KINDS = ("experienced", "witnessed", "noticed", "heard", "told", "own_life", "promise_heard", "said", "knows", "revision")
FIRST_HAND = ("experienced", "witnessed", "noticed", "own_life")
THEM = "the stranger"
_CAPS: dict | None = None


def caps() -> dict:
    global _CAPS
    if _CAPS is None:
        import yaml
        _CAPS = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "memory.yaml").read_text(encoding="utf-8")) or {}
    return _CAPS


def cap(holder: str, kind: str) -> int:
    """The most rows of this kind a person keeps. A kind with no cap of its own (an older save's) is held to experienced's."""
    table = caps().get("townsfolk") or {}
    return int(table.get(kind) or table.get("experienced") or 40)


def keep(npc, text: str, *, day: int, turn: int, kind: str = "experienced", subject: str = "player", importance: int = 1,
         source: str = "", about: str = "", minute: int = -1):
    """A memory made: appended to the person's window, written as a row when they are saved (and trimmed to its kind's cap there)."""
    from npc.models import Memory
    if kind not in KINDS:
        raise ValueError(f"no such kind of memory: {kind}")
    m = Memory(day=day, turn=turn, text=text, importance=int(importance), kind=kind, subject=subject,
               source=source or ("self" if kind in FIRST_HAND else ""), about=about, minute=int(minute))
    npc.memories.append(m)
    return m


def render(text: str) -> str:
    """A memory's words as they are read: the slot for the one who did a deed is "the stranger" until each character is named (f486),
    "The stranger" where it opens a sentence."""
    text = text or ""
    if text.startswith("{them}"):
        text = THEM[0].upper() + THEM[1:] + text[len("{them}"):]
    return text.replace(". {them}", ". " + THEM[0].upper() + THEM[1:]).replace("{them}", THEM)


def problems() -> list[str]:
    """The startup check: every cap a whole number above zero, every kind one KINDS knows."""
    bad = []
    for holder, table in (caps() or {}).items():
        for kind, n in (table or {}).items():
            if kind not in KINDS:
                bad.append(f"memory.yaml {holder}.{kind}: no such kind of memory")
            if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                bad.append(f"memory.yaml {holder}.{kind}: needs a whole number above 0")
    if "townsfolk" not in (caps() or {}):
        bad.append("memory.yaml: needs the townsfolk's caps")
    return bad

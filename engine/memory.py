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
    """The most rows of this kind a person keeps (a hire, holder "hire:<id>", by the hire's table). A kind with no cap of its own (an
    older save's) is held to experienced's."""
    table = caps().get("hire" if str(holder).startswith("hire:") else "townsfolk") or {}
    return int(table.get(kind) or table.get("experienced") or 40)


def records(store, holder: str) -> list[dict]:
    """(f479) One record shape for everyone who remembers (a townsperson by id, a hire as "hire:<id>"): every row, oldest first, as
    {id, day, turn, kind, importance, text, subject, source, about, minute, times}, the slot read."""
    cols = ("id", "day", "turn", "kind", "importance", "text", "subject", "source", "about", "minute", "times")
    with store._lock:
        rows = store._db.execute(f"SELECT {', '.join(cols)} FROM npc_memory WHERE npc_id = ? AND forgotten = 0 ORDER BY id", (holder,)).fetchall()
    return [dict(zip(cols, r), text=render(r[5])) for r in rows]


# ---- (f479) a hire's memories: rows under hire:<id>, with the record carrying the window the game reads (engine/party.py)
HIRE_WINDOW = 8                       # the window a hire's record carries, as the party's eight always were (engine/party.py MEMORY_KEEP)


def hire_row(m: dict) -> dict:
    """A hire's memory as a row: a fact the player told them is told, by the player; anything else they lived, experienced, about the
    player. weight is importance, key is about, count is times."""
    told = m.get("kind") == "fact"
    return {"day": int(m.get("day", 0)), "turn": -1, "kind": "told" if told else "experienced", "importance": int(m.get("weight", 1)),
            "text": str(m.get("text", "")), "subject": "player", "source": "player" if told else "self", "about": str(m.get("key", "")),
            "minute": -1, "times": int(m.get("count", 1))}


def hire_memory(r: dict) -> dict:
    """A row as the hire's record carries it (engine/party.py reads day, text, weight, count, kind and key)."""
    out = {"id": r["id"], "day": r["day"], "text": r["text"], "weight": r["importance"], "count": r["times"],
           "kind": "fact" if r["kind"] == "told" else "event"}
    if r.get("about"):
        out["key"] = r["about"]
    return out


def hire_window(rows: list[dict]) -> list[dict]:
    """The window a hire's record carries: the rule the party kept its eight by, over every row (the heaviest survive, then the newest)."""
    mem = [hire_memory(r) for r in rows]
    while len(mem) > HIRE_WINDOW:
        old = mem[:len(mem) // 2]
        mem.remove(min(old, key=lambda x: (x["weight"], x["day"])))
    return mem


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
            if kind not in KINDS and holder != "maren":
                bad.append(f"memory.yaml {holder}.{kind}: no such kind of memory")
            if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                bad.append(f"memory.yaml {holder}.{kind}: needs a whole number above 0")
    if "townsfolk" not in (caps() or {}) or "hire" not in (caps() or {}):
        bad.append("memory.yaml: needs the townsfolk's and the hires' caps")
    return bad

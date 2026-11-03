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
CLAIMS = ("told", "heard", "said", "promise_heard")    # (f482) what someone said, never what is: no rule reads these (the fence in claims_482_test)
FIRST_HAND = ("experienced", "witnessed", "noticed", "own_life")
THEM = "the stranger"
_CAPS: dict | None = None


def caps() -> dict:
    global _CAPS
    if _CAPS is None:
        import yaml
        _CAPS = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "memory.yaml").read_text(encoding="utf-8")) or {}
    return _CAPS


def certainty(kind: str) -> str:
    """(f482) How sure a person is of a memory of this kind (data/rules/memory.yaml certainty): sure, they say, hearsay, their word."""
    return str((caps().get("certainty") or {}).get(kind, "sure"))


def strip_relative(text: str) -> str:
    """(f482) A claim kept without the words of time true only on the day it was said ("yesterday", "last week"): the row's minute keeps
    when it was said, and the telling says how long ago from now (f477)."""
    import re
    out = text
    for w in sorted(caps().get("relative_time") or [], key=len, reverse=True):
        out = re.sub(rf"(,\s*)?\b{re.escape(w)}\b(\s*,)?", " ", out, flags=re.I)
    out = re.sub(r"\s+([,.;!?])", r"\1", re.sub(r"\s{2,}", " ", out)).strip()
    return out[:1].upper() + out[1:] if out else text


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
        if "state" in store._memory_cols():                                           # (f483)
            cols = cols + ("state",)
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
         source: str = "", about: str = "", minute: int = -1, state: str = ""):
    """A memory made: appended to the person's window, written as a row when they are saved (and trimmed to its kind's cap there)."""
    from npc.models import Memory
    if kind not in KINDS:
        raise ValueError(f"no such kind of memory: {kind}")
    if kind in CLAIMS:
        text = strip_relative(text)                         # (f482) "yesterday" is true only on the day it was said
    m = Memory(day=day, turn=turn, text=text, importance=int(importance), kind=kind, subject=subject,
               source=source or ("self" if kind in FIRST_HAND else ""), about=about, minute=int(minute), state=state)
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
    for kind, word in ((caps() or {}).get("certainty") or {}).items():       # (f482)
        if kind not in KINDS or not isinstance(word, str) or not word.strip():
            bad.append(f"memory.yaml certainty.{kind}: needs a kind KINDS knows and a word")
    if not all(isinstance(w, str) and w.strip() for w in (caps() or {}).get("relative_time") or []):
        bad.append("memory.yaml relative_time: needs words")
    for holder, table in (caps() or {}).items():
        if holder in ("certainty", "relative_time", "identity"):
            continue
        for kind, n in (table or {}).items():
            if kind not in KINDS and holder != "maren":
                bad.append(f"memory.yaml {holder}.{kind}: no such kind of memory")
            if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                bad.append(f"memory.yaml {holder}.{kind}: needs a whole number above 0")
    if "townsfolk" not in (caps() or {}) or "hire" not in (caps() or {}):
        bad.append("memory.yaml: needs the townsfolk's and the hires' caps")
    return bad

"""(f480) What a person makes of each character, kept per character id (npc/models.py Regard on NPC.regard): trust, whether they have
met, how they know them, when they last spoke, the journal's note, Easy Company, and why their trust moved. GOALS.md, the owner's
decision of 2026-11-03: a townsperson's view of each character is kept separate, so a second character beside the first is a stranger
to someone the first has known for years.

- of(npc, who) reads one character's view; a person with no view of them gives a read-only blank one (a new acquaintance's).
- own(npc, who) is the view to write: made when it is not there yet, within the cap on characters per person.
- step(npc, who, n, cause) is the one writer of trust: clamped to 0..100, and the move kept with its cause (capped in data).
- aggregate(npc) is what the store's index columns hold: met by any, the highest trust, the name known to any, heard of by any; readers
  with no acting character (the world's own doings) read it.

Every caller passes the character's id; nothing here knows who is playing."""
from __future__ import annotations

from pathlib import Path

from npc.models import Regard, _Unmet

_RULES: dict | None = None
_BLANK = _Unmet()


def rules() -> dict:
    global _RULES
    if _RULES is None:
        import yaml
        _RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "regard.yaml").read_text(encoding="utf-8")) or {}
    return _RULES


def of(npc, who: str) -> Regard:
    """This person's view of the character `who`; a read-only blank one (trust 50, never met) when they hold none."""
    return npc.regard.get(who) or _BLANK


def own(npc, who: str, minute: int = -1) -> Regard:
    """This person's view of `who`, to write to: made when it is not there yet (its first_met left at -1 until they meet). Past the cap on
    characters, the view of the one longest unseen goes (never `who`'s)."""
    r = npc.regard.get(who)
    if r is None:
        r = npc.regard[who] = Regard()
        cap = int(rules().get("characters", 16))
        while len(npc.regard) > cap:
            oldest = min((k for k in npc.regard if k != who),
                         key=lambda k: (max(npc.regard[k].last_talk_at, npc.regard[k].first_met), k))
            del npc.regard[oldest]
    return r


def meet(npc, who: str, minute: int) -> Regard:
    """They have met `who`: the view made if need be, met set, and the first meeting's minute kept."""
    r = own(npc, who)
    if not r.met:
        r.met = True
        if r.first_met < 0:
            r.first_met = minute
    return r


def step(npc, who: str, n: int, cause: str, about: str = "", minute: int = -1, lo: int = 0, hi: int = 100) -> int:
    """The one writer of trust: `who`'s trust moved by n, held within lo..hi (0..100), the move kept with its cause and what it was about
    (the last `moves` of them, data/rules/regard.yaml). Returns how far it actually moved."""
    r = own(npc, who)
    before = r.trust
    r.trust = max(max(0, lo), min(min(100, hi), before + int(n)))
    moved = r.trust - before
    if moved:
        r.moves = (list(r.moves) + [{"minute": minute, "n": moved, "cause": cause, "about": about}])[-int(rules().get("moves", 12)):]
    return moved


def set_trust(npc, who: str, value: int, cause: str, minute: int = -1) -> int:
    """`who`'s trust set to a value (a start's people, someone freed, Maren), through step so the move is kept like any other."""
    return step(npc, who, int(value) - of(npc, who).trust, cause, minute=minute)


def aggregate(npc) -> dict:
    """What the store's index columns hold for a person: met by any character, the highest trust any holds (50 with none), the name
    known to any, heard of by any. Readers with no acting character read these."""
    views = list(npc.regard.values())
    return {"met": any(r.met for r in views), "trust": max((r.trust for r in views), default=50),
            "name_known": any(r.name_known for r in views), "heard_of": any(bool(r.heard_of) for r in views)}


def problems() -> list[str]:
    bad = []
    R = rules()
    for k in ("moves", "characters"):
        if not isinstance(R.get(k), int) or R.get(k) < 1:
            bad.append(f"regard.yaml {k}: needs a whole number of at least 1")
    return bad

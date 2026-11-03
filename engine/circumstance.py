"""(f483, Bundle D G5) How a person is, and what is on their mind, each with where it came from and how it ends.

- A mood has a cause (mood_source: the matter, the motive, the moment, the fall of a town...) and a clock (mood_until), set by set_mood,
  the one writer; drift lets it fade when the clock runs out (engine/drift.py).
- A concern has a cause (concern_from) and a state (concern_state: active, then settled or let go). It is released when what caused it
  ends (a matter, a motive, a job), leaving them a line of their own life, never left on their mind after its cause is gone.
- A person's identity changes through identity.revise (engine/identity.py), never by writing a trait or a profile in place."""
from __future__ import annotations


def _days(kind: str = "mood") -> int:
    from engine import pulse
    return int(((pulse.P.get("drift") or {}).get("moods") or {}).get("days", 6))


def set_mood(npc, text: str, t: int, source: str, days: int | None = None) -> None:
    """How they have been lately, from `source`, for `days` (data: pulse.yaml drift.moods.days when not given)."""
    npc.mood = text
    npc.mood_source = source
    npc.mood_until = int(t) + int(days if days is not None else _days()) * 1440


def clear_mood(npc) -> None:
    """The mood has faded: it and what gave it go together."""
    npc.mood, npc.mood_source, npc.mood_until = "", "", 0


def set_concern(npc, text: str, source: str) -> None:
    """What is on their mind, from `source` (a matter's id, quest:<id>, motive, profile). Nothing at all is no worry, from nothing."""
    if not (text or "").strip():
        npc.concern, npc.concern_from, npc.concern_state = "", "", ""
        return
    npc.concern, npc.concern_from, npc.concern_state = text, source, "active"


def release_concern(npc, source: str, state: str, t: int, line: str = "", day: int = -1, turn: int = -1) -> bool:
    """What `source` put on their mind is gone: settled (it came out well, or was dealt with) or let go. Leaves them `line` as their own
    life when given. False when their concern came from something else."""
    if not npc.concern or (npc.concern_from or "") != (source or ""):
        return False
    npc.concern, npc.concern_from, npc.concern_state = "", "", state
    if line:
        from engine import clock, memory
        memory.keep(npc, line, day=clock.day(t) if day < 0 else day, turn=turn, kind="own_life", subject="", minute=int(t), importance=2)
    return True

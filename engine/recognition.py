"""(f382) People know the player again: a person met before, spoken to again after a while, is told it is a return, when they last
spoke and the last thing between them; the narrator is told who in a room knows the player. Rules and wording in
data/rules/recognition.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from core import yamlio

ROOT = Path(__file__).resolve().parent.parent
R = yamlio.safe_load((ROOT / "data" / "rules" / "recognition.yaml").read_text(encoding="utf-8"))


def last_talk(npc, who: str) -> int:
    """The minute of their last conversation with the character `who` (f480), -1 for never. A record from before the minute was kept has
    only the day."""
    from engine import regard
    r = regard.of(npc, who)
    if r.last_talk_at >= 0:
        return r.last_talk_at
    return r.last_talk_day * 1440 if r.last_talk_day >= 0 else -1


def ago(now: int, then: int) -> str:
    """How long since, the way a person would put it: (f477) the one converter's words (engine/clock.py ago, data/rules/time_words.yaml)."""
    from engine import clock
    return clock.ago(then, now)


def away(npc, now: int, who: str) -> bool:
    """Have they met the character `who`, and is it long enough since they last spoke that this is that character coming back?"""
    from engine import regard
    then = last_talk(npc, who)
    return regard.of(npc, who).met and then >= 0 and now - then >= int(R.get("after_minutes", 180))


def line(npc, now: int, who: str) -> str:
    """What the person is told as a new conversation opens with the character `who`, or '' when it is no return."""
    if not away(npc, now, who):
        return ""
    from engine import memory
    mem = next((memory.render(m.text) for m in reversed(getattr(npc, "memories", []) or []) if m.kind != "own_life"), "")   # (f478) by kind
    last = R["last"].format(memory=mem.rstrip(".") + ".") if mem else ""
    return R["line"].format(ago=ago(now, last_talk(npc, who)), last=last)


def seen(npc, now: int, who: str) -> str:
    """What the narrator is told of a present person who knows the character `who` and has not seen them for a while, or ''."""
    return R["seen"].format(ago=ago(now, last_talk(npc, who))) if away(npc, now, who) else ""

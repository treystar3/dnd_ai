"""(f382) People know the player again: a person met before, spoken to again after a while, is told it is a return, when they last
spoke and the last thing between them; the narrator is told who in a room knows the player. Rules and wording in
data/rules/recognition.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
R = yaml.safe_load((ROOT / "data" / "rules" / "recognition.yaml").read_text(encoding="utf-8"))
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def last_talk(npc) -> int:
    """The minute of their last conversation with the player, -1 for never. A record from before the minute was kept has only the day."""
    at = getattr(npc, "last_talk_at", -1)
    if at is not None and at >= 0:
        return at
    day = getattr(npc, "last_talk_day", -1)
    return day * 1440 if day is not None and day >= 0 else -1


def ago(now: int, then: int) -> str:
    """How long since, the way a person would put it."""
    from engine import clock
    days = clock.day(now) - clock.day(then)
    if days <= 0:
        return "earlier today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{WORDS[days]} days ago"
    if days < 14:
        return "about a week ago"
    if days < 60:
        return f"{WORDS.get(days // 7, 'some')} weeks ago"
    return "months ago"


def away(npc, now: int) -> bool:
    """Have they met, and is it long enough since they last spoke that this is the player coming back?"""
    then = last_talk(npc)
    return bool(getattr(npc, "met_player", False)) and then >= 0 and now - then >= int(R.get("after_minutes", 180))


def line(npc, now: int) -> str:
    """What the person is told as a new conversation opens, or '' when it is no return."""
    if not away(npc, now):
        return ""
    mem = next((m.text for m in reversed(getattr(npc, "memories", []) or []) if not m.text.startswith("(my own life)")), "")
    last = R["last"].format(memory=mem.rstrip(".") + ".") if mem else ""
    return R["line"].format(ago=ago(now, last_talk(npc)), last=last)


def seen(npc, now: int) -> str:
    """What the narrator is told of a present person who knows the player and has not seen them for a while, or ''."""
    return R["seen"].format(ago=ago(now, last_talk(npc))) if away(npc, now) else ""

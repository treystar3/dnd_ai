"""How hard a moment hits each companion who sees it: composed, sobered, shaken or devastated, from how grave the moment is (its weight)
and how close they are to whom it concerns (themselves, a companion, the player, or nobody in particular). Nothing here names an event:
a death, a betrayal, something grim found, the player's own grief all go through the same table (data/rules/severity.yaml).

The level decides how they speak for that moment (register, given to each speaker on their own), which way it goes is their own (their
rolled way of breaking, speech.yaml tells: devastated), and what it leaves behind (a lasting mood and a memory, once per moment)."""
from __future__ import annotations

from pathlib import Path

import yaml

SV = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "severity.yaml").read_text(encoding="utf-8"))
LEVELS = ("composed", "sobered", "shaken", "devastated")


def closeness(listener: dict, concerns: str | None, pair_score: int | None = None, stands_out: bool = False) -> str:
    """self, close, known or distant. concerns: the listener's own id, another member's id (pair_score: their relation score), 'player'
    (the listener's trust in the player), or None (nobody in particular: known, or close when it stands out against their own life)."""
    C = SV["closeness"]
    if concerns is not None and concerns == listener.get("id"):
        return "self"
    if concerns == "player":
        b = listener.get("bond", 0)
        return "close" if b >= C["bond"]["close"] else ("known" if b >= C["bond"]["known"] else "distant")
    if concerns:
        s = pair_score or 0
        return "close" if s >= C["pair"]["close"] else ("known" if s >= C["pair"]["known"] else "distant")
    return "close" if stands_out else C["nobody"]


def level(weight: str, close: str, told: bool = False) -> str:
    """composed, sobered, shaken or devastated. told: they heard of it rather than saw it (a step or more lower)."""
    lvl = SV["level"].get(weight or "light", SV["level"]["light"]).get(close, "composed")
    if told:
        lvl = LEVELS[max(0, LEVELS.index(lvl) - int(SV.get("told_step_down", 1)))]
    return lvl


def register(lvl: str, in_fight: bool = False) -> str:
    """How this level changes the way they speak, for this one moment ('' when it does not)."""
    out = SV["register"].get(lvl, "") or ""
    if in_fight and lvl != "composed":
        out = (out + " " + SV["in_fight"]).strip()
    return " ".join(out.split())


def emotion(lvl: str) -> str:
    """The feeling whose rolled tell shows how they break (speech.yaml tells), for the levels that have one."""
    return "devastated" if lvl == "devastated" else ""


def at_least(lvl: str, floor: str) -> bool:
    return LEVELS.index(lvl) >= LEVELS.index(floor)


def may_be_silent(lvl: str, weight: str = "") -> bool:
    """They may answer with a word or with nothing but a gesture: hit hard enough themselves (severity.yaml may_be_silent_from), or
    given the floor at a moment grave enough that silence is a true answer from anyone (all_may_be_silent_at). The director decides who
    may react; this decides who has to speak."""
    return bool(lvl) and lvl in LEVELS and (at_least(lvl, SV["may_be_silent_from"]) or weight == SV["all_may_be_silent_at"])


def silent_line(name: str) -> str:
    """What is shown for someone who says nothing and makes no gesture that can be shown."""
    return SV["silent_shown"].format(first=name.split()[0])


def is_silent(shown: str) -> bool:
    """A shown line that is only a gesture or silence: '(Isel goes still.)', with no words after it."""
    t = (shown or "").strip()
    return t.startswith("(") and t.endswith(")") and "\n" not in t


REACTIONS: list[tuple[str, bool]] = []     # (level, silent) for each reaction to a moment at sobered or above (the live check reads this)


def note_reaction(lvl: str, silent: bool) -> None:
    if lvl and lvl != "composed":
        REACTIONS.append((lvl, bool(silent)))


def leave_mark(member: dict, lvl: str, short: str, key: str, minutes: int) -> bool:
    """What a shaking or devastating moment leaves behind: a mood that lasts, and a memory. Once per moment (key), however many times it
    is talked of afterwards. True if it was left now."""
    after = SV["after"].get(lvl)
    if not after or not key or key in (member.get("hit_by") or []):
        return False
    from engine import party as rules
    member.setdefault("hit_by", []).append(key)
    del member["hit_by"][:-20]
    from engine import canon
    canon.journal("struck", "", member.get("id", ""), f"{member.get('name', '')} was {lvl} by {short}", level=lvl)
    rules.set_mood(member, after["mood"].format(short=short), minutes, lasts=int(after["hours"] * 60))
    rules.remember(member, minutes // 1440, SV["memory"].format(short=short), 3 if lvl == "devastated" else 2)
    return True

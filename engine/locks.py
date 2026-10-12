"""Locks: records of locked rooms and containers, and the keys that open them. Pure rules - no model, no screen.

A lock belongs to a place (PlaceState.locks) and usually to a person. It is made when the player goes looking for something that is
plausibly kept behind a lock, or for the key to one (scenes/law_actions.py asks the model whether that is plausible; the engine builds
the record). Opening one is a roll on the theft bar (engine/law.py); a key opens its own lock with no roll. Numbers: data/rules/law.yaml, lock."""
import re

from engine import law

LK = law.L["lock"]


def words(text: str) -> set[str]:
    stop = {"the", "a", "an", "to", "of", "in", "my", "his", "her", "their", "locked", "door", "key"}
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", text.lower().replace("_", " ")) if len(w) > 2 and w not in stop}


def quality(worth: str) -> int:
    return LK["quality_by_worth"].get(worth, LK["quality_by_worth"]["ordinary"])


def make(name: str, owner_id: str, worth: str, existing: list[dict]) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "lock"
    uid, n = f"lock_{slug}", 2
    while any(l["id"] == uid for l in existing):
        uid, n = f"lock_{slug}_{n}", n + 1
    return {"id": uid, "name": name.strip(), "quality": quality(worth), "owner": owner_id, "state": "locked", "jam": 0, "change_day": -1}


def find(locks: list[dict], text: str, owner_id: str = "") -> dict | None:
    """The lock the words mean: the one whose name shares the most words with them (that person's first), else the only closed one."""
    w = words(text)
    best, hits = None, 0
    for l in locks:
        n = len(w & words(l["name"])) + (0.5 if owner_id and l["owner"] == owner_id else 0)
        if n > hits and w & words(l["name"]):
            best, hits = l, n
    if best:
        return best
    closed = [l for l in locks if l["state"] != "open"]
    return closed[0] if len(closed) == 1 and not w else None


def is_open(lock: dict) -> bool:
    return lock["state"] == "open"


def key_fits(lock: dict, day: int) -> bool:
    """A key taken unseen stops fitting after a few days; one taken in view stops at once (change_day is set then)."""
    return lock["change_day"] < 0 or day < lock["change_day"]


def key_stolen(lock: dict, day: int, seen: bool) -> None:
    lock["change_day"] = day if seen else day + LK["key_change_days"]


def jam(lock: dict) -> None:
    lock["jam"] = min(LK["jam_cap"], lock["jam"] + LK["jam_step"])


def difficulty(lock: dict) -> float:
    """Percent of the roll window this lock adds to the bar."""
    return lock["quality"] + lock["jam"]

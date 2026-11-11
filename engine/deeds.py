"""Deeds: a short ledger of what the player has done that the world could notice - a creature killed, a person persuaded,
a dungeon cleared, a contract finished. Big events read it to see whether their resolution paths are met, and the judge reads it
to decide whether the player ended an event in a way nobody planned. It lives in world_state.json under "deeds".

A deed is {"kind", "minute", "place", ...data}. Kinds: kill, persuade, deliver, dungeon_cleared, quest_done, found, defend, offense,
settled (f363: a situation the player ended; engine/events.py finish).
"""

import yaml
from core import yamlio
from pathlib import Path

E = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "events.yaml").read_text(encoding="utf-8"))
KEEP = E["judge"]["keep_deeds"]


def tick(state: dict) -> int:
    """(f547's fifth review) The world's own count of what has happened, in order: every deed, every ruling kept and every mark a
    situation's way takes (kept safe, told, trusted) gets the next. A count orders what minutes cannot (two things in one minute) and
    what a person has already answered (their stance) from what came after."""
    state["seq"] = int(state.get("seq") or 0) + 1
    return state["seq"]


def add(state: dict, kind: str, minute: int, place: str = "", **data) -> dict:
    """(f578) Number a deed and append it to the state in hand, kept at the cap; the caller holds the world and saves it."""
    deed = {"kind": kind, "minute": minute, "place": place, **data}
    deed["seq"] = tick(state)
    deeds = state.setdefault("deeds", [])
    deeds.append(deed)
    del deeds[:-KEEP]
    return deed


def log(store, kind: str, minute: int, place: str = "", **data) -> dict:
    """Record a deed. Returns it. Never raises: the ledger is a convenience, not a rule."""
    deed = {"kind": kind, "minute": minute, "place": place, **data}
    try:
        state = store.load_world_state()
        if not state:
            return deed
        deed = add(state, kind, minute, place, **data)
        store.save_world_state(state)
    except Exception:
        pass
    return deed


def since(state: dict, minute: int, kinds: tuple[str, ...] | list[str] | None = None) -> list[dict]:
    from storage.worldrow import deeds_matching          # (f589) one definition, the seam's
    return deeds_matching(state, minute, kinds)


def describe(d: dict) -> str:
    """One plain line for the judge."""
    k = d["kind"]
    where = f" at {d['place']}" if d.get("place") else ""
    if k == "kill":
        tag = f" ({d['rank']})" if d.get("rank") and d["rank"] != "normal" else ""
        return f"killed {d.get('creature', 'a creature')}{tag} level {d.get('level', '?')}{where}"
    if k == "persuade":
        return f"persuaded {d.get('npc_name') or d.get('npc', 'someone')}{where}"
    if k == "deliver":
        return f"delivered {d.get('item', 'an item')} to {d.get('npc_name') or d.get('npc', 'someone')}{where}"
    if k == "dungeon_cleared":
        return f"cleared the dungeon{where} and killed its master"
    if k == "quest_done":
        return f"finished the job '{d.get('title', 'a job')}'{where}"
    if k == "defend":
        return f"held the gate{where} against the host"
    if k == "settled":
        return f"settled '{d.get('title', 'a matter')}'{where}" + (f", {d['how']}" if d.get("how") else "")
    if k == "offense":
        return f"{d.get('offense', 'broke the law')}{(' (' + d['item'] + ')') if d.get('item') else ''}{where}, seen by {len(d.get('witnesses', []))}"
    return f"{k}{where}"

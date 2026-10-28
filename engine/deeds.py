"""Deeds: a short ledger of what the player has done that the world could notice - a creature killed, a person persuaded,
a dungeon cleared, a contract finished. Big events read it to see whether their resolution paths are met, and the judge reads it
to decide whether the player ended an event in a way nobody planned. It lives in world_state.json under "deeds".

A deed is {"kind", "minute", "place", ...data}. Kinds: kill, persuade, deliver, dungeon_cleared, quest_done, found, defend, offense,
settled (f363: a situation the player ended; engine/events.py finish).
"""

import yaml
from pathlib import Path

E = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "events.yaml").read_text(encoding="utf-8"))
KEEP = E["judge"]["keep_deeds"]


def log(store, kind: str, minute: int, place: str = "", **data) -> dict:
    """Record a deed. Returns it. Never raises: the ledger is a convenience, not a rule."""
    deed = {"kind": kind, "minute": minute, "place": place, **data}
    try:
        state = store.load_world_state()
        if not state:
            return deed
        deeds = state.setdefault("deeds", [])
        deeds.append(deed)
        del deeds[:-KEEP]
        store.save_world_state(state)
    except Exception:
        pass
    return deed


def since(state: dict, minute: int, kinds: tuple[str, ...] | list[str] | None = None) -> list[dict]:
    return [d for d in state.get("deeds", []) if d["minute"] >= minute and (not kinds or d["kind"] in kinds)]


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

"""A record of what the world did: when the pulse fired and what it changed, and (f355) what of it the player met - a moment, a scene, a
summons, a line about the room changing, people met on their routine. Shown by #pulse when the game runs with --debug, and appended as
one JSON row per event to config.PULSE_LOG_PATH (tools/world_report.py reads it, per game day). Nothing reads it back into the game."""
import json
from collections import deque
from pathlib import Path

LOG: deque = deque(maxlen=400)


def _write(row: dict) -> None:
    import config
    path = getattr(config, "PULSE_LOG_PATH", "")
    if not path:
        return
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def mark(kind: str, text: str, t: int, **data) -> dict:
    """(f355) Something the player met or did: kind moment | scene | summons | stay | routine | retold | board, or end (how=player) for a situation the
    player ended. Logged at once."""
    row = {"t": t, "kind": kind, "text": text, "effects": [], **data}
    LOG.append(row)
    _write(row)
    return row
_tick = {"t": 0, "fired": False}


def clear() -> None:
    LOG.clear()


def begin(t: int) -> None:
    """A pulse tick starts. It counts as quiet unless something is noted before the next one."""
    close()
    _tick.update(t=t, fired=False)


def close() -> None:
    if _tick["t"] and not _tick["fired"]:
        if LOG and LOG[-1]["kind"] == "quiet":
            LOG[-1]["count"] += 1
            LOG[-1]["to"] = _tick["t"]
        else:
            LOG.append({"t": _tick["t"], "to": _tick["t"], "kind": "quiet", "text": "", "count": 1, "effects": []})
    _tick["t"] = 0


def note(kind: str, text: str, effects: list | None = None, **data) -> dict:
    """kind: thread | stage | end | motive | effect | miss | drift. effects: [{"text", "result"}] applied by this event. Extra fields
    (tier, place, how...) ride along into the saved row."""
    row = {"t": _tick["t"], "kind": kind, "text": text, "effects": effects or [], **data}
    LOG.append(row)
    _tick["fired"] = True
    _write(row)
    return row


def effect(row: dict, text: str, result: str) -> None:
    row["effects"].append({"text": text, "result": result})


def describe(e: dict, store, world) -> str:
    """One effect as a line: what it is, to whom, where."""
    bits = [e.get("kind", "?")]
    if e.get("npc"):
        n = store.load_npc(e["npc"]) if store.npc_exists(e["npc"]) else None
        bits.append(n.name if n else f"{e['npc']} (no such person)")
    if e.get("other"):
        bits.append(f"toward {e['other']}")
    if e.get("place"):
        p = world.places.get(e["place"])
        bits.append("at " + (p.name if p else f"{e['place']} (unknown)"))
    if e.get("role"):
        bits.append(e["role"])
    if e.get("creature"):
        bits.append(e["creature"])
    if e.get("value") not in (None, ""):
        bits.append(f"value {e['value']}")
    if e.get("add") or e.get("remove"):
        bits.append(f"trait {e.get('remove') or '-'} -> {e.get('add') or '-'}")
    if e.get("days"):
        bits.append(f"{e['days']}d")
    if e.get("text"):
        bits.append('"' + str(e["text"])[:90] + '"')
    return " ".join(str(b) for b in bits)

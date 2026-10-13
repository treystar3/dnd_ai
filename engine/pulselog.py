"""A developer's record of what the world pulse did this session: when it fired and what it changed. Shown by #pulse when the game runs with --debug.
Nothing here is saved, and nothing reads it back into the game."""
from collections import deque

LOG: deque = deque(maxlen=400)
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


def note(kind: str, text: str, effects: list | None = None) -> dict:
    """kind: thread | stage | end | motive | effect | miss. effects: [{"text", "result"}] applied by this event."""
    row = {"t": _tick["t"], "kind": kind, "text": text, "effects": effects or []}
    LOG.append(row)
    _tick["fired"] = True
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

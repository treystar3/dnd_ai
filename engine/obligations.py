"""(f481) Offers and obligations between a person and a character, kept in the registry (engine/entities.py, the save's entities table)
with a lifecycle each (data/rules/lifecycles.yaml offer and obligation) and families in data/rules/obligations.yaml. GOALS.md S2: nothing
ends by age. A work offer is withdrawn when the working day is over, when the character leaves the town or when other work is offered in
its place; a request is released when the character says no, or when a new conversation opens without a yes; a contract is fulfilled
at the hand-in, broken when walked away from, or released when the one it was for is gone. Each end is said with a reason a person
could give (one of several lines, drawn from a die of the holder's own), and may leave the holder a memory of it.

The holder is in links (npc), the character in data.with always and in owner while it is open (entities.move clears owner on a final
state). Each row's `key` is the id the night's measures have always used: work:<npc>, request:<npc>, the contract's own id."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_F: dict | None = None


def rules() -> dict:
    global _F
    if _F is None:
        _F = yaml.safe_load((ROOT / "data" / "rules" / "obligations.yaml").read_text(encoding="utf-8")) or {}
    return _F


def family(name: str) -> dict:
    return (rules().get("families") or {})[name]


def open_(store, fam: str, holder: str, who: str, title: str, minute: int, terms: dict | None = None, key: str = ""):
    """A new offer or obligation of a family, from the person `holder` to the character `who` (or theirs to the holder, for a contract),
    in its kind's first state. `terms` is what it is (a job's task, pay and minutes; a request's posting)."""
    from engine import entities, streams
    kind = family(fam)["kind"]
    ref = f"obl:{streams.new_id(8, 'obl')}"
    while store.load_entity(ref) is not None:               # the id stream repeats after a reload at the same turn: never write over a row
        ref = f"obl:{streams.new_id(8, 'obl')}"
    return entities.begin(store, kind, ref, title[:120], minute, owner=who,
                          links={"npc": holder} if holder else {},
                          data={"family": fam, "with": who, "title": title, "terms": dict(terms or {}), "key": key or f"{fam}:{holder}"})


def _mine(e, fam: str | None, holder: str | None, who: str | None) -> bool:
    return (fam is None or e.data.get("family") == fam) and (holder is None or e.links.get("npc") == holder) \
        and (who is None or e.data.get("with") == who)


def current(store, fam: str, holder: str | None = None, who: str | None = None):
    """The open offer or obligation of this family from this holder (with this character), or None."""
    kind = family(fam)["kind"]
    start = "offered" if kind == "offer" else "active"
    rows = [e for e in store.find_entities(kind=kind, state=start) if _mine(e, fam, holder, who)]
    return rows[-1] if rows else None


def open_ones(store, fam: str | None = None, holder: str | None = None, who: str | None = None) -> list:
    """Every open offer and obligation, oldest first, of a family, holder or character when asked."""
    out = [e for e in store.find_entities(kind="offer", state="offered") + store.find_entities(kind="obligation", state="active")
           if _mine(e, fam, holder, who)]
    return sorted(out, key=lambda e: (e.since, e.ref))


def find(store, key: str):
    """The open one whose measures key this is (a contract's id), or None."""
    return next((e for e in open_ones(store) if e.data.get("key") == key), None)


def reason(e, to: str, cause: str) -> str:
    """The line this end is said with: one of the family's, drawn from a die of the holder's own (engine/streams.py keyed)."""
    from engine import streams
    lines = (((family(e.data["family"]).get("reasons") or {}).get(to) or {}).get(cause)) or [cause.replace("_", " ")]
    return streams.keyed("obligation", e.links.get("npc", ""), e.ref, len(e.history)).choice(list(lines))


def close(store, e, to: str, cause: str, minute: int, npc=None, day: int = -1, turn: int = 0):
    """End it: moved to `to` (refused when its lifecycle does not allow it), with the reason said for `cause`, and what the holder keeps
    of it remembered (data: remember) on `npc` when given (the caller saves it), else on the record."""
    from engine import clock, entities, memory
    if e is None:
        return None
    day = clock.day(minute) if day < 0 else day
    turn = turn or store.meta.turn
    why = reason(e, to, cause)
    e.data = {**e.data, "cause": cause}
    entities.move(store, e, to, minute, why)
    line = (family(e.data["family"]).get("remember") or {}).get(to)
    holder = e.links.get("npc", "")
    if line and holder:
        n = npc if npc is not None else (store.load_npc(holder) if store.npc_exists(holder) else None)
        if n is not None and not n.gone:
            memory.keep(n, line.replace("{title}", e.data.get("title", "")), day=day, turn=turn, kind="experienced",
                        subject=e.data.get("with", ""), about=f"obl:{e.data.get('key', '')}", minute=minute, importance=2)
            if npc is None:
                store.save_npc(n)
    return e


def lapse(ws) -> list:
    """(the world's own operation, each line) Work offers that no longer stand are withdrawn, for a reason: the one who offered it is off
    work for the day, or the character has left their town. Returns what was withdrawn."""
    from engine import clock, pulse
    out = []
    here = pulse.town_of(ws.world, ws.player.location) if ws.player.location in ws.world.places else ""
    for e in open_ones(ws.store, "work", who=ws.acting):
        holder = e.links.get("npc", "")
        n = ws.store.load_npc(holder) if holder and ws.store.npc_exists(holder) else None
        if n is None or n.gone:
            close(ws.store, e, "withdrawn", "gone", ws.minutes)
        elif n.location in ws.world.places and pulse.town_of(ws.world, n.location) != here:
            close(ws.store, e, "withdrawn", "left_town", ws.minutes)
        elif n.role in ws.world.roles and not clock.in_hours(ws.minutes, ws.world.roles[n.role].hours) and ws.minutes - e.since >= 60:
            close(ws.store, e, "withdrawn", "day_over", ws.minutes)
        else:
            continue
        out.append(e)
    trim(ws.store, ws.minutes)
    return out


def trim(store, minute: int) -> int:
    """Final rows older than keep_days are removed (what the holder remembers of them stays). Returns how many."""
    keep = int(rules().get("keep_days", 30)) * 1440
    gone = 0
    from engine import entities
    for kind in ("offer", "obligation"):
        for e in store.find_entities(kind=kind):
            if entities.final(e) and minute - e.since > keep:
                store.delete_entity(e.ref)
                gone += 1
    return gone


def for_state(store, who: str, quests=()) -> list[dict]:
    """What is owed between the world and the character `who`, in the shape the night's measures have always read: {id, kind, holder,
    title, state}. The contracts in hand are 'taken'; an open work offer 'open'; an open request 'offered'."""
    out = [{"id": q["id"], "kind": q.get("kind", ""), "holder": q.get("issuer", "") or "guild", "title": q.get("title", ""), "state": "taken"}
           for q in quests]
    for e in open_ones(store, who=who):
        fam = e.data.get("family")
        if fam in ("work", "request"):
            out.append({"id": e.data.get("key", e.ref), "kind": fam, "holder": e.links.get("npc", ""), "title": e.data.get("title", "")[:80],
                        "state": "open" if fam == "work" else "offered"})
    return out


def closed_since(store, minute: int) -> list[dict]:
    """Offers and obligations that ended at or after `minute`, as {id, state, reason}: the night's `closed` (C5 counts them apart from
    what vanished with no reason)."""
    from engine import entities
    out = []
    for kind in ("offer", "obligation"):
        for e in store.find_entities(kind=kind):
            if entities.final(e) and e.since >= minute:
                out.append({"id": e.data.get("key", e.ref), "ref": e.ref, "state": e.state,
                            "reason": (e.history[-1][3] if e.history else "")[:120], "cause": e.data.get("cause", "")})
    return out


def problems() -> list[str]:
    from engine import entities
    bad = []
    for name, spec in (rules().get("families") or {}).items():
        kind = spec.get("kind")
        if kind not in entities.L:
            bad.append(f"obligations.yaml {name}: kind '{kind}' has no lifecycle")
            continue
        finals = set(entities.L[kind].get("final") or [])
        for to, causes in (spec.get("reasons") or {}).items():
            if to not in finals:
                bad.append(f"obligations.yaml {name}: reasons for '{to}', which is not a final state of {kind}")
            for cause, lines in (causes or {}).items():
                if not isinstance(cause, str):
                    bad.append(f"obligations.yaml {name}: {to}.{cause} is read as {cause!r}, not a word: quote it")
                if not lines or not all(isinstance(l, str) and l.strip() for l in lines):
                    bad.append(f"obligations.yaml {name}: {to}.{cause} needs at least one line")
        for to in (spec.get("remember") or {}):
            if to not in finals:
                bad.append(f"obligations.yaml {name}: remember for '{to}', which is not a final state of {kind}")
    if not isinstance(rules().get("keep_days"), int):
        bad.append("obligations.yaml keep_days: needs a whole number")
    return bad

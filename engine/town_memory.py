"""(f484, Bundle D G3) What a town remembers: the one writer of a town's memory (PlaceState.memory, on the town's own place row).

A row is typed: {kind, subjects, minute, keep_until, text}, its words with no date in them (the minute says when; a reader tells it
from now in words), and `mark` for one that leaves a lasting mark. Each kind has its own cap and term in data (doors.yaml memory.kinds
for what ends a matter or a job, moments.yaml memory for a moment), so thirty moments never push out what the player settled a week
ago. Past its term a row goes; a settled matter leaves its mark (PlaceState.marks, capped), so the town keeps the detail for a month and
then one lasting line (the owner's decision of 2026-11-03).

Rows go at the one append path (file) and at the sweep the world's operation runs for the player's town each turn (sweep): nothing
ages out at read, and nothing read is written."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_K: dict | None = None


def kinds() -> dict:
    """{kind: {days, cap, mark?}}: a matter's and a job's from doors.yaml, a moment's from moments.yaml."""
    global _K
    if _K is None:
        D = yaml.safe_load((ROOT / "data" / "rules" / "doors.yaml").read_text(encoding="utf-8"))
        M = yaml.safe_load((ROOT / "data" / "rules" / "moments.yaml").read_text(encoding="utf-8"))
        _K = dict((D.get("memory") or {}).get("kinds") or {})
        _K["moment"] = {"days": int(M.get("memory_days", 3)), "cap": int((M.get("memory") or {}).get("cap", 12))}
        _K["_marks"] = {"cap": int((D.get("memory") or {}).get("marks_cap", 12))}
    return _K


def _until(r: dict) -> int:
    """When a row's term ends: its own keep_until; a row from before (f484) by the term it had then."""
    if "keep_until" in r:
        return int(r["keep_until"])
    if "until" in r:
        return int(r["until"])                                   # a moment's, before
    return int(r.get("minute", 0)) + int(kinds().get("settled", {}).get("days", 30)) * 1440


def _kind(r: dict) -> str:
    return r.get("kind") or ("moment" if "until" in r else "note")


def _town(world, place_id: str) -> str:
    from engine import pulse
    town = pulse.town_of(world, place_id)
    return town if town in world.places and not world.places[town].danger else ""


def _sweep(ps, now: int) -> bool:
    """Rows past their term go; one with a mark leaves it. True when anything changed."""
    keep, changed = [], False
    cap = kinds()["_marks"]["cap"]
    for r in ps.memory:
        if _until(r) > now:
            keep.append(r)
            continue
        changed = True
        if r.get("mark") and r["mark"] not in ps.marks:
            ps.marks = (ps.marks + [r["mark"]])[-cap:]
    ps.memory = keep
    return changed


def file(store, world, place_id: str, kind: str, text: str, minute: int, subjects=(), mark: str = "") -> None:
    """One thing the town will remember, for its kind's term, its kind held to its cap (the oldest of that kind goes first)."""
    town = _town(world, place_id)
    K = kinds().get(kind)
    if not town or not K or not (text or "").strip():
        return
    ps = store.load_place(town)
    _sweep(ps, minute)
    row = {"kind": kind, "subjects": [str(s) for s in subjects], "minute": int(minute), "keep_until": int(minute) + int(K["days"]) * 1440,
           "text": text.strip()}
    if mark:
        row["mark"] = mark.strip()
    ps.memory.append(row)
    same = [i for i, r in enumerate(ps.memory) if _kind(r) == kind]
    if len(same) > int(K["cap"]):
        drop = set(same[:len(same) - int(K["cap"])])
        ps.memory = [r for i, r in enumerate(ps.memory) if i not in drop]
    store.save_place(ps)


def sweep(store, world, place_id: str, now: int) -> None:
    """The town's rows past their term go now, a settled one leaving its mark (the world's operation, for the player's town)."""
    town = _town(world, place_id)
    if not town:
        return
    ps = store.load_place(town)
    if _sweep(ps, now):
        store.save_place(ps)


def lines(store, world, place_id: str, now: int, only=None) -> list[str]:
    """What the town remembers now, oldest first, in its words (a row from before f484 read without its date); `only`: these kinds."""
    from engine import matters
    town = _town(world, place_id)
    if not town:
        return []
    return [matters._undated(r["text"]) for r in store.load_place(town).memory
            if _until(r) > now and int(r.get("minute", 0)) <= now and (only is None or _kind(r) in only)]


SETTLEMENTS = ("settled", "ignored", "note", "job")


def problems() -> list[str]:
    bad = []
    for k, v in kinds().items():
        if k.startswith("_"):
            continue
        if not isinstance(v, dict) or int(v.get("days", 0)) < 1 or int(v.get("cap", 0)) < 1:
            bad.append(f"town memory kind {k}: needs days and cap, both at least 1")
    for k in SETTLEMENTS:
        if k not in kinds():
            bad.append(f"doors.yaml memory.kinds: no {k}")
    if kinds()["_marks"]["cap"] < 1:
        bad.append("doors.yaml memory.marks_cap: at least 1")
    return bad

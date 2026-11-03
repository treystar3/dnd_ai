"""(f438) A fingerprint of a campaign's whole state, and of the game it was played on.

The rebuild checks every stage against what the game did before it: a recorded session is replayed through the real turn, and after
each line the state must match what was recorded (tools/rerun.py). That needs one canonical reading of the save, the same however its
rows came to be written, and a fingerprint of the rules and content a recording was made with, so a replay on other data is known
for what it is.

dump() reads every table in a fixed order, JSON with sorted keys; digest() hashes each table and the whole; diff() names the first
table and key where two dumps part. The save's own folder name and the clock time it was made are not state (a replay plays a copy
under another name), so they are left out; everything else is in."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# table -> (the query, how many leading columns are its key, which columns hold JSON). The order here is the order of the dump.
TABLES = {
    "kv": ("SELECT key, json FROM kv ORDER BY key", 1, (1,)),
    "places": ("SELECT id, json FROM places ORDER BY id", 1, (1,)),
    "npcs": ("SELECT * FROM npcs ORDER BY id", 1, (1,)),
    "npc_memory": ("SELECT * FROM npc_memory ORDER BY id", 1, ()),
    "event_log": ("SELECT * FROM event_log ORDER BY seq", 1, (6,)),
    "entities": ("SELECT * FROM entities ORDER BY ref", 1, (6,)),
}
NOT_STATE = {("kv", "campaign"): ("name", "created")}    # the save's folder name and when it was made: a replay plays a copy under another
NOT_STATE_ROWS = {("kv", "operations"), ("kv", "presentation")}   # (f462) the record of what committed and what of it is left to show: the
                                                                 # state's history and its telling, not the state; a replay compares the record through the recording


def _canon(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def dump(store) -> dict[str, list]:
    """Every table as a list of rows, in key order, JSON columns read as values."""
    out = {}
    with store._lock:
        for table, (sql, keys, js) in TABLES.items():
            try:
                rows = store._db.execute(sql).fetchall()
            except Exception:                                  # an older save without that table
                rows = []
            got = []
            for r in rows:
                row = [_canon(v) if i in js else v for i, v in enumerate(r)]
                if keys and (table, row[0]) in NOT_STATE_ROWS:
                    continue
                drop = NOT_STATE.get((table, row[0])) if keys else None
                if drop and isinstance(row[1], dict):
                    row[1] = {k: v for k, v in row[1].items() if k not in drop}
                got.append(row)
            out[table] = got
    return out


def _h(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def digest(store=None, dumped: dict | None = None) -> dict[str, str]:
    """{table: sha256 of its rows, "all": sha256 of every table's}."""
    d = dumped if dumped is not None else dump(store)
    out = {t: _h(rows) for t, rows in d.items()}
    out["all"] = _h([out[t] for t in TABLES])
    return out


def diff(a: dict, b: dict, limit: int = 3) -> list[str]:
    """Where two dumps part: the table, the row's key, and the first differing field, for a replay report."""
    found = []
    for table in TABLES:
        ra, rb = a.get(table, []), b.get(table, [])
        if ra == rb:
            continue
        ka, kb = {r[0]: r for r in ra}, {r[0]: r for r in rb}
        for key in sorted(set(ka) | set(kb), key=str):
            x, y = ka.get(key), kb.get(key)
            if x == y:
                continue
            if x is None or y is None:
                found.append(f"{table} {key}: {'only in the second' if x is None else 'only in the first'}")
            else:
                found.append(f"{table} {key}: {_first(x, y)}")
            if len(found) >= limit:
                return found
    return found


def _first(x, y, path: str = "") -> str:
    """The first place two values differ, as a dotted path and both values, cut short."""
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y), key=str):
            if x.get(k) != y.get(k):
                return _first(x.get(k), y.get(k), f"{path}.{k}" if path else str(k))
    if isinstance(x, list) and isinstance(y, list):
        for i, (p, q) in enumerate(zip(x, y)):
            if p != q:
                return _first(p, q, f"{path}[{i}]")
        if len(x) != len(y):
            return f"{path or 'row'}: {len(x)} items against {len(y)}"
    return f"{path or 'value'}: {str(x)[:80]!r} against {str(y)[:80]!r}"


def data_hash(root: Path = ROOT) -> str:
    """The game a recording was made on: every file under data/ (but data/replay, the recordings and cases kept to test against, which
    are not the game, and (f459) data/measured, the card's measured speeds, which describe a machine and not the game), the model, the
    version, and the save schema."""
    import config
    from core.version import VERSION
    from storage import migrations
    h = hashlib.sha256()
    for f in sorted((root / "data").rglob("*")):
        rel = f.relative_to(root)
        if f.is_file() and "__pycache__" not in f.parts and rel.parts[:2] not in (("data", "replay"), ("data", "measured")):
            h.update(rel.as_posix().encode("utf-8") + b"\0")
            h.update(f.read_bytes())
    h.update(f"\0{config.MODEL}\0{VERSION}\0{migrations.CURRENT}".encode("utf-8"))
    return h.hexdigest()


def _short(v, n: int = 80):
    s = json.dumps(v, ensure_ascii=False, sort_keys=True, default=str) if not isinstance(v, str) else v
    return s if len(s) <= n else s[:n - 3] + "..."


def changes(before: dict, after: dict) -> dict:
    """(f476) What one input changed, row by row, from two dump()s: per table, each row added, gone or changed, keyed by its first
    column (a memory's id, an entity's ref, a person's id, a kv key), and for a changed row the columns, or for a JSON column the keys
    (one level down), that moved, each with its new value cut short. A re-bless names these, so a feature that predicted "memory row
    1, its kind" can be held to exactly that. Empty when nothing moved."""
    out: dict = {}
    for table, (_sql, _keys, js) in TABLES.items():
        old = {json.dumps(r[0], default=str): r for r in before.get(table, [])}
        new = {json.dumps(r[0], default=str): r for r in after.get(table, [])}
        t: dict = {}
        added = [k for k in new if k not in old]
        gone = [k for k in old if k not in new]
        if added:
            t["added"] = {json.loads(k) if k.startswith('"') else k: _short(new[k][1:], 160) for k in added[:40]}
        if gone:
            t["gone"] = [json.loads(k) if k.startswith('"') else k for k in gone[:40]]
        moved = {}
        for k in new:
            if k in old and old[k] != new[k]:
                diff = {}
                for i, (a, b) in enumerate(zip(old[k], new[k])):
                    if a == b:
                        continue
                    if i in js and isinstance(a, dict) and isinstance(b, dict):
                        for sub in sorted(set(a) | set(b)):
                            if a.get(sub) != b.get(sub):
                                diff[f"{i}.{sub}"] = _short(b.get(sub, "(gone)"))
                    else:
                        diff[str(i)] = _short(b)
                moved[json.loads(k) if k.startswith('"') else k] = diff
        if moved:
            t["changed"] = dict(list(moved.items())[:40])
        if t:
            out[table] = t
    return out

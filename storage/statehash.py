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
    "players": ("SELECT character_id, place, json FROM players ORDER BY character_id", 1, (2,)),
    # (f640) a list's rows by where they stand: the same reading whatever numbers the rows came to have
    "threads": ("SELECT row_number() OVER (ORDER BY ord), id, status, place, json FROM threads ORDER BY ord", 1, (4,)),
    "deeds": ("SELECT row_number() OVER (ORDER BY ord), seq, minute, kind, actor, place, json FROM deeds ORDER BY ord", 1, (6,)),
    "news": ("SELECT row_number() OVER (ORDER BY ord), minute, origin, thread, json FROM news ORDER BY ord", 1, (4,)),
    "effects": ('SELECT row_number() OVER (ORDER BY ord), kind, place, "until", thread, json FROM effects ORDER BY ord', 1, (5,)),
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
    out["all"] = _h([out[t] for t in TABLES if t in d])       # (f640) a view (below) holds the tables its version had
    return out


def _as_v16(d: dict) -> dict:
    """The state as version 16 held it: the player's record and the world's four lists in the small table, and no table of theirs."""
    from storage import playerstable, worldtables
    kv = []
    for key, value in d["kv"]:
        if key == worldtables.KEY and isinstance(value, dict):
            value = {k: [r[-1] for r in d.get(k, [])] if k in worldtables.LISTS and v == worldtables.marker(k) else v for k, v in value.items()}
        kv.append([key, value])
    first = [[playerstable.KEY, r[-1]] for r in d.get(playerstable.TABLE, []) if r[0] == playerstable.FIRST]
    kv = [r for r in kv if not (first and r[0] == playerstable.KEY)] + first
    moved = set(worldtables.LISTS) | {playerstable.TABLE}
    return {t: (sorted(kv, key=lambda r: r[0]) if t == "kv" else rows) for t, rows in d.items() if t not in moved}


# (f640) a dump read as an older version of the save held it: what a recording from before a move of rows is replayed against
VIEWS = {16: _as_v16}


def view(dumped: dict, schema: int) -> dict:
    if schema not in VIEWS:
        raise ValueError(f"no view of the state as version {schema} held it (there is one for: {', '.join(str(v) for v in sorted(VIEWS))})")
    return VIEWS[schema](dumped)


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


WORDING = ("data", "rules", "wording.yaml")    # (f718) which strings of which data files are wording
WORD = "\0w"                                   # ...and what stands where one was, in the rules


def wording(root: Path = ROOT) -> dict[str, list[tuple[str, ...]]]:
    """(f718) {a data file, from data/: the keys of it whose strings are wording}. A key is a dotted path, * for any one key or
    place in a list, and covers all under it; ** is the whole file."""
    f = root.joinpath(*WORDING)
    if not f.is_file():
        return {}
    from core import yamlio
    raw = (yamlio.safe_load(f.read_text(encoding="utf-8")) or {}).get("wording") or {}
    return {str(rel): [tuple(str(key).split(".")) for key in keys] for rel, keys in raw.items()}


def _covers(key: tuple, path: tuple) -> bool:
    return key == ("**",) or (len(key) == len(path) and all(k in ("*", p) for k, p in zip(key, path)))


def _split(value, keys: list, path: tuple, inside: bool, words: list):
    """A file's value with a mark where each string of wording was, the strings themselves in words with their paths. The shape
    stays in the rules: the keys the engine looks a line up by, how many lines a list holds (a draw is by the count), where in a
    list a line stands, whether a line is empty (code may ask). Numbers stay too, wherever they stand."""
    inside = inside or any(_covers(k, path) for k in keys)
    if isinstance(value, dict):
        return {f"{type(k).__name__} {k}": _split(v, keys, path + (str(k),), inside, words) for k, v in value.items()}
    if isinstance(value, list):
        return [_split(v, keys, path + (str(i),), inside, words) for i, v in enumerate(value)]
    if inside and isinstance(value, str) and value:
        words.append([list(path), value])
        return WORD
    return value if not isinstance(value, str) else f"s {value}"       # no string of the file's own reads as the mark


def _strict(value) -> str:
    """As _h, but a value JSON has no word for is refused: the file is then hashed whole, as rules."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _read(f: Path):
    from core import yamlio
    text = f.read_text(encoding="utf-8")
    return json.loads(text) if f.suffix == ".json" else yamlio.safe_load(text)


def data_hashes(root: Path = ROOT) -> dict[str, str]:
    """The game a recording was made on, in two parts (f718). "data", the rules: every file under data/ (but data/replay, the
    recordings and cases kept to test against, which are not the game, (f459) data/measured, the card's measured speeds, and (f522)
    data/runtime, how this machine runs the model server: both describe a machine and not the game), the model, and the save schema.
    (f572) Not the version: a release that changes no content is the same game; the recording's meta keeps the version, and the
    replay itself catches a change in the code. "words", the wording: the strings data/rules/wording.yaml lists, each a mark in
    the rules. A listed file is read as data, so its comments are in neither; one that cannot be read is rules, whole."""
    import config
    from storage import migrations
    h, w = hashlib.sha256(), hashlib.sha256()
    listed = wording(root)
    for f in sorted((root / "data").rglob("*")):
        rel = f.relative_to(root)
        if f.is_file() and "__pycache__" not in f.parts and rel.parts[:2] not in (("data", "replay"), ("data", "measured"), ("data", "runtime")):
            h.update(rel.as_posix().encode("utf-8") + b"\0")
            keys = listed.get(rel.relative_to("data").as_posix())
            if keys:
                try:
                    words: list = []
                    rest = _split(_read(f), keys, (), False, words)
                    h.update(_strict(rest).encode("utf-8"))
                    w.update(rel.as_posix().encode("utf-8") + b"\0" + _h(words).encode("utf-8"))
                    continue
                except Exception:
                    pass
            b = f.read_bytes()
            h.update(b if b"\0" in b[:8000] else b.replace(b"\r\n", b"\n"))   # (f560) the game, not the checkout's line endings
    h.update(f"\0{config.MODEL}\0{migrations.CURRENT}".encode("utf-8"))
    return {"data": h.hexdigest(), "words": w.hexdigest()}


def data_hash(root: Path = ROOT) -> str:
    """The rules a recording was made on: what a kept recording is held to."""
    return data_hashes(root)["data"]


def words_hash(root: Path = ROOT) -> str:
    """(f718) The wording a recording was made on: kept beside the rules, and held to nothing; a replay shows what a new word changed."""
    return data_hashes(root)["words"]


def wording_problems(listed: dict | None = None, root: Path = ROOT) -> list[str]:
    """(f718) Start-up check of data/rules/wording.yaml: every file listed is there and read as data, and every key holds a string."""
    listed = wording(root) if listed is None else {rel: [tuple(str(k).split(".")) for k in keys] for rel, keys in listed.items()}
    bad = []
    for rel, keys in listed.items():
        f = root / "data" / rel
        if not f.is_file():
            bad.append(f"wording.yaml {rel}: no such data file")
            continue
        try:
            value = _read(f)
        except Exception as e:
            bad.append(f"wording.yaml {rel}: cannot be read as data ({e})")
            continue
        for key in keys:
            words: list = []
            _split(value, [key], (), False, words)
            if not words:
                bad.append(f"wording.yaml {rel}: {'.'.join(key)} holds no words")
    return bad


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

"""The player's saves (f345): every game is its own folder under saves/, and saves/index.json remembers which folders are the
player's games and when each was last played.

Why an index and not every folder: the saves folder also holds what tools and tests make, so a folder is a game only once the game
itself has opened it as one. Games from before this existed are adopted the first time the list is read: the old single save
("main") and every backup New game used to set aside ("main_backup_<time>").

A game's folder name is made once, when it is started, and never changes; the character's own name is read from inside it. Deleting
moves the folder to saves/_deleted/, so a mistake can be undone by moving it back."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from storage.campaign import DB_NAME, SAVES_DIR

INDEX = "index.json"
DELETED = "_deleted"
LEGACY = re.compile(r"^main(_backup_\d{8}_\d{6})?$")


def _index_path(saves_dir: Path) -> Path:
    return Path(saves_dir) / INDEX


def load_index(saves_dir: Path | None = None) -> dict:
    saves_dir = Path(saves_dir or SAVES_DIR)
    try:
        data = json.loads(_index_path(saves_dir).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("saves"), dict):
            return {"last": data.get("last", ""), "saves": data["saves"]}
    except (OSError, ValueError):
        pass
    return {"last": "", "saves": {}}


def _write_index(index: dict, saves_dir: Path) -> None:
    Path(saves_dir).mkdir(parents=True, exist_ok=True)
    tmp = _index_path(saves_dir).with_suffix(".tmp")
    tmp.write_text(json.dumps(index, indent=1), encoding="utf-8")
    tmp.replace(_index_path(saves_dir))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_name(saves_dir: Path | None = None) -> str:
    """A folder name for a new game: when it was begun, made unique."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    base = f"game_{datetime.now():%Y%m%d_%H%M%S}"
    name, n = base, 2
    while (Path(saves_dir) / name).exists() or name in load_index(saves_dir)["saves"]:
        name, n = f"{base}_{n}", n + 1
    return name


def touch(name: str, saves_dir: Path | None = None) -> None:
    """This game is being played now: it is in the index, and it is the one Continue opens."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    index = load_index(saves_dir)
    entry = index["saves"].setdefault(name, {"created": _now()})
    entry["played"] = _now()
    index["last"] = name
    _write_index(index, saves_dir)


def summary(name: str, saves_dir: Path | None = None) -> dict | None:
    """What the home page shows of one game, read straight from its database without opening it as a game: the character, their
    class and level, where they are, the in-game day. None when the folder holds no database; `ready: False` with a reason when it
    cannot be played here (no character yet, or a save from a newer build)."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    from storage import migrations
    path = Path(saves_dir) / name / DB_NAME
    if not path.exists():
        return None
    out = {"name": name, "ready": False, "why": "", "character": "", "class": "", "level": 0, "place": "", "minutes": 0,
           "played": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
    try:
        db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=2)
        try:
            version = int(db.execute("PRAGMA user_version").fetchone()[0])
            rows = dict(db.execute("SELECT key, json FROM kv WHERE key IN ('player', 'campaign')").fetchall())
        finally:
            db.close()
    except sqlite3.Error as e:
        out["why"] = f"the save could not be read ({e})"
        return out
    if version > migrations.CURRENT:
        out["why"] = "made by a newer version of the game: update to play it"
        return out
    try:
        meta = json.loads(rows.get("campaign") or "{}")
        out["minutes"] = int(meta.get("minutes") or 0)
        player = json.loads(rows["player"]) if rows.get("player") else None
    except (ValueError, TypeError):
        player = None
    if not player:
        out["why"] = "no character yet: creation was not finished"
        return out
    c = player.get("character") or {}
    out.update(ready=True, character=c.get("name", ""), level=int(c.get("level") or 1),
               place=player.get("location", ""))
    out["class"] = c.get("custom_class") or ""
    return out


def adopt_legacy(saves_dir: Path | None = None) -> list[str]:
    """Games from before the index: the old single save and the backups New game set aside. Added once; returns what was added."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    index = load_index(saves_dir)
    added = []
    for folder in sorted(Path(saves_dir).glob("*")) if Path(saves_dir).exists() else []:
        if folder.is_dir() and LEGACY.match(folder.name) and folder.name not in index["saves"] and (folder / DB_NAME).exists():
            mtime = datetime.fromtimestamp((folder / DB_NAME).stat().st_mtime).isoformat(timespec="seconds")
            index["saves"][folder.name] = {"created": mtime, "played": mtime}
            added.append(folder.name)
    if added:
        if not index["last"] and "main" in index["saves"]:
            index["last"] = "main"
        _write_index(index, saves_dir)
    return added


def list_saves(saves_dir: Path | None = None) -> list[dict]:
    """Every game, the one played last first; folders that have gone missing are dropped from the index."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    adopt_legacy(saves_dir)
    index = load_index(saves_dir)
    found, gone = [], []
    for name, entry in index["saves"].items():
        s = summary(name, saves_dir)
        if s is None:
            gone.append(name)
            continue
        s["played"] = entry.get("played") or s["played"]
        found.append(s)
    if gone:
        for name in gone:
            index["saves"].pop(name, None)
        if index["last"] in gone:
            index["last"] = ""
        _write_index(index, saves_dir)
    found.sort(key=lambda s: s["played"], reverse=True)
    return found


def last(saves_dir: Path | None = None) -> dict | None:
    """The game Continue opens: the one played last that can be played."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    saves = list_saves(saves_dir)
    want = load_index(saves_dir)["last"]
    return next((s for s in saves if s["name"] == want and s["ready"]), None) or next((s for s in saves if s["ready"]), None)


def discard(name: str, saves_dir: Path | None = None) -> bool:
    """Forget a game left before it had a character (Main menu during creation): its folder goes and so does its place in the index.
    A game with a character is never discarded - delete() keeps a copy of those. Returns whether it was."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    s = summary(name, saves_dir)
    if s is not None and s["ready"]:
        return False
    shutil.rmtree(Path(saves_dir) / name, ignore_errors=True)
    index = load_index(saves_dir)
    index["saves"].pop(name, None)
    if index["last"] == name:
        index["last"] = ""
    _write_index(index, saves_dir)
    return True


def delete(name: str, saves_dir: Path | None = None) -> Path | None:
    """Move a game to saves/_deleted/ and take it out of the index. Returns where it went, or None when there was nothing to move."""
    saves_dir = Path(saves_dir or SAVES_DIR)
    src = Path(saves_dir) / name
    index = load_index(saves_dir)
    if name not in index["saves"] or not src.exists():
        return None
    dest_dir = Path(saves_dir) / DELETED
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"
    shutil.move(str(src), str(dest))
    index["saves"].pop(name, None)
    if index["last"] == name:
        index["last"] = ""
    _write_index(index, saves_dir)
    return dest

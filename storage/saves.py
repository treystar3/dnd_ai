"""The player's saves (f345): every game is its own folder under saves/, and the folder itself says it is the player's game, by a
small file beside its database (MARK: when it was begun and last played) written when the game opens it as one. saves/index.json is
a cache of the marks, when each game was played and which was played last, rebuilt from them when it is missing or cannot be read.

Why a mark and not every folder: the saves folder also holds what tools and tests make, so a folder is a game only once the game
itself has opened it as one. Why in the folder and not the index: a game moved back out of saves/_deleted/, or copied in from
another install, is a game whatever the index holds. Games from before the marks are marked the first time the list is read: the
ones an index of that time names, the old single save ("main") and every backup New game used to set aside ("main_backup_<time>").

A game's folder name is made once, when it is started, and never changes; the character's own name is read from inside it. Deleting
moves the folder to saves/_deleted/, so a mistake can be undone by moving it back.

A tool's or a test's save (scratch, drop) carries a mark of its own (SCRATCH), and nothing else is ever cleared by one: not a game,
not a name the game gives its games, not a folder outside saves/, and not, when the name was typed on a tool's command line, a
folder no tool marked. whose() reads the two marks, and every reader here asks it.

The folder is storage.campaign.SAVES_DIR, read at each call (folder_of): a test that points it elsewhere finds everything there."""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from storage import campaign
from storage.campaign import DB_NAME

INDEX = "index.json"
DELETED = "_deleted"
LEGACY = re.compile(r"^main(_backup_\d{8}_\d{6})?$")
MARK = "game.json"
MARKED = "marked"                                   # (f741) the older games are marked: from here the index is only a cache
# (f742) discard() erases on no character, or no database, alone
READY, NO_CHARACTER, UNREADABLE, NEWER = "ready", "no_character", "unreadable", "newer"
SCRATCH = "scratch.json"                            # (f743) a tool's own save says so: only such a folder is ever cleared by one
GAME, TOOL = "game", "tool"                         # (f741) whose a folder is: the player's game, or a tool's own save
GAME_PREFIX = "game_"                               # (f743) new_name()'s folders begin so, and GAME_NAME reads them by the same
GAME_NAME = re.compile(rf"{LEGACY.pattern}|^{GAME_PREFIX}\d{{8}}_\d{{6}}", re.IGNORECASE)   # (f743) what the game names its games
PLAIN = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?")


class Refused(SystemExit):
    """(f743) A tool's save that may not be cleared, or could not be: the message names the folder, and no tool goes on past it."""


def folder_of(saves_dir: Path | None = None) -> Path:
    """(f741) The saves folder: the one given, else the one source, storage.campaign.SAVES_DIR, read now."""
    return Path(saves_dir or campaign.SAVES_DIR)


def whose(folder: Path) -> str:
    """(f741) Whose a folder is, the one answer every reader asks: GAME when it carries the game's mark (with a database or not; a mark
    that cannot be read still marks), else TOOL when it carries the tools' mark, else "" (no mark, or no folder)."""
    if (Path(folder) / MARK).exists():
        return GAME
    return TOOL if (Path(folder) / SCRATCH).is_file() else ""


def _index_path(saves_dir: Path) -> Path:
    return Path(saves_dir) / INDEX


def _read_index(saves_dir: Path) -> dict | None:
    """The index as it is on disk, or None when it is missing or cannot be read."""
    try:
        data = json.loads(_index_path(saves_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("saves"), dict) else None


def _write_index(index: dict, saves_dir: Path) -> None:
    Path(saves_dir).mkdir(parents=True, exist_ok=True)
    tmp = Path(saves_dir) / f"{INDEX}.{os.getpid()}.tmp"         # (f741) a reader may write too: two processes never share one
    tmp.write_text(json.dumps({"last": index["last"], "saves": index["saves"], MARKED: True}, indent=1), encoding="utf-8")
    tmp.replace(_index_path(saves_dir))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _db_time(folder: Path) -> str:
    return datetime.fromtimestamp((folder / DB_NAME).stat().st_mtime).isoformat(timespec="seconds")


def _mark(folder: Path) -> dict:
    """What a game's folder says of itself (created, played), {} when its mark cannot be read."""
    try:
        data = json.loads((folder / MARK).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_mark(folder: Path, created: str, played: str) -> None:
    (folder / MARK).write_text(json.dumps({"created": created, "played": played}), encoding="utf-8")


def _games(saves_dir: Path) -> dict[str, dict]:
    """Every game on disk, each with its mark: the direct children of saves/ that are games and hold a database, never the deleted folder."""
    root = Path(saves_dir)
    if not root.is_dir():
        return {}
    return {f.name: _mark(f) for f in sorted(root.iterdir())
            if f.is_dir() and f.name != DELETED and whose(f) == GAME and (f / DB_NAME).exists()}


def load_index(saves_dir: Path | None = None) -> dict:
    """When each game was played and which was played last: the index, kept to the games' own marks. One that is missing or cannot
    be read is rebuilt from them, never read as empty; a game it does not name is added, a name that is no game is dropped. Not a
    pure read: it marks the games from before the marks and rewrites index.json when it differs from them."""
    saves_dir = folder_of(saves_dir)
    adopted = adopt_legacy(saves_dir)
    data = _read_index(saves_dir)
    cached = data["saves"] if data else {}
    index = {"last": str(data.get("last") or "") if data else "", "saves": {}}
    for name, mark in _games(saves_dir).items():
        entry = cached.get(name) if isinstance(cached.get(name), dict) else {}
        when = _db_time(Path(saves_dir) / name)
        index["saves"][name] = {"created": entry.get("created") or mark.get("created") or when,
                                "played": max(str(entry.get("played") or ""), str(mark.get("played") or "")) or when}
    if index["last"] not in index["saves"]:
        played = index["saves"]
        index["last"] = "main" if "main" in adopted else max(played, key=lambda n: played[n]["played"], default="")
    if (index["saves"] or data is not None) and (data is None or data.get(MARKED) is not True
                                                 or data.get("last") != index["last"] or data["saves"] != index["saves"]):
        _write_index(index, saves_dir)
    return index


def new_name(saves_dir: Path | None = None) -> str:
    """A folder name for a new game: when it was begun, made unique."""
    saves_dir = folder_of(saves_dir)
    base = f"{GAME_PREFIX}{datetime.now():%Y%m%d_%H%M%S}"
    name, n = base, 2
    while (Path(saves_dir) / name).exists() or name in load_index(saves_dir)["saves"]:
        name, n = f"{base}_{n}", n + 1
    return name


def touch(name: str, saves_dir: Path | None = None) -> None:
    """This game is being played now: its folder says it is the player's game, it is in the index, and it is the one Continue opens."""
    saves_dir = folder_of(saves_dir)
    folder, now = Path(saves_dir) / name, _now()
    index = load_index(saves_dir)
    entry = index["saves"].setdefault(name, {"created": now})
    entry["played"] = now
    if folder.is_dir():
        _write_mark(folder, entry["created"], now)
    index["last"] = name
    _write_index(index, saves_dir)


def summary(name: str, saves_dir: Path | None = None) -> dict | None:
    """What the home page shows of one game, read straight from its database without opening it as a game: the character, their
    class and level, where they are, the in-game day. None when the folder holds no database; `ready: False` with a reason when it
    cannot be played here, and `state` says which: no character yet, a save that cannot be read, or one from a newer build."""
    saves_dir = folder_of(saves_dir)
    from storage import migrations, playerstable
    path = Path(saves_dir) / name / DB_NAME
    if not path.exists():
        return None
    out = {"name": name, "ready": False, "state": UNREADABLE, "why": "", "character": "", "class": "", "level": 0, "place": "",
           "minutes": 0, "played": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}
    try:
        db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=2)
        try:
            version = int(db.execute("PRAGMA user_version").fetchone()[0])
            rows = dict(db.execute("SELECT key, json FROM kv WHERE key IN ('player', 'campaign')").fetchall())
            if db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (playerstable.TABLE,)).fetchone():
                found = db.execute(f'SELECT json FROM "{playerstable.TABLE}" WHERE character_id = ?', (playerstable.FIRST,)).fetchone()
                if found:                                 # (f640) the players table; a save not opened since has the row above
                    rows[playerstable.KEY] = found[0]
        finally:
            db.close()
    except sqlite3.Error as e:
        out["why"] = f"the save could not be read ({e})"
        return out
    if version > migrations.CURRENT:
        out["why"], out["state"] = "made by a newer version of the game: update to play it", NEWER
        return out
    try:
        meta = json.loads(rows.get("campaign") or "{}")
        out["minutes"] = int(meta.get("minutes") or 0)
        player = json.loads(rows["player"]) if rows.get("player") else None
    except (ValueError, TypeError, AttributeError) as e:
        out["why"] = f"the save could not be read ({e})"   # (f742) a character's row that does not read is no proof there is none
        return out
    if not player:
        out["why"], out["state"] = "no character yet: creation was not finished", NO_CHARACTER
        return out
    c = player.get("character") or {}
    out.update(ready=True, state=READY, character=c.get("name", ""), level=int(c.get("level") or 1),
               place=player.get("location", ""))
    out["class"] = c.get("custom_class") or ""
    return out


def adopt_legacy(saves_dir: Path | None = None) -> list[str]:
    """Games from before the marks: the names an index written before them lists, the old single save and the backups New game set
    aside. Each is marked once: the index written next says so, and from then on a folder is a game by its mark alone. Returns what
    was marked."""
    saves_dir = folder_of(saves_dir)
    data = _read_index(saves_dir)
    if data and data.get(MARKED) is True:
        return []
    old = data["saves"] if data else {}
    legacy = [f.name for f in sorted(Path(saves_dir).glob("*")) if f.is_dir() and LEGACY.match(f.name)] if Path(saves_dir).exists() else []
    added = []
    for name in dict.fromkeys([*old, *legacy]):
        folder = Path(saves_dir) / name
        if (folder / DB_NAME).exists() and not whose(folder):
            entry = old.get(name) if isinstance(old.get(name), dict) else {}
            when = _db_time(folder)
            _write_mark(folder, entry.get("created") or when, entry.get("played") or when)
            added.append(name)
    return added


def list_saves(saves_dir: Path | None = None) -> list[dict]:
    """Every game, the one played last first: every folder that says it is one, whatever the index held."""
    saves_dir = folder_of(saves_dir)
    found = []
    for name, entry in load_index(saves_dir)["saves"].items():
        s = summary(name, saves_dir)
        if s is not None:
            s["played"] = entry.get("played") or s["played"]
            found.append(s)
    found.sort(key=lambda s: s["played"], reverse=True)
    return found


def last(saves_dir: Path | None = None) -> dict | None:
    """The game Continue opens: the one played last that can be played."""
    saves_dir = folder_of(saves_dir)
    saves = list_saves(saves_dir)
    want = load_index(saves_dir)["last"]
    return next((s for s in saves if s["name"] == want and s["ready"]), None) or next((s for s in saves if s["ready"]), None)


def discard(name: str, saves_dir: Path | None = None) -> bool:
    """Forget a game left before it had a character (any way out of creation): its folder goes and so does its place in the index,
    but only when its save says plainly that it has no character. A folder marked as the player's game is never touched, a game with
    a character never discarded, and a save that cannot be read here (damaged, or from a newer build) is moved aside as delete()
    moves it. Returns whether it was discarded."""
    saves_dir = folder_of(saves_dir)
    folder = Path(saves_dir) / name
    if whose(folder) == GAME:
        return False
    s = summary(name, saves_dir)
    gone = s is None or s["state"] == NO_CHARACTER
    if gone:
        shutil.rmtree(folder, ignore_errors=True)
    elif s["state"] == READY:
        return False
    else:
        try:
            folder.rename(_set_aside(name, saves_dir))          # (f742) it may hold a character: kept, as delete() keeps a game
        except OSError:
            return False
    index = load_index(saves_dir)
    index["saves"].pop(name, None)
    if index["last"] == name:
        index["last"] = ""
    _write_index(index, saves_dir)
    return gone


def _set_aside(name: str, saves_dir: Path) -> Path:
    """Where a game goes when it is moved aside: saves/_deleted/, under its name and the time."""
    dest_dir = Path(saves_dir) / DELETED
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}"


def delete(name: str, saves_dir: Path | None = None) -> Path | None:
    """Move a game to saves/_deleted/ and take it out of the index. Returns where it went, or None when there was nothing to move."""
    saves_dir = folder_of(saves_dir)
    src = Path(saves_dir) / name
    index = load_index(saves_dir)
    if name not in index["saves"] or not src.exists():
        return None
    dest = _set_aside(name, saves_dir)
    shutil.move(str(src), str(dest))
    index["saves"].pop(name, None)
    if index["last"] == name:
        index["last"] = ""
    _write_index(index, saves_dir)
    return dest


def _never_tools(name: str, saves_dir: Path) -> str:
    """Why saves/<name> can never be a tool's save, or "" when it can. Read only: the index is read as it is on disk, never rebuilt."""
    if not isinstance(name, str) or not PLAIN.fullmatch(name) or ".." in name:
        return f"The save name \"{name}\" is not a plain folder name inside {Path(saves_dir).as_posix()}: nothing was removed."
    folder = (Path(saves_dir) / name).as_posix()
    if name.casefold() == DELETED:
        return f"{folder} holds the deleted games: a tool never clears it."
    if GAME_NAME.match(name):
        return f"{folder} is a name the game gives its own games: a tool never clears it. Give the tool another save name."
    if whose(Path(saves_dir) / name) == GAME:
        return f"{folder} is one of the player's games: a tool never clears it. Give the tool another save name."
    data = _read_index(saves_dir)
    if data and name.casefold() in {str(n).casefold() for n in data["saves"]}:
        return f"{folder} is on the Load page: a tool never clears it. Give the tool another save name."
    if (Path(saves_dir) / name).exists() and not (Path(saves_dir) / name).is_dir():
        return f"{folder} is a file, not a save folder: nothing was removed."
    return ""


def _mark_scratch(folder: Path) -> None:
    (folder / SCRATCH).write_text(json.dumps({"made": _now()}), encoding="utf-8")


def _clear(folder: Path) -> None:
    """A tool's folder removed, or Refused when it is still there afterwards: on Windows rmtree leaves a folder with a file held open
    in silence. One left behind keeps the tools' mark, so the next run may clear it."""
    if not folder.exists():
        return
    shutil.rmtree(folder, ignore_errors=True)
    if folder.exists():
        try:
            _mark_scratch(folder)
        except OSError:
            pass
        raise Refused(f"{folder.as_posix()} could not be cleared: something in it is still open, most likely the game or another "
                      "tool's run. Close it and run again.")


def scratch(name: str, typed: bool = False, saves_dir: Path | None = None) -> Path:
    """(f743) An empty save of a tool's own, the one way a tool or a test gets one: saves/<name> made anew, with the mark that says a
    tool made it. Refused, with a line naming the folder, for a name that can never be a tool's (no plain folder name in saves/, the
    deleted games, a name the game gives its games, a game's folder, a name the Load page lists); for a folder already there that no
    tool marked when the name was typed on a command line (`typed`: a tool's --save), while one a tool or a test names in its own
    code is taken as the tool's own; and when the folder is still there after it was cleared. Returns it."""
    saves_dir = folder_of(saves_dir)
    why = _never_tools(name, saves_dir)
    if why:
        raise Refused(why)
    folder = saves_dir / name
    if typed and folder.exists() and whose(folder) != TOOL:
        raise Refused(f"{folder.as_posix()} is already there and no tool marked it as its own, so it is left as it is. Remove it by "
                      "hand if it is not wanted, or give the tool another save name.")
    _clear(folder)
    folder.mkdir(parents=True)
    _mark_scratch(folder)
    return folder


def drop(name: str, saves_dir: Path | None = None) -> bool:
    """(f743) A tool's own save removed at the end of its run, the one way a tool removes one: only a folder that carries the tools'
    mark, never a game. Returns whether one was removed; Refused when it is still there afterwards, unless the run is already going
    down with an error (a drop in a `finally`): then that error goes on with its own traceback, and carries the line as a note."""
    crash = sys.exc_info()[1]                         # (f743) a Refused raised now would take the crash's place and hide its traceback
    saves_dir = folder_of(saves_dir)
    if _never_tools(name, saves_dir) or whose(saves_dir / name) != TOOL:
        return False
    try:
        _clear(saves_dir / name)
    except Refused as e:
        if crash is None or isinstance(crash, SystemExit):
            raise
        crash.add_note(str(e))
        return False
    return True

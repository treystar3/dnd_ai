"""The game's own check, run by `python main.py --check` and by the built game's `Meravia.exe --check`: the startup check of the data
(engine/data_check.py), the world as written, the traits, every file the window serves and, in a built game, the window library. It
starts no model server and takes no lock. What it found is written anew to logs/selfcheck.log beside the exe, and the answer is the exit
code: 0 when nothing is wrong, 1 otherwise. A built game has no console, so the file and the code are the signal. build_exe.bat runs it
from source before it builds and on the built game after."""
from __future__ import annotations

import time
import traceback
from pathlib import Path

from core import paths


def log_path() -> Path:
    """logs/selfcheck.log beside the exe (the project folder from source), asked at the call."""
    return Path(paths.APP) / "logs" / "selfcheck.log"


def _data() -> list[str]:
    from engine import data_check
    return data_check.check()


def _world() -> list[str]:
    from world.loader import WorldError, authored
    try:
        authored()
    except WorldError as e:
        return [str(e)]
    return []


def _traits() -> list[str]:
    from npc.traits import load_traits
    load_traits()
    return []


def _page() -> list[str]:
    """Every file the window serves (ui/gui/server.py: the page and STATIC, under WEB), read as the server reads it."""
    from ui.gui import server
    out = []
    for name in ["index.html"] + [p.lstrip("/") for p in server.STATIC]:
        f = Path(server.WEB) / name
        try:
            if name == "index.html":
                f.read_text(encoding="utf-8")                          # the server fills its token into it as text
            else:
                f.read_bytes()
        except (OSError, UnicodeDecodeError) as e:
            out.append(f"{name}: {e}")
    return out


def _window() -> list[str]:
    import webview                                                    # noqa: F401 (the built game's window; from source the browser stands in)
    return []


def parts() -> list[tuple[str, object]]:
    """What is checked, in order: its name in the log, and the function that answers its problems."""
    out = [("the data check", _data), ("the world as written", _world), ("the traits", _traits), ("the window's files", _page)]
    if paths.FROZEN:
        out.append(("the window library", _window))
    return out


def run(log: Path | None = None, say=None) -> int:
    """Every part checked and what was found written to the log (anew, so it does not grow), and handed to say when one is given: 0 when
    nothing is wrong, else 1. A part that raises is a problem of that part, its trace kept in the log."""
    from core.version import VERSION
    lines = [f"Meravia {VERSION}: its own check, {time.strftime('%Y-%m-%d %H:%M:%S')}, {'a built game' if paths.FROZEN else 'run from source'}"]
    failed = False
    for name, fn in parts():
        trace = ""
        try:
            found = list(fn())
        except Exception as e:
            found, trace = [f"{type(e).__name__}: {e}"], traceback.format_exc()
        failed = failed or bool(found)
        lines.append(f"{name}: " + ("ok" if not found else f"{len(found)} problem{'' if len(found) == 1 else 's'}"))
        lines += [f"  - {p}" for p in found]
        lines += ["    " + t for t in trace.rstrip().splitlines()]
    lines.append("FAILED" if failed else "PASSED")
    text = "\n".join(lines) + "\n"
    path = log_path() if log is None else Path(log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if say is not None:
        say(text.rstrip("\n"))
    return 1 if failed else 0

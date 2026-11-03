"""(f449) Where a fault goes when the game goes on without it.

The owner's playthrough of 2026-11-01 ended with "Something went wrong and the game has to stop": a model call failed in a way the
gateway did not count as a failed try, and the error climbed out of the turn, through main.py, to the window. The window showed the
details; nothing wrote them down, so the logs the owner sent had no trace of it. Now a turn that raises anything is rolled back and
the player reads a line in the narrator's words (engine/failures.py); the fault itself is written here, logs/crash.log, with its
traceback and where it happened, so the next upload carries it. main.py writes here too for the faults that still end the game (before
a campaign is open, on the home page, during creation). The file is plain text, newest last, trimmed to the last CRASH_KEEP entries so
a long campaign never grows it without bound. SESSION holds this process's entries for the tests and the night tools."""
from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
SEP = "\n" + "-" * 78 + "\n"
KEEP = int(getattr(config, "CRASH_KEEP", 50))
SESSION: list[dict] = []


def path() -> Path:
    return ROOT / getattr(config, "CRASH_LOG_PATH", "logs/crash.log")


def record(exc: BaseException, where: str, **context) -> dict:
    """Write one fault: when, where in the game, what the player had typed and where they stood, the exception and its traceback.
    Returns the entry (also kept in SESSION). Never raises: a log that cannot be written must not become a second fault."""
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "where": where,
             "error": f"{type(exc).__name__}: {exc}"[:300], **{k: v for k, v in context.items() if v not in (None, "")}}
    SESSION.append(entry)
    del SESSION[:-KEEP]
    text = (f"{entry['time']}  {where}: {entry['error']}\n"
            + "".join(f"  {k}: {v}\n" for k, v in context.items() if v not in (None, ""))
            + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    try:
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        entries = [e for e in old.split(SEP) if e.strip()] + [text.rstrip("\n")]
        p.write_text(SEP.join(entries[-KEEP:]) + "\n", encoding="utf-8")
    except OSError:
        pass
    return entry


def last() -> dict | None:
    return SESSION[-1] if SESSION else None

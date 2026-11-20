"""(f449) Where a fault goes when the game goes on without it.

The owner's playthrough of 2026-11-01 ended with "Something went wrong and the game has to stop": a model call failed in a way the
gateway did not count as a failed try, and the error climbed out of the turn, through main.py, to the window. The window showed the
details; nothing wrote them down, so the logs the owner sent had no trace of it. Now a turn that raises anything is rolled back and
the player reads a line in the narrator's words (engine/failures.py); the fault itself is written here, logs/crash.log, with its
traceback and where it happened, so the next upload carries it. main.py writes here too for the faults that still end the game (before
a campaign is open, on the home page, during creation). The file is plain text, newest last, trimmed to the last CRASH_KEEP entries so
a long campaign never grows it without bound. SESSION holds this process's entries for the tests and the night tools.

carried() is for work the game goes on without when it fails (work no operation rolls back, or where a result already taken must not
be lost): the fault is written here once per place and kind a session, and counted after that in CARRIED; as the session ends its
count, settle() writes the faults met more than once with their counts. Inside an operation the rule is to let the fault roll the
operation back instead (f449). run_every() runs the stages of a close each whatever the one before it did: the first error is raised
once the last has run, and a later one is carried."""
from __future__ import annotations

import contextlib
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import config
from core import paths
from core.interrupts import Interrupt
from engine import actor

SEP = "\n" + "-" * 78 + "\n"
KEEP = int(getattr(config, "CRASH_KEEP", 50))
SESSION: list[dict] = []
CARRIED: dict[tuple[str, str], tuple[int, bool]] = {}   # (where, error type): (times carried this session, quiet), oldest let go past KEEP
_LOCK = threading.Lock()


def path() -> Path:
    """crash.log: config.CRASH_LOG_PATH placed by core.paths, beside the exe in a built game (f777)."""
    return paths.written(getattr(config, "CRASH_LOG_PATH", "logs/crash.log"))


def record(exc: BaseException, where: str, **context) -> dict:
    """Write one fault: when, where in the game, what the player had typed and where they stood, the exception and its traceback.
    Returns the entry (also kept in SESSION). Never raises: a log that cannot be written must not become a second fault."""
    context = {"actor": actor.who(), **context}            # (f629) who acted, when someone did: the bound actor
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "where": where,
             "error": f"{type(exc).__name__}: {exc}"[:300], **{k: v for k, v in context.items() if v not in (None, "")}}
    SESSION.append(entry)
    del SESSION[:-KEEP]
    text = (f"{entry['time']}  {where}: {entry['error']}\n"
            + "".join(f"  {k}: {v}\n" for k, v in context.items() if v not in (None, ""))
            + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    _append(text, path())
    return entry


@contextlib.contextmanager
def carried(where: str, quiet: type[BaseException] | tuple[type[BaseException], ...] = (), **context):
    """The work inside may fail and the game goes on. An Interrupt goes on up (a cancel, a replay that parted: never a fault); a type
    in `quiet`, a failure already filed elsewhere (an LLMError the gateway logged, a log that refused a write), is only counted; any
    other Exception is recorded here once per (where, error type) a session and counted after that. One `where` names one subject (a
    place and what it was working on), so a second subject that fails the same way is written down too. Never raises a fault of its
    own; a `quiet` that is not an exception type or a tuple of them is refused as the block is entered, before the work runs."""
    quiet = (quiet,) if isinstance(quiet, type) else quiet
    if not (isinstance(quiet, tuple) and all(isinstance(q, type) and issubclass(q, BaseException) for q in quiet)):
        raise TypeError(f"carried({where!r}): quiet takes an exception type or a tuple of them, not {quiet!r}")
    try:
        yield
    except Interrupt:
        raise
    except Exception as e:
        if not _first(e, where, quiet):
            return
        try:
            record(e, where, **context)
        except Exception:                              # (f781) a fault in writing a fault down has nowhere to go: it was counted
            pass


def run_every(where: str, *stages: tuple[str, Callable[[], object]]) -> None:
    """(f783) Run each stage, a (name, function) pair, whatever the one before it did: a close, where a stage that stops the rest
    leaves the next campaign what the rest would have put back. The first error is raised once the last stage has run, a note on it
    naming "<where>: <its name>"; a stage that fails after it is carried, written down under that name, so none is lost and the one
    raised is the one that came first. An Interrupt or what is no Exception (Ctrl+C) in a later stage still lets the rest run, then
    goes on up in the first error's place, which it holds as its context."""
    for i, (name, stage) in enumerate(stages):
        try:
            stage()
        except BaseException as e:
            e.add_note(f"{where}: {name}")
            _rest(where, stages[i + 1:])
            raise


def _rest(where: str, stages: tuple) -> None:
    """(f783) The stages after one that failed: each carried, and one that carried lets go (an Interrupt, Ctrl+C) runs the rest first."""
    for i, (name, stage) in enumerate(stages):
        try:
            with carried(f"{where}: {name}"):
                stage()
        except BaseException as e:
            e.add_note(f"{where}: {name}")
            _rest(where, stages[i + 1:])
            raise


def _first(e: Exception, where: str, quiet: tuple) -> bool:
    """Count one carried fault; True when it is to be written down: the first of its (where, type) this session, and not quiet."""
    key, hushed = (where, type(e).__name__), isinstance(e, quiet)
    with _LOCK:
        seen, _ = CARRIED.pop(key, (0, hushed))
        CARRIED[key] = (seen + 1, hushed)              # the newest last, so the cap lets the oldest go
        while len(CARRIED) > KEEP:
            del CARRIED[next(iter(CARRIED))]
    return not seen and not hushed


def settle() -> None:
    """The session ends its count (a campaign opening or closing; engine/owned.py): each fault written down and met again since is one
    entry with its count, so a fault carried five hundred times is not read as one. A quiet one stays out, as it stayed out of the log.
    Then the count starts again. Never raises."""
    with _LOCK:
        again = [(where, kind, n) for (where, kind), (n, hushed) in CARRIED.items() if n > 1 and not hushed]
        CARRIED.clear()
    if again:                                          # (f781) the count nobody would otherwise read
        note("faults carried again after they were written down, this session",
             "".join(f"\n  {where} ({kind}): {n} times" for where, kind, n in again))


def note(where: str, text: str, to: Path | None = None) -> None:
    """(f522) One entry with no exception (a model server that ended, and the tail of what it said), in record()'s form, so the file
    is counted and trimmed entry by entry. `to` is the file (the runtime's logs folder); crash.log by default. Never raises."""
    _append(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}  {where}: {text}", to or path())


def _append(text: str, p: Path) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        entries = [e for e in old.split(SEP) if e.strip()] + [text.rstrip("\n")]
        p.write_text(SEP.join(entries[-KEEP:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def last() -> dict | None:
    return SESSION[-1] if SESSION else None

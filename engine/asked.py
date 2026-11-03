"""(f485, Bundle D R1: read, ask, commit) A model call an operation needs is asked outside the operation's transaction.

The executor runs an operation that may ask (scenes/world.py asked_operation) as a restartable attempt. When its body reaches a call of
a task named in data/rules/budget.yaml `asked_outside`, the gateway does not call the model inside the transaction: it raises
NeedAnswer, the operation rolls back as if it had never begun (nothing written, nothing shown, not counted as a failure), the executor
makes the call with no operation open, and the operation runs again from its start: the same id, the same dice (the streams put back as
they were), the same scene. At the same point the body is now given the answer, or the same failure (the site's own fallback then
stands, as it always did), and it goes on to the next call or to its commit. So the save never waits on the model, a reply that fails
leaves nothing behind, and nothing the commit does calls the model.

The answers are kept in the order they were asked, each with the hash of its request. Running again, the body must ask the same thing
at the same point: if a request differs, what the body read moved between the attempts (another writer, the background resident
thread), and the operation stops as a fault (Drift) with no second call: the line is not taken, as a failed reply is not."""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_TASKS: frozenset | None = None


def tasks() -> frozenset:
    """The tasks asked outside the operation that needs them (budget.yaml asked_outside): a family moves out by being named here."""
    global _TASKS
    if _TASKS is None:
        B = yaml.safe_load((ROOT / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8")) or {}
        _TASKS = frozenset(B.get("asked_outside") or [])
    return _TASKS


def most() -> int:
    """(f489) The most calls one operation may ask outside it (budget.yaml asked_max)."""
    B = yaml.safe_load((ROOT / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8")) or {}
    return int(B.get("asked_max", 48))


class NeedAnswer(BaseException):
    """The body reached a call that is asked outside: roll back, ask, run again. A BaseException, so no `except Exception` a body keeps
    for its own fallbacks can mistake it for a failure and go on."""

    def __init__(self, key: str, ask):
        super().__init__("asked outside the operation")
        self.key, self.ask = key, ask


class Drift(BaseException):
    """Running again, the body asked something other than what was asked for it: what it read moved between the attempts. The executor
    takes it as the game's own fault (logs/crash.log): the operation stands down, the line not taken."""


class _Serving:
    """The answers of one restartable operation, in the order asked, and how far the attempt now running has come."""

    def __init__(self):
        self.answers: list[tuple[str, object, BaseException | None]] = []
        self.at = 0


_SERVING: _Serving | None = None


def serving() -> _Serving | None:
    return _SERVING


def begin(s: _Serving | None) -> None:
    global _SERVING
    _SERVING = s
    if s is not None:
        s.at = 0


def end() -> None:
    begin(None)


def key(task: str, system: str, user_text: str, schema_name: str) -> str:
    return hashlib.sha256("\x1f".join((task, system, user_text, schema_name)).encode("utf-8")).hexdigest()[:20]


def call(task: str, k: str, ask):
    """For the gateway, inside a restartable operation: the answer this point was given (or its failure, raised again). Reached for the
    first time, a task asked outside raises NeedAnswer (the executor makes `ask()` with no operation open); any other task is made here,
    inside, as it always was, and kept, so running the operation again never asks the model twice for one call."""
    global _SERVING
    s = _SERVING
    if s.at < len(s.answers):
        want, result, error = s.answers[s.at]
        if want != k:
            raise Drift(f"{task}: the request at this point differs from the one asked ({want} -> {k}); what the operation read moved")
        s.at += 1
        if error is not None:
            raise error
        return result.model_copy(deep=True) if hasattr(result, "model_copy") else result
    if task in tasks():
        raise NeedAnswer(k, ask)
    from core.interrupts import Interrupt
    _SERVING = None                                      # made inside, as before: the call itself is no attempt's to serve
    try:
        result, error = ask(), None
    except BaseException as e:
        result, error = None, e
    finally:
        _SERVING = s
    if isinstance(error, (NeedAnswer, Drift, Interrupt)) or not isinstance(error, (Exception, type(None))):
        raise error                                      # an Interrupt and the executor's own signals pass straight through
    s.answers.append((k, result, error))
    s.at += 1
    if error is not None:
        raise error
    return result.model_copy(deep=True) if hasattr(result, "model_copy") else result


def wanted(task: str) -> bool:
    """Whether this call, now, goes through the operation's answers: any task, inside a restartable operation."""
    return _SERVING is not None


def problems(known: set[str]) -> list[str]:
    """The startup check: every task named to be asked outside is a task the code asks for."""
    return [f"budget.yaml asked_outside: '{t}' is no task the code asks for" for t in sorted(tasks() - set(known))]

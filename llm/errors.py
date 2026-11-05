"""(f514) The model's errors, in a module that carries no runtime.

Importing this starts nothing and imports neither the model's client nor its transport, so anything that only needs to catch a model
failure (engine/budget.py, main.py) can import it without pulling the server's client in behind it. The gateway re-exports LLMError,
so every `from llm.gateway import LLMError` keeps catching the same class.

- LLMError: a call that gave up (every try failed, or the turn's budget refused it). Callers get this, never raw text.
- Failure: what a model source raises for one try, by kind; the gateway decides what each kind does (f516).
- Cancelled: a call stopped on purpose (a session closing, the turn taking its slot back; f523). It is an Interrupt
  (core/interrupts.py), so every catch that lets an Interrupt through lets it through: never a failed try, never a fallback.
"""

from core.interrupts import Interrupt

KINDS = ("loading", "too_big", "invalid", "server", "unreachable", "deadline", "cancelled")


class LLMError(Exception):
    pass


class Failure(Exception):
    """One try's failure from a model source: kind is one of KINDS, detail is for the logs, legacy is the (type, text) of the error the
    old client raised, kept so a recording made before the switch reads the same."""

    def __init__(self, kind: str, detail: str = "", legacy: tuple | None = None):
        if kind not in KINDS:
            raise ValueError(f"no such failure kind: {kind!r} (one of {', '.join(KINDS)})")
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind, self.detail, self.legacy = kind, detail, legacy


class Cancelled(Interrupt):
    """A call stopped on purpose, not a failure of the model's."""


class NoServer(ConnectionError):
    """(f518) There is no model server in this process at all (MERAVIA_NO_SERVER: the test suite, the recording makers, a replay): a
    call with nothing installed fails at once as unreachable (llm/backend.py failure_of), never as the server's failure, and builds and
    starts nothing. A ConnectionError, so whatever catches a missing server catches it; a ConnectionError raised on purpose (the
    recording scripts' planted failures) is still the server's (design_plan.md:665)."""

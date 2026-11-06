"""(f523) The model worker: who may use the chat server's two slots when. It carries no call itself: every call is still made on its
caller's own thread (so everything that reads the calling thread, the turn's budget, the gateway's task, the open operation, the
recorder's serving, reads it exactly as before); the worker only decides when a background call may start, and takes the card back
from one when the turn needs it.

Lanes, declared by the caller (llm/backend.py lane): foreground by default (the turn, the first entry, creation's own calls, the
validators); background, declared by the two thread bodies that run beside the player, npc/backfill.py's run() and
character/creation.py's _run(); input, the night bot's line, which never takes the card from anyone.

- A foreground call is never held: it is sent at once, and any background call in flight is cancelled (its connection closed, so
  llama-server frees the slot within about a second) unless it has been cancelled max_cancels times already or the turn is waiting on
  it. The cancelled call is not a failure: it is sent again, below the recorder, once no foreground call has run for
  resume_idle_seconds, so a recording keeps one row for it and its caller never knows.
- A background call waits while a foreground call runs, and for resume_idle_seconds after the last one ended, so it starts in the
  player's reading time, not between two calls of one turn.
- promote(thread): the turn waits on that background job (npc/backfill.py settle and collect, creation's result()): its call is never
  cancelled again and starts without the idle wait.
- After max_cancels, a call runs beside a turn rather than starve (a fast typist and a 47-second populate_place).
- cancel_session(key): a closing campaign's background calls end Cancelled (in flight or waiting); another campaign's go on.
- close(): every call in flight ends Cancelled; nothing waits.
- STRICT (a session that must replay exactly): nothing is ever preempted, so the recorded rows keep their order (its background
  people are taken in at an input's edge, f439, so a background call never runs beside a turn's there anyway).
"""

from __future__ import annotations

import threading
import time

from llm.errors import Cancelled, Failure


class _Call:
    __slots__ = ("thread", "lane", "session", "cancels", "flag", "reason")

    def __init__(self, thread: int, lane: str, session: str | None):
        self.thread, self.lane, self.session = thread, lane, session
        self.cancels = 0
        self.flag: threading.Event | None = None
        self.reason = ""


class Worker:
    def __init__(self, max_cancels: int = 3, resume_idle: float = 2.0, step: float = 0.05):
        self.max_cancels, self.resume_idle, self.step = int(max_cancels), float(resume_idle), float(step)
        self._cv = threading.Condition()
        self._foreground = 0
        self._last_foreground = 0.0
        self._background: dict[int, _Call] = {}        # a background thread's call, waiting or in flight
        self._promoted: set[int] = set()
        self._closed_sessions: set[str] = set()
        self._closed = False
        self.preempted = 0                             # how many times a background call gave the card back (the night counts it)
        self.waited_ms = 0.0                           # how long background calls waited for the card, in all

    # -- the turn's side
    def _strict(self) -> bool:
        try:
            from engine import streams
            return bool(streams.STRICT)
        except Exception:
            return False

    def foreground(self, send, lane: str = "foreground"):
        """A foreground (or input) call: sent at once. A foreground call takes the card back from the background calls that may be."""
        with self._cv:
            if self._closed:
                raise Cancelled("the model is closing")
            if lane == "foreground":
                self._foreground += 1
                if not self._strict():
                    for c in self._background.values():
                        if c.flag is not None and c.cancels < self.max_cancels and c.thread not in self._promoted:
                            c.reason = "preempted"
                            c.flag.set()
        try:
            return send(None)
        finally:
            if lane == "foreground":
                with self._cv:
                    self._foreground -= 1
                    self._last_foreground = time.monotonic()
                    self._cv.notify_all()

    # -- the background's side
    def background(self, send, session: str | None = None):
        """A background call: waits for the card, is sent, and is sent again (unseen above) when the turn took the card back."""
        me = threading.get_ident()
        call = _Call(me, "background", session)
        with self._cv:
            self._background[me] = call
        try:
            while True:
                self._admit(call)
                flag = threading.Event()
                with self._cv:
                    call.flag, call.reason = flag, ""
                try:
                    return send(flag)
                except Failure as f:
                    if f.kind != "cancelled" or call.reason != "preempted":
                        raise
                    with self._cv:
                        call.cancels += 1
                        self.preempted += 1
                        call.flag = None
                    continue
                finally:
                    with self._cv:
                        call.flag = None
        finally:
            with self._cv:
                self._background.pop(me, None)
                self._promoted.discard(me)
                self._cv.notify_all()

    def _admit(self, call: _Call) -> None:
        t0 = time.monotonic()
        with self._cv:
            while True:
                if self._closed or (call.session is not None and call.session in self._closed_sessions):
                    raise Cancelled("the campaign that asked is closing")
                if call.thread in self._promoted or call.cancels >= self.max_cancels or self._strict():
                    break
                idle = time.monotonic() - self._last_foreground
                if self._foreground == 0 and idle >= self.resume_idle:
                    break
                self._cv.wait(self.step if self._foreground else max(self.step, self.resume_idle - idle))
        self.waited_ms += (time.monotonic() - t0) * 1000.0

    # -- promotion, cancels
    def promote(self, thread_ident: int | None) -> None:
        if thread_ident is None:
            return
        with self._cv:
            self._promoted.add(int(thread_ident))
            self._cv.notify_all()

    def cancel_session(self, session: str) -> int:
        """A campaign closing: its background calls end Cancelled, waiting or in flight. Returns how many were in flight."""
        n = 0
        with self._cv:
            self._closed_sessions.add(str(session))
            for c in self._background.values():
                if c.session == str(session) and c.flag is not None:
                    c.reason = "closing"
                    c.flag.set()
                    n += 1
            self._cv.notify_all()
        return n

    def reopen_session(self, session: str) -> None:
        with self._cv:
            self._closed_sessions.discard(str(session))

    def close(self) -> None:
        with self._cv:
            self._closed = True
            for c in self._background.values():
                if c.flag is not None:
                    c.reason = "closing"
                    c.flag.set()
            self._cv.notify_all()

    def stats(self) -> dict:
        with self._cv:
            return {"preempted": self.preempted, "background_wait_ms": round(self.waited_ms), "in_flight": len(self._background)}

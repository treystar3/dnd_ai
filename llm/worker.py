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
- promote(thread): the turn waits on that background job (npc/backfill.py settle and collect, creation's result()): its calls are never
  cancelled again and start without the idle wait, every call the job makes until its thread ends. (f523's review) A promotion names
  the Thread itself, never only its ident (Linux hands a finished thread's ident to the next one at once), and a finished thread is
  never promoted.
- After max_cancels, a call runs beside a turn rather than starve (a fast typist and a 47-second populate_place); and so does a call
  that has waited max_wait seconds without being let in at all (turns less than resume_idle apart never leave it a reading time:
  the owner's "after it has been put off twice", two turns of the 60-second budget).
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
    __slots__ = ("thread", "obj", "lane", "session", "cancels", "flag", "reason", "since")

    def __init__(self, thread: int, lane: str, session: str | None):
        self.thread, self.lane, self.session = thread, lane, session
        self.obj = threading.current_thread()          # (f523's review) the Thread itself: an ident is reused once its thread ends
        self.cancels = 0
        self.flag: threading.Event | None = None
        self.reason = ""
        self.since = time.monotonic()


class Worker:
    def __init__(self, max_cancels: int = 3, resume_idle: float = 2.0, step: float = 0.05, max_wait: float = 120.0):
        self.max_cancels, self.resume_idle, self.step = int(max_cancels), float(resume_idle), float(step)
        self.max_wait = float(max_wait)
        self._cv = threading.Condition()
        self._foreground = 0
        self._last_foreground = 0.0
        self._background: dict[int, _Call] = {}        # a background thread's call, waiting or in flight
        self._promoted: dict[int, threading.Thread] = {}   # ident -> the Thread promoted (the ident alone may be another thread's)
        self._closed_sessions: set[str] = set()
        self._closed = False
        self.preempted = 0                             # how many times a background call gave the card back (the night counts it)
        self.waited_ms = 0.0                           # how long background calls waited for the card, in all

    # -- the turn's side
    def _is_promoted(self, call: _Call) -> bool:
        return self._promoted.get(call.thread) is call.obj

    def _given_up_waiting(self, call: _Call) -> bool:
        return time.monotonic() - call.since >= self.max_wait

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
                        if (c.flag is not None and c.cancels < self.max_cancels and not self._is_promoted(c)
                                and not self._given_up_waiting(c)):
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
                flag = self._admit(call)                    # (f523's review) armed in the same hold of the lock that lets it in
                try:
                    return send(flag)
                except Failure as f:
                    with self._cv:
                        preempted = call.reason == "preempted"
                    if f.kind != "cancelled" or not preempted:
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
                self._background.pop(me, None)              # a promotion lasts while its thread lives: the job's next call is
                self._cv.notify_all()                       # the turn's wait too (the gateway's retry, a second generate)

    def _admit(self, call: _Call) -> threading.Event:
        """Wait until the call may be sent, then arm its cancel flag in the same hold of the lock (f523's review: a foreground call,
        cancel_session or close landing between the two found no flag, and the call was sent anyway)."""
        t0 = time.monotonic()
        with self._cv:
            while True:
                if self._closed or (call.session is not None and call.session in self._closed_sessions):
                    raise Cancelled("the campaign that asked is closing")
                if (self._is_promoted(call) or (call.cancels and call.cancels >= self.max_cancels) or self._strict()
                        or self._given_up_waiting(call)):
                    break                               # (max_cancels 0 never takes the card back, and still waits for the reading time)
                idle = time.monotonic() - self._last_foreground
                if self._foreground == 0 and idle >= self.resume_idle:
                    break
                left = self.max_wait - (time.monotonic() - call.since)
                self._cv.wait(max(0.0, min(left, self.step if self._foreground else max(self.step, self.resume_idle - idle))))
            flag = threading.Event()
            call.flag, call.reason = flag, ""
            self.waited_ms += (time.monotonic() - t0) * 1000.0
        return flag

    # -- promotion, cancels
    def promote(self, thread) -> None:
        """The turn waits on this thread's job (a Thread, or a live thread's ident). (f523's review) A thread that has ended is never
        promoted (its ident may already be another job's), and promotions of ended threads are let go here, so the table never grows."""
        if thread is None:
            return
        t = thread if isinstance(thread, threading.Thread) else next((x for x in threading.enumerate() if x.ident == int(thread)), None)
        if t is None or not t.is_alive() or t.ident is None:
            return
        with self._cv:
            for k in [k for k, v in self._promoted.items() if not v.is_alive()]:
                del self._promoted[k]
            self._promoted[t.ident] = t
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
            flying = sum(1 for c in self._background.values() if c.flag is not None)
            return {"preempted": self.preempted, "background_wait_ms": round(self.waited_ms), "in_flight": flying,
                    "waiting": len(self._background) - flying}

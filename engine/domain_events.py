"""Typed events for the things that happen to the game's state, and a small synchronous bus that carries them.

A service (services/party.py first) changes the state and publishes an event saying what it did; whoever needs to know subscribes to
the event's type and is called at once, in the same transaction, in the order of subscription. The journal is one subscriber (every
event is a row in the campaign's event log, through engine.canon.journal); the tests are another (they read RECENT). Nothing waits in
a queue and nothing runs later: a turn is one transaction, and an event is part of the turn that caused it.

Rules:
  - an event is a frozen dataclass naming what happened, with ids rather than records: it is a fact, not a handle on the state
  - publish() is called after the state has changed, never before: a subscriber may read the state and must see the new one
  - a subscriber that raises stops the turn (the turn is rolled back by scenes/world.py): a bug here is not hidden
  - subscribers do not publish from inside a handler of the same event type (no cascades on one bus pass); a service publishes, a
    subscriber reads

Adding an event: declare the dataclass here with `kind` (the journal's kind), `actor` and `target` (ids), and text(); publish it from
the service that makes the change."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, fields
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind: str = field(init=False, default="event")
    minute: int = 0

    @property
    def actor(self) -> str:
        return ""

    @property
    def target(self) -> str:
        return ""

    def text(self) -> str:
        return self.kind

    def data(self) -> dict:
        """The event's own fields (not kind or minute), for the journal row."""
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in ("kind", "minute")}


# ---- the party

@dataclass(frozen=True)
class MemberJoined(Event):
    kind: str = field(init=False, default="party_joined")
    member_id: str = ""
    name: str = ""
    role: str = ""
    fee: int = 0
    how: str = "hired"            # hired | companion (an npc who joins for a thread) | story (Maren)

    @property
    def actor(self) -> str:
        return "player"

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return {"hired": f"{self.name} was hired", "story": f"{self.name} came along"}.get(self.how, f"{self.name} joined the party")


@dataclass(frozen=True)
class MemberLeft(Event):
    kind: str = field(init=False, default="party_left")
    member_id: str = ""
    name: str = ""
    how: str = "dismissed"        # dismissed | disbanded | home (a companion whose thread ended) | gone

    @property
    def actor(self) -> str:
        return "player" if self.how == "dismissed" else ""

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was {self.how}" if self.how in ("dismissed", "disbanded") else f"{self.name} left the party ({self.how})"


@dataclass(frozen=True)
class MemberDied(Event):
    kind: str = field(init=False, default="party_died")
    member_id: str = ""
    name: str = ""
    how: str = "fight"
    in_fight: bool = True         # True: it happened in front of the others, mid-fight; False: found so when the fight ended

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was killed in a fight" if self.how == "fight" else f"{self.name} died: {self.how}"


@dataclass(frozen=True)
class MemberCarried(Event):
    kind: str = field(init=False, default="party_carried")
    member_id: str = ""
    name: str = ""

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} went down and was carried out alive"


@dataclass(frozen=True)
class MemberPromoted(Event):
    kind: str = field(init=False, default="party_promoted")
    member_id: str = ""
    name: str = ""
    old_rank: str = ""
    new_rank: str = ""
    fee: int = 0

    @property
    def actor(self) -> str:
        return "player"

    @property
    def target(self) -> str:
        return self.member_id

    def text(self) -> str:
        return f"{self.name} was raised from {self.old_rank}-rank to {self.new_rank}-rank"


@dataclass(frozen=True)
class PartyModeChanged(Event):
    kind: str = field(init=False, default="party_mode")
    mode: str = "with"            # with | hold

    @property
    def actor(self) -> str:
        return "player"

    def text(self) -> str:
        return "the party moves with the player" if self.mode == "with" else "the party holds back"


# ---- the bus

_SUBSCRIBERS: dict[type, list[Callable[[Event], None]]] = {}
RECENT: deque = deque(maxlen=64)       # the last events published, newest last (tests and the live check read these)


def subscribe(event_type: type, fn: Callable[[Event], None]) -> Callable[[], None]:
    """Call fn for every event of this type (or a subclass of it; Event itself for everything). Returns a function that unsubscribes."""
    lst = _SUBSCRIBERS.setdefault(event_type, [])
    if fn not in lst:
        lst.append(fn)

    def off() -> None:
        if fn in lst:
            lst.remove(fn)
    return off


def publish(event: Event) -> Event:
    """Deliver the event to every subscriber of its type and its bases, in subscription order, now. Returns the event."""
    RECENT.append(event)
    for cls in type(event).__mro__:
        for fn in list(_SUBSCRIBERS.get(cls, ())):
            fn(event)
    return event


def clear() -> None:
    """Forget every subscriber and the recent events (tests)."""
    _SUBSCRIBERS.clear()
    RECENT.clear()


_JOURNAL_ON = False


def journal_everything() -> None:
    """Every event becomes a row in the campaign's event log (engine.canon.journal, bound by the scene). Idempotent."""
    global _JOURNAL_ON
    if _JOURNAL_ON:
        return
    from engine import canon

    def to_journal(e: Event) -> None:
        canon.journal(e.kind, e.actor, e.target, e.text(), **e.data())
    subscribe(Event, to_journal)
    _JOURNAL_ON = True

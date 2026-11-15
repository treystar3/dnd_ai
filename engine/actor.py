"""The actor's context and the turn's (docs/design/20_phase3_plan.md; docs/design/13_foundations_design.md).

(f632) ActorContext is what a scene plays for: the character's record, the dice, where the text goes, the clock and the turn's
context. A scene holds one (`scene.actor`); its `player` is a view over it, and so is the party's and the fight's
(services/party.py, services/fight.py), so a record put in the scene's place (a reload after a failed operation, the pulse, an
arc's end) is the one each of them reads next. The scene's entries bind it (`bound`), and the one bound before is back on the way
out; `current()` is the one bound, the process's own (PROCESS) when none is: no player, the process's dice, the console's
channel as it stands. Clock is the save's time as a view with nothing of its own; its `advance` is the one writer in play.

(f631) TurnContext is the fields a line and its operations keep while they are played. The scene reads each field through a
descriptor of the same name (TurnField), so no call site knows the field moved: `self.ran`, `getattr(self, "ran", [])` and
`self.halted = True` mean what they did. FIELDS declares every field: whether a new line resets it (LINE), whether a failed
operation puts it back to what the operation found (ROLLED), or neither (KEPT: it stands across lines and failures until the
turn's own code writes it). The operation's snapshot is kept here too (engine/session.py begin_turn, rollback).

HOMES declares where every name a failed operation puts back belongs once a scene is split for several characters (multiplayer
M1): the turn's, one character's view, or the scene's, shared by everyone in it. Only the turn's have moved; the rest are still
attributes of the scene, and this is the list that split starts from.

(f633) Registers is what a turn keeps while it is played, which five modules each held under names of their own: the operation
open now, what reached the page and the calls made inside a transaction (engine/operation.py), the ledger's rows, the last
turn's and the totals (engine/ledger.py), the input's budget and the last one's summary (engine/budget.py), the turn log's open
turn and its count of things shown (engine/turnlog.py), and the answers served to an operation that runs again
(engine/asked.py). Those modules' functions are still how it is read and written; each reaches the registers of the actor
bound (`registers()`). `owner` is the thread that plays the turn, the one field where there were three: off it there is no
turn (a call from the people written behind the scenes is not charged, filed under the operation or served an answer).

One actor a scene, one turn's context and one set of registers for the process, while a scene has one character; M1 makes it
one for each."""
from __future__ import annotations

import collections
import contextlib
import contextvars
import functools
import sys
import threading
import types
from dataclasses import dataclass, field
from typing import Callable

from engine import clock as calendar
from engine import streams

LINE, ROLLED, KEPT = "line", "rolled", "kept"
UNSET = object()


@dataclass(frozen=True)
class Field:
    marks: frozenset                       # LINE and ROLLED, either or both; or KEPT alone
    fresh: Callable | None = None          # what a new line starts it as; None for a LINE field: the scene gives it (begin_line)
    default: object = UNSET                # what it reads as before anything set it; UNSET: it is not there (AttributeError)


def _f(*marks, fresh=None, default=UNSET) -> Field:
    return Field(frozenset(marks), fresh, default)


FIELDS: dict[str, Field] = {
    # ---- the line being played
    "last_crash": _f(LINE, fresh=bool),                    # the line's last failure was the game's own fault
    "line_ops": _f(LINE, fresh=list),                      # its operations that stood, in order
    "line_failed": _f(LINE, fresh=list),                   # ...and the player's that did not
    "line_world_failed": _f(LINE, fresh=list),             # ...and the world's own that did not
    "line_done": _f(LINE, ROLLED, fresh=list),             # what the actions that stood did
    "passages": _f(LINE, fresh=list),                      # the passages its operations queued
    "line_untold": _f(LINE, fresh=list),                   # the passage operations told by a stand-in
    "unshown_ops": _f(LINE, fresh=dict),                   # operations whose later lines wait on a passage
    "collecting": _f(LINE, fresh=bool),                    # the line's actions are running
    "line_from": _f(LINE),                                 # where the line began
    "line_log": _f(LINE),                                  # where the journal stood when it began
    "line_losses": _f(LINE, ROLLED, fresh=int),            # deaths this line
    # ---- the step being done
    "step": _f(ROLLED, default=None),                      # the plan's step, while one is
    "ran": _f(ROLLED),                                     # the kinds of action the line has run
    "interpret_calls": _f(ROLLED),                         # the interpreter's calls, for the turn log
    "buffering": _f(ROLLED),                               # several actions told in one passage
    # ---- kept across lines and failures: a failed operation puts `pending` back by its own hand and writes `halted` and
    # `last_failure` itself (scenes/world.py abandon, operation); `last_budget` is the last input's, closed
    "pending": _f(KEPT),
    "halted": _f(KEPT),
    "last_failure": _f(KEPT),
    "last_budget": _f(KEPT),
}

TURN, VIEW, SCENE = "turn", "view", "scene"
HOMES: dict[str, str] = {
    **{name: TURN for name, f in FIELDS.items() if ROLLED in f.marks},
    # ---- one character's view: what they were offered, what their own next step carries
    "weight_hint": VIEW, "exits_due": VIEW, "journey_event_factor": VIEW, "haggle_factor": VIEW, "craft_boost": VIEW,
    "camp_bonus": VIEW, "rank_options": VIEW, "learn_options": VIEW, "pending_check": VIEW, "pending_beats": VIEW,
    "last_social": VIEW, "last_plan": VIEW, "sneaking": VIEW, "queued_buffs": VIEW, "fight_text": VIEW,
    # ---- the scene's, shared by everyone in it: what was told of it, the conversation, the road being walked, the fight that
    # is coming or was fled and how its beats landed on the party, what is in view
    "recent_narration": SCENE, "convo": SCENE, "last_spoken": SCENE, "partner": SCENE, "stance": SCENE, "wildlife": SCENE,
    "resume_pending": SCENE, "recently_fled": SCENE, "held_yield": SCENE, "orenna_fight": SCENE, "camp_fight": SCENE,
    "dungeon_fight": SCENE, "surrender_took": SCENE, "last_hits": SCENE,
}
UNLISTED: dict[str, str] = {               # scene fields no list held before this: a failure leaves each as it stands
    "broken": VIEW,                        # the lines that failed on the game's own fault, and how often
    "last_text": VIEW,                     # the line last typed
    "recovered_at_load": VIEW,             # outcomes told at this load
    "crash_after_commit": SCENE,           # the suite's injection: the game stops after this kind's commit
}


class TurnContext:
    """The turn's fields as they stand (`values`), and what the operation being played may have to give back (`snapshot`)."""

    def __init__(self) -> None:
        self.values: dict = {}
        self.snapshot = None

    def begin_line(self, **given) -> None:
        """A line begins: every LINE field starts fresh, the ones the scene gives (where it began) from `given`."""
        for name, f in FIELDS.items():
            if LINE in f.marks:
                self.values[name] = f.fresh() if f.fresh is not None else given.pop(name)
        if given:
            raise TypeError(f"not fields a line is given: {sorted(given)}")

    def add(self, name: str, item) -> None:
        """One more on a field that is a list, made when the first is added."""
        self.values.setdefault(name, []).append(item)


class Clock:
    """(f632) The save's time, read from the save's meta each time it is asked: nothing here to go stale when the meta is replaced
    whole (a reload, an asked restore) or a harness sets it."""

    def __init__(self, store) -> None:
        self._store = store

    @property
    def minutes(self) -> int:
        return self._store.meta.minutes

    @property
    def day(self) -> int:
        return self._store.meta.day

    def advance(self, minutes: int) -> int:
        """Time passes: the minute, and the day with it. The one writer of the save's time in the game's code."""
        meta = self._store.meta
        meta.minutes += minutes
        meta.day = calendar.day(meta.minutes)
        return meta.minutes


class Registers:
    """(f633) The turn's registers, each as a new one holds it (FRESH). The session puts them back when a campaign opens or
    closes (engine/owned.py, engine/session.py)."""

    FRESH: dict[str, Callable] = {
        "owner": lambda: None,                 # the thread playing the turn; none between turns
        "operation": lambda: None,             # the operation open now
        "presented": list,                     # what reached the page, in order: {"op": id, "how": shown | stand_in | recovered}
        "legacy": list,                        # the tasks asked for while an operation held the save's transaction open
        "rows": list,                          # the ledger: this turn's rows
        "last": list,                          # ...the last turn's, once it has ended
        "totals": collections.Counter,         # ...and how many of each kind stand
        "budget": lambda: None,                # the input's budget, while it is open
        "budget_last": dict,                   # the last closed budget's summary, with the stand-ins the line showed
        "open_turn": lambda: None,             # the turn log's rows of the turn being played, waiting for what it showed
        "shown": int,                          # things shown since the start: a turn that moved it not at all said nothing
        "serving": lambda: None,               # the answers of the operation that runs again
    }

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        for name, fresh in self.FRESH.items():
            setattr(self, name, fresh())

    def held(self) -> dict[str, str]:
        """Every register that is not as a new one holds it, by name, with what it holds."""
        return {name: repr(getattr(self, name))[:80] for name, fresh in self.FRESH.items() if getattr(self, name) != fresh()}

    def claim(self) -> None:
        """A budget, an operation or a serving opens: the turn is the calling thread's. While an operation or a serving is
        open the turn stays its thread's. A budget alone never holds it: one left open by a line that never closed it goes
        to the thread that opens next, and charges that thread's calls from then on."""
        if self.operation is None and self.serving is None:
            self.owner = threading.get_ident()

    def release(self) -> None:
        """One of the three closed: with none left open, the turn is nobody's."""
        if self.operation is None and self.budget is None and self.serving is None:
            self.owner = None

    def mine(self) -> bool:
        """Whether the calling thread is the one playing the turn. With nothing open, no thread is."""
        return self.owner == threading.get_ident()


SHARED = Registers()                           # the process's one set, every actor's while there is one actor


@dataclass(eq=False)
class ActorContext:
    player: object = None                      # the character's record (PlayerState); none for the process's own
    dice: streams.Streams = streams.DEFAULT    # the set of dice that answers engine/streams.py while this actor is bound
    out: object = None                         # the console's channel while it is bound; None: the channel as it stands
    clock: Clock | None = None
    turn: TurnContext = field(default_factory=TurnContext)
    registers: Registers = SHARED              # (f633) the turn's registers: the process's one, until a second actor has its own

    @property
    def character_id(self) -> str:
        return self.player.character.id


PROCESS = ActorContext()                       # no actor bound: the process's dice and the console's channel answer
_bound: contextvars.ContextVar = contextvars.ContextVar("actor", default=PROCESS)


def current() -> ActorContext:
    """The actor whose entry is running on this thread; PROCESS outside every entry and on a thread no entry runs on."""
    return _bound.get()


def registers() -> Registers:
    """(f633) The turn's registers of the actor bound on this thread: the process's one outside every entry, and on a thread
    no entry runs on, where `owner` says the turn is not that thread's."""
    return current().registers


def moved(module_name: str, names: dict[str, str]) -> None:
    """(f633) Names a module once held its state under, now held elsewhere: reading one or setting one raises and says what
    to call. Setting is refused too, or `module.NAME = ...` would quietly make a dead name nothing reads."""
    def gone(name: str) -> AttributeError:
        return AttributeError(f"{module_name}.{name} is no longer the module's (engine/actor.py Registers): use {names[name]}")

    class Moved(types.ModuleType):
        def __getattr__(self, name):
            raise gone(name) if name in names else AttributeError(f"module {module_name!r} has no attribute {name!r}")

        def __setattr__(self, name, value):
            if name in names:
                raise gone(name)
            super().__setattr__(name, value)

    sys.modules[module_name].__class__ = Moved


def who() -> str:
    """(f629) The id of the character whose entry is running on this thread, for a log's row or a record; "" when none is (a
    load, the people written behind the scenes, a harness outside every entry). The one source of who acted: three of the logs
    are written where there is no scene to ask."""
    mine = current()
    return mine.character_id if mine.player is not None else ""


@contextlib.contextmanager
def bind(mine: ActorContext):
    """This actor is the current one until the block ends, its dice with it; the one before is back after, a fault or not. Both
    are this thread's. A channel of its own takes the console's text for the whole process (ui/console.py use), every thread's
    with it, until the output seam is the channel's (f635)."""
    from ui import console
    token = _bound.set(mine)
    try:
        with streams.use(mine.dice), (console.use(mine.out) if mine.out is not None else contextlib.nullcontext()):
            yield mine
    finally:
        _bound.reset(token)


def actor_of(scene) -> ActorContext:
    """The scene's actor, made the first time it is asked for (the scene's constructor, as it is given its player). Under no `_`
    name: the session's sweep of the scene's caches would copy it at every operation and put a stale one back."""
    mine = scene.__dict__.get("actor")
    if mine is None:
        mine = scene.__dict__["actor"] = ActorContext(clock=Clock(scene.store))
    return mine


def bound(entry):
    """An entry of the scene (open_world, run, turn, handle, command, the pulse): its actor is bound while it runs. One entry
    inside another binds nothing again, so a channel put over the actor's in between stays."""
    @functools.wraps(entry)
    def run(scene, *args, **kwargs):
        mine = actor_of(scene)
        if current() is mine:
            return entry(scene, *args, **kwargs)
        with bind(mine):
            return entry(scene, *args, **kwargs)
    run.binds_actor = True
    return run


def turn_of(scene) -> TurnContext:
    """The turn's context of the scene's actor."""
    return actor_of(scene).turn


class TurnField:
    """A scene's name for one of the turn's fields: read, set and deleted on the scene's turn context."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, scene, owner=None):
        if scene is None:
            return self
        values = turn_of(scene).values
        if self.name in values:
            return values[self.name]
        default = FIELDS[self.name].default
        if default is UNSET:
            raise AttributeError(self.name)
        return default

    def __set__(self, scene, value) -> None:
        turn_of(scene).values[self.name] = value

    def __delete__(self, scene) -> None:
        try:
            del turn_of(scene).values[self.name]
        except KeyError:
            raise AttributeError(self.name) from None


def install(cls) -> None:
    """Give a scene class its name for every field."""
    for name in FIELDS:
        setattr(cls, name, TurnField(name))

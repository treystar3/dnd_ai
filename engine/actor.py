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

(f720) ATTRS declares every other attribute of the world scene, once: what a failed operation does with it (put back to what
the operation found; left as it stands, with the reason; written only outside operations, so a failure finds it as it left it;
read again from the save; set once when the scene is made) and where it
belongs once a scene is split for several characters (multiplayer M1): one character's view, or the scene's, shared by everyone
in it. A name that begins with `_` is a private cache, copied and put back whole by the session, and needs no row; nor does a
property of the scene, which holds nothing of its own. HOMES (every
name a failed operation puts back, with its home), UNLISTED (what a failure leaves as it stands) and WorldScene.ROLLED are read
from FIELDS and ATTRS; tools/sim/rollback_declared_720_test.py holds every name the scene's code sets to a declaration.

(f751) OPENING declares, beside it, what an opening (the save closed and opened again) does with every row of ATTRS and every
private name set on a scene: kept in a row of the save, made again from the save, forgotten (why), or owed (kept by the owner's
default and lost today, with who keeps it). The turn's fields need no row: a line sets each before it reads it. The
reopen_declared test (tools/sim) holds every name to a row, and a session closed and opened part-way to the same session
played straight.

(f633) Registers is what a turn keeps while it is played, which five modules each held under names of their own: the operation
open now, what reached the page and the calls made inside a transaction (engine/operation.py), the ledger's rows, the last
turn's and the totals (engine/ledger.py), the input's budget and the last one's summary (engine/budget.py), the turn log's open
turn and its count of things shown (engine/turnlog.py), and the answers served to an operation that runs again
(engine/asked.py). Those modules' functions are still how it is read and written; each reaches the registers of the actor
bound (`registers()`). `owner` is the thread that plays the turn, the one field where there were three: off it there is no
turn (a call from the people written behind the scenes is not charged, filed under the operation or served an answer).

(f634) Caches is what a scene keeps for its character between lines, which five more modules held the same way: the journal
the canon writes to, the ids behind names, what became of each claim and the drafts under review (engine/canon.py), the
companions' pronouns (engine/names.py), the stand-in and dropped-question lines said last (engine/failures.py,
engine/questions.py) and the enchanter's discount (engine/enchanting.py). Read and written through those modules' functions,
which reach the caches of the actor bound (`caches()`).

(f636) Prefs is what a player chose for their own screen: the engine's debug lines and commands (#debug, --debug at the
start), the numbers under a narrated round (#numbers) and whether conversations are narrated (#dialogue). Read where it
matters as `prefs()`, the actor's bound. The player's for the run: no campaign's close puts one back.

One actor a scene, one turn's context, and one set of registers, of caches and of preferences for the process, while a scene
has one character; M1 makes it one for each."""
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

import config
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
    "passages": _f(LINE, fresh=list),                      # the passages its operations queued
    "line_untold": _f(LINE, fresh=list),                   # the passage operations told by a stand-in
    "unshown_ops": _f(LINE, fresh=dict),                   # operations whose later lines wait on a passage
    "waiting": _f(LINE, ROLLED, fresh=list),               # what waits behind the line's one passage (f722)
    "collecting": _f(LINE, fresh=bool),                    # the line's actions are running
    "line_from": _f(LINE),                                 # where the line began
    "line_log": _f(LINE),                                  # where the journal stood when it began
    "line_losses": _f(LINE, ROLLED, fresh=int),            # deaths this line
    "line_plan": _f(LINE, fresh=list),                     # the steps it was read as, all of them (f715)
    "own_steps": _f(LINE, fresh=bool),                     # a passage asked for now is its own, not the world's (f715)
    "silent": _f(LINE, ROLLED, fresh=bool),                # the tail found it showed the player nothing (f721): the close says so
    "stood": _f(LINE, fresh=type(None)),                   # how the input stood, once settled (f721): True, "part" or False
    "decision": _f(LINE, ROLLED, fresh=type(None)),        # what the engine decided for the line's reply (f724)
    "input_count": _f(LINE, fresh=type(None)),             # the count its input was given, kept across a failed operation (f753)
    # ---- the step being done
    "step": _f(ROLLED, default=None),                      # the plan's step, while one is
    "plan_now": _f(ROLLED, default=()),                    # ...and the plan it is a step of (f645)
    "ran": _f(ROLLED),                                     # the kinds of action the line has run
    "interpret_calls": _f(ROLLED),                         # the interpreter's calls, for the turn log
    "buffering": _f(LINE, ROLLED, fresh=bool),             # several actions told in one passage; a line's (f722)
    # ---- kept across lines and failures: a failed operation puts `pending` back by its own hand and writes `halted` and
    # `last_failure` itself (scenes/world.py abandon, operation); `last_budget` is the last input's, closed
    "pending": _f(KEPT),
    "halted": _f(KEPT),
    "last_failure": _f(KEPT),
    "last_budget": _f(KEPT),
}

TURN, VIEW, SCENE = "turn", "view", "scene"
SAVED, ONCE, OUTSIDE = "saved", "once", "outside"


@dataclass(frozen=True)
class Attr:
    how: str                               # ROLLED, KEPT, OUTSIDE (written only outside operations), SAVED (read again from the
                                           # save) or ONCE (set when the scene is made)
    home: str                              # VIEW: one character's; SCENE: shared by everyone in the scene
    why: str = ""                          # for one a failure does not put back: why not


def _rows(how: str, home: str, names: str, why: str = "") -> dict[str, Attr]:
    return {name: Attr(how, home, why) for name in names.split()}


ATTRS: dict[str, Attr] = {
    # ---- put back, one character's view: what they were offered, what their own next step carries, how they arrived
    **_rows(ROLLED, VIEW, "weight_hint exits_due journey_event_factor haggle_factor craft_boost camp_bonus rank_options learn_options "
                          "learn_request pending_check pending_beats last_social last_plan sneaking queued_buffs fight_text "
                          "first_arrival revisit repairs"),
    # ---- put back, the scene's: what was told of it, the conversation, the fight that is coming or was fled and how its beats
    # landed on the party, what is in view, who came looking (they stand in the room, for everyone), the host at the gate
    **_rows(ROLLED, SCENE, "recent_narration convo last_spoken partner stance moves wildlife wildlife_at recently_fled "
                           "orenna_fight camp_fight dungeon_fight surrender_took last_hits visitors assault camp_events"),
    # ---- left as it stands
    **_rows(KEPT, VIEW, "broken", "the lines that failed on the game's own fault, and how often: a failure is what it counts"),
    **_rows(KEPT, VIEW, "last_text", "the line last typed: it was typed, whatever came of it"),
    **_rows(KEPT, SCENE, "crash_after_commit", "the suite's injection: the game stops after this kind's commit"),
    **_rows(KEPT, VIEW, "rng", "the scene's dice: what a failed operation drew is spent, and the line typed again is a new input "
                               "with dice of its own; an attempt that stood down to ask has them put back (asked_operation)"),
    **_rows(KEPT, VIEW, "to_menu", "the player asked for the menu: they leave, whatever became of the command"),
    # ---- written only outside operations
    **_rows(OUTSIDE, VIEW, "line_text dropped_steps last_interpret", "the reading of the line, written as it is read, before its operations"),
    **_rows(OUTSIDE, VIEW, "recovered_at_load", "outcomes told at this load: counted as the save opens, before any line"),
    # ---- read again from the save, where an operation gives back (scenes/world.py give_back). The character's record is loaded
    # again there too: it is the actor's, and the scene's name for it is a property, as its name for the save's question is
    **_rows(SAVED, SCENE, "combat", "the fight, resumed from its row, or none"),
    **_rows(SAVED, SCENE, "residents present", "the people of the place and who is here now, read again from their rows"),
    # ---- set when the scene is made
    **_rows(ONCE, SCENE, "session store world catalog", "the campaign's own: a turn writes through them, never over them"),
    **_rows(ONCE, VIEW, "actor", "the scene's actor, made as it is given its player"),
}
HOMES: dict[str, str] = {**{name: TURN for name, f in FIELDS.items() if ROLLED in f.marks},
                         **{name: a.home for name, a in ATTRS.items() if a.how == ROLLED}}
UNLISTED: dict[str, str] = {name: a.home for name, a in ATTRS.items() if a.how in (KEPT, OUTSIDE)}

IN_SAVE, REMADE, FORGOTTEN, OWED = "in the save", "remade", "forgotten", "owed"


@dataclass(frozen=True)
class Opening:
    fate: str                              # IN_SAVE, REMADE, FORGOTTEN or OWED (the module's docstring says each)
    why: str                               # IN_SAVE: the row; REMADE: from what; FORGOTTEN: why; OWED: "<who keeps it>: what a player meets"
    fresh: Callable | None = None          # FORGOTTEN or OWED, for a name the scene's constructor sets: what a new scene holds


def _opens(fate: str, names: str, why: str, fresh: Callable | None = None) -> dict[str, Opening]:
    return {name: Opening(fate, why, fresh) for name in names.split()}


# (f751) so what a close loses is declared, never found first by a player who stopped for the night
OPENING: dict[str, Opening] = {
    # ---- kept in the save
    **_opens(IN_SAVE, "recent_narration", "story: the last six passages, put back by the opening when a passage was shown"),
    **_opens(IN_SAVE, "convo partner stance moves last_spoken",
             "talk: put back once the one spoken with is here (restore_talk); with someone on their routine, a captive or a visitor "
             "it is lost today (RELOAD-4)"),
    **_opens(IN_SAVE, "combat", "the fight's row, resumed by the opening"),
    # ---- made again from the save
    **_opens(REMADE, "session store world catalog", "made with the scene, over the save"),
    **_opens(REMADE, "actor", "made with the scene, over the save; its caches (f634) start empty, as a campaign's open puts them back"),
    **_opens(REMADE, "rng", "the line's key: every input begins the scene's dice again (engine/streams.py)"),
    **_opens(REMADE, "residents present _doing_changes _routine_here _routine_cache _streets_cache",
             "the place's people and streets, read from their rows by the opening's entry"),
    **_opens(REMADE, "first_arrival revisit", "the opening's entry, from the visited list and the place's row (an arrival today: RELOAD-8)"),
    **_opens(REMADE, "weight_hint", "the opening: none on a reload"),
    **_opens(REMADE, "recovered_at_load _recovered_unreported", "the opening's recovery of what stood and was never shown (recover_unshown)"),
    **_opens(REMADE, "_people_missing", "the opening's entry, when the place's people could not be written"),
    **_opens(REMADE, "_talk_saved", "the talk row, read as the scene is made"),
    **_opens(REMADE, "_truth", "the truth scene, built again from the state at its next read"),
    **_opens(REMADE, "_house_names", "the house voices' names, from the data at the first read"),
    # ---- forgotten: the line's own, set afresh before any later line reads it
    **_opens(FORGOTTEN, "sneaking", "the line's own: every line sets it afresh", bool),
    **_opens(FORGOTTEN, "queued_buffs", "the line's own: every line sets it afresh", list),
    **_opens(FORGOTTEN, "fight_text", "the line's own: every line sets it afresh", str),
    **_opens(FORGOTTEN, "last_text", "the line last typed: every line sets it", str),
    **_opens(FORGOTTEN, "pending_check pending_beats", "the step's own: every step sets it afresh"),
    **_opens(FORGOTTEN, "line_text dropped_steps last_interpret _asked_place _question_let_go repairs",
             "the reading of the line: written as each line is read"),
    **_opens(FORGOTTEN, "exits_due journey_event_factor haggle_factor camp_bonus _wrote_turn _time_notes _looking _heard_now _following "
                        "_handed_in _back _live _deferred_from _deferred_exchange _arrival_lines",
             "the line's own: set and spent inside the line that sets it"),
    **_opens(FORGOTTEN, "last_plan surrender_took last_hits camp_events", "nothing in the game reads it after the line that wrote it"),
    # ---- forgotten: what only spaces out chatter inside one sitting, or what this visit has been shown
    **_opens(FORGOTTEN, "_banter_due _banter_last _banter_loc _chimed _party_said _quirk_loc _habits_at _habits_due _remembered "
                        "_last_claims _last_topic", "the party's chatter, spaced out inside one sitting"),
    **_opens(FORGOTTEN, "_framed_here _shown_here _crowd_told _happenings_seen _news_seen",
             "what this visit has been shown: a new sitting is told the place afresh"),
    **_opens(FORGOTTEN, "_stay _stay_people_turn", "the stay's one line: the opening's entry starts the stay"),
    **_opens(FORGOTTEN, "_stood", "the opening's own: set and taken inside open_world"),
    **_opens(FORGOTTEN, "_routine_marked", "the debug pulse log's mark, once a period: a new sitting marks it again"),
    **_opens(FORGOTTEN, "broken", "the lines that failed on the game's own fault this sitting: a new sitting tries afresh", dict),
    **_opens(FORGOTTEN, "to_menu", "the menu asked for ends the sitting", bool),
    **_opens(FORGOTTEN, "crash_after_commit", "the suite's injection, for one sitting", str),
    # ---- owed: kept by the owner's default, lost at a close today
    **_opens(OWED, "dungeon_fight camp_fight orenna_fight assault",
             "RELOAD-3: what a fight is for; a fight resumed after a close ends with none of its consequences"),
    **_opens(OWED, "visitors", "RELOAD-4: someone who came looking is gone from the room after a close"),
    **_opens(OWED, "_hire_last", "RELOAD-4: the hire who spoke last; after a close a reply to them is read as to no one"),
    **_opens(OWED, "_worn _said_in_town _after_starts _after_opened _exemplars _framed_hires _partings_heard",
             "RELOAD-6: what the checks and prompts remember of the telling; after a close the worn words pass again"),
    **_opens(OWED, "_door_loc", "RELOAD-8: after a close the next line's door reads the open as an arrival"),
    **_opens(OWED, "craft_boost", "RELOAD-11: a crafting ability's boost is spent and the next piece of work after a close is not better"),
    **_opens(OWED, "_appeared", "RELOAD-12: the day's count of people ruled into a place starts again at a close"),
    **_opens(OWED, "_errand", "STALE_COPIES-3: a companion's errand asked for is forgotten at a close"),
    **_opens(OWED, "rank_options learn_options learn_request",
             "reported: what a teacher offered; after a close 'the first one' is a line about nothing"),
    **_opens(OWED, "wildlife wildlife_at", "reported: the creature in view is gone after a close, and an attack on it finds nothing",
             type(None)),
    **_opens(OWED, "_trail", "reported: the fresh signs a search found; after a close they cannot be followed"),
    **_opens(OWED, "recently_fled", "reported: a fight just fled may be met again by the next search after a close", bool),
    **_opens(OWED, "last_social", "reported: a persuasion won over someone; after a close their secret is shut again"),
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


class Held:
    """A set of named fields, each as a new set holds it (FRESH). The session puts the process's back when a campaign opens or
    closes (engine/owned.py, engine/session.py)."""

    FRESH: dict[str, Callable] = {}

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        for name, fresh in self.FRESH.items():
            setattr(self, name, fresh())

    def held(self) -> dict[str, str]:
        """Every field that is not as a new set holds it, by name, with what it holds."""
        return {name: repr(getattr(self, name))[:80] for name, fresh in self.FRESH.items() if getattr(self, name) != fresh()}


class Registers(Held):
    """(f633) The turn's registers."""

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


class Caches(Held):
    """(f634) What a scene keeps for the character it plays, between lines."""

    FRESH: dict[str, Callable] = {
        "journal": lambda: None,               # where the canon's facts go: fn(kind, actor, target, text, data), bound by the scene
        "ids": dict,                           # name -> stable id for the people the game knows: the party, the mentor, the character
        "events": list,                        # what became of each claim: kept, same, contradicts, given (the live check reads it)
        "sink": list,                          # while a draft is under review its events wait here, kept only if it is committed
        "cast": dict,                          # first name -> 'he' | 'she': the companions, for what reaches the screen
        "said_failure": dict,                  # the stand-in line said last, by kind: never the same one twice running
        "said_question": str,                  # ...and the line for a dropped question
        "discount": int,                       # the enchanter's fee taken off, in percent, from the character's passives
    }


class Prefs(Held):
    """(f636) What a player chose for their own screen."""

    FRESH: dict[str, Callable] = {
        "debug": bool,                         # the engine's decisions shown, and the debug commands open
        "numbers": lambda: True,               # the numbers under each narrated round of a fight
        "dialogue": lambda: True,              # conversations wrapped in narration; off, the words alone
    }


SHARED = Registers()                           # the process's one set, every actor's while there is one actor
SHARED_CACHES = Caches()                       # (f634) ...and its one set of caches
SHARED_PREFS = Prefs()                         # (f636) ...and of preferences: the first player's


@dataclass(eq=False)
class ActorContext:
    player: object = None                      # the character's record (PlayerState); none for the process's own
    dice: streams.Streams = streams.DEFAULT    # the set of dice that answers engine/streams.py while this actor is bound
    out: object = None                         # the console's channel while it is bound; None: the channel as it stands
    clock: Clock | None = None
    turn: TurnContext = field(default_factory=TurnContext)
    registers: Registers = SHARED              # (f633) the turn's registers: the process's one, until a second actor has its own
    caches: Caches = SHARED_CACHES             # (f634) what is kept for the character between lines: the process's, likewise
    prefs: Prefs = SHARED_PREFS                # (f636) what the player chose for their screen: the process's, likewise

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


def caches() -> Caches:
    """(f634) The caches of the actor bound on this thread; the process's one outside every entry."""
    return current().caches


def prefs() -> Prefs:
    """(f636) The preferences of the actor bound on this thread; the process's one outside every entry."""
    return current().prefs


def moved(module_name: str, names: dict[str, str]) -> None:
    """(f633) Names a module once held its state under, now held elsewhere: reading one or setting one raises and says what
    to call. Setting is refused too, or `module.NAME = ...` would quietly make a dead name nothing reads."""
    def gone(name: str) -> AttributeError:
        return AttributeError(f"{module_name}.{name} is no longer the module's (engine/actor.py): use {names[name]}")

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
    are this thread's. (f635) So is a channel of its own: everything the game shows or asks on this thread goes to it
    (ui/console.py use), and another thread keeps its own, or the process's."""
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


moved("config", {"DEBUG": "actor.prefs().debug", "COMBAT_NUMBERS": "actor.prefs().numbers", "NARRATED_DIALOGUE": "actor.prefs().dialogue"})   # (f636)

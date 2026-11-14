"""(f631) The turn's context: the fields a line and its operations keep while they are played, on an object of their own
(docs/design/20_phase3_plan.md; docs/design/13_foundations_design.md).

A scene holds one (`scene.turnctx`) and reads each field through a descriptor of the same name (TurnField), so no call site knows
the field moved: `self.ran`, `getattr(self, "ran", [])` and `self.halted = True` mean what they did. FIELDS declares every field:
whether a new line resets it (LINE), whether a failed operation puts it back to what the operation found (ROLLED), or neither
(KEPT: it stands across lines and failures until the turn's own code writes it). The operation's snapshot is kept here too
(engine/session.py begin_turn, rollback).

HOMES declares where every name a failed operation puts back belongs once a scene is split for several characters (multiplayer
M1): the turn's, one character's view, or the scene's, shared by everyone in it. Only the turn's have moved; the rest are still
attributes of the scene, and this is the list that split starts from.

One context a scene while there is one actor; M1 makes it one for each."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


def turn_of(scene) -> TurnContext:
    """The scene's turn context, made the first time it is asked for. Under no `_` name: the session's sweep of the scene's caches
    would copy it at every operation and put a stale one back."""
    ctx = scene.__dict__.get("turnctx")
    if ctx is None:
        ctx = scene.__dict__["turnctx"] = TurnContext()
    return ctx


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

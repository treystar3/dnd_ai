"""The intercepts: what reads a typed line before the model does, declared in one ordered table.

A few things claim a line before the interpreter sees it: the mentor stepping in on a newcomer's first move, the answer to a companion's
errand, a word about your own trial, a party order, a camp approached, a line said to Maren or to a hire, the hunt setting out, a way out
of town. They used to be wired by hand in handle(), in an order nobody could see. Now each mixin declares the intercepts it owns
(its INTERCEPTS tuple), the scene gathers them in order, handle() tries them one after another, and the first that takes the line ends
the turn under its name: the turn log says which (engine/turnlog.py), --debug prints it, and data_check refuses to start a game whose
table is inconsistent (a method missing, a name or an order used twice).

An intercept is a scene method `fn(text) -> bool`: it acts on the line and returns True when the line was its to take. `after` names a
method run once it has (the camp: dungeons and the pulse). The combat turn is not here: a fight reads every line with its own reader
(scenes/combat_scene.py) and comes first."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intercept:
    name: str                  # what the turn log calls it
    order: int                 # lower runs first
    method: str                # the scene method: fn(text) -> bool, True when the line was taken and acted on
    note: str = ""             # what it takes, for anyone reading the table
    after: str = ""            # a scene method to run once it took the line


def gather(scene_class) -> tuple[Intercept, ...]:
    """Every intercept the scene's classes declare, in order of `order`."""
    found: list[Intercept] = []
    for cls in scene_class.__mro__:
        found.extend(cls.__dict__.get("INTERCEPTS", ()))
    return tuple(sorted(found, key=lambda i: i.order))


def problems(scene_class) -> list[str]:
    """What does not agree: a method or an `after` the scene lacks, a name or an order declared twice."""
    out = []
    table = gather(scene_class)
    names = [i.name for i in table]
    orders = [i.order for i in table]
    for n in sorted({n for n in names if names.count(n) > 1}):
        out.append(f"intercept '{n}' is declared twice")
    for o in sorted({o for o in orders if orders.count(o) > 1}):
        out.append(f"intercept order {o} is used twice: {', '.join(i.name for i in table if i.order == o)}")
    for i in table:
        if not callable(getattr(scene_class, i.method, None)):
            out.append(f"intercept '{i.name}' names a method the scene lacks: {i.method}")
        if i.after and not callable(getattr(scene_class, i.after, None)):
            out.append(f"intercept '{i.name}' names an after-step the scene lacks: {i.after}")
    return out


def describe(scene_class) -> list[str]:
    return [f"{i.order:>4}  {i.name:<18} {i.method}{(' -> ' + i.after) if i.after else ''}  {i.note}" for i in gather(scene_class)]

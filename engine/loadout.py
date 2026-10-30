"""The loadout (data/rules/training.yaml loadout, f232): every ability learned stays in the book, but a character brings only so many.
Spells (mana) and techniques (stamina) each have their own room - 5 at first, growing to 10 by level 100. Every active ability counts.
The loadout is changed only out of combat and once a day (the first change is free); a newly learned ability goes straight in when
there is room. Nothing here talks to a model."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
L = yaml.safe_load((ROOT / "data" / "rules" / "training.yaml").read_text(encoding="utf-8"))["loadout"]
POOLS = ("spells", "techniques")
WORD = {"spells": "spells", "techniques": "techniques"}


def pool_of(a) -> str:
    return "spells" if getattr(a.resource, "value", a.resource) == "mana" else "techniques"


def room(level: int) -> int:
    """How many of each - spells and techniques - a character of this level brings."""
    return min(int(L["max"]), int(L["start"]) + max(0, int(level)) // int(L["levels_per_more"]))


def _rank(a) -> tuple:
    order = L["priority"]
    eff = getattr(a.effect, "value", a.effect)
    tier = {"heavy": 0, "moderate": 1, "light": 2}.get(getattr(a.tier, "value", a.tier), 3)
    return (order.index(eff) if eff in order else len(order), tier)


def _tops(actives: list) -> list:
    """(f397) The abilities worth bringing on their own: a spell line's lower ranks stay in the book unless chosen."""
    best: dict[str, int] = {}
    for a in actives:
        if getattr(a, "rank", 0):
            k = a.line or a.id
            best[k] = max(best.get(k, 0), a.rank)
    return [a for a in actives if not getattr(a, "rank", 0) or a.rank == best[a.line or a.id]]


def _spread(cands: list, n: int) -> list:
    """An automatic pick: one of each kind first, in priority order, then the strongest of what is left."""
    out, kinds = [], set()
    for a in sorted(cands, key=_rank):
        k = getattr(a.effect, "value", a.effect)
        if k not in kinds and len(out) < n:
            out.append(a)
            kinds.add(k)
    for a in sorted(cands, key=_rank):
        if a not in out and len(out) < n:
            out.append(a)
    return out


def settle(c) -> None:
    """Keep the loadout true to the book: forget what is no longer known, fit the room, and bring a newly learned ability along when
    there is room for it (or make the first pick, for a character who never had a loadout)."""
    known = {a.id: a for a in c.actives}
    prepared = [i for i in c.prepared if i in known]
    seen = set(c.book_seen) & set(known)
    first = not c.book_seen and not c.prepared
    n = room(c.level)
    for pool in POOLS:
        mine = [i for i in prepared if pool_of(known[i]) == pool]
        for extra in mine[n:]:
            prepared.remove(extra)                       # never more than the room (it only grows, but be safe)
        mine = mine[:n]
        tops = _tops(c.actives)
        if first:
            pick = _spread([a for a in tops if pool_of(a) == pool], n)
            prepared += [a.id for a in pick if a.id not in prepared]
            continue
        for a in tops:                                   # newly learned, and there is room: it comes along
            if a.id not in seen and pool_of(a) == pool and a.id not in prepared and len(mine) < n:
                prepared.append(a.id)
                mine.append(a.id)
        if n > c.loadout_room and len(mine) < n:        # a level brought more room: the best of the book fills the new places
            left = [a for a in tops if pool_of(a) == pool and a.id not in prepared]
            for a in _spread(left, n - len(mine)):
                prepared.append(a.id)
                mine.append(a.id)
    c.prepared = prepared
    c.book_seen = list(known)
    c.loadout_room = n


def prepared(c) -> list:
    """The abilities this character brings, in book order."""
    settle(c)
    keep = set(c.prepared)
    return [a for a in c.actives if a.id in keep]


def book(c) -> list:
    """The abilities left in the book, not brought."""
    settle(c)
    keep = set(c.prepared)
    return [a for a in c.actives if a.id not in keep]


def can_change(c, day: int, in_combat: bool) -> str:
    """Why the loadout cannot be changed now; '' if it can."""
    if in_combat:
        return "You cannot change what you bring in the middle of a fight."
    if c.loadout_free:
        return ""
    if c.loadout_day == day:
        return "You have already changed what you bring today. You can change it again tomorrow."
    return ""


def change(c, wanted: list[str], day: int, in_combat: bool) -> str:
    """Set the loadout to these abilities (ids or names, from the book). The pools not named are left as they were. Uses the day's
    change (the first is free). Returns what happened, for the player."""
    why = can_change(c, day, in_combat)
    if why:
        return why
    settle(c)
    picked = []
    for w in wanted:
        w_ = w.strip().lower()
        a = next((x for x in c.actives if x.id.lower() == w_ or x.name.lower() == w_), None) or \
            next((x for x in c.actives if w_ and w_ in x.name.lower()), None)
        if a is None:
            return f"There is nothing called '{w}' in your book."
        if a not in picked:
            picked.append(a)
    if not picked:
        return "Name what you want to bring."
    n = room(c.level)
    pools = {pool_of(a) for a in picked}
    for pool in pools:
        count = sum(1 for a in picked if pool_of(a) == pool)
        if count > n:
            return f"You can bring at most {n} {WORD[pool]}; you named {count}."
    keep = [i for i in c.prepared if pool_of(next(a for a in c.actives if a.id == i)) not in pools]
    c.prepared = keep + [a.id for a in picked]
    was_free = c.loadout_free
    c.loadout_free = False
    c.loadout_day = day
    names = ", ".join(a.name for a in picked)
    return f"You will bring: {names}." + (" (Your first change is free - from now on, once a day.)" if was_free else
                                           " You can change it again tomorrow.")


def lines(c, day: int, in_combat: bool) -> list[str]:
    """The book, as the player reads it: what is brought, what is left behind, the room and whether it can change today."""
    settle(c)
    n = room(c.level)
    out = []
    num = 0
    for pool in POOLS:
        mine = [a for a in c.actives if pool_of(a) == pool]
        if not mine:
            continue
        brought = [a for a in mine if a.id in c.prepared]
        out.append(f"{WORD[pool].upper()} - bringing {len(brought)} of {n}:")
        for a in mine:
            num += 1
            mark = "*" if a.id in c.prepared else " "
            eff = getattr(a.effect, "value", a.effect)
            from engine import spells
            out.append(f"  {mark} {num}. {a.name} ({' '.join(w for w in (spells.grade(a), eff) if w)})")     # (f400) a buff: no tier
    why = can_change(c, day, in_combat)
    out.append("* = brought. " + (why if why else "Change it with: #prepare <names or numbers, separated by commas>"
                                  + (" - your first change is free." if c.loadout_free else " - once a day.")))
    return out


def by_number(c, tokens: list[str]) -> list[str]:
    """The book's numbers (as lines() shows them) turned into ability ids; anything else passes through as a name."""
    settle(c)
    ordered = [a for pool in POOLS for a in c.actives if pool_of(a) == pool]
    out = []
    for t in tokens:
        t = t.strip()
        if t.isdigit() and 1 <= int(t) <= len(ordered):
            out.append(ordered[int(t) - 1].id)
        elif t:
            out.append(t)
    return out

"""Only what matters to this moment goes into a character's prompt. Whatever is in a prompt, a model wants to talk about, so a character's
motive, leanings, habits and memories are offered only when they are close in meaning to what was said or what brought the talk up. A
small core is always there, and now and then one thing that is simply on their mind, so they can still bring something up unprompted."""
from __future__ import annotations

import random
import re

import config

STOP = {"the", "and", "you", "your", "with", "that", "this", "for", "are", "was", "have", "has", "they", "them", "their", "what", "how", "who",
        "why", "when", "from", "been", "not", "but", "all", "any", "about", "into", "just", "will", "would", "could", "should", "there", "here"}


def stem(w: str) -> str:
    """The word without its common ending, so that 'earned' and 'earn', 'contracts' and 'contract' count as one when there is no helper
    model to compare meanings."""
    for end in ("ing", "ed", "es", "s"):
        if w.endswith(end) and len(w) - len(end) >= 4:
            return w[:-len(end)]
    return w


def _words(t: str) -> set[str]:
    return {stem(w) for w in re.findall(r"[a-z]{4,}", t.lower()) if w not in STOP}


def pick(query: str, items: list[str], k: int = 2, floor: float | None = None) -> list[str]:
    """Up to k of the items that are about the same thing as the query, closest first. By meaning when the helper model is there, else by
    shared words."""
    items = [i for i in items if i and i.strip()]
    if not items or not (query or "").strip():
        return []
    floor = config.SIM_RELEVANT if floor is None else floor
    from llm import embed
    sims = embed.whole(query, items)
    if sims is not None:
        ranked = sorted(zip(sims, items), key=lambda x: -x[0])
        return [t for v, t in ranked if v >= floor][:k]
    words = _words
    q = words(query)
    ranked = sorted(((len(q & words(t)), t) for t in items), key=lambda x: -x[0])
    return [t for n, t in ranked if n >= 1][:k]


def stands_out(query: str, mine: list[str], theirs: list[str], floor: float, margin: float) -> tuple[bool, float, float]:
    """Is the query close to these records in particular - close enough (floor), and clearly closer to them than to the others' (margin)?
    Any line is somewhat close to anyone's life; what counts is standing out. Returns (yes, closest of mine, closest of theirs). By
    meaning when the helper model is there; else by shared words, needing more in common with mine than with any of theirs."""
    mine = [i for i in mine if i and i.strip()]
    theirs = [i for i in theirs if i and i.strip()]
    if not mine or not (query or "").strip():
        return False, 0.0, 0.0
    from llm import embed
    sims = embed.whole(query, mine + theirs)
    if sims is not None:
        a = max(sims[:len(mine)])
        b = max(sims[len(mine):], default=0.0)
        return a >= floor and a - b >= margin, a, b
    words = _words
    q = words(query)
    a = max(len(q & words(t)) for t in mine)
    b = max((len(q & words(t)) for t in theirs), default=0)
    return a >= 1 and a > b, float(a), float(b)


def ranked(query: str, items: list[str], floors: list[float] | None = None) -> list[str]:
    """The items about the same thing as the query, closest first, each needing its own floor (an item that should come in only when the
    moment is clearly about it has a higher one). By meaning when the helper model is there; else by shared words, a raised floor asking
    for one more word in common."""
    pairs = [(i, f) for i, f in zip(items, floors or [0.0] * len(items)) if i and i.strip()]
    if not pairs or not (query or "").strip():
        return []
    from llm import embed
    sims = embed.whole(query, [i for i, _ in pairs])
    if sims is not None:
        ranked_ = sorted(((v, i) for v, (i, f) in zip(sims, pairs) if v >= config.SIM_RELEVANT + f), key=lambda x: -x[0])
        return [i for _, i in ranked_]
    words = _words
    q = words(query)
    ranked_ = sorted(((len(q & words(i)), i) for i, f in pairs if len(q & words(i)) >= 1 + (1 if f > 0 else 0)), key=lambda x: -x[0])
    return [i for _, i in ranked_]


def on_mind(items: list[str], rng: random.Random, chance: float = 0.2) -> list[str]:
    """Now and then, one thing simply on their mind."""
    items = [i for i in items if i and i.strip()]
    return [rng.choice(items)] if items and rng.random() < chance else []

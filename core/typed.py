"""(f781) What a player types, as the game takes it in.

A line from outside the game (the terminal, the page's JSON, a choice the page sends as JSON inside its line) can hold half a
surrogate pair: an emoji the page split, or cut at its box's length. No seed, file or request takes such a line, and the page must
never be shown broken text (pillar 5), so the half is dropped where the line comes in. A pair sent in two halves is its one character."""
from __future__ import annotations


def whole(text: str) -> str:
    """The text with every half surrogate pair dropped and every pair sent in two halves made its one character."""
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "ignore")

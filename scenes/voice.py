"""The game master's voice, shared by every narrator, and a guard against repetition.

Narration should feel like a live DM at the table: specific, responsive, varied, and never on autopilot.
"""

import re

from llm.gateway import generate
from llm.prompts import WORLD_RULES

DM_VOICE = """You are the game master, running this world live for one player at the table. Speak to them the way a
great DM does: present tense, second person, vivid and specific, but economical - every sentence earns its place.
- React to what the player actually said and did, including small touches (marking a tree, a joke, a hesitation).
  Show that it registered.
- Keep it fresh. Never open the way RECENT NARRATION opened, and never reuse its images, phrases or sentence shapes.
  Weather, air and smells are seasoning, not a refrain: mention them only when they change or matter.
- One sharp, concrete detail beats three generic ones. Avoid stock phrases like "the air hangs heavy", "the scent of
  damp earth", "a sense of", "you can't help but", "little do you know".
- Group what happens in parallel ("the rest of them close in around you") instead of walking through each person.
- Let danger be felt before it lands. When the odds are bad, the world itself should warn the player - numbers,
  movement, the look in a foe's eyes - without you saying "this is dangerous".
- Now and then, not every time, end on a beat that invites the player to act: a sound, an opening, a choice.
- Never contradict the facts you are given, and never add facts that change the situation. The player's gear is exactly what
  you are told they carry: never add a piece, and never name something they lack.

""" + WORLD_RULES + "\n"

STALE = ["the air hangs heavy", "hangs heavy", "scent of damp earth", "smell of damp earth", "cool morning air",
         "a sense of", "can't help but", "little do you know", "send shivers down", "sends a shiver"]


def _shingles(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def stale_phrases(text: str, recent: list[str]) -> list[str]:
    """Phrases of five or more words reused from recent narration, plus known stock phrases."""
    mine = _shingles(text)
    seen = set()
    for r in recent[-4:]:
        seen |= _shingles(r)
    repeats = sorted(mine & seen)
    lower = text.lower()
    return repeats[:6] + [s for s in STALE if s in lower]


def fresh(task: str, system: str, request: str, schema, recent: list[str], fields=("text",),
          temperature: float = 0.9, max_tokens: int = 600):
    """Generate narration; if it repeats recent phrasing or stock phrases, rewrite once with them called out."""
    result = generate(task, system, request, schema, temperature=temperature, max_tokens=max_tokens)
    text = " ".join(getattr(result, f, "") or "" for f in fields)
    hits = stale_phrases(text, recent)
    if not hits:
        return result
    nudge = ("\n\nYOUR DRAFT REUSED STALE PHRASING. Do not use any of these again: "
             + "; ".join(f'"{h}"' for h in hits) + ". Write it fresh, with the same events.")
    return generate(task, system, request + nudge, schema, temperature=min(1.1, temperature + 0.1), max_tokens=max_tokens)

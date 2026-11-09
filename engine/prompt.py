"""A prompt made of typed parts, so the engine knows where every piece of text came from.

  instruction  how to behave: a temperament, a voice, a rule. Never words to say. A line that reuses a run of words from here was copied.
  fact         what is true: who they are, what has happened, what is here. Saying it is the point.
  material     words that may be said as they are, when the engine offers them: a saying from home, a curse, a word of their tongue.
  history      what was said lately. The repetition guard deals with it.

The gateway renders the parts in order and, for any reply that carries speech, checks that the speech does not reuse six words running from
the instructions (the system prompt counts as instruction), unless the same words are also in a fact, a piece of material or what was said.
Nothing is listed by hand: what counts as copying comes from the prompt that was actually sent."""
from __future__ import annotations

import re

KINDS = ("instruction", "fact", "material", "history")
N = 6
STOP = {"a", "an", "the", "and", "or", "but", "if", "of", "to", "in", "on", "at", "by", "for", "with", "from", "as", "is", "are", "was", "were",
        "be", "been", "it", "its", "it's", "this", "that", "these", "those", "you", "your", "they", "them", "their", "he", "she", "him", "her",
        "his", "i", "me", "my", "we", "us", "our", "not", "no", "do", "does", "did", "have", "has", "had", "will", "would", "can", "could",
        "should", "so", "than", "then", "there", "here", "what", "who", "how", "when", "where", "why", "all", "any", "some", "one", "more",
        "most", "just", "only", "too", "very", "up", "out", "about", "into", "over", "than", "s", "t", "don't", "i'm", "it's", "that's"}


class Prompt:
    def __init__(self):
        self.parts: list[tuple[str, str, str]] = []          # (kind, label, text)
        self.tail_at: int | None = None                       # (f475) where the part that changes call to call begins, when marked

    def add(self, kind: str, text: str, label: str = "") -> "Prompt":
        assert kind in KINDS, kind
        if text and str(text).strip():
            self.parts.append((kind, label, str(text).strip()))
        return self

    def instruction(self, text: str, label: str = "") -> "Prompt":
        return self.add("instruction", text, label)

    def fact(self, text: str, label: str = "") -> "Prompt":
        return self.add("fact", text, label)

    def material(self, text: str, label: str = "") -> "Prompt":
        return self.add("material", text, label)

    def history(self, text: str, label: str = "") -> "Prompt":
        return self.add("history", text, label)

    def render(self) -> str:
        return "\n\n".join(_one(label, text) for _, label, text in self.parts)

    # ---- (f475) the prompt's shape, measured: where its length goes, its layout without its words, and the part that changes. The
    # server reuses a cached prefix only up to where a prompt first differs (the Bundle D gap search), so what follows the stable part is
    # what a call pays to read afresh; the gateway logs all three beside every call, outside the request's hash.
    def sizes(self) -> list[tuple[str, str, int]]:
        """Each part's kind, label and rendered characters, in order (the parts and the blank lines between them make render())."""
        return [(kind, label, len(_one(label, text))) for kind, label, text in self.parts]

    def skeleton(self) -> str:
        """The layout without the words: each part's kind and label, in order. A reordering moves it; new wording does not."""
        return "|".join(f"{kind}:{label}" for kind, label, _ in self.parts)

    def mark_tail(self) -> "Prompt":
        """What is added from here on is the tail: the part that changes from one call to the next."""
        self.tail_at = len(self.parts)
        return self

    def tail(self) -> str:
        """The tail, rendered: from the mark on, or the last part when none was marked."""
        start = self.tail_at if self.tail_at is not None else max(0, len(self.parts) - 1)
        return "\n\n".join(_one(label, text) for _, label, text in self.parts[start:])

    def __str__(self) -> str:
        return self.render()

    def texts(self, *kinds: str) -> list[str]:
        return [t for k, _, t in self.parts if k in kinds]


def _one(label: str, text: str) -> str:
    return (f"{label}:\n{text}" if "\n" in text else f"{label}: {text}") if label else text


def words(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", (text or "").lower())


def grams(text: str, n: int = N) -> set[tuple[str, ...]]:
    w = words(text)
    out = set()
    for i in range(len(w) - n + 1):
        g = tuple(w[i:i + n])
        if sum(1 for x in g if x not in STOP and len(x) >= 3) >= 2:      # a run of mostly small words is just English, not a copy
            out.add(g)
    return out


def copied(spoken: str, system: str, prompt: Prompt, also_allowed: list[str] | None = None) -> str:
    """The run of words this speech took from the instructions, or ''."""
    said = grams(spoken)
    if not said:
        return ""
    instr = grams(system)
    for t in prompt.texts("instruction"):
        instr |= grams(t)
    hit = said & instr
    if not hit:
        return ""
    allowed = set()
    for t in prompt.texts("fact", "material", "history") + list(also_allowed or []):
        allowed |= grams(t)
    hit -= allowed
    return " ".join(sorted(hit)[0]) if hit else ""

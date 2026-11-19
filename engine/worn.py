"""(f349) The worn-word watch: which words the writing has leaned on lately, found rather than listed.

Why: a fixed ban list ages (the model finds the next "steady") and a quota ("fewer than N") is not writing. Instead the engine keeps the
last few dozen passages and counts, per passage, the words of the kind that wear out - manner words and the suffixed adjectives, adverbs
and abstractions ("unreadable", "steadily", "weariness") - and hands the narrator the handful it has used most, as WORDS YOU HAVE WORN
OUT, and holds every draft to them (f584: shown and checked, as measured). Nouns of the scene (the smith, the gate) are never on the
list: they are facts, not habits. Two watches run, one for prose and one
for what people say, because "folk" wears out in mouths and "expression" wears out in frames.

The rules live in data/rules/voice.yaml under `worn`: the seed words, the suffixes, how many passages are kept, how many passages a word
must appear in and how many words are held to. scenes/voice.fresh asks for one rewrite when a draft leans on two or more of them, and a
reply that does is sent back (llm/contracts.py).

(f761) A passage is kept as what the watch reads of it (reduce), never its text, so the watch is small enough to keep in the save
(engine/telling.py) and no passage is stored twice: its words in lower case, sorted by how they were seen."""
from __future__ import annotations

import re
from collections import deque

from engine.voice_rules import V

W = V.get("worn", {})
_TOKEN = re.compile(r"(^|[.!?:;]\s+|[\"\u201c(]\s*)?([A-Za-z][a-z']+)")      # a word, and whether a sentence or a quote begins at it
STOP = {"nothing", "something", "anything", "everything", "morning", "evening", "thing", "things", "during", "spring", "string", "ceiling",
        "building", "sibling", "clothing", "lightning", "wedding", "shilling", "only", "early", "family", "ally", "really", "nearly",
        "likely", "mostly", "almost", "about", "around", "against", "without", "within", "between", "before", "after", "being", "going",
        "coming", "saying", "doing", "getting", "having", "making", "taking", "looking", "player", "silence", "distance", "entrance",
        "business", "witness", "harness", "fortress", "wilderness", "goodness", "darkness", "unless", "across", "yours", "theirs"}
_WORD = re.compile(r"[A-Za-z][a-z']+")


def _suffixed(w: str) -> bool:
    return any(w.endswith(s) and len(w) > len(s) + 2 for s in W.get("suffixes", []))


def _stem(lw: str, seed: set[str]) -> str:
    """'steadily', 'weariness' and 'folks' count as 'steady', 'weary' and 'folk' when those are seed words."""
    if lw in seed:
        return lw
    for suf in ("ness", "ly", "s"):
        if lw.endswith(suf) and len(lw) > len(suf) + 2:
            b = lw[:-len(suf)]
            for cand in (b, b[:-1] + "y" if b.endswith("i") else b, b + "e"):
                if cand in seed:
                    return cand
    return lw


def reduce(text: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """(f761) What the watch reads of a passage: its words of four letters or more, in lower case and never stemmed (the seed words
    are data and may change between sittings), each once, as (seen in lower case, seen capitalised inside a sentence and never in
    lower case here, seen only capitalised where a sentence or a quote begins). A shorter word is never worn and never a name."""
    lower, caps, starts = set(), set(), set()
    for m in _TOKEN.finditer(text or ""):
        w = m.group(2)
        lw = w.lower()
        if len(lw) < 4:
            continue
        if w[0].islower():
            lower.add(lw)
        elif m.group(1) is None:                              # (an empty match of ^ is still a sentence start)
            caps.add(lw)
        else:
            starts.add(lw)
    caps -= lower
    return tuple(sorted(lower)), tuple(sorted(caps)), tuple(sorted(starts - lower - caps))


class Watch:
    """The last `keep` passages, each as reduce() reads it, and the words they leaned on."""

    def __init__(self, seed: list[str] | None = None, keep: int | None = None):
        self.passages: deque[tuple] = deque(maxlen=keep or int(W.get("keep", 30)))
        self.seed = set(seed if seed is not None else W.get("seed", []))

    def add(self, text: str) -> None:
        if (text or "").strip():
            self.passages.append(reduce(text))

    def rows(self) -> list[list[list[str]]]:
        """(f761) The kept passages as the save's row holds them."""
        return [[list(part) for part in p] for p in self.passages]

    @classmethod
    def load(cls, rows: list, seed: list[str] | None = None, keep: int | None = None) -> "Watch":
        """(f761) A watch read back from its row (rows()), held to today's `keep`."""
        w = cls(seed, keep)
        for p in rows or []:
            lower, caps, starts = p
            w.passages.append((tuple(map(str, lower)), tuple(map(str, caps)), tuple(map(str, starts))))
        return w

    def _names(self) -> set[str]:
        """Words seen capitalised inside a sentence and never in lower case are names: never worn, whatever the count. A capital at the
        start of a sentence or a quote says nothing."""
        caps, lower = set(), set()
        for p_lower, p_caps, _ in self.passages:
            lower.update(p_lower)
            caps.update(p_caps)
        return caps - lower

    def counts(self, keep: tuple[str, ...] | list[str] = ()) -> dict[str, int]:
        """How many of the kept passages each wearable word appears in."""
        skip = {w.lower() for k in keep for w in _WORD.findall(k or "")} | STOP
        names = self._names()
        out: dict[str, int] = {}
        for p in self.passages:
            seen = set()
            for lw in (w for part in p for w in part):
                base = _stem(lw.strip("'"), self.seed)
                if base in seen or base in skip or base in names or len(base) < 4:
                    continue
                if base in self.seed or _suffixed(base):
                    seen.add(base)
            for b in seen:
                out[b] = out.get(b, 0) + 1
        return out

    def worn(self, keep: tuple[str, ...] | list[str] = ()) -> list[str]:
        """The words to hand over: in at least `least` of the kept passages, the `top` most used, most used first."""
        least, top = int(W.get("least", 4)), int(W.get("top", 8))
        if len(self.passages) < least:
            return []
        c = self.counts(keep)
        return [w for w, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])) if n >= least][:top]


def leaned_on(text: str, worn: list[str]) -> list[str]:
    """Which of the worn words a draft uses: the word, or its plural, -ly, -ness, -ed or -ing form ('wearily' leans on 'weary')."""
    low = (text or "").lower()
    out = []
    for w in worn:
        stem = re.escape(w[:-1]) + "[yi]" if w.endswith("y") else re.escape(w)
        if re.search(rf"\b{stem}(s|ly|ness|ed|ing|er|est)?\b", low):
            out.append(w)
    return out

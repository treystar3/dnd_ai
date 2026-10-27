"""(f349) The worn-word watch: which words the writing has leaned on lately, found rather than listed.

Why: a fixed ban list ages (the model finds the next "steady") and a quota ("fewer than N") is not writing. Instead the engine keeps the
last few dozen passages and counts, per passage, the words of the kind that wear out - manner words and the suffixed adjectives, adverbs
and abstractions ("unreadable", "steadily", "weariness") - and hands the narrator the handful it has used most, as WORDS YOU HAVE WORN
OUT. Nouns of the scene (the smith, the gate) are never on the list: they are facts, not habits. Two watches run, one for prose and one
for what people say, because "folk" wears out in mouths and "expression" wears out in frames.

The rules live in data/rules/voice.yaml under `worn`: the seed words, the suffixes, how many passages are kept, how many passages a word
must appear in and how many words are handed over. scenes/voice.fresh asks for one rewrite when a draft leans on two or more of them."""
from __future__ import annotations

import re
from collections import deque

from engine.voice_rules import V

W = V.get("worn", {})
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


class Watch:
    """The last `keep` passages and the words they leaned on."""

    def __init__(self, seed: list[str] | None = None, keep: int | None = None):
        self.texts: deque[str] = deque(maxlen=keep or int(W.get("keep", 30)))
        self.seed = set(seed if seed is not None else W.get("seed", []))

    def add(self, text: str) -> None:
        if (text or "").strip():
            self.texts.append(text)

    def _names(self) -> set[str]:
        """Words seen capitalised inside a sentence and never in lower case are names: never worn, whatever the count. A capital at the
        start of a sentence or a quote says nothing."""
        caps, lower = set(), set()
        for t in self.texts:
            for m in re.finditer(r"(^|[.!?:;]\s+|[\"\u201c(]\s*)?([A-Za-z][a-z']+)", t):
                w = m.group(2)
                if w[0].islower():
                    lower.add(w.lower())
                elif m.group(1) is None:                      # (an empty match of ^ is still a sentence start)
                    caps.add(w.lower())
        return caps - lower

    def counts(self, keep: tuple[str, ...] | list[str] = ()) -> dict[str, int]:
        """How many of the kept passages each wearable word appears in."""
        skip = {w.lower() for k in keep for w in _WORD.findall(k or "")} | STOP
        names = self._names()
        out: dict[str, int] = {}
        for t in self.texts:
            seen = set()
            for w in _WORD.findall(t):
                lw = w.lower().strip("'")
                base = _stem(lw, self.seed)
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
        if len(self.texts) < least:
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

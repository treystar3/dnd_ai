"""What has been asked of a speaker, and what they answered: kept by the engine, for every speaker (Maren and the hires alike).

When the player asks much the same thing again, the speaker is not left to notice it, and repetition is not left to a rule that refuses the
answer until the model gives up. The engine finds the earlier question by meaning, and the request says so plainly: asked this before, this
many times, and what was answered. The reply gives the same facts again, usually shorter; the repetition guard compares it with their other
recent lines but never with that earlier answer, since the same answer to the same question is the right one ("A rank. Still.")."""
from __future__ import annotations

import re

import config

KEEP = 20


def _norm(t: str) -> set[str]:
    from engine.banter import STOP
    return set(w.split("'")[0] for w in re.findall(r"[a-z']{3,}", (t or "").lower())) - STOP - {"again", "tell", "please"}


QUESTION = re.compile(r"\?\s*[\"']?\s*$|^\W*(?:who|what|where|when|why|how|which|whose|do|does|did|is|are|was|were|can|could|would|will|"
                      r"have|has|had|should|shall|may|might|tell me|any)\b", re.I)


def is_question(text: str) -> bool:
    """(f422) Only a question can be asked again: 'Thanks, Odly' and 'Let's go' were matched to earlier lines and answered as asked
    before, on some sixty lines a night that asked nothing."""
    return bool(QUESTION.search((text or "").strip()))


def find(holder: dict, text: str) -> dict | None:
    """The earlier question this is much the same as, or None. By meaning when the helper model is there, else by shared words."""
    log = holder.get("convo", [])
    if not log or not (text or "").strip() or not is_question(text):
        return None
    from llm import embed
    sims = embed.whole(text, [e["asked"] for e in log])
    if sims is not None:
        best = max(range(len(log)), key=lambda i: sims[i])
        return log[best] if sims[best] >= config.SIM_ASKED else None
    words = _norm(text)
    if not words:
        return None
    for e in reversed(log):
        o = _norm(e["asked"])
        if o and len(words & o) / len(words | o) >= 0.5:
            return e
    return None


def record(holder: dict, text: str, reply: str, now: int) -> None:
    """After they answer: the question and the answer are kept (the latest answer, if asked again). Only a question is kept."""
    if not (text or "").strip() or not is_question(text):
        return
    e = find(holder, text)
    if e:
        e["times"] = e.get("times", 1) + 1
        e["answer"] = (reply or e.get("answer", ""))[:300]
        e["at"] = now
        if reply:
            e.setdefault("answers", [e["answer"]] if e.get("answer") else [])
            e["answers"] = (e["answers"] + [reply[:300]])[-ANSWERS_KEPT:]
    else:
        holder.setdefault("convo", []).append({"asked": text[:200], "answer": (reply or "")[:300], "answers": [reply[:300]] if reply else [],
                                               "times": 1, "at": now})
        del holder["convo"][:-KEEP]


ORDINAL = {2: "a second", 3: "a third", 4: "a fourth", 5: "a fifth"}


def again_fact(e: dict) -> str:
    n = e.get("times", 1) + 1
    when = ORDINAL.get(n, f"the {n}th")
    return f"They have asked this before; this is {when} time. They asked: \"{e['asked']}\". What you answered last time: {e['answer'] or '(nothing)'}"


def again_rule(manner: str) -> str:
    """Asked the same thing again: the same facts, usually shorter. That they asked before may be noticed, in their way, but it is not the
    subject. Saying the same thing again is allowed here (the answer is not checked against the last one). (f422) "they are still true"
    was read as a line to say."""
    return ("Answer with the same facts as before. Usually shorter. You may notice they asked before, as you would ("
            + manner + "), but the asking again is not what the reply is about.")


ANSWERS_KEPT = 6


def others_lately(said: list[str], before: dict | None) -> list[str]:
    """What a repeat is checked against: their other recent lines, never any answer they have given to this same question (asked a third
    time, the first answer is as much 'the answer' as the second)."""
    given = {a[:300] for a in (before or {}).get("answers") or []} | ({before["answer"][:300]} if before and before.get("answer") else set())
    return [s for s in said if s[:300] not in given]

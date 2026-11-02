"""(f460) A question the world asks in the middle of a turn ends the turn; the answer is the next line typed. (The rebuild's Stage 3,
Bundle C decision 10: a question inside a turn ends the operation, and the answer is the next input.) Before this, eleven places read the
answer at once with console.ask inside the turn: a y/n before an enchantment, an allocation or a discarded key item, which fork to
take, which roll to keep and whether to take the new ones, how to meet the watch, the stranger's two questions and the Executioner's one
in the quest Orenna, and the seal in the fight with the High Keeper. Each now asks with WorldScene.ask_next(kind, question, **data) and
finishes in on_answer_<kind>(asked, text) when the next line comes.

The question is kept in the save (storage/campaign.py save_question: the kv row `question`, present only while one stands), so a turn
rolled back takes its question back with it, a save closed on a question asks it again when it opens (run()), and a #command typed
meanwhile runs and leaves it standing. scenes/world.py handle() hands the next line to the handler before anything else reads it. A
handler returns True when the line was the answer (the turn is spent on it), False when it was not and the handler has said so in the
world's words, None when it was not and nothing was said: then handle() lets the question go with one of the lines here (dropped), and
either way the line is read as new. A question that needs a particular answer (a fork, a roll, the watch) is asked again instead, up to
TRIES lines, and then its own default applies, as the loops it replaces did. Maren's tutorial keeps its seven console.ask calls until f461.

The words that count as yes or no, TRIES and the dropped lines are in data/rules/questions.yaml, checked at startup (problems)."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml
from engine import streams
from engine.failures import DASH, MACHINERY

Q = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "questions.yaml").read_text(encoding="utf-8"))
TRIES: int = int(Q.get("tries") or 3)
_last = ""


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", (text or "").lower()).split())


def _opens_with(text: str, phrase: str) -> bool:
    return bool(phrase) and (text == phrase or text.startswith(phrase + " "))


def yes_no(text: str) -> bool | None:
    """True for a line that says yes, False for one that says no, None for a line that is something else (an action, a question of the
    player's own). The longest opening that matches wins: "I do not" is a no though "I do" is a yes; "yesterday" is neither."""
    t = _norm(text)
    best, polarity = "", None
    for phrases, value in ((Q.get("yes") or [], True), (Q.get("no") or [], False)):
        for p in phrases:
            p = _norm(str(p))
            if _opens_with(t, p) and len(p) > len(best):
                best, polarity = p, value
    return polarity


def dropped(rng: random.Random | None = None) -> str:
    """The line read when a yes-or-no question was met with something else: the question is let go. Never the one shown last."""
    global _last
    lines_ = Q["dropped"]
    pick = [l for l in lines_ if l != _last] or lines_
    _last = (rng or streams.get("scene")).choice(pick)
    return _last


def problems(data: dict | None = None) -> list[str]:
    """For engine/data_check.py: a whole number of tries, enough words each way and none counting both ways, and at least six dropped
    lines, all different, none machinery, none with a dash, none a question."""
    d = Q if data is None else data
    bad = []
    if not isinstance(d, dict):
        return ["questions.yaml: needs a mapping"]
    t = d.get("tries")
    if not isinstance(t, int) or isinstance(t, bool) or t < 1:
        bad.append("questions.yaml tries: needs a whole number of 1 or more")
    for key in ("yes", "no"):
        words = d.get(key)
        if not isinstance(words, list) or len(words) < 3 or not all(isinstance(w, str) and w.strip() for w in words):
            bad.append(f"questions.yaml {key}: needs at least three words")
    both = {_norm(str(w)) for w in (d.get("yes") or [])} & {_norm(str(w)) for w in (d.get("no") or [])}
    if both:
        bad.append(f"questions.yaml: {sorted(both)} count as both yes and no")
    lines_ = d.get("dropped")
    if not isinstance(lines_, list) or len(lines_) < 6 or not all(isinstance(l, str) and l.strip() for l in lines_):
        bad.append("questions.yaml dropped: needs at least 6 lines of text")
        return bad
    if len({l.strip().lower() for l in lines_}) != len(lines_):
        bad.append("questions.yaml dropped: a line is there twice")
    for l in lines_:
        hit = MACHINERY.search(l)
        if hit:
            bad.append(f"questions.yaml dropped: '{l}' speaks of the machinery ('{hit.group(0)}'); say it in the world's words")
        if DASH.search(l):
            bad.append(f"questions.yaml dropped: '{l}' carries a dash; the page carries none")
        if "?" in l:
            bad.append(f"questions.yaml dropped: '{l}' asks something; it lets a question go")
    return bad

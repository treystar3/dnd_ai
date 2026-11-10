"""(f486, Bundle D) What a speaker is given for one reply: chosen from the records for the line in front of them (data/rules/brief.yaml).

Pure: nothing here writes, and nothing is kept between replies. lore() picks the lore that bears on this line, every clue held, and one
line naming the rest; asked() says whether a facet (the town's list, the land, the guild board) comes in full for this line or this
role; pronoun() is the character's, for the block about the one in front of them."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from core import yamlio

ROOT = Path(__file__).resolve().parent.parent
_B: dict | None = None
_WORD = re.compile(r"[a-z]{4,}")


def rules(profile: str = "townsfolk") -> dict:
    global _B
    if _B is None:
        _B = yamlio.safe_load((ROOT / "data" / "rules" / "brief.yaml").read_text(encoding="utf-8")) or {}
    return _B.get(profile) or {}


def _words(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


def lore(facts: list, line: str, recent: list[str] = (), profile: str = "townsfolk") -> tuple[list, str]:
    """(shown, index): every clue fact (id clue:...), then at most `lore` facts that bear on the line and the last lines of the talk, in a
    fixed order (score, then id); the index names each other fact they know by its subject, so asked about it they know it is theirs."""
    R = rules(profile)
    clues = [f for f in facts if str(f.id).startswith("clue:")]
    rest = [f for f in facts if not str(f.id).startswith("clue:")]
    query = " ".join([line or ""] + [str(x) for x in list(recent)[-int(R.get("recent_lines", 4)):]])
    q = _words(query)
    scored = sorted(((len(q & _words(f.text)), str(f.id), f) for f in rest), key=lambda x: (-x[0], x[1]))
    pre = [f for n, _, f in scored if n >= 1][: int(R.get("prefilter", 12))]
    from engine import relevance
    order = relevance.ranked(query, [f.text for f in pre]) if pre else []
    by_text = {}
    for f in pre:
        by_text.setdefault(f.text, f)
    picked = [by_text[t] for t in order if t in by_text][: int(R.get("lore", 4))]
    others = [f for f in rest if f not in picked]
    index = ""
    if others:
        index = f"{R.get('index_label', 'YOU ALSO KNOW OF')}: " + "; ".join(_subject(f) for f in others)
    return clues + picked, index


def _subject(f) -> str:
    """What a fact is about, in a few words: its id read as words."""
    return str(f.id).replace("_", " ").replace(":", " ").strip()


def asked(facet: str, text: str, role: str = "", profile: str = "townsfolk") -> bool:
    """Whether this facet comes in full for this line: the line is about it, or the role's work is it."""
    R = rules(profile)
    if role and role in ((R.get("always") or {}).get(facet) or []):
        return True
    said = (text or "").lower().replace("\u2019", "'")
    for phrase in R.get("about_them") or []:                    # (f488) "where are you from?" asks about them, not the town
        said = said.replace(str(phrase).lower(), " ")
    words = set(re.findall(r"[a-z]+", said))
    return bool(words & set((R.get("asked") or {}).get(facet) or []))


def _has(phrase: str, said: str) -> bool:
    return bool(re.search(r"(?<![a-z])" + re.escape(phrase.lower()) + r"(?![a-z])", said))


def promised(*lines: str) -> bool:
    """(f493) Whether what was said to a townsperson may promise them something (brief.yaml promise.words): only then does their reply
    ask what was promised (llm/contracts.py NPCReplyPromised)."""
    said = " ".join(lines).lower().replace("’", "'")
    return any(_has(str(w), said) for w in (rules().get("promise") or {}).get("words") or [])


def promise_kept(text: str) -> str:
    """(f493) What a reply says was promised, as it is kept: its first clause, in a few words, or nothing when it is the model's note to
    itself ('none_given_this_turn', 'empty', 'Wait, let me re-read the rules')."""
    P = rules().get("promise") or {}
    text = str(text or "")
    for end in P.get("clause_ends") or []:
        text = text.split(str(end))[0]
    text = text.strip().strip(".,;:!?\"'“” ").strip()
    low = text.lower()
    if (not text or any(c in text for c in P.get("not_in") or []) or any(_has(str(w), low) for w in P.get("not_one") or [])
            or len(text.split()) > int(P.get("max_words") or 0)):
        return ""
    return text


def pronoun(ws, char_id: str) -> str:
    """The character's pronoun, as the one in front of a speaker: theirs, by id."""
    from engine import truth
    for c in getattr(ws, "characters", lambda: [ws.player.character])():
        if c.id == char_id:
            return truth.player_pronoun(c)
    return truth.player_pronoun(ws.player.character)


def page(log: list, profile: str = "hire") -> None:
    """(f488) A talk window cut only when full: past `talk_window` lines it keeps its last `talk_turn`, a page turned. Between turns the
    lines shown only grow, so a reply's talk is the last reply's and what was said since."""
    R = rules(profile)
    if len(log) > int(R.get("talk_window", 8)):
        del log[:-int(R.get("talk_turn", 4))]


def problems() -> list[str]:
    bad = []
    H = rules("hire")
    for k in ("voice_habits", "talk_window", "talk_turn"):
        if not isinstance(H.get(k), int) or H.get(k) < 1:
            bad.append(f"brief.yaml hire.{k}: a whole number above zero")
    if isinstance(H.get("talk_turn"), int) and isinstance(H.get("talk_window"), int) and H["talk_turn"] >= H["talk_window"]:
        bad.append("brief.yaml hire.talk_turn: fewer than talk_window, or the page never turns")
    R = rules()
    for k in ("lore", "prefilter", "recent_lines"):
        if not isinstance(R.get(k), int) or R.get(k) < 1:
            bad.append(f"brief.yaml townsfolk.{k}: a whole number above zero")
    if R.get("many_addressees", "one_call") not in ("one_call", "flat_each"):
        bad.append("brief.yaml townsfolk.many_addressees: one_call or flat_each")
    for facet in ("land", "town", "board"):
        if not (R.get("asked") or {}).get(facet):
            bad.append(f"brief.yaml townsfolk.asked.{facet}: needs its words")
    P = R.get("promise") or {}                                  # (f493)
    for k in ("max_chars", "max_words"):
        if not isinstance(P.get(k), int) or P.get(k) < 1:
            bad.append(f"brief.yaml townsfolk.promise.{k}: a whole number above zero")
    for k in ("words", "clause_ends", "not_one", "not_in"):
        if not isinstance(P.get(k), list) or not P.get(k) or not all(isinstance(w, str) and w for w in P[k]):
            bad.append(f"brief.yaml townsfolk.promise.{k}: a list of words")
    if isinstance(P.get("words"), list) and any(w != w.lower() for w in P["words"] if isinstance(w, str)):
        bad.append("brief.yaml townsfolk.promise.words: lower case (the line is read in lower case)")
    return bad

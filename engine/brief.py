"""(f486, Bundle D) What a speaker is given for one reply: chosen from the records for the line in front of them (data/rules/brief.yaml).

Pure: nothing here writes, and nothing is kept between replies. lore() picks the lore that bears on this line, every clue held, and one
line naming the rest; asked() says whether a facet (the town's list, the land, the guild board) comes in full for this line or this
role; pronoun() is the character's, for the block about the one in front of them."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_B: dict | None = None
_WORD = re.compile(r"[a-z]{4,}")


def rules(profile: str = "townsfolk") -> dict:
    global _B
    if _B is None:
        _B = yaml.safe_load((ROOT / "data" / "rules" / "brief.yaml").read_text(encoding="utf-8")) or {}
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
    words = set(re.findall(r"[a-z]+", (text or "").lower()))
    return bool(words & set((R.get("asked") or {}).get(facet) or []))


def pronoun(ws, char_id: str) -> str:
    """The character's pronoun, as the one in front of a speaker: theirs, by id."""
    from engine import truth
    for c in getattr(ws, "characters", lambda: [ws.player.character])():
        if c.id == char_id:
            return truth.player_pronoun(c)
    return truth.player_pronoun(ws.player.character)


def problems() -> list[str]:
    bad = []
    R = rules()
    for k in ("lore", "prefilter", "recent_lines"):
        if not isinstance(R.get(k), int) or R.get(k) < 1:
            bad.append(f"brief.yaml townsfolk.{k}: a whole number above zero")
    if R.get("many_addressees", "one_call") not in ("one_call", "flat_each"):
        bad.append("brief.yaml townsfolk.many_addressees: one_call or flat_each")
    for facet in ("land", "town", "board"):
        if not (R.get("asked") or {}).get(facet):
            bad.append(f"brief.yaml townsfolk.asked.{facet}: needs its words")
    return bad

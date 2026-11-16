"""(f649) Who a typed line speaks to, read from where a name stands in it, never from a name anywhere in it.

A line speaks to someone when a sentence or the words said begin with their name ("Kennard, guard me", "Kennard guard me", "Kennard
attacks the wolf", "Kennard and Raerei, hold back"), when a name said alone begins the next sentence's words ("Kennard! Fall back!"),
when a sentence calls them at its end or in its middle ("Cover me, Kennard!", "Cover Raerei, Kennard, while I take wolf 1"), when the
player tells, orders, asks, shouts or signals to them ("I tell Almund to take wolf 1", "I shout for Kennard to fall back", "I nod at
Kennard: take wolf 1"), when words in quotes are said to them by the sentence after ('"Cover Raerei," I tell Kennard.'), or when it
begins with the whole party ("Everyone, hold back"). A name followed by how they are ("Raerei is down") is spoken of, not to, and so
is any name elsewhere ("behind Kennard's shield"). What the player says they do themself in the same words ("Kennard, take wolf 1 and
I'll take wolf 0", "Kennard, I'll take wolf 1!") is cut off what is said to them and kept as the player's own (Address.mine).
The names of the player's own abilities and gear are taken out of a line before a word in it is read for what it asks (without):
"Guard Breaker" is a blow, "Shield Wall" a stance, never an order to guard (docs/design/21_play_faults_plan.md, B1)."""
from __future__ import annotations

import re
from typing import NamedTuple

PARTY = "*"                                          # who a line speaks to when it speaks to the whole party
APOS, DASH, QUOTES = chr(0x2019), chr(0x2014), '"' + chr(0x201C) + chr(0x201D)
GROUP = r"everyone|everybody|all of you|you all|y'all|party|team|you two|you both|you three|both of you|the both of you"
LEAD = r"(?:and\s+|now\s+|then\s+|so\s+|quick,?\s+)?"
TELLING = (r"(?:i\s+)?(?:tell|order|ask|have|get|command|urge|beg|shout|yell|call|cry|whisper|hiss|bark)(?:s|ed)?(?:\s+out)?\s+"
           r"(?:(?:for|to|at|over to|towards?)\s+)?")
SIGNING = r"(?:i\s+)?(?:signal|nod|gesture|motion|wave|beckon|point|turn|look|glance)(?:s|ed)?\s+(?:(?:for|to|at|over to|towards?)\s+)?"
CAUSING = r"(?:i\s+)?(?:have|has|get|gets|let|lets|make|makes)\s+"     # "I have Kennard guard me", "I let Kennard take wolf 1"
STATE = re.compile(r"^(?:is|was|isn't|wasn't|has|had|hasn't|looks|seems|lies|lay|stands there|sits|sat|stays down|groans|gasps|bleeds|'s)\b")
FIRST = (r"(?:i'll|i will|i shall|let me|myself|i(?!'m|'d|'ve)\s+(?!need\b|want\b|would\b|am\b|was\b|have\b|had\b|can'?t\b|cannot\b|"
         r"must\b|think\b|know\b|see\b|hope\b|beg\b|told\b|said\b|mean\b)\w+)")     # the player doing a thing; "I'm done for", "I need you to" are said
MINE = re.compile(rf"\s*(?:,\s*)?\b(?:and|while|then|so|but|as)\s+(?=(?:then\s+)?{FIRST})|,\s*(?=(?:then\s+)?{FIRST})")
BACK = re.compile(rf",\s*(?!(?:and\s+|then\s+)?{FIRST})")             # where the words to the companion start again after the player's part


class Address(NamedTuple):
    who: tuple                                       # the ids spoken to, or (PARTY,)
    said: str                                        # what is said to them, lowered
    clause: str                                      # the clause it is said in, as typed
    mine: str                                        # what the player says they do themself in it ('' when nothing)


class Part(NamedTuple):
    text: str                                        # a sentence of the line, or the words said in it
    quoted: bool                                     # it was words in quotes


def _parts(text: str) -> list[Part]:
    """The sentences of a line and the words said in it, each its own, saying which were in quotes."""
    out = []
    for k, part in enumerate(re.split(f"[{QUOTES}]", (text or "").replace(APOS, "'"))):
        out += [Part(c.strip(), k % 2 == 1) for c in re.split(r"(?<=[.!?;])\s+|(?<=[.!?;])$", part) if c.strip(" .!?;,")]
    return out


def clauses(text: str) -> list[str]:
    """The sentences of a line and the words said in it, each its own: a quote is cut out of the narration around it."""
    return [c for c, _quoted in _parts(text)]


def without(text: str, names) -> str:
    """The line with each of these names (the player's abilities, their gear) taken out, the longest first, so no word of theirs is
    read as what the line asks."""
    for n in sorted({n.strip() for n in names if n and n.strip()}, key=len, reverse=True):
        text = re.sub(rf"(?<![\w']){re.escape(n)}(?![\w'])", " ~ ", text, flags=re.I)
    return text


def _alt(forms) -> str:
    return "|".join(re.escape(f) for f in sorted({f.lower().replace(APOS, "'") for f in forms if f}, key=len, reverse=True))


def _split_mine(said: str) -> tuple[str, str]:
    """What is said to them, and what the player says they do themself in the same words: from "and I", "while I" or a comma before
    an "I", up to where the words to them start again ("Kennard, while I strike wolf 0, take wolf 1")."""
    if re.match(rf"^\s*{FIRST}", said):              # all theirs: "I yell, and charge wolf 1"
        return "", said
    m = MINE.search(said)
    if not m:
        return said, ""
    start, said_end = m.end(), m.start()
    back = BACK.search(said, start)
    end = back.start() if back else len(said)
    rest = said[back.end():] if back else ""
    return (said[:said_end] + (", " if said[:said_end].strip() and rest else "") + rest).strip(" ,"), said[start:end]


def addressed(text: str, people: dict, others=(), asks=None) -> list[Address]:
    """Each clause of the line that speaks to someone. people: {id: [the forms of their name, the full name first]}. others: names
    that are not these people however they begin ("Wolf 1" when a companion is called Wolf). asks: whether words ask a companion
    something (the fight's order words); a sentence that asks, after one said to someone, is said to them too ("Kennard, I'm hurt.
    Cover me!")."""
    names = "|".join(f"(?:{_alt(f)})" for f in people.values() if _alt(f))
    if not names:
        return []
    many = rf"(?:{names})(?:\s*(?:,|and|,\s*and)\s*(?:{names}))*"
    not_them = _alt(others)

    def who_in(s: str) -> tuple:
        return tuple(pid for pid, forms in people.items() if _alt(forms) and re.search(rf"(?<![\w'])(?:{_alt(forms)})(?![\w'])", s))

    out, waiting, carry, last_quote = [], None, None, None
    for clause, quoted in _parts(text):
        low = " ".join(clause.lower().split())
        foe_first = bool(not_them and re.match(rf"^{LEAD}(?:{not_them})(?![\w'])", low))    # "Wolf 1 is on me": the foe, not a companion
        alone = None if foe_first else (re.match(rf"^{LEAD}({many})[\s,:;!.{DASH}-]*$", low) or re.match(rf"^{LEAD}({GROUP})[\s,:;!.]*$", low))
        if alone:                                         # a name said alone: the words that follow are to them
            waiting = who_in(alone.group(1)) or (PARTY,)
            continue
        found, quote = None, None
        m = None if foe_first else re.match(rf"^{LEAD}((?:{names}))(?![\w'])[\s,:;!{DASH}-]*(.*)$", low)
        if m and m.group(2) and not STATE.match(m.group(2)):
            heads, said = [m.group(1)], m.group(2)
            more = re.match(rf"^(?:and\s+)?((?:{names}))\s*[,:;!]\s*(.*)$", said)     # "Kennard, Raerei, hold back": a list ends at its comma
            while more:
                heads.append(more.group(1))
                said = more.group(2)
                more = re.match(rf"^(?:and\s+)?((?:{names}))\s*[,:;!]\s*(.*)$", said)
            joined = re.match(rf"^and\s+((?:{names}))(?![\w'])\s+(.*)$", said)        # "Kennard and Raerei take wolf 1"
            if joined and not STATE.match(joined.group(2)):
                heads.append(joined.group(1))
                said = joined.group(2)
            found = (who_in(" , ".join(heads)), said)
        if found is None:
            m = (re.match(rf"^{TELLING}({many})(?![\w'])\s*(?:(?:to\b|:|,)\s*(.*?))?[\s.!;]*$", low)
                 or re.match(rf"^{CAUSING}({many})(?![\w'])\s+(.*?)[\s.!;]*$", low)
                 or re.match(rf"^{SIGNING}({many})(?![\w'])\s*(?::|to\b|,(?!\s*(?:and|then|so|before)\b)(?!\s*{FIRST}))\s*(.*?)[\s.!;]*$", low))
            if m:                                         # told "to" do it; a sign needs its words ("I look at Kennard, then take" is the player's)
                said = m.group(2) or ""
                quote = last_quote                        # '"Cover Raerei," I tell Kennard.'
                found = (who_in(m.group(1)), said)
        if found is None:
            m = re.match(rf"^(.*?\S)\s*,\s*({many})\s*,\s*(.*)$", low)
            if m and not STATE.match(m.group(3)):
                found = (who_in(m.group(2)), f"{m.group(1)}, {m.group(3)}")
        if found is None:
            m = re.match(rf"^(.*\S)\s*,\s*({many})\s*[.!?]*$", low)
            if m:
                found = (who_in(m.group(2)), m.group(1))
        if found is None:
            m = re.match(rf"^{LEAD}(?:{GROUP})\b[\s,:;!]*(.*)$", low)
            if m and m.group(1):
                found = ((PARTY,), m.group(1))
        if found is None and waiting:                     # "Kennard!" then "I yell, and charge" is all the player's (_split_mine)
            found = (waiting, low)
        if found is None and carry and asks is not None and asks(low) and not re.match(rf"^\s*{FIRST}", low):
            found = (carry, low)
        waiting = None
        carry = found[0] if found is not None else None
        last_quote = clause if quoted and found is None else None
        if found is not None and found[0]:
            said, mine = _split_mine(found[1])
            if not said.strip(" .!?;,") and quote is not None:          # the words told are the quote before: '"Hold back," I tell Kennard'
                said = " ".join(quote.lower().split())
            mine = mine.strip(" .,;:!")
            typed = " ".join(clause.split())
            at = typed.lower().rfind(mine) if mine else -1
            out.append(Address(found[0], said, clause, typed[at:at + len(mine)] if at >= 0 else mine))
    return out


def spoken_of(text: str, people: dict) -> list[str]:
    """The ids of everyone named in a stretch of the line, in the order they are named."""
    low = " " + (text or "").lower().replace(APOS, "'") + " "
    hits = []
    for pid, forms in people.items():
        a = _alt(forms)
        m = re.search(rf"(?<![\w'])(?:{a})(?!\w|'(?!s\b))", low) if a else None          # "Raerei's" is Raerei
        if m:
            hits.append((m.start(), pid))
    return [pid for _, pid in sorted(hits)]

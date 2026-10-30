"""(f412) The people's names and pronouns, kept as they were given. A night's three runs wrote one companion's name six ways (Zurra as
Zorra, Zumra, Zerra, Zwra; Thavathiel's family name as Liaror ten times; Lookie Doodleflick as Dodgeflick), and a woman who fought beside
the player became 'he' in the middle of fights, and 'grips their sword hilt' in her gestures.

Two mends, made in place, without asking the model again:
- a NAME the model was told, written wrong: every name an answer may use is in its request, so a word in the answer that is not one of
  them, is no English word, and is one or two letters off a name in the request is that name (mend_answer, at the gateway);
- a PRONOUN for someone whose pronoun the game knows: a gesture's 'their' for a he or a she, and 'Odly lowers his blade' for a she
  (mend_pronouns, on the way to the screen, with the cast the scene keeps in CAST)."""
from __future__ import annotations

import collections
import re
from pathlib import Path

REPAIRS: collections.Counter = collections.Counter()
CAP = re.compile(r"\b[A-Z][a-z]{3,}\b")
WORD = re.compile(r"\b[a-z]+\b")
CAST: dict[str, str] = {}                 # first name -> 'he' | 'she' | 'they': the player's companions, set by the scene each turn
_VOCAB: set[str] = set()


def vocab() -> set[str]:
    """Every word the game's own data writes in lower case: the ordinary words, so 'Wind' at the head of a sentence is never taken for the
    river Wend. Names are written capitalised there, so they are not in it."""
    if not _VOCAB:
        root = Path(__file__).resolve().parent.parent / "data"
        for p in root.rglob("*.yaml"):
            try:
                _VOCAB.update(WORD.findall(p.read_text(encoding="utf-8")))
            except OSError:
                pass
    return _VOCAB


def _distance(a: str, b: str, most: int) -> int:
    """Edits (insert, delete, change, swap two neighbours) between a and b, or most + 1 once it is past most."""
    if abs(len(a) - len(b)) > most:
        return most + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > most:
            return most + 1
        prev2, prev = prev, cur
    return prev[-1]


def known_names(request: str) -> set[str]:
    """The names in a request: capitalised words that never appear there in lower case (so not 'The' or 'Rain'), and at least once in
    the middle of a sentence (so not an instruction's first word, 'Describe' or 'Respond')."""
    lower = set(WORD.findall(request))
    out = set()
    for m in CAP.finditer(request):
        w = m.group(0)
        if w in out or w.lower() in lower:
            continue
        before = request[:m.start()].rstrip(" \t")
        if before and before[-1] not in ".!?\n\"":                    # after a label's colon is a name's place too ('SPEAKERS: Zurra')
            out.add(w)
    return out


def near_miss(word: str, known: set[str], plain: set[str]) -> str:
    """The known name this word is a misspelling of, or ''. Not a word the request or answer uses in lower case (an ordinary word at the
    head of a sentence), not one that only adds to or cuts the end of a name (Lanterns, Parth's), and the first letter the same."""
    if word in known or word.lower() in plain or word.lower() in vocab():
        return ""
    best, hits = "", 0
    for k in known:
        if k[0] != word[0] or k.startswith(word) or word.startswith(k):
            continue
        most = 1 if len(k) <= 6 else 2
        if _distance(word.lower(), k.lower(), most) <= most:
            best, hits = k, hits + 1
    return best if hits == 1 else ""                                   # two names it could be: leave it


def mend_text(text: str, known: set[str], plain: set[str]) -> str:
    out = text
    for w in set(CAP.findall(text)):
        k = near_miss(w, known, plain)
        if k:
            out = re.sub(rf"\b{w}\b", k, out)
            REPAIRS["name"] += 1
    return out


def mend_answer(value, request: str) -> None:
    """A model's answer, its prose fields mended in place: a name it was told, written wrong, written right."""
    from engine import hygiene
    known = known_names(request)
    if not known or value is None:
        return
    plain = set(WORD.findall(request))

    def walk(v) -> None:
        for key in list(getattr(type(v), "model_fields", {}) or {}):
            x = getattr(v, key, None)
            if isinstance(x, str) and key in hygiene.PROSE:
                setattr(v, key, mend_text(x, known, plain | set(WORD.findall(x))))
            elif isinstance(x, list):
                for j, y in enumerate(x):
                    if isinstance(y, str) and key in hygiene.PROSE:
                        x[j] = mend_text(y, known, plain | set(WORD.findall(y)))
                    elif hasattr(y, "model_fields"):
                        walk(y)
            elif hasattr(x, "model_fields"):
                walk(x)
    walk(value)


# ---------- pronouns ----------

POSSESSIVE = {"he": "his", "she": "her"}
SELF = {"he": "himself", "she": "herself"}
OTHERS = {"is", "was", "asks", "tells", "gives", "shows", "hands", "offers", "lets", "helps", "watches", "sees", "follows", "meets", "thanks",
          "takes", "calls", "names", "wants", "needs", "likes", "misses", "loves", "hates", "knows", "finds", "leaves", "joins", "pays"}


def set_cast(cast: dict[str, str]) -> None:
    CAST.clear()
    CAST.update({k: v for k, v in cast.items() if k and v in ("he", "she")})


def gesture(text: str, pronoun: str) -> str:
    """A gesture is the speaker's own: 'their' and 'themselves' in it are theirs, said with their pronoun when it is he or she."""
    if pronoun not in POSSESSIVE or not text:
        return text
    out = re.sub(r"\btheir\b", POSSESSIVE[pronoun], text)
    out = re.sub(r"\bthemsel(?:f|ves)\b", SELF[pronoun], out)
    if out != text:
        REPAIRS["pronoun"] += 1
    return out


def mend_pronouns(text: str) -> str:
    """'Odly lowers his blade' for a she: the possessive right after the subject's own verb is the subject's. Only the unambiguous turns
    are mended: 'his' and 'himself' for a she, 'herself' for a he ('her' after a verb can be someone else: 'Bram pushes her back')."""
    if not CAST or not text:
        return text
    out = text
    for name, p in CAST.items():
        if name not in out:
            continue
        wrong = r"(?:his|himself)" if p == "she" else r"herself"
        pat = re.compile(rf"\b({re.escape(name)}(?: [A-Z][a-z]+)?) (\w+s) ({wrong})\b")

        def fix(m: re.Match) -> str:
            if m.group(2) in OTHERS:                                    # 'Odly was his sister', 'Odly asks his name': someone else's
                return m.group(0)
            w = m.group(3)
            right = SELF[p] if w.endswith("self") else POSSESSIVE[p]
            return f"{m.group(1)} {m.group(2)} {right}"
        new = pat.sub(fix, out)
        if new != out:
            REPAIRS["pronoun"] += 1
            out = new
    return out

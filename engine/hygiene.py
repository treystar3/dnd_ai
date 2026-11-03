"""(f391) The output gate: the machinery never shows in the story (data/rules/hygiene.yaml).

Two nights of play put the game's workings in front of the player: a reasoning fragment and a JSON brace at the end of a passage,
"mud_r_{road}", "silks_1827359406-bdcc-...", 'find_the_sinkhole', a literal "\\n", "The player pulls out...", and "my own shadow" in
the narrator's voice. problem() finds these in the prose fields of a model's answer, so the gateway sends it back with a reason and the
model writes it again; clean() mends whatever still reaches the screen, on every line the player sees, and counts what it mended
(REPAIRS) so a night's summary can say how much got through."""
from __future__ import annotations

import collections
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
H = yaml.safe_load((ROOT / "data" / "rules" / "hygiene.yaml").read_text(encoding="utf-8"))
PROSE = set(H["prose_fields"])
NARRATOR = set(H["narrator_tasks"])
REPAIRS: collections.Counter = collections.Counter()      # what clean() mended on the way to the screen, by kind

JSON_BITS = re.compile(r'```|^\s*[\{\[]\s*"|"\s*,\s*"?[A-Za-z0-9_%]+"?\s*:\s|\{\s*"[A-Za-z_]+"\s*:|"\s*\}|\}\s*$|\}"\w')
PLACEHOLDER = re.compile(r"\{[A-Za-z_]+\}")
CODED = re.compile(r"\b[A-Za-z]+_[0-9a-f]{6,}(?:-[0-9a-f]+)*")             # silks_1827359406-bdcc-...
SNAKE = re.compile(r"(?<![#`/\w])[A-Za-z]+(?:_[A-Za-z0-9]+)+_*(?![\w{])")      # find_the_sinkhole, (f409) Right_Nickkelly (not #commands), (f431) window_pane_
# (f431) what got past both gates on the f425 night: "parchment,#her eyes", a passage cut off on "beside you,{", "]h1[", a line headed
# "REASON: ...", "kind: ambush, detail: 1 x ghost, creatures: ghost", '}"v1_0"'
STRAY = re.compile(r"(?<=[^\s#\w])#(?=[A-Za-z])|(?<=\s)#(?=\s)")
DANGLING = re.compile(r"[ \t]*[\{\[]+[ \t]*$|\]h\d+\[")
LABEL = re.compile(r"(?m)^[ \t]*(?:REASON|NOTE|KIND|DETAIL|SCENE|TITLE|VERDICT|MEANING|SUMMARY|CREATURES|SPEECH|GESTURE)\s*:.*$")
FIELDS = re.compile(r"\b(?:kind|detail|creatures|check|meets_role|title|scene)\s*:\s*[^,.;\n]+(?:,\s*(?:kind|detail|creatures|check|meets_role|title|scene)"
                    r"\s*:\s*[^,.;\n]+)+")
TRAILING = re.compile(r"\b([A-Za-z]+)_(?![\w{])")                         # arches_
COMMAND = re.compile(r"(#[a-z]+(?:\s+[A-Za-z0-9_<>]+)?)")
PLAYER = re.compile(r"\b([Tt])he player(?!s)(?!\s+of\b)('s)?(\s+([A-Za-z]+))?")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”'                                  # someone's words, or (f447) words written on a page:
                    r"|(?<![\w])'(?=\S)(?:[^']|'(?=\w))*?(?<=\S)'(?!\w)"      # in single quotes, its own apostrophes kept ('I'm done')
                    r"|‘(?:[^’]|’(?=\w))*’")
FIRST = re.compile(r"\b(I|[Mm]e|[Mm]y|[Mm]ine|[Mm]yself)\b")
# (f404) "[h4_damage_implied/hidden_by_rules? No wait, use events only.]": the model's note to itself. A bracket that is not a blow's tag
# and has the marks of one: an underscore, a question, a slash, a broken tag (h4...), or four words or more.
NOTE = re.compile(r"[ \t]*\[(?!\s*h\d+\s*\])(?=[^\]\n]*(?:_|\?|/|\bh\d|(?:\S+\s+){3}\S))[^\]\n]{1,240}\]")
# (f449) A stage direction the model wrote into a line, a whole sentence in round brackets ("(Lammer looks toward the stranger.)" in a
# hire's speech on the owner's log), is taken out: what someone does is the gesture's, and the player never reads a script's brackets.
# An aside that is part of the sentence ("(as you asked)") is left alone: no capital at its start, no full stop at its end.
STAGE = re.compile(r"[ \t]*\([ \t]*[A-Z][^()\n]{2,200}?[.!?][ \t]*\)[ \t]*")
TO_BE = {"is": "are", "was": "were", "has": "have", "does": "do", "goes": "go"}
NOT_VERBS = {"as", "his", "this", "us", "was", "is", "has", "does", "goes", "always", "perhaps", "towards", "afterwards"}


def reason(kind: str) -> str:
    return H["reasons"].get(kind, "write it in plain words")


def prose_of(value, key: str = "") -> list[str]:
    """The prose the player reads inside an answer: the strings under the prose fields, however deep."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, str):
        return [value] if key in PROSE else []
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in prose_of(v, k)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in prose_of(v, key)]
    return []


def problem(task: str, value) -> tuple[str, str]:
    """(kind, what was found) for the first thing in this answer's prose that is the machinery's, or ('', '')."""
    for t in prose_of(value):
        if not t:
            continue
        if "\\n" in t:
            return "escape", "\\n"
        m = CONTROL.search(t)                               # (f407) a stray escape in the model's JSON: "still\\but" read as backspace + "ut"
        if m:
            return "broken", t[max(0, m.start() - 12):m.start() + 12]
        for kind, pat in (("json", JSON_BITS), ("json", LABEL), ("json", FIELDS), ("json", DANGLING), ("placeholder", PLACEHOLDER), ("id", CODED),
                          ("id", SNAKE), ("id", TRAILING), ("note", NOTE), ("broken", STRAY)):
            m = pat.search(t)
            if m:
                return kind, m.group(0).strip()
        m = PLAYER.search(t)
        if m:
            return "player", m.group(0).split("'")[0].strip()
        if task in NARRATOR:
            m = FIRST.search(QUOTED.sub(" ", t))
            if m:
                return "first_person", m.group(0)
    return "", ""


def _base(verb: str) -> str:
    """'pulls' -> 'pull': a verb after 'the player', as it goes after 'you'."""
    v = verb.lower()
    if v in TO_BE:
        out = TO_BE[v]
    elif v.endswith("ies") and len(v) > 4:
        out = v[:-3] + "y"
    elif re.search(r"(ss|sh|ch|x|z|o)es$", v):
        out = v[:-2]
    elif v.endswith("s") and not v.endswith("ss") and v not in NOT_VERBS:
        out = v[:-1]
    else:
        out = v
    return out.capitalize() if verb[:1].isupper() else out


def second_person(text: str, whole: bool = False) -> str:
    """'The player pulls out their journal' -> 'You pull out their journal'. whole=True: the line is all about the player, so their,
    them and themselves are theirs too ('You pull out your journal')."""
    def one(m: re.Match) -> str:
        you = "You" if m.group(1) == "T" else "you"
        if m.group(2):
            return ("Your" if you == "You" else "your") + (m.group(3) or "")
        if m.group(4):
            return f"{you}{m.group(3)[:-len(m.group(4))]}{_base(m.group(4))}"
        return you
    out = PLAYER.sub(one, text or "")
    if whole:
        out = re.sub(r"\btheir\b", "your", out)
        out = re.sub(r"\bthemselves\b", "yourself", out)
        out = re.sub(r"\bthem\b", "you", out)
    return out


def unnote(text: str) -> str:
    """(f404) A story line without the model's notes to itself in square brackets; a blow's tag ([h1]) stays for its figure."""
    if not isinstance(text, str) or "[" not in text:
        return text
    t = NOTE.sub("", text)
    if t != text:
        REPAIRS["note"] += 1
        t = re.sub(r"[ \t]+([.,;:!?])", r"\1", t)
    return t


def unstage(text: str) -> str:
    """(f449) A story line without the model's stage directions: a whole sentence in round brackets is a script's, not a person's words.
    Counted in REPAIRS as 'stage'."""
    if not isinstance(text, str) or "(" not in text:
        return text
    t = STAGE.sub(" ", text)
    if t != text:
        REPAIRS["stage"] += 1
        t = re.sub(r"[ \t]{2,}", " ", t)
        t = re.sub(r"[ \t]+\n|\n[ \t]+", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip(" \t")
        t = re.sub(r"[ \t]+([.,;:!?])", r"\1", t)
    return t


def clean(text: str) -> str:
    """The line as the player should see it: escapes made real, a JSON tail cut off, codes and placeholders made words, 'the player'
    made 'you'. What was mended is counted in REPAIRS."""
    if not isinstance(text, str) or not text:
        return text
    t = text
    if "\r" in t:                                         # (f424) a carriage return is a space, before the control characters go: 'the\rgate' was 'thegate'
        t = re.sub(r"\r\n?", lambda m: "\n" if m.group(0) == "\r\n" else " ", t)
        REPAIRS["escape"] += 1
    if CONTROL.search(t):                                   # (f407) never a box on the page: "still\x08ut" was shown as "still\u25a1ut"
        t = re.sub(r"[ \t]*([\x08\x0c])", lambda m: EATEN[m.group(1)], t)
        t = CONTROL.sub("", t)
        REPAIRS["broken"] += 1
    if "\\n" in t:
        t = t.replace("\\n", "\n")
        REPAIRS["escape"] += 1
    if "\\" in t:                                          # (f411) a stray backslash before punctuation: "iron shears.\, nearby"
        t2 = re.sub(r"\\+(?=[\s,.;:!?'\"]|$)", "", t)
        if t2 != t:
            REPAIRS["escape"] += 1
            t = t2
    for pat, rep, kind in ((LABEL, "", "json"), (FIELDS, "", "json"), (DANGLING, "", "json"), (STRAY, " ", "broken")):    # (f431)
        t2 = pat.sub(rep, t)
        if t2 != t:
            REPAIRS[kind] += 1
            t = t2
    lead = re.match(r'^\s*\{\s*"[A-Za-z_]+"\s*:\s*"', t)
    if lead:
        t = t[lead.end():]
        REPAIRS["json"] += 1
    m = JSON_BITS.search(t)
    if m and m.start() > 0:
        t = t[:m.start()].rstrip(' "\'\n,')
        REPAIRS["json"] += 1
    if "{" in t:
        t2 = PLACEHOLDER.sub("", re.sub(r"\b([A-Za-z]+)_\w*\{\w+\}", r"\1", t))
        if t2 != t:
            REPAIRS["placeholder"] += 1
            t = t2
    if "_" in t:
        parts = COMMAND.split(t)                          # a #command and what it takes are typed as they stand: '#goto trading_square'
        t2 = "".join(p if i % 2 else TRAILING.sub(r"\1", SNAKE.sub(lambda m: m.group(0).rstrip("_").replace("_", " "),
                                                                    CODED.sub(lambda m: m.group(0).split("_")[0], p)))
                     for i, p in enumerate(parts))
        if t2 != t:
            REPAIRS["id"] += 1
            t = t2
    if "player" in t:
        t2 = second_person(t)
        if t2 != t:
            REPAIRS["player"] += 1
            t = t2
    from engine import names                              # (f412) 'Odly lowers his blade' for a she
    t = names.mend_pronouns(t)
    if "{" in t or "}" in t:                              # (f431) a brace is never the story's: '}"v1_0"' left in a passage
        t = re.sub(r'[{}]+(?:"[\w.]{0,24}")?', "", t)
        REPAIRS["json"] += 1
    if t != text:
        t = re.sub(r"[ \t]{2,}", " ", t).replace(" .", ".").replace(" ,", ",")
        t = re.sub(r"(?<!\.)\.\s?\.(?!\.)", ".", t)          # (f431) a cut field run leaves "ghost.. It"
        if not text[:1].isspace():
            t = t.lstrip()
    return t


# (f396) The narrator writes no dashes: the owner's one exception to leaving the narrator's style alone. An em dash, an en dash, a
# double hyphen or a spaced hyphen between words is mended to the punctuation it stands for. Hyphenated words are left as they are.
DASH = re.compile(r"[ \t]*(?:\u2014|\u2013|--)[ \t]*|[ \t]+-[ \t]+")
RANGE = re.compile(r"(\d)\s*[\u2013\u2014]\s*(\d)")
CLOSING = "\"\u201d'\u2019)"
OPENING = "\"\u201c'\u2018("
GO_ON = {"and", "but", "or", "nor", "then", "yet", "so", "not", "until", "before", "after", "as", "like", "only", "just", "maybe",
         "perhaps", "if", "though", "although", "because", "while", "when", "where", "which", "who", "whose", "even", "still", "almost"}
BREAK_OFF = {"no", "wait", "never", "listen", "look", "forget", "nevermind"}     # (f403) a thought broken off: "I was going to... no"


def undash(text: str) -> str:
    """The same passage without dashes: a dash that breaks off speech is an ellipsis, one that opens a line is dropped, a pair around an
    aside are commas, one before 'and', 'but', 'then' and the like is a comma, and one before the rest of a thought is a colon (or a
    comma, when the sentence has a colon already). (f403) In speech: a stammer ("I-I") and a thought broken off ("I was going to- no")
    are an ellipsis."""
    if not isinstance(text, str) or not text or not ("\u2014" in text or "\u2013" in text or "--" in text or " - " in text or "\t-" in text):
        return text
    t = RANGE.sub(r"\1 to \2", text)
    out, i, cap = [], 0, False
    matches = list(DASH.finditer(t))
    for n, m in enumerate(matches):
        before, after = t[:m.start()], t[m.end():]
        piece = t[i:m.start()]
        out.append(piece[:1].upper() + piece[1:] if cap else piece)
        i, cap = m.end(), False
        prev = before.rstrip(" \t")
        nxt = after.lstrip(" \t")
        start = max(before.rfind(c) for c in ".!?\n")             # the sentence this dash is in
        end = min([x for x in (after.find(c) for c in ".!?\n") if x >= 0] or [len(after)])
        sentence_has = sum(1 for x in matches if start < x.start() < m.end() + end and x is not m)
        if not prev or prev[-1] in OPENING or prev.endswith("\n"):
            rep, cap = "", True                                   # a dash that opens a line or a quotation
        elif not nxt or nxt[0] in CLOSING or nxt[0] == "\n":
            rep = "..."                                           # a word broken off: "But I-"
        elif nxt[0] in ".,;:!?":
            rep = ""
        elif sentence_has:
            rep = ", "                                            # a pair around an aside
        elif (re.search(r"([A-Za-z']+)$", prev) or [None, ""])[1].lower() == (re.match(r"[A-Za-z']+", nxt) or [""])[0].lower() \
                or (re.match(r"[A-Za-z']+", nxt) or [""])[0].lower() in BREAK_OFF:
            rep = "... "                                          # a stammer, or a thought broken off
        elif (re.match(r"[A-Za-z']+", nxt) or [""])[0].lower() in GO_ON or ":" in t[start + 1:m.start()] + after[:end]:
            rep = ", "
        else:
            rep = ": "
        out.append(rep)
    out.append(t[i:][:1].upper() + t[i:][1:] if cap else t[i:])
    s = "".join(out)
    s = re.sub(r"\s+([,;:])", r"\1", s)
    s = re.sub(r"([,;:])\s*([,;:.!?])", r"\2", s)
    s = re.sub(r"\.\.\.\s*([.,])", "...", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    if s != text:
        REPAIRS["dash"] += 1
    return s


LONE_BREAK = re.compile(r"(?<!\n)[ \t]*\n[ \t]*(?!\n)")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
EATEN = {"\x08": " b", "\x0c": " f"}          # the letter a JSON escape swallowed (\b, \f) put back, when the model was not asked again


def unwrap(text: str) -> str:
    """(f407) The model's prose without line breaks of its own inside a paragraph: a paragraph is what a blank line ends. A night's play had
    Maren's arrival come back broken after nearly every clause, and every break shown as a paragraph of its own."""
    if not isinstance(text, str) or "\n" not in text:
        return text
    t = LONE_BREAK.sub(" ", text)
    if t != text:
        REPAIRS["wrap"] += 1
    return t


def undash_answer(task: str, value) -> None:
    """(f396) An answer from the model, mended in place: its prose fields carry no dashes. (f403) Every task's, speech and gestures too:
    the narrator was held to it and the people it voices were not, and their dashes showed as often as the narrator's had."""
    if value is None:
        return
    for key in list(getattr(type(value), "model_fields", {}) or {}):
        v = getattr(value, key, None)
        if isinstance(v, str) and key in PROSE:
            setattr(value, key, undash(unwrap(v)))
        elif isinstance(v, list):
            for j, x in enumerate(v):
                if isinstance(x, str) and key in PROSE:
                    v[j] = undash(unwrap(x))
                elif hasattr(x, "model_fields"):
                    undash_answer(task, x)
        elif hasattr(v, "model_fields"):
            undash_answer(task, v)


def problems() -> list[str]:
    bad = []
    for k in ("prose_fields", "narrator_tasks", "reasons"):
        if not H.get(k):
            bad.append(f"hygiene.yaml: needs {k}")
    for kind in ("json", "placeholder", "id", "escape", "player", "first_person", "note", "broken"):
        if kind not in (H.get("reasons") or {}):
            bad.append(f"hygiene.yaml: needs a reason for {kind}")
    return bad

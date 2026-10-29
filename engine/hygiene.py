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

JSON_BITS = re.compile(r'```|^\s*[\{\[]\s*"|"\s*,\s*"?[A-Za-z0-9_%]+"?\s*:\s|\{\s*"[A-Za-z_]+"\s*:|"\s*\}|\}\s*$')
PLACEHOLDER = re.compile(r"\{[A-Za-z_]+\}")
CODED = re.compile(r"\b[A-Za-z]+_[0-9a-f]{6,}(?:-[0-9a-f]+)*")             # silks_1827359406-bdcc-...
SNAKE = re.compile(r"(?<![#`/\w])[a-z]+(?:_[a-z0-9]+)+\b")                 # find_the_sinkhole (not #commands)
TRAILING = re.compile(r"\b([A-Za-z]+)_(?![\w{])")                         # arches_
COMMAND = re.compile(r"(#[a-z]+(?:\s+[A-Za-z0-9_<>]+)?)")
PLAYER = re.compile(r"\b([Tt])he player(?!s)(?!\s+of\b)('s)?(\s+([A-Za-z]+))?")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
FIRST = re.compile(r"\b(I|[Mm]e|[Mm]y|[Mm]ine|[Mm]yself)\b")
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
        for kind, pat in (("json", JSON_BITS), ("placeholder", PLACEHOLDER), ("id", CODED), ("id", SNAKE), ("id", TRAILING)):
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


def clean(text: str) -> str:
    """The line as the player should see it: escapes made real, a JSON tail cut off, codes and placeholders made words, 'the player'
    made 'you'. What was mended is counted in REPAIRS."""
    if not isinstance(text, str) or not text:
        return text
    t = text
    if "\\n" in t:
        t = t.replace("\\n", "\n")
        REPAIRS["escape"] += 1
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
        t2 = "".join(p if i % 2 else TRAILING.sub(r"\1", SNAKE.sub(lambda m: m.group(0).replace("_", " "),
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
    if t != text:
        t = re.sub(r"[ \t]{2,}", " ", t).replace(" .", ".").replace(" ,", ",")
    return t


def problems() -> list[str]:
    bad = []
    for k in ("prose_fields", "narrator_tasks", "reasons"):
        if not H.get(k):
            bad.append(f"hygiene.yaml: needs {k}")
    for kind in ("json", "placeholder", "id", "escape", "player", "first_person"):
        if kind not in (H.get("reasons") or {}):
            bad.append(f"hygiene.yaml: needs a reason for {kind}")
    return bad

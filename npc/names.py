"""Who gets which name. The engine builds every resident's name from their people's sounds (f346), seeded by the campaign, and never
gives two people the same first name in one save, nor ever the same full name. The model is told the name and writes only the look
and the day.

build() makes a name from data/world/name_sounds.yaml: each people has the pieces its names begin, continue and end with, and a name
is those pieces joined, checked against the people's rules (length, how many vowels or consonants may run together, sounds it never
makes). A people may also say how many of its names have one syllable, two, three or more (`syllables`). There is no list of
forbidden names, and no list of names at all: each kind can make thousands, so any one name is rare."""
from __future__ import annotations

import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

_DATA = Path(__file__).resolve().parent.parent / "data" / "world"


@lru_cache(maxsize=1)
def reserved() -> frozenset[str]:
    """First names the story uses for named characters, so no passer-by shares them."""
    m = yaml.safe_load((_DATA / "mentor.yaml").read_text(encoding="utf-8"))
    return frozenset(w for w in (m.get("name", "").split()[:1]))


def first_of(full: str) -> str:
    return (full or "").strip().split(" ")[0].lower()


def pick(people: str, taken: list[str], rng: random.Random) -> tuple[str, str]:
    """-> (full name, gender), built from the people's sounds. `taken` holds the full names already in the save: a first name already
    given is passed over while a fresh one can be built, and a full name already given is never used again."""
    gender = rng.choice(["male", "female"])
    firsts = {first_of(n) for n in taken} | {w.lower() for w in reserved()}
    fulls = {n.strip().lower() for n in taken}
    spare = ""
    for _ in range(400):
        full = f"{build(people, gender, rng)} {build(people, 'family', rng)}".strip()
        if full.lower() in fulls:
            continue
        if first_of(full) not in firsts:
            return full, gender
        spare = spare or full                            # a first name the save has: used only if no fresh one turns up
    return spare or full, gender


# ---- (f346) names built from each people's sounds

VOWELS = "aeiouy"


@lru_cache(maxsize=1)
def sounds() -> dict:
    return yaml.safe_load((_DATA / "name_sounds.yaml").read_text(encoding="utf-8"))


def _rules(people: str, kind: str) -> dict:
    """The people's rules for a kind of name (male, female or family), following family_from."""
    peoples = sounds()["peoples"]
    rules = peoples.get(people) or peoples["human"]
    if kind == "family" and rules.get("family_from"):
        rules = peoples[rules["family_from"]]
    return rules


def _join(a: str, b: str) -> str:
    """Glue two pieces. A vowel that ends one piece and starts the next is said once: 'ala' + 'aric' is 'alaric'."""
    if a and b and a[-1] == b[0] and a[-1] in VOWELS:
        return a + b[1:]
    return a + b


def acceptable(name: str, rules: dict) -> bool:
    """Does a built name keep its people's rules and the shared ones (data/world/name_sounds.yaml: length, runs, avoid, syllables)?"""
    shared = sounds()
    low = name.lower()
    lo, hi = rules.get("length", shared["length"])
    if not lo <= len(low) <= hi or not low.isalpha():
        return False
    if re.search(r"(.)\1\1", low):                                   # no letter three times running
        return False
    if re.search(f"[{VOWELS}]{{{rules.get('max_vowels', shared['max_vowels']) + 1}}}", low):
        return False
    if re.search(f"[^{VOWELS}]{{{rules.get('max_consonants', shared['max_consonants']) + 1}}}", low):
        return False
    if any(re.search(pat, low) for pat in shared["avoid"] + rules.get("avoid", [])):
        return False
    return syllables(low) >= rules.get("min_syllables", 1)


def syllables(name: str) -> int:
    """How many syllables a name has, near enough: runs of vowels ('Cael' one, 'Aeris' two), a pair said apart counting twice
    ('Cecilia', 'Theodoric'), and an e at the end not counting when it is silent ('Crane', 'Lyle'; 'Gable' keeps it)."""
    low = name.lower()
    n = len(re.findall(f"[{VOWELS}]+", low)) + len(re.findall("(?=ia|io|eo|ua|iu)", low))
    if n > 1 and re.search(f"[^{VOWELS}]e$", low) and not re.search(f"[^{VOWELS}l]le$", low):
        n -= 1
    return n


def possible(people: str, kind: str) -> set[str]:
    """Every name the people's sounds can make for a kind that keeps its rules: how much room there is, so no one name comes up often."""
    import itertools
    rules = _rules(people, kind)
    out = set()
    for form in rules[kind]:
        for count in (int(c) for c, w in (form.get("middles") or {0: 1}).items() if w > 0):
            for first in form["first"]:
                for middles in itertools.product(form.get("middle") or [""], repeat=count):
                    for last in form["last"]:
                        name = (first or "").lower()
                        for m in middles:
                            name = _join(name, (m or "").lower())
                        name = _join(name, (last or "").lower())
                        name = name[:1].upper() + name[1:]
                        if acceptable(name, rules):
                            out.add(name)
    return out


def build(people: str, kind: str, rng: random.Random) -> str:
    """A new name of `kind` (male, female or family) for `people`, made from its sounds. Same rng, same name. When the people has
    a `syllables` table, how many syllables the name has is drawn from it first, and names are built until one has that many."""
    rules = _rules(people, kind)
    forms = rules[kind]
    table = rules.get("syllables")                                      # count: weight; the last count means that many or more
    want = rng.choices(list(table), weights=list(table.values()))[0] if table else None
    spare = None
    for _ in range(2000):
        form = rng.choices(forms, weights=[f.get("weight", 1) for f in forms])[0]
        middles = form.get("middles", {0: 1})
        n = rng.choices(list(middles), weights=list(middles.values()))[0]
        name = (rng.choice(form["first"]) or "").lower()                # a piece may be "" (a name with no opening sound)
        for _ in range(int(n)):
            name = _join(name, (rng.choice(form["middle"]) or "").lower())
        name = _join(name, (rng.choice(form["last"]) or "").lower())
        name = name[:1].upper() + name[1:]
        if not acceptable(name, rules):
            continue
        if want is None or syllables(name) == want or (want == max(table) and syllables(name) > want):
            return name
        spare = spare or name
    if spare:                                                           # no name that long came up: the sounds can hardly make one
        return spare
    raise ValueError(f"name_sounds.yaml: {people} {kind} names cannot be built within their rules")

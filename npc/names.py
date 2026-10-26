"""Who gets which name. The engine picks every resident's name from data/world/names.yaml, seeded by the campaign, and never gives
two people the same first name in one save (unless a people's list has run dry, and then never the same full name). The model is told the
name and writes only the look and the day.

build() makes new names instead of picking them (f346): each people has its own sounds in data/world/name_sounds.yaml - the pieces
its names begin, continue and end with - and a name is those pieces joined, checked against the people's rules (length, how many
vowels or consonants may run together, what never to produce) and against a list of names other stories own."""
from __future__ import annotations

import random
import re
from functools import lru_cache
from pathlib import Path

import yaml

_DATA = Path(__file__).resolve().parent.parent / "data" / "world"


@lru_cache(maxsize=1)
def pools() -> dict:
    raw = yaml.safe_load((_DATA / "names.yaml").read_text(encoding="utf-8"))
    out = {}
    for people, p in raw.items():
        fam = p.get("family")
        if p.get("family_from"):
            fam = raw[p["family_from"]]["family"]
        out[people] = {"male": list(p["male"]), "female": list(p["female"]), "family": list(fam or [])}
    return out


@lru_cache(maxsize=1)
def reserved() -> frozenset[str]:
    """First names the story uses for named characters, so no passer-by shares them."""
    m = yaml.safe_load((_DATA / "mentor.yaml").read_text(encoding="utf-8"))
    return frozenset(w for w in (m.get("name", "").split()[:1]))


def first_of(full: str) -> str:
    return (full or "").strip().split(" ")[0].lower()


def pick(people: str, taken: list[str], rng: random.Random) -> tuple[str, str]:
    """-> (full name, gender). `taken` holds the full names already in the save."""
    pool = pools().get(people) or pools()["human"]
    firsts = {first_of(n) for n in taken} | {w.lower() for w in reserved()}
    fulls = {n.strip().lower() for n in taken}
    for _ in range(2):                                   # second pass only if every unused first name is gone
        gender = rng.choice(["male", "female"])
        for g in (gender, "female" if gender == "male" else "male"):
            free = [n for n in pool[g] if n.lower() not in firsts]
            if free:
                first = rng.choice(free)
                break
        else:
            firsts = set()                               # pools exhausted: repeats of a first name are allowed now
            continue
        fam = pool["family"] or [""]
        open_fams = [f for f in fam if f"{first} {f}".strip().lower() not in fulls]
        if open_fams:
            return f"{first} {rng.choice(open_fams)}".strip(), g
        firsts.add(first.lower())                        # every family name is used with this one: try another first name
    gender = rng.choice(["male", "female"])
    left = [(f, x) for f in pool[gender] for x in (pool["family"] or [""]) if f"{f} {x}".strip().lower() not in fulls]
    f, x = rng.choice(left) if left else (rng.choice(pool[gender]), rng.choice(pool["family"] or [""]))
    return f"{f} {x}".strip(), gender


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
    """Does a built name keep its people's rules and the shared ones (data/world/name_sounds.yaml: length, runs, avoid, taken)?"""
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
    if syllables(low) < rules.get("min_syllables", 1):
        return False
    return low not in _taken()


def syllables(name: str) -> int:
    """How many syllables a name has, counted as runs of vowels ('Cael' one, 'Aeris' two). Close enough to tell Brom from Brommek."""
    return len(re.findall(f"[{VOWELS}]+", name.lower()))


@lru_cache(maxsize=1)
def _taken() -> frozenset[str]:
    """Names never built: those another story owns, and common English words (name_sounds.yaml `taken` and `words`)."""
    return frozenset(n.lower() for n in sounds()["taken"] + sounds().get("words", []))


def possible(people: str, kind: str) -> set[str]:
    """Every name the people's sounds can make for a kind, each kept only if it keeps the rules (for checking the sounds whole)."""
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
    """A new name of `kind` (male, female or family) for `people`, made from its sounds. Same rng, same name."""
    rules = _rules(people, kind)
    forms = rules[kind]
    for _ in range(400):
        form = rng.choices(forms, weights=[f.get("weight", 1) for f in forms])[0]
        middles = form.get("middles", {0: 1})
        n = rng.choices(list(middles), weights=list(middles.values()))[0]
        name = (rng.choice(form["first"]) or "").lower()                # a piece may be "" (a name with no opening sound)
        for _ in range(int(n)):
            name = _join(name, (rng.choice(form["middle"]) or "").lower())
        name = _join(name, (rng.choice(form["last"]) or "").lower())
        name = name[:1].upper() + name[1:]
        if acceptable(name, rules):
            return name
    raise ValueError(f"name_sounds.yaml: {people} {kind} names cannot be built within their rules")

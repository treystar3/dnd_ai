"""Who gets which name. The engine picks every resident's name from data/world/names.yaml, seeded by the campaign, and never gives
two people the same first name in one save (unless a people's list has run dry, and then never the same full name). The model is told the
name and writes only the look and the day."""
from __future__ import annotations

import random
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

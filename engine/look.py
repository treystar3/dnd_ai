"""(f388) Who the player was, before the goddess speaks: a people, how others speak of them, and a look (data/rules/look.yaml).

The engine makes one plain sentence of the choices ("A stocky dwarf woman with braided copper hair and a burn scar along the jaw; soot
never quite washes from her hands") that the truth layer gives every speaker, and the narrator, from then on. It changes no number. The
night's runs had the people of the world calling one player sir, madam, lad and lass, because nothing said who stood in front of them."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
L = yaml.safe_load((ROOT / "data" / "rules" / "look.yaml").read_text(encoding="utf-8"))
PRONOUNS = {p["id"]: p for p in L["pronouns"]}


def axes_for(people: str) -> list[str]:
    """The rows of the look for this people, in page order: hair for most, scales in its place for the dragonborn, an element as well
    for the genasi."""
    spec = L["peoples"].get(people, {})
    names = ["build", "age", "hair"]
    for old, new in (spec.get("replaces") or {}).items():
        names = [new if n == old else n for n in names]
    names += list(spec.get("adds") or [])
    return [a for a in L["order"] if a in names]


def flags_for(people: str) -> list[str]:
    return [f for f, spec in L["flags"].items() if spec["axis"] in axes_for(people)]


def clean(choice: dict) -> dict:
    """The choices as the engine keeps them: a known people and pronoun, a known option on each of its axes (the default otherwise),
    known flags on, and 'anything else' as plain words, shortened."""
    people = choice.get("people") if choice.get("people") in L["peoples"] else "human"
    pronoun = choice.get("pronoun") if choice.get("pronoun") in PRONOUNS else "they"
    look = {}
    for a in axes_for(people):
        v = str((choice.get("look") or {}).get(a, "")).strip().lower()
        look[a] = v if v in L["axes"][a]["options"] else L["axes"][a]["default"]
    flags = [f for f in (choice.get("flags") or []) if f in flags_for(people) and look.get(L["flags"][f]["axis"]) not in ("none", None)]
    extra = re.sub(r"[\x00-\x1f<>{}\[\]]", " ", str(choice.get("extra") or ""))
    extra = " ".join(extra.split())[: int(L["extra_most"])].strip(" .;,")
    return {"people": people, "pronoun": pronoun, "look": look, "flags": flags, "extra": extra}


def describe(choice: dict) -> str:
    """The one sentence the world sees."""
    c = clean(choice)
    spec, pr, look = L["peoples"][c["people"]], PRONOUNS[c["pronoun"]], c["look"]
    before = []
    for a in axes_for(c["people"]):
        ax = L["axes"][a]
        if "say" in ax and look[a] not in ax.get("none", []):
            before.append(ax["say"].format(v=look[a]))
    if c["people"] == "human":
        words = before + [pr["noun"]]                             # "a stocky woman": a human is the plain word
    else:
        words = before + [spec["word"]] + ([pr.get("after_people", pr["noun"])] if pr.get("after_people", pr["noun"]) else [])
    withs = []
    for a in axes_for(c["people"]):
        ax = L["axes"][a]
        if look[a] == "none" and ax.get("none_with"):
            withs.append(ax["none_with"])
        elif "with" in ax:
            flagged = [L["flags"][f]["word"] for f in c["flags"] if L["flags"][f]["axis"] == a]
            withs.append(" ".join(flagged + [ax["with"].format(v=look[a])]))
    head = " ".join(words)
    s = f"{'An' if head[:1].lower() in 'aeiou' else 'A'} {head}" + (f" with {' and '.join(withs)}" if withs else "")
    extra = c["extra"]
    if extra:
        first, _, rest = extra.partition(",")
        if re.match(r"^(a|an|one|two|some)\s", first.strip(), re.I):
            s += (" and " if withs else " with ") + first.strip()[0].lower() + first.strip()[1:] + (f"; {rest.strip()}" if rest.strip() else "")
        else:
            s += "; " + extra[0].lower() + extra[1:]
    return s.rstrip(".") + "."


def surprise(rng: random.Random | None = None) -> dict:
    """A whole look chosen at random, for the page's Surprise me and a night bot that does not choose."""
    rng = rng or random.Random()
    people = rng.choice(list(L["peoples"]))
    look = {a: rng.choice([o for o in L["axes"][a]["options"]]) for a in axes_for(people)}
    flags = [f for f in flags_for(people) if look.get(L["flags"][f]["axis"]) != "none" and rng.random() < 0.3]
    return clean({"people": people, "pronoun": rng.choice(["he", "she", "they"]), "look": look, "flags": flags})


def from_text(text: str) -> dict:
    """A typed answer read for its choices (the terminal, or the page's text box): a people named, he, she or they (or man, woman), the
    options named; whatever words are left over are 'anything else'."""
    low = " " + " ".join(re.findall(r"[a-z']+", (text or "").lower().replace("-", " ").replace("_", " "))) + " "
    people = next((p for p in L["peoples"] if f" {p.replace('_', ' ')} " in low or f" {L['peoples'][p]['word'].replace('-', ' ')} " in low), "human")
    pronoun = next((p for p, ws in (("she", ("she", "her", "woman", "girl", "female")), ("he", ("he", "him", "man", "boy", "male")),
                                    ("they", ("they", "them", "person"))) if any(f" {w} " in low for w in ws)), "they")
    look = {a: next((o for o in L["axes"][a]["options"] if f" {o} " in low), "") for a in axes_for(people)}
    flags = [f for f, spec in L["flags"].items() if f" {spec['word']} " in low]
    used = {people.replace("_", " "), L["peoples"][people]["word"].replace("-", " "), "she", "her", "woman", "he", "him", "man", "they", "them",
            "person", "girl", "boy", "female", "male", "a", "an", "and", "with", "hair", "scales", "i", "am", "was", "i'm"}
    used |= {o for a in axes_for(people) for o in L["axes"][a]["options"]} | {spec["word"] for spec in L["flags"].values()}
    used |= set(people.replace("_", " ").split()) | set(L["peoples"][people]["word"].replace("-", " ").split())
    words = list(re.finditer(r"[a-z']+", (text or "").lower().replace("-", " ").replace("_", " ")))
    first = next((i for i, m in enumerate(words) if m.group(0) not in used), None)
    extra = ""
    if first is not None and len(words) - first >= 2:                # what is left after the choices: "a burn scar on her jaw"
        if first > 0 and words[first - 1].group(0) in ("a", "an"):
            first -= 1
        extra = (text or "")[words[first].start():].strip()
    return clean({"people": people, "pronoun": pronoun, "look": look, "flags": flags, "extra": extra})


def page() -> dict:
    """Everything the creation page's first step draws."""
    from world.loader import authored
    names = {p.id: p.name for p in authored().peoples.values()}       # (f434) the written world, parsed once a run, not once a page
    return {"intro": L["intro"], "title": L["title"], "hint": L["hint"], "extra_hint": L["extra_hint"], "extra_most": L["extra_most"],
            "peoples": [{"id": p, "name": names.get(p, p.replace("_", "-").title()), "blurb": spec["blurb"], "word": spec["word"],
                         "axes": axes_for(p), "flags": flags_for(p)} for p, spec in L["peoples"].items()],
            "pronouns": [p["id"] for p in L["pronouns"]],
            "nouns": {p["id"]: {"noun": p["noun"], "after_people": p.get("after_people", p["noun"])} for p in L["pronouns"]},
            "axes": {a: {k: ax[k] for k in ("label", "options", "default", "say", "with", "none", "none_with") if k in ax} for a, ax in L["axes"].items()},
            "flags": {f: {"axis": s["axis"], "label": s["label"], "word": s["word"]} for f, s in L["flags"].items()},
            "default": clean({"people": "human", "pronoun": "they"})}


def problems(world) -> list[str]:
    """look.yaml against the world: every people of the world has a look, and nothing names a people that is not there."""
    have, want = set(L["peoples"]), {p.id for p in world.peoples.values()}
    out = [f"look.yaml: no look for the people '{p}'" for p in sorted(want - have)]
    out += [f"look.yaml: '{p}' is not a people of data/world/peoples.yaml" for p in sorted(have - want)]
    for a in L["order"]:
        if a not in L["axes"]:
            out.append(f"look.yaml: order names '{a}', which is no axis")
    return out

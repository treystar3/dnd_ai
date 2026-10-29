"""(f350) How one person talks, drawn by the engine: the voice kit.

Why: the model, asked to write a voice, wrote the same one for everybody ("slow, measured, gravelly, steady"), a sound that text cannot
act; and a person in a five-hour run was no more like themselves than like a stranger across town. A kit is one option on each of a few
audible axes (how much they say, the shape of a sentence, whether they ask back, how a line opens, contractions, what they call you, how
they refuse, where their words come from), drawn once and kept on the person (speech["kit"]). Each option is behaviour the model is told
and, where the engine can hear it, a check the reply must pass (check()): a terse person over the word cap is sent back, a person who never
asks back cannot end on a question. Nobody needs to be memorable; two people need to sound different, so draw() keeps, of several candidate
kits, the one farthest from the kits already in use here (a town's people, a list's hires), weighted by how audible each axis is.

(f374) A kit carries at most `max_marked` habits (two). The first playthrough after kits came in met a clerk who never asked, never used
a contraction, said madam, refused by excuse and counted everything, and a hire who repeated every question back before answering it:
six or seven habits at once, each told as a rule, read as a caricature, and the model applied every one to every line. A person is
mostly ordinary with one or two things you would notice. Drawing apart still works: two people differ on which habits they have. A kit
kept from before (an old save's) is trimmed as it is read (kit_of), keeping its most audible habits, so nobody is re-drawn.

The house-phrase guard is the same idea across people: a run of words that several other people in this town have said lately is how
everyone here talks, and a reply that uses it is sent back. The tables are data/rules/voices.yaml."""
from __future__ import annotations

import random
import re
from collections import deque
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
V = yaml.safe_load((ROOT / "data" / "rules" / "voices.yaml").read_text(encoding="utf-8"))
AXES: dict = V["axes"]
_STOP = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with", "from", "by", "as", "is", "are", "was", "were",
         "be", "it", "its", "i", "you", "your", "we", "they", "them", "their", "he", "she", "his", "her", "this", "that", "these", "those",
         "there", "here", "not", "no", "yes", "do", "does", "did", "have", "has", "had", "will", "would", "can", "could", "should", "if",
         "then", "than", "so", "just", "only", "all", "any", "some", "more", "most", "much", "very", "too", "what", "which", "who", "when",
         "where", "why", "how", "my", "me", "our", "us", "s", "re", "ve", "ll", "d", "m", "t", "about", "been", "up", "out", "one"}


# ---------- drawing

def _pick(rng: random.Random, options: dict) -> str:
    keys = list(options)
    return rng.choices(keys, weights=[options[k].get("weight", 1) for k in keys])[0]


def roll(rng: random.Random) -> dict:
    """One kit: an option on every axis, by weight."""
    return {axis: _pick(rng, spec["options"]) for axis, spec in AXES.items()}


def unmarked(axis: str) -> str:
    """The option on an axis that says nothing (its text is empty): what most people are."""
    opts = AXES[axis]["options"]
    return next((k for k, o in opts.items() if not o.get("text")), next(iter(opts)))


def trim(kit: dict) -> dict:
    """(f374) The kit with at most `max_marked` habits: the most audible marked axes (by axis weight, then in axis order) are kept and
    the rest go back to unmarked."""
    if not kit:
        return kit
    cap = int(V.get("max_marked", 2))
    marked = [a for a in AXES if kit.get(a) and AXES[a]["options"].get(kit[a], {}).get("text")]
    if len(marked) <= cap:
        return kit
    keep = set(sorted(marked, key=lambda a: (-AXES[a].get("weight", 1), list(AXES).index(a)))[:cap])
    return {a: (v if a in keep or a not in AXES else unmarked(a)) for a, v in kit.items()}


def distance(a: dict, b: dict) -> int:
    """How differently two kits sound: the weights of the axes they differ on."""
    return sum(spec.get("weight", 1) for axis, spec in AXES.items() if (a or {}).get(axis) != (b or {}).get(axis))


def draw(rng: random.Random, taken: list[dict] | tuple = ()) -> dict:
    """The kit for someone new: of `draw_tries` candidates, the one farthest (by its nearest neighbour) from the kits already in use here."""
    taken = [trim(t) for t in taken if t]
    cands = [trim(roll(rng)) for _ in range(int(V.get("draw_tries", 12)))]
    if not taken:
        return cands[0]
    return max(cands, key=lambda k: min(distance(k, t) for t in taken))


def ensure(speech: dict, rng: random.Random, taken: list[dict] | tuple = ()) -> dict:
    """The kit on a speech profile (a hire's member["speech"], a townsperson's npc.speech), drawn once."""
    if not isinstance(speech, dict):
        return {}
    kit = speech.get("kit")
    if not kit or any(axis not in kit or kit[axis] not in spec["options"] for axis, spec in AXES.items()):
        speech["kit"] = draw(rng, taken)
    return trim(speech["kit"])


def kit_of(member_or_speech) -> dict:
    sp = member_or_speech.get("speech") if isinstance(member_or_speech, dict) and "speech" in member_or_speech else member_or_speech
    return trim((sp or {}).get("kit") or {}) if isinstance(sp, dict) else {}


# ---------- what the model is told

def lines(kit: dict) -> list[str]:
    """The kit as HOW YOU TALK lines: the marked options' texts, in axis order. Unmarked axes say nothing."""
    out = []
    for axis, spec in AXES.items():
        opt = spec["options"].get((kit or {}).get(axis, ""), {})
        if opt.get("text"):
            out.append(opt["text"])
    return out


def room(kit: dict, level: str) -> str:
    """The reply's length level moved by the kit: a terse person a step down, a full one a step up."""
    order = ["short", "medium", "long"]
    if level not in order:
        return level
    shift = sum(int(spec["options"].get((kit or {}).get(axis, ""), {}).get("room", 0)) for axis, spec in AXES.items())
    return order[max(0, min(len(order) - 1, order.index(level) + shift))]


# ---------- what the engine can hear

_ADDRESS = re.compile(r"\b(friend|stranger|traveller|traveler|lad|lass|lassie|laddie|sir|madam|ma'am|m'lady|my lord|my lady|you there|"
                      r"newcomer|outsider)\b", re.I)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def check(kit: dict, speech: str) -> str:
    """Why a line breaks this person's way of talking, in words that send it back, or ''."""
    if not kit or not (speech or "").strip():
        return ""
    from llm.contracts import opener_of
    from engine.quirks import CONTRACTION
    words = re.findall(r"[A-Za-z'’]+", speech)
    for axis, spec in AXES.items():
        opt = spec["options"].get(kit.get(axis, ""), {})
        c = opt.get("check") or {}
        if "max_words" in c and len(words) > int(c["max_words"]):
            return f"this person {opt['text']}: under {c['max_words']} words"
        if "max_sentence_words" in c and any(len(re.findall(r"[A-Za-z'’]+", s)) > int(c["max_sentence_words"]) for s in _sentences(speech)):
            return f"this person speaks in {opt['text']}: no sentence over {c['max_sentence_words']} words"
        if c.get("no_question") and "?" in speech:
            return f"this person {opt['text']}: no question in the reply"
        if c.get("no_stock_opener") and opener_of(speech):
            return f"this person {opt['text']}: not on '{opener_of(speech).capitalize()}'"
        if c.get("no_contractions") and CONTRACTION.search(speech):
            return f"this person {opt['text']}: 'do not', 'I am', 'it is'"
        if c.get("no_address") and _ADDRESS.search(speech):
            return f"this person {opt['text']}: drop '{_ADDRESS.search(speech).group(0)}'"
        if "max_long_words" in c and sum(1 for w in words if len(w) >= 11) > int(c["max_long_words"]):
            long_ = [w for w in words if len(w) >= 11]
            return f"this person uses {opt['text']}: not '{long_[0]}'"
    return ""


def check_member(member: dict, speech: str) -> str:
    return check(kit_of(member), speech)


# ---------- who is around: the kits in use here

def kits_in_town(store, world, npc) -> list[dict]:
    """The kits of everyone else in this person's town, so theirs is drawn to differ."""
    from engine import pulse, retrieval
    town = pulse.town_of(world, npc.location)
    ids = [row.id for row in retrieval.people_in_town(store, world, town) if row.id != npc.id]
    return [trim(k) for k in store.speech_kits(ids) if isinstance(k, dict) and k]     # (f374) from the records: the index rows carry no speech


def kits_in_party(party: list[dict], member: dict | None = None) -> list[dict]:
    return [kit_of(o) for o in party if o is not member and kit_of(o)]


# ---------- the house-phrase guard

def _grams(text: str, n: int = 4) -> set[str]:
    w = re.findall(r"[a-z']+", (text or "").lower())
    out = set()
    for i in range(len(w) - n + 1):
        g = w[i:i + n]
        if sum(1 for x in g if x not in _STOP and len(x) > 2) >= 2:
            out.add(" ".join(g))
    return out


def _names(ws):
    """The world's place and road names as one pattern (without 'the'): a run of words that carries one is a name, not a habit ('on the
    Coast Road' was sent back nine times in one run as how everyone talks). Cached on the scene; None when the scene has no world."""
    if "_house_names" not in ws.__dict__:
        world = getattr(ws, "world", None)
        names = set()
        for coll in (getattr(world, "places", None) or {}, getattr(world, "roads", None) or {}):
            for p in (coll.values() if hasattr(coll, "values") else coll):
                n = re.sub(r"^the\s+", "", str(getattr(p, "name", "") or "").lower()).strip()
                if len(n) >= 4:
                    names.add(n)
        ws.__dict__["_house_names"] = re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b") if names else None
    return ws.__dict__["_house_names"]


def heard(ws, town: str, speaker: str, speech: str) -> None:
    """A line said in this town, kept for the guard (the last `window` lines of the session)."""
    H = V.get("house", {})
    log = ws.__dict__.setdefault("_said_in_town", deque(maxlen=int(H.get("window", 60))))
    names = _names(ws)
    grams = {g for g in _grams(speech) if not (names and names.search(g))}
    if grams:
        log.append((town, speaker, grams))


def house_phrases(ws, town: str, speaker: str) -> set[str]:
    """The runs of words that `others` or more OTHER people have said lately, in any town: how everyone talks (the habit is the
    model's, and it travels with the player)."""
    H = V.get("house", {})
    by_gram: dict[str, set[str]] = {}
    for t, who, grams in ws.__dict__.get("_said_in_town", ()):
        if who == speaker:                                        # every town's lines: the house voice is the model's, not the town's
            continue
        for g in grams:
            by_gram.setdefault(g, set()).add(who)
    return {g for g, whos in by_gram.items() if len(whos) >= int(H.get("others", 2))}


def house_hit(speech: str, house: set[str] | list[str]) -> str:
    """The first house phrase a line uses, or ''."""
    if not house:
        return ""
    mine = _grams(speech)
    hits = sorted(mine & set(house))
    return hits[0] if hits else ""


# ---------- the data

def problems() -> list[str]:
    bad = []
    sound = [w.lower() for w in V.get("sound_words", [])]
    known = {"max_words", "max_sentence_words", "no_question", "no_stock_opener", "no_contractions", "no_address", "max_long_words"}
    for axis, spec in AXES.items():
        opts = spec.get("options") or {}
        if not opts or sum(o.get("weight", 1) for o in opts.values()) <= 0:
            bad.append(f"voices.yaml: axis {axis} has no options")
        for name, o in opts.items():
            text = (o.get("text") or "").lower()
            for w in sound:
                if re.search(rf"\b{re.escape(w)}\b", text):
                    bad.append(f"voices.yaml: {axis}.{name} describes a sound ('{w}'); write behaviour")
            for c in (o.get("check") or {}):
                if c not in known:
                    bad.append(f"voices.yaml: {axis}.{name} has an unknown check '{c}'")
            if '"' in text:
                bad.append(f"voices.yaml: {axis}.{name} holds words to say; describe behaviour")
    return bad

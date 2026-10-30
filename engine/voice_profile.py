"""Who a hire is when they speak: their people, the culture that raised them, how well they speak Common, how strongly their culture shows,
and how they show what they feel. Rolled once (data/rules/speech.yaml), kept on the hire as member["speech"].

Nothing here is handed to the model whole. Each reply, compile() picks a few concrete instructions for this moment: now and then a line of
their culture's way of talking (by how strongly it shows in them), now and then their first tongue showing through (by fluency), the one way
they show the feeling the engine knows they have right now, and the one way they show warmth or irritation toward whoever they are talking
to. The engine rolls the dice; the model never sees the words "occasional" or "rare", only what applies this time."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "speech.yaml").read_text(encoding="utf-8"))


def _pick(weights: dict, rng: random.Random):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def roll_people(rng: random.Random) -> str:
    return _pick(S["hire_peoples"], rng)


def roll(rng: random.Random, people: str, culture: str = "", fluency: str = "") -> dict:
    """A speech profile for someone of this people (the culture and fluency may be fixed by the caller)."""
    culture = culture or _pick(S["peoples"].get(people, S["peoples"]["human"]), rng)
    tongue = S["cultures"][culture].get("tongue", "")
    fluency = fluency or (_pick(S["fluency"]["weights"], rng) if tongue else "native")
    return {"people": people, "culture": culture, "fluency": fluency, "strength": _pick(S["strength"]["weights"], rng),
            "background": roll_background(rng, culture),
            "tells": {e: rng.choice(opts) for e, opts in S["tells"].items()},
            "expression": {k: rng.choice(opts) for k, opts in S["expression"].items()}}


def resident_culture(people: str, region: str, rng: random.Random) -> str:
    """(f347) The culture a resident of this people was raised in, in a town of this region: their people's weight for each culture plus
    regions_pull times the region's weight for it. A culture the people is never raised in stays impossible; a region not listed leaves
    the people's weights alone."""
    pw = S["peoples"].get(people, S["peoples"]["human"])
    rw = S.get("regions", {}).get(region)
    if not rw:
        return _pick(pw, rng)
    pull = S.get("regions_pull", 2)
    return _pick({c: w + pull * rw.get(c, 0) for c, w in pw.items()}, rng)


def ensure_npc(npc, rng: random.Random, region: str = "", taken: list[dict] | tuple = ()) -> dict:
    """(f347) Every townsperson spoken to has a speech profile, rolled once from their people and their town's region and kept on the record
    (npc.speech); an older save's person gets one the first time they are spoken to. (f350) And a voice kit, drawn to differ from `taken`,
    the kits of the rest of their town (engine/voices.py)."""
    from engine import voices
    if not npc.speech:
        npc.speech = roll(rng, npc.people or "human", resident_culture(npc.people or "human", region, rng))
        npc.speech["background"] = ""                  # a townsperson's family is not written here; their profile and concern already say who they are
    voices.ensure(npc.speech, rng, taken)
    return npc.speech


def resident_lines(npc, rng: random.Random, toward: str = "the stranger") -> tuple[str, list[str], list[str]]:
    """(f347) What a townsperson's reply is told about how they talk: the plain fact of their people and tongue (who), this reply's
    instructions (how their regard shows, and at most one feature of their culture on the culture budget), and any material offered to be
    said as it is (a saying). The same engine as a hire's, on a record instead of a party row."""
    from engine import voices
    if (npc.speech or {}).get("own_voice"):                         # (f374) written by hand: their voice and lines are in the prompt already
        return "", [], []
    member = {"id": npc.id, "name": npc.name, "speech": npc.speech, "said": list(npc.said), "people": npc.people}
    relation = relation_kind(score=getattr(npc, "trust", 50) - 50)
    feature = culture_feature(member, rng)
    lines = voices.lines(voices.kit_of(npc.speech)) + ([accent(member)] if accent(member) else []) \
        + compile(member, rng, relation=relation, toward=toward, budget=2, feature=feature)   # (f350) the kit first: it is the voice; (f410) the accent always
    return who(member), lines, material_for_feature(member, feature)


def roll_background(rng: random.Random, culture: str) -> str:
    """Who their family were, apart from where: the place only shifts the odds."""
    mult = S.get("culture_backgrounds", {}).get(culture, {})
    weights = {b: spec["weight"] * mult.get(b, 1.0) for b, spec in S.get("backgrounds", {}).items()}
    return _pick({b: w for b, w in weights.items() if w > 0}, rng) if weights else ""


def family(member: dict) -> str:
    sp = member.get("speech") or {}
    return S.get("backgrounds", {}).get(sp.get("background", ""), {}).get("family", "")


def ensure(member: dict, rng: random.Random, taken: list[dict] | tuple = ()) -> dict:
    """Every hire has a profile. An old save's hire, or one whose voice was 'English is not their first language', gets one that agrees
    with what is already true of them: their old tongue's culture, or the heartland if they already have a past of their own. (f350) And
    a voice kit, drawn to differ from `taken`, the kits of the rest of the party."""
    from engine import voices
    if member.get("speech"):
        voices.ensure(member["speech"], rng, taken)
        return member["speech"]
    q = member.get("quirks") or {}
    old_tongue = q.get("tongue", "") if q.get("voice") == "second_tongue" else ""
    culture = next((c for c, spec in S["cultures"].items() if old_tongue and spec.get("tongue") == old_tongue), "")
    if old_tongue:
        q["voice"] = "plain"                              # the tongue is the profile's now, not a voice quirk
    elif member.get("details") or member.get("canon"):
        culture = "heartland"
    member["speech"] = roll(rng, member.get("people") or "human", culture, "learner" if old_tongue else "")
    if member.get("details"):                             # their life is already written; a family trade rolled now could contradict it
        member["speech"]["background"] = ""
    member.setdefault("people", member["speech"]["people"])
    voices.ensure(member["speech"], rng, taken)
    return member["speech"]


def culture(member: dict) -> dict:
    sp = member.get("speech") or {}
    return S["cultures"].get(sp.get("culture", ""), {})


def tongue_of(member: dict) -> dict:
    """Their first tongue, if it is not Common: home, habits (how it shows through) and words; with their culture's sayings."""
    from engine import quirks
    sp = member.get("speech") or {}
    c = culture(member)
    tid = c.get("tongue", "")
    if not tid:
        old = (member.get("quirks") or {}).get("tongue", "") if not sp else ""
        return dict(quirks.Q["tongues"].get(old, {}))
    t = dict(quirks.Q["tongues"].get(tid) or S["tongues"].get(tid) or {})
    t["sayings"] = list(c.get("sayings", []))
    return t


def sayings(member: dict) -> list[str]:
    return list(culture(member).get("sayings", []))


def who(member: dict) -> str:
    """One plain line of fact, in every reply: their people and how they speak Common. Where they were raised and who their family were are
    records (origin_records), carried only when the moment touches them."""
    sp = member.get("speech") or {}
    if not sp:
        return ""
    people = sp.get("people", "human").replace("_", "-")
    c = culture(member)
    line = f"{'An' if people[0] in 'aeiou' else 'A'} {people}"
    if c.get("tongue") and sp.get("fluency") != "native":
        line += (f"; Common is their second language, {'spoken fluently' if sp.get('fluency') == 'fluent' else 'still being learned'}: "
                 "they speak it plainly, in normal word order, and most of what they say is fully correct")
    elif c.get("tongue"):
        line += "; they grew up speaking Common and their home tongue both"
    return line + "."


def origin_records(member: dict) -> list[dict]:
    """Where they were raised and who their family were, as records for the scene builder (engine/context.py)."""
    out = []
    home = culture(member).get("home", "")
    if home:
        out.append({"kind": "origin", "text": f"Raised in {home}."})
    fam = family(member)
    if fam:
        out.append({"kind": "origin", "text": f"Their family were {fam}."})
    return out


def regard_shows(rng: random.Random, emotion: str = "") -> bool:
    """Whether how they feel toward the other shows in this reply: now and then, more often when the moment is charged."""
    R = S["regard"]
    return rng.random() < (R["emotional"] if emotion else R["show"])


def emotion_for(situation_kind: str) -> str:
    return S["emotions"].get(situation_kind or "", "")


def relation_kind(score: int | None = None, bond_tier: str = "") -> str:
    """Toward whom they are speaking: warmth, irritation, or nothing in particular."""
    if score is not None:
        if score >= S["relation_affection"]:
            return "affection"
        if score <= -S["relation_affection"]:
            return "irritation"
        return ""
    return {"trusted": "affection", "devoted": "affection", "cold": "irritation"}.get(bond_tier, "")


def culture_feature(member: dict, rng: random.Random) -> tuple[str, object]:
    """The culture budget: ('', None) for most replies; otherwise exactly one feature of their culture for this reply - an instruction
    ('dialect', 'transfer', 'imagery': the text) or something to say ('saying': the saying; 'word': (word, meaning))."""
    sp = member.get("speech") or {}
    if not sp:
        return "", None
    C = S["culture"]
    if rng.random() >= C["show"].get(sp.get("strength", "moderate"), 0.4):
        return "", None
    c = culture(member)
    t = tongue_of(member)
    said = member.get("said", [])
    lately = " ".join(said[-4:]).lower()
    W = C["weights"]
    opts: list[tuple[float, str, object]] = []
    if c.get("dialect"):
        opts.append((W["dialect"], "dialect", rng.choice(c["dialect"])))
    says = [x for x in c.get("sayings", []) if x.lower()[:24] not in lately]
    if says and (sp.get("saying_at") is None or len(said) - sp["saying_at"] >= S.get("saying_gap", 12)):
        opts.append((W["saying"], "saying", rng.choice(says)))
    n = len(said)
    if c.get("imagery") and (sp.get("imagery_at") is None or n - sp["imagery_at"] >= S.get("imagery_gap", 6)):
        opts.append((W["imagery"], "imagery", rng.choice(c["imagery"])))
    words = [(w, t["words"][w]) for w in t.get("offer", []) if w in t.get("words", {}) and w not in lately]
    if words and W["word"] > 0 and (sp.get("word_at") is None or n - sp["word_at"] >= S.get("word_gap", 8)):
        opts.append((W["word"], "word", rng.choice(words)))
    if not opts:
        return "", None
    _, kind, payload = rng.choices(opts, weights=[o[0] for o in opts])[0]
    if kind == "imagery":
        sp["imagery_at"] = n
    if kind == "saying":
        sp["saying_at"] = n
    if kind == "word":
        sp["word_at"] = n
    return kind, payload


def accent(member: dict) -> str:
    """(f410) How their Common sounds, in every reply: an accent is how someone talks, not a flourish rolled for some replies. A smith
    whose first tongue puts the verb last said 'Hammer in hand, work to finish I have', and his next reply had no trace of it."""
    sp = member.get("speech") or {}
    t = tongue_of(member)
    fl = sp.get("fluency", "native")
    if not t or fl == "native" or not t.get("habits"):
        return ""
    if fl == "learner":
        return (f"Their Common, in every line and the same each time (it is how they talk, not a flourish): {t['habits']}. "
                "Never broken, never comic.")
    return f"Their Common is good, with a light touch of home in most lines, the same each time: {t['habits']}. Never broken, never comic."


def tell_for(member: dict, emotion: str) -> str:
    """How they show a feeling that was added after they were rolled: chosen from their id, so it is the same for them every time, and
    kept on them."""
    opts = S["tells"].get(emotion or "")
    sp = member.get("speech")
    if not opts or not isinstance(sp, dict):
        return ""
    t = random.Random(f"{member.get('id', member.get('name', ''))}:tell:{emotion}").choice(opts)
    sp.setdefault("tells", {})[emotion] = t
    return t


def compile(member: dict, rng: random.Random, emotion: str = "", relation: str = "", toward: str = "", budget: int = 3,
            feature: tuple[str, object] = ("", None)) -> list[str]:
    """The few instructions about how they speak that apply to this one reply, at most `budget` of them, by priority: how they show what
    they feel right now, how they are toward whoever they are talking to (now and then: regard_shows), and then this reply's one feature of their culture, if the culture
    budget gave it one (culture_feature). A saying or a home word is offered as material, not here."""
    sp = member.get("speech") or {}
    if not sp or budget <= 0:
        return []
    out: list[str] = []
    tell = (sp.get("tells") or {}).get(emotion, "") or tell_for(member, emotion)
    if tell:
        out.append(f"Right now they are {emotion}, and with them it shows like this: {tell}.")
    expr = (sp.get("expression") or {}).get(relation, "")
    if expr and regard_shows(rng, emotion):
        out.append(f"Toward {toward or 'the one they are talking to'}, their {relation} shows like this: {expr}.")
    kind, payload = feature
    c = culture(member)
    if kind == "dialect":
        out.append(f"Raised in {c.get('home', '')}, they have its way of talking: " + _lower(str(payload)))
    elif kind == "transfer":
        out.append(f"This time, home shows through in their Common: {payload}; never broken, never comic.")
    elif kind == "imagery":
        out.append(f"Only if this reply naturally calls for a comparison, it may borrow from {payload}; a turn of phrase, never the subject "
                   "of what they say.")
    return out[:budget]


def material_for_feature(member: dict, feature: tuple[str, object]) -> list[str]:
    """This reply's culture feature, when it is something to say."""
    kind, payload = feature
    if kind == "saying":
        return [f"a saying from home{', put word for word into Common' if tongue_of(member) else ''}, if it fits: '{payload}'"]
    if kind == "word":
        w, mean = payload
        return [f"a word of their home tongue, said aloud for feeling, if it fits: '{w}' ({mean})"]
    return []


def _lower(line: str) -> str:
    return line[:1].lower() + line[1:]




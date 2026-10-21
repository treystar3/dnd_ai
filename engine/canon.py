"""What a character has said about themselves becomes true.

The engine does not trust a speaker to report its own inventions (a small model leaves an optional list empty). Instead, when a conversation
is about the speaker - their past, their people, where they come from, why they do what they do, judged by meaning - one small extraction
call reads what they just said and pulls out any new, specific facts: about themselves (kept as their canon, offered back when the moment is
about them, so the next answer agrees with the last) or about the world (kept as what that character believes: people can be wrong, and a
model must not rewrite the world through a hire's mouth).

A new claim close in meaning to something already true of them is checked once for a contradiction; a contradiction sends the line back
to be written again, and if it comes back contradicting still, the line stands and the claim is not kept."""
from __future__ import annotations

import re

import config

MAX_CANON = 60
MAX_BELIEFS = 30
MAX_WORDS = 30
EMPTY = {"", "none", "n/a", "nothing", "no", "null", "-"}


def clean(claims) -> list[str]:
    out = []
    for c in claims or []:
        c = " ".join(str(c).split()).strip('"“”')
        if c.lower().strip(".") in EMPTY or len(c.split()) > MAX_WORDS or len(c.split()) < 3:
            continue
        out.append(c if c.endswith((".", "!", "?")) else c + ".")
    return out[:2]


def given(member: dict) -> list[str]:
    """What the game gave them to begin with, as they would say it: their work, where they are from, what drives them. A claim that only
    says this again is not new."""
    from engine import party as rules, quirks
    out = [f"I am a hired {member.get('role', 'adventurer')}, {member.get('blurb', '')}.".replace(", .", ".")]
    from engine import voice_profile
    home = voice_profile.culture(member).get("home") or quirks.tongue(member).get("home")
    if home:
        out.append(f"I come from {home}" + (", and its tongue was my first." if quirks.tongue(member) else "."))
    fam = voice_profile.family(member)
    if fam:
        out.append(f"My family were {fam}.")
    if member.get("people") and member.get("people") != "human":
        out.append(f"I am {'an' if member['people'][0] in 'aeiou' else 'a'} {member['people'].replace('_', '-')}.")
    mt = rules.P["motives"].get(member.get("motive", ""), "")
    if mt:
        out.append(f"Underneath it all, I {mt.replace('wants', 'want').replace('keeps', 'keep').replace('works', 'work').replace('is ', 'am ', 1)}.")
    return out


def _restates(c: str, facts: list[str]) -> bool:
    if not facts:
        return False
    sims = _sims(c, facts)
    if sims is not None:
        return max(sims) >= config.SIM_RESTATE
    import re as _re
    w = lambda t: set(_re.findall(r"[a-z]{4,}", t.lower()))
    cw = w(c)
    return any(cw and len(cw & w(f)) / len(cw) >= 0.6 for f in facts)


FIRST = [(r"\bthey are\b", "I am"), (r"\bthey were\b", "I was"), (r"\bthey have\b", "I have"), (r"\bthemselves\b", "myself"),
         (r"\btheir\b", "my"), (r"\bthem\b", "me"), (r"\bthey\b", "I"), (r"\bshe is\b", "I am"), (r"\bshe was\b", "I was"),
         (r"\bherself\b", "myself"), (r"\bher\b", "my"), (r"\bshe\b", "I")]


def first_person(text: str) -> str:
    """A detail written about them ("They grew up by the sea") as they would say it ("I grew up by the sea"), so the two compare cleanly."""
    import re as _re
    t = text
    for a, b in FIRST:
        t = _re.sub(a, b, t, flags=_re.I)
    return t[:1].upper() + t[1:]


def known(member: dict, details: list[str] | None = None) -> list[str]:
    """Everything already true of them, in their own voice: the details written at hire (or authored, for Maren), the secrets they have
    told, and what they have said since."""
    base = list(member.get("details", []) if details is None else details)
    told = [m["text"].split(": ", 1)[-1] for m in member.get("memories", []) if m.get("text", "").startswith("I told them something I tell nobody")]
    return [first_person(d) for d in base] + told + [c["text"] for c in member.get("canon", []) + member.get("traits", [])]


def _sims(text: str, items: list[str]) -> list[float] | None:
    if not items:
        return []
    from llm import embed
    return embed.whole(text, items)


def judge(claim: str, facts: list[str]) -> tuple[str, str]:
    """('same' | 'contradicts' | 'new', the fact it repeats or contradicts). One small call; if the model cannot be asked, it is new."""
    from llm.contracts import CanonCheck
    from llm.gateway import generate, LLMError
    listed = "\n".join(f"{i + 1}. {f}" for i, f in enumerate(facts))
    try:
        r = generate("canon_check", "You compare a new statement a person makes about themselves with what is already true of them. "
                     "same: it says the same fact again, in other words or with a little more detail that changes nothing. contradicts: it "
                     "and a listed fact cannot both be true. new: it adds something that is not already there and fits with it. Respond only "
                     "with JSON matching the schema: {\"verdict\": \"new\", \"which\": 0}.",
                     f"ALREADY TRUE OF THEM:\n{listed}\n\nNEW STATEMENT: {claim}", CanonCheck, temperature=0.1, retries=1, max_tokens=40)
    except LLMError:
        return "new", ""
    hit = facts[r.which - 1] if 1 <= r.which <= len(facts) else (facts[0] if facts else "")
    return r.verdict, hit if r.verdict != "new" else ""


def vet(member: dict, claims: list[str], details: list[str] | None = None, given_facts: list[str] | None = None,
        who: str = "", kept_as: str = "backstory") -> tuple[list[str], list[tuple[str, str]]]:
    """(new claims to keep, [(claim, the fact it contradicts)]). Repeats of what is already known are dropped quietly."""
    facts = known(member, details)
    base = given(member) if given_facts is None else given_facts
    keep, bad = [], []
    who = who or member.get("name", "")
    for c in claims:
        if _restates(c, base):                                       # only what they were given to begin with, said again
            _event(who, c, "given")
            continue
        sims = _sims(c, facts)
        if sims is None:                                            # no helper model: word for word known is a repeat; shared words are near
            if c.lower() in {f.lower() for f in facts}:
                _event(who, c, "same")
                continue
            from engine import relevance
            near = relevance.pick(c, facts, k=3)
        elif sims and max(sims) >= config.SIM_RESTATE:                 # the same fact in other words is not new
            _event(who, c, "same", facts[sims.index(max(sims))])
            continue
        else:
            near = [f for v, f in sorted(zip(sims, facts), key=lambda x: -x[0]) if v >= config.SIM_CANON][:3]
        verdict, hit = judge(c, near) if near else ("new", "")
        _event(who, c, kept_as if verdict == "new" else verdict, hit)
        if verdict == "contradicts":
            bad.append((c, hit))
        elif verdict == "new":
            keep.append(c)
    return keep, bad


# What someone says about themselves falls in one of these. Only backstory and traits are canon - checked for contradictions and true for
# good. The rest are kept as what they are: what they own, what they mean to do, what they have promised, what is true of them today - each
# for as long as such a thing usually stays true, and each offered back under its own name, so a passing remark never becomes who they are.
BUCKETS = {
    "backstory":  {"key": "canon",       "label": "Your past (true; you said it before)",      "days": None, "cap": 60, "canon": True},
    "trait":      {"key": "traits",      "label": "True of you (you said it before)",           "days": None, "cap": 20, "canon": True},
    "possession": {"key": "possessions", "label": "Something you own",                          "days": 10,   "cap": 8},
    "intention":  {"key": "intentions",  "label": "Something you mean to do",                   "days": 30,   "cap": 6},
    "commitment": {"key": "commitments", "label": "Something you have promised, or owe",        "days": 60,   "cap": 6},
    "moment":     {"key": "state_now",   "label": "True of you for now (you said it today)",    "days": 1,    "cap": 6},
    "situation":  {"key": "situations",  "label": "True of you for a while (an ongoing situation)", "days": 14, "cap": 6},
    "opinion":    {"key": "opinions",    "label": "What you have said of {about}",              "days": None, "cap": 16},
}
STATE_DAYS = BUCKETS["moment"]["days"]


def _fresh(x: dict, days: int | None, day: int | None) -> bool:
    return days is None or day is None or day - x.get("day", day) <= days


def keep_light(member: dict, bucket: str, facts: list[str], day: int, who: str = "", weights: dict | None = None) -> None:
    """A fact that is not canon: kept in its own bucket for as long as such things stay true. The same thing said again (by meaning) only
    refreshes it."""
    B = BUCKETS[bucket]
    items = [x for x in member.get(B["key"], []) if _fresh(x, B["days"], day)]
    for f in clean(facts):
        texts = [x["text"] for x in items]
        sims = _sims(f, texts) if texts else []
        same = (max(sims) >= config.SIM_RESTATE if sims else False) if sims is not None else f.lower() in {t.lower() for t in texts}
        if same:
            hit = items[sims.index(max(sims))] if sims else next(x for x in items if x["text"].lower() == f.lower())
            hit["day"] = day
            _event(who or member.get("name", ""), f, f"{bucket} (again)")
            continue
        items.append({"text": f, "day": day, "gravity": (weights or {}).get(_norm(f), "personal")})
        _event(who or member.get("name", ""), f, bucket)
    member[B["key"]] = items[-B["cap"]:]


JOURNAL = None                # bound by the scene: fn(kind, actor, target, text, data) -> None (storage event_log); None in tools without a game


def journal(kind: str, actor: str = "", target: str = "", text: str = "", **data) -> None:
    """An authoritative fact, for the campaign's event journal (storage.campaign.journal). Nothing when no game is bound."""
    if JOURNAL is not None:
        try:
            JOURNAL(kind, actor, target, text, data)
        except Exception:
            pass


IDS: dict[str, str] = {}      # name -> stable id for the people a game knows (set by the scene: party members, Maren, 'the player'); names are display


def about_id(name: str) -> str:
    """The stable id behind a name, when the game knows the person; else the name itself (someone outside the party, by name only)."""
    if not name:
        return ""
    if name == "the player":
        return "player"
    low = name.lower()
    for n, i in IDS.items():
        if n.lower() == low or n.split()[0].lower() == low:
            return i
    return name


def keep_opinions(member: dict, said: list[tuple[str, str]], day: int, who: str = "", weights: dict | None = None) -> None:
    """What they have said of a particular person - the player, a companion, someone they know: kept under that person's stable id (the
    name only for display), the newest kept; the same thing said again of the same person only refreshes it."""
    B = BUCKETS["opinion"]
    items = list(member.get(B["key"], []))
    for about, f in said:
        f = (clean([f]) or [""])[0]
        if not f:
            continue
        aid = about_id(about)
        mine = [x for x in items if x.get("about_id", x.get("about")) == aid]
        sims = _sims(f, [x["text"] for x in mine]) if mine else []
        same = (max(sims) >= config.SIM_RESTATE if sims else False) if sims is not None else f.lower() in {x["text"].lower() for x in mine}
        if same:
            hit = mine[sims.index(max(sims))] if sims else next(x for x in mine if x["text"].lower() == f.lower())
            hit["day"] = day
            _event(who or member.get("name", ""), f"({about}) {f}", "opinion (again)")
            continue
        items.append({"about_id": aid, "about": about, "text": f, "day": day, "gravity": (weights or {}).get(_norm(f), "personal")})
        _event(who or member.get("name", ""), f"({about}) {f}", "opinion")
    member[B["key"]] = items[-B["cap"]:]


def opinions_of(member: dict, whom: str) -> list[str]:
    """What this person has said of someone: by stable id ('player', a member id), or by name for someone the game knows only by name."""
    aid = about_id(whom)
    return [x["text"] for x in member.get("opinions", []) if x.get("about_id", x.get("about")) in (aid, whom)]


def keep_now(member: dict, facts: list[str], day: int, who: str = "") -> None:
    keep_light(member, "moment", facts, day, who)


def keep(member: dict, about_me, about_world, day: int, details: list[str] | None = None, given_facts: list[str] | None = None,
         who: str = "", now: list[str] | None = None, buckets: dict | None = None) -> list[tuple[str, str]]:
    """Check what they just said and keep it, each in its bucket - all of it, or, if any of it contradicts what is true of them (backstory
    and traits), none of it. The contradictions found, for a second try. about_me is backstory; now is the moment."""
    p = review(member, about_me, about_world, day, details, given_facts, who, now, buckets)
    if not p.bad:
        p.commit()
    return p.bad


def _keep_into(member: dict, about_me, about_world, day: int, details, given_facts, who, now, buckets) -> list[tuple[str, str]]:
    buckets = dict(buckets or {})
    if now:
        buckets["moment"] = list(buckets.get("moment", [])) + list(now)
    for b in ("possession", "intention", "commitment", "moment", "situation"):
        if buckets.get(b):
            keep_light(member, b, buckets[b], day, who, buckets.get(WEIGHTS))
    if buckets.get("opinion"):
        keep_opinions(member, buckets["opinion"], day, who, buckets.get(WEIGHTS))
    bad = []
    for b in ("backstory", "trait"):
        claims = clean(list(about_me if b == "backstory" else []) + list(buckets.get(b, [])))
        if not claims:
            continue
        new, wrong = vet(member, claims, details, given_facts, who, kept_as=b)
        bad += wrong
        key = BUCKETS[b]["key"]
        for c in new:
            member.setdefault(key, []).append({"text": c, "day": day, "gravity": (buckets.get(WEIGHTS) or {}).get(_norm(c), "personal")})
        del member.setdefault(key, [])[:-BUCKETS[b]["cap"]]
    world = clean(about_world) + clean(buckets.get("world", []))
    have = {x["text"].lower() for x in member.get("beliefs", [])}
    for c in world:
        if c.lower() not in have:
            member.setdefault("beliefs", []).append({"text": c, "day": day})
            _event(who or member.get("name", ""), c, "belief")
    del member.setdefault("beliefs", [])[:-MAX_BELIEFS]
    return bad


HELD = tuple(B["key"] for B in BUCKETS.values()) + ("beliefs",)


class Pending:
    """What one draft would add to a person, worked out but not yet kept. A draft that contradicts what is true of them is written again,
    and nothing from it - not even the parts that were fine - is kept: the player never heard it. commit() keeps an accepted one."""
    def __init__(self, member: dict, after: dict, bad: list[tuple[str, str]], events: list[dict]):
        self.member, self.after, self.bad, self.events = member, after, bad, events

    def commit(self) -> None:
        for k, v in self.after.items():
            if v or k in self.member:
                self.member[k] = v
        EVENTS.extend(self.events)
        del EVENTS[:-200]


def review(member: dict, about_me, about_world, day: int, details: list[str] | None = None, given_facts: list[str] | None = None,
           who: str = "", now: list[str] | None = None, buckets: dict | None = None) -> Pending:
    """keep(), worked out on a copy: nothing about the person changes until the result is committed."""
    import copy
    shadow = {k: copy.deepcopy(member[k]) for k in HELD if k in member}
    shadow.update({k: v for k, v in member.items() if k not in HELD})     # read-only context (details, memories, name...) as it is
    _SINK.append([])
    try:
        bad = _keep_into(shadow, about_me, about_world, day, details, given_facts, who, now, buckets)
    finally:
        events = _SINK.pop()
    return Pending(member, {k: shadow.get(k, []) for k in HELD}, bad, events)


def records(member: dict, day: int | None = None) -> list[dict]:
    """What they have said about themselves, each under its own name, for the scene builder (engine/context.py)."""
    out = []
    for b, B in BUCKETS.items():
        if b == "opinion":
            out += [{"kind": "opinion", "about": x.get("about", ""), "text": f"{B['label'].format(about=x.get('about', 'someone'))}: {x['text']}",
                     "gravity": x.get("gravity", "light")} for x in member.get(B["key"], [])]
            continue
        out += [{"kind": "canon" if B.get("canon") else "state", "text": f"{B['label']}: {x['text']}", "gravity": x.get("gravity", "personal")}
                for x in member.get(B["key"], []) if _fresh(x, B["days"], day)]
    out += [{"kind": "belief", "text": "You believe: " + x["text"], "gravity": "light"} for x in member.get("beliefs", [])]
    return out


def said_about_self(member: dict) -> list[str]:
    """Everything they have said about themselves that is still held, for the extractor's ALREADY KNOWN."""
    return [x["text"] for B in BUCKETS.values() for x in member.get(B["key"], [])]


def conflict_rule(bad: list[tuple[str, str]]) -> str:
    return "ALREADY TRUE OF YOU, NEVER CONTRADICT IT: " + " ".join(dict.fromkeys(f for _, f in bad))


ABOUT_THEM = ("their own past, family and people (father, mother, brother, sister, children), where they grew up or come from, how they came to this work, why they do what they do, "
              "a person or a place in their life, something that happened to them")


def worth_reading(prompted: str) -> bool:
    """Was this moment about the speaker - what the player asked, or what brought the talk up - so that what they said may hold something
    new about them? Judged on what prompted the reply, not on the reply (anyone may mention their past in passing; reading every line would
    cost a call each). By meaning, like every topic."""
    from engine import relevance
    return bool((prompted or "").strip()) and bool(relevance.pick(prompted, [ABOUT_THEM], 1, floor=config.SIM_TOPIC))


EVENTS: list[dict] = []          # what happened to each claim: kept, same, contradicts, given (the live check reads this)


_SINK: list[list[dict]] = []    # while a draft is under review, its events wait here, and reach EVENTS only if it is committed


def _event(who: str, claim: str, verdict: str, against: str = "") -> None:
    e = {"who": who, "claim": claim, "verdict": verdict, "against": against}
    if _SINK:
        _SINK[-1].append(e)
        return
    EVENTS.append(e)
    del EVENTS[:-200]


EXTRACT_SYSTEM = ("You read lines a person in a fantasy world just said and list any NEW, CONCRETE facts they stated as true about "
                  "themselves or about the world. A fact counts only if it names something particular. Put each in one kind:\n"
                  "  backstory: their past - a person in their life, where they lived, something that happened to them, how they came to "
                  "this work.\n"
                  "  trait: something lastingly true of them now - a fear, a skill, a taste, a thing they cannot do, a scar.\n"
                  "  possession: something they own or carry.\n"
                  "  intention: something they mean to do, soon or someday.\n"
                  "  commitment: something they have promised, or owe, to someone.\n"
                  "  moment: true only of this moment or this day - what they are eating, paying for, feeling in their legs, doing now.\n"
                  "  world: a fact about the world beyond the moment (a place, a people, a custom).\n"
                  "Give each a weight, how heavy it is to talk about: light (anyone might mention it over a meal - a food, a habit, a skill), "
                  "personal (their own life - family, a rival, money owed, a promise), heavy (a death, a fear, a shame, a regret).\n"
                  "Say whom each claim is about, as subject: self (the speaker, of themselves), player (the one they are talking to), world "
                  "(a place, a people, a custom, people in general), or the name of someone else. Only a claim the speaker makes of themselves is "
                  "subject self: 'most newcomers end up with a limp' is about the world, never 'I have a limp'; 'Bram does the heavy lifting' "
                  "is about Bram. What the speaker thinks or feels about a particular person ('I'd trust Isel's hands on a wound over anyone's') "
                  "is about that person, never a trait of the speaker.\n"
                  "Say how long each stays true, as lasts: years (their past, their family, a lasting trait, a settled conviction), while (weeks: "
                  "a plan, a debt, something they own, a situation they are in), now (only here and today: where they are, what they are doing, "
                  "how they feel this hour). And common: true when it is something anyone would know (the guild exists, winter is cold).\n"
                  "A claim of self in the first person, the others plainly, one short sentence each. Leave out general statements about their character "
                  "or values (a person saying they like to keep moving has stated no fact), passing feelings, jokes, figures of speech, guesses, and "
                  "anything listed as ALREADY KNOWN. Most lines hold nothing new: then return an empty list. Respond only with JSON matching the "
                  "schema: {\"facts\": [{\"speaker\": \"name\", \"subject\": \"self\", \"kind\": \"backstory\", \"claim\": \"...\", "
                  "\"weight\": \"personal\", \"lasts\": \"years\", \"common\": false}]}.")


def extract(lines: list[tuple[str, str]], known_by: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    """{speaker: {kind: [facts]}} from what was just said (kinds: BUCKETS, and 'world'). One call for all the lines; nothing if it fails."""
    lines = [(w, t) for w, t in lines if t and t.strip()]
    if not lines:
        return {}
    from llm.contracts import Extracted
    from llm.gateway import generate, LLMError
    req = ("ALREADY KNOWN:\n" + "\n".join(f"  {n}: " + (" | ".join(k[-12:]) or "(nothing)") for n, k in known_by.items()) +
           "\n\nWHAT WAS JUST SAID:\n" + "\n".join(f"  {w}: {' '.join(t.split())}" for w, t in lines))
    try:
        r = generate("canon_extract", EXTRACT_SYSTEM, req, Extracted, temperature=0.1, retries=1, max_tokens=280,
                     validation_context={"speakers": list(known_by)})
    except LLMError:
        return {}
    out: dict[str, dict] = {}
    said_by = {}
    for w, t in lines:
        said_by.setdefault(w, []).append(t)
    others_named = sorted({f.subject for f in r.facts if f.subject not in ("self", "player", "world")})
    for f in r.facts:
        about, kind = route(f, [n for n in known_by if n != f.speaker] + others_named)
        if kind is None:
            _event(f.speaker, f.text, about)                        # common knowledge, or a fact of the scene the engine already holds: dropped
            continue
        if kind == "opinion":                                       # what they think of a particular person: kept under that person's name
            out.setdefault(f.speaker, {}).setdefault("opinion", []).append((about, f.text))
            out[f.speaker].setdefault(WEIGHTS, {})[_norm(f.text)] = f.weight
            continue
        if kind != "world" and not owned(f.text, " ".join(said_by.get(f.speaker, [])), [n for n in known_by if n != f.speaker] + others_named):
            _event(f.speaker, f.text, "not about them")             # read as theirs, but not said of themselves: dropped
            continue
        out.setdefault(f.speaker, {}).setdefault(kind, []).append(f.text)
        out[f.speaker].setdefault(WEIGHTS, {})[_norm(f.text)] = f.weight        # how heavy each is to talk about (engine/gravity.py)
    return out


def route(f, others: list[str]) -> tuple[str, str | None]:
    """Where one extracted claim belongs, decided by the engine from what the extractor said of it: (whom it is about, the bucket), or
    (why it is dropped, None).
      common knowledge                       -> dropped
      about the world, true only now          -> dropped: where they are, who is here and the hour are the engine's, not a belief
      about the player or someone else        -> an opinion, under that person's name
      of themselves, true only now            -> today (moment)
      of themselves, true for a while         -> an ongoing situation, if it was read as their past or a trait; a plan, debt or thing
                                                 owned keeps its own bucket and life
      a 'trait' that names someone else       -> an opinion of that one: a feeling about a person is not who the speaker is"""
    if f.common:
        return "common knowledge", None
    if f.subject == "world" or f.kind == "world":
        return ("a fact of the scene, not a belief", None) if f.lasts == "now" else ("world", "world")
    if f.subject != "self":
        return ("the player" if f.subject == "player" else f.subject), "opinion"
    if f.kind == "trait":
        for n in others:
            if re.search(rf"\b{re.escape(n.split()[0])}\b", f.text) if n.split() else False:
                return n, "opinion"
    if f.lasts == "now":
        return "self", "moment"
    if f.lasts == "while" and f.kind in ("backstory", "trait"):
        return "self", "situation"
    return "self", f.kind


FIRST_PERSON = re.compile(r"\b(I|me|my|mine|myself|I'm|I've|I'd|I'll)\b", re.I)


def owned(claim: str, said: str, others: list[str] | None = None) -> bool:
    """A check behind the extractor's own subject: a claim marked as the speaker's must be in the first person, and the sentence of theirs
    it comes from (closest in meaning, else most shared words) must not be one about someone else present - 'Bram does the heavy lifting'
    is not Tamsin's - unless they speak of themselves in it too. A sentence that names nobody ('An A rank, earned the slow way') is
    theirs. Generalisations ('most newcomers end up with a limp') are the subject's job: the extractor marks them world."""
    if not FIRST_PERSON.search(claim or ""):
        return False
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join((said or "").split())) if s.strip()]
    if not sentences:
        return False
    from llm import embed
    sims = embed.whole(claim, sentences)
    if sims is not None:
        source = sentences[max(range(len(sentences)), key=lambda i: sims[i])]
    else:
        words = lambda t: set(re.findall(r"[a-z]{3,}", t.lower())) - {"the", "and", "for", "with", "that", "this"}
        source = max(sentences, key=lambda s: len(words(s) & words(claim)))
    if FIRST_PERSON.search(source):
        return True
    names = {p for n in (others or []) for p in n.split() if len(p) > 2}
    return not any(re.search(rf"\b{re.escape(n)}\b", source) for n in names)


WEIGHTS = "_weight"


def _norm(t: str) -> str:
    return " ".join(str(t).lower().split()).strip(" .!?\"\u201c\u201d")


def read(member: dict, name: str, said: str, prompt_text: str, day: int, details: list[str] | None = None,
         given_facts: list[str] | None = None) -> Pending | None:
    """After one speaker's draft: if the moment was about them, what it would add (not kept yet), or None. The caller commits it once the
    line is the one said, or writes the line again if it contradicts what is true of them."""
    if not worth_reading(prompt_text):
        return None
    got = extract([(name, said)], {name: known(member, details) + said_about_self(member)}).get(name)
    if not got:
        return None
    return review(member, [], [], day, details, given_facts, name, buckets=got)


def settle(pending: Pending | None, attempt: int, tries: int = 2) -> str:
    """The one rule for every speaker: a draft that contradicts canon is written again (the returned rule says what is true); the line that
    stands has its claims kept - minus any that still contradict, on the last try. '' means keep this line."""
    if pending is None:
        return ""
    if pending.bad and attempt < tries - 1:
        return conflict_rule(pending.bad)
    pending.commit()
    return ""
